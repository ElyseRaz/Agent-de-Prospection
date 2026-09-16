import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import RawDocumentPayload
from app.collectors.http import CircuitBreaker, InMemoryCounterStore
from app.collectors.registry import get_connector_class
from app.models.source import ProcessingStatus, RawDocument, ScrapeRun, ScrapeRunStatus, Source

log = structlog.get_logger(__name__)


class CollectionError(Exception):
    """Erreur remontee lorsque la collecte d'une source echoue completement."""


@dataclass(slots=True)
class DryRunResult:
    """Resultat d'une collecte en mode dry-run : jamais persiste en base."""

    source_slug: str
    items_fetched: int
    sample: list[dict] = field(default_factory=list)


def compute_content_hash(raw_payload: dict) -> str:
    canonical = json.dumps(raw_payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def run_collection(
    db: AsyncSession,
    source: Source,
    *,
    dry_run: bool = False,
    http_client: httpx.AsyncClient | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    since: datetime | None = None,
    sample_limit: int = 5,
) -> ScrapeRun | DryRunResult:
    """Execute une collecte pour `source` : resout le connecteur via le
    registre, fetch les documents, et les upsert de maniere idempotente dans
    `raw_documents` (cle naturelle source_id + external_id). En dry-run,
    aucune ecriture en base n'est effectuee (ni scrape_run, ni raw_document)."""

    connector_cls = get_connector_class(source.kind)

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=20.0)
    breaker = circuit_breaker or CircuitBreaker(InMemoryCounterStore())

    connector = connector_cls(
        base_url=source.base_url,
        config=source.config,
        http_client=client,
        circuit_breaker=breaker,
    )

    run: ScrapeRun | None = None
    if not dry_run:
        run = ScrapeRun(source_id=source.id, status=ScrapeRunStatus.RUNNING)
        db.add(run)
        await db.flush()

    items_fetched = 0
    items_new = 0
    items_updated = 0
    sample: list[dict] = []

    try:
        async for doc in connector.fetch(since=since):
            items_fetched += 1
            if dry_run:
                if len(sample) < sample_limit:
                    sample.append(doc.raw_payload)
                continue

            assert run is not None
            is_new, is_updated = await _upsert_raw_document(db, source=source, run=run, doc=doc)
            items_new += int(is_new)
            items_updated += int(is_updated)

    except Exception as exc:
        if run is not None:
            run.status = ScrapeRunStatus.FAILED
            run.error_message = str(exc)[:2000]
            run.finished_at = datetime.now(UTC)
            run.items_fetched = items_fetched
            run.items_new = items_new
            run.items_updated = items_updated
            await db.commit()
        log.error("collection_failed", source=source.slug, error=str(exc))
        raise CollectionError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()

    if dry_run:
        log.info("dry_run_completed", source=source.slug, items_fetched=items_fetched)
        return DryRunResult(source_slug=source.slug, items_fetched=items_fetched, sample=sample)

    assert run is not None
    run.status = ScrapeRunStatus.SUCCESS
    run.finished_at = datetime.now(UTC)
    run.items_fetched = items_fetched
    run.items_new = items_new
    run.items_updated = items_updated
    await db.commit()
    await db.refresh(run)
    log.info(
        "collection_completed",
        source=source.slug,
        items_fetched=items_fetched,
        items_new=items_new,
        items_updated=items_updated,
    )
    return run


async def _upsert_raw_document(
    db: AsyncSession, *, source: Source, run: ScrapeRun, doc: RawDocumentPayload
) -> tuple[bool, bool]:
    """Ecrit `doc` de maniere idempotente. Retourne (is_new, is_updated).
    Un contenu identique (meme content_hash) ne declenche aucune ecriture."""

    content_hash = compute_content_hash(doc.raw_payload)

    existing = await db.scalar(
        select(RawDocument).where(
            RawDocument.source_id == source.id, RawDocument.external_id == doc.external_id
        )
    )

    if existing is None:
        stmt = (
            pg_insert(RawDocument)
            .values(
                source_id=source.id,
                run_id=run.id,
                external_id=doc.external_id,
                url=doc.url,
                content_hash=content_hash,
                raw_payload=doc.raw_payload,
                fetched_at=doc.fetched_at,
                processing_status=ProcessingStatus.PENDING,
            )
            .on_conflict_do_nothing(constraint="uq_raw_documents_source_external")
        )
        result = await db.execute(stmt)
        return (result.rowcount or 0) > 0, False

    if existing.content_hash == content_hash:
        return False, False

    existing.content_hash = content_hash
    existing.raw_payload = doc.raw_payload
    existing.url = doc.url
    existing.run_id = run.id
    existing.fetched_at = doc.fetched_at
    existing.processing_status = ProcessingStatus.PENDING
    existing.processed_at = None
    return False, True
