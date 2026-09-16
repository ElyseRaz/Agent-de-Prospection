import asyncio

import httpx
import redis.asyncio as redis_asyncio
import structlog
from celery import Celery
from sqlalchemy import select

from app.collectors.http import CircuitBreaker
from app.collectors.registry import discover_connectors
from app.core.config import get_settings
from app.core.db import create_engine_and_session
from app.embeddings.sentence_transformer_backend import SentenceTransformerEmbeddingBackend
from app.models.source import Source
from app.normalization.llm_extraction import AnthropicJobExtractionBackend
from app.normalization.raw_text.registry import discover_raw_text_extractors
from app.services.backfill import backfill_embeddings_and_dedup
from app.services.collection import DryRunResult, run_collection
from app.services.expiry import mark_expired_jobs
from app.services.normalization import normalize_pending_documents

settings = get_settings()
log = structlog.get_logger(__name__)

celery_app = Celery(
    "remoteradar",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={},
    imports=[],
)

discover_connectors()
discover_raw_text_extractors()

# Modele charge une seule fois au demarrage du worker (processus long-vivant),
# jamais par tache : le chargement (quelques secondes, poids pre-telecharges
# dans l'image Docker) serait sinon repete a chaque appel.
_embedding_backend = SentenceTransformerEmbeddingBackend(model_name=settings.embedding_model_name)


@celery_app.task(name="collection.collect_source")
def collect_source_task(source_slug: str, dry_run: bool = False) -> dict:
    """Declenche une collecte pour la source `source_slug`. Reutilisable pour
    un appel manuel (`celery call`) ou, plus tard, une planification Beat par
    source (cron lu depuis `sources.schedule_cron`)."""
    return asyncio.run(_collect_source_async(source_slug, dry_run))


@celery_app.task(name="normalization.normalize_pending")
def normalize_pending_task(limit: int = 100, source_slug: str | None = None) -> dict:
    """Normalise les raw_documents en attente (statut PENDING) en offres
    canoniques. Reutilisable pour un appel manuel ou une planification Beat
    reguliere (apres chaque collecte, par exemple)."""
    return asyncio.run(_normalize_pending_async(limit, source_slug))


@celery_app.task(name="deduplication.backfill_embeddings")
def backfill_embeddings_task(limit: int = 100) -> dict:
    """Complete embedding/search_tsv/dedup_hash des jobs normalises avant la
    phase 4, sans reappeler le LLM."""
    return asyncio.run(_backfill_embeddings_async(limit))


@celery_app.task(name="expiry.mark_expired_jobs")
def mark_expired_jobs_task(stale_days: int = 14) -> dict:
    """Marque EXPIRED les jobs non reconfirmes depuis `stale_days`."""
    return asyncio.run(_mark_expired_jobs_async(stale_days))


async def _collect_source_async(source_slug: str, dry_run: bool) -> dict:
    engine, session_factory = create_engine_and_session(settings)
    redis_client = redis_asyncio.from_url(settings.redis_url, decode_responses=True)

    try:
        async with session_factory() as db:
            source = await db.scalar(select(Source).where(Source.slug == source_slug))
            if source is None:
                raise LookupError(f"Source introuvable: {source_slug}")

            breaker = CircuitBreaker(redis_client)
            result = await run_collection(db, source, dry_run=dry_run, circuit_breaker=breaker)

        if isinstance(result, DryRunResult):
            return {
                "dry_run": True,
                "source_slug": result.source_slug,
                "items_fetched": result.items_fetched,
            }

        return {
            "dry_run": False,
            "run_id": str(result.id),
            "status": result.status.value,
            "items_fetched": result.items_fetched,
            "items_new": result.items_new,
            "items_updated": result.items_updated,
        }
    finally:
        await redis_client.aclose()
        await engine.dispose()


async def _normalize_pending_async(limit: int, source_slug: str | None) -> dict:
    engine, session_factory = create_engine_and_session(settings)
    backend = AnthropicJobExtractionBackend(model=settings.llm_model)

    async with httpx.AsyncClient(timeout=20.0) as http_client:
        try:
            async with session_factory() as db:
                source_id = None
                if source_slug is not None:
                    source = await db.scalar(select(Source).where(Source.slug == source_slug))
                    if source is None:
                        raise LookupError(f"Source introuvable: {source_slug}")
                    source_id = source.id

                summary = await normalize_pending_documents(
                    db,
                    backend=backend,
                    embedding_backend=_embedding_backend,
                    http_client=http_client,
                    model=settings.llm_model,
                    limit=limit,
                    source_id=source_id,
                )

            return {
                "processed": summary.processed,
                "failed": summary.failed,
                "skipped": summary.skipped,
            }
        finally:
            await engine.dispose()


async def _backfill_embeddings_async(limit: int) -> dict:
    engine, session_factory = create_engine_and_session(settings)
    try:
        async with session_factory() as db:
            summary = await backfill_embeddings_and_dedup(
                db, embedding_backend=_embedding_backend, limit=limit
            )
        return {"embedded": summary.embedded, "skipped": summary.skipped}
    finally:
        await engine.dispose()


async def _mark_expired_jobs_async(stale_days: int) -> dict:
    engine, session_factory = create_engine_and_session(settings)
    try:
        async with session_factory() as db:
            count = await mark_expired_jobs(db, stale_days=stale_days)
        return {"expired": count}
    finally:
        await engine.dispose()
