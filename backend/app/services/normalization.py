import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingBackend
from app.embeddings.text_builder import build_embedding_text
from app.models.job import ContractType, Job, RatePeriod, RemoteType, SeniorityLevel
from app.models.source import ProcessingStatus, RawDocument, Source
from app.normalization.company import get_or_create_company
from app.normalization.html_clean import clean_html
from app.normalization.language import detect_language
from app.normalization.llm_extraction import JobExtractionBackend, extract_job_structured
from app.normalization.prompt_loader import load_prompt
from app.normalization.quality import compute_quality_score
from app.normalization.raw_text.base import RawText
from app.normalization.raw_text.registry import get_raw_text_extractor
from app.normalization.schema import ExtractedJobLLM
from app.normalization.search_index import search_tsv_expression
from app.normalization.skills import upsert_skills_for_job
from app.services.currency import get_rate_to_eur
from app.services.deduplication import compute_dedup_hash, deduplicate_job

log = structlog.get_logger(__name__)

PROMPT_VERSION = "extract_job_v1"


class NormalizationError(Exception):
    """Erreur non recuperable lors de la normalisation d'un raw_document."""


@dataclass(slots=True)
class NormalizationSummary:
    processed: int = 0
    failed: int = 0
    skipped: int = 0


async def normalize_raw_document(
    db: AsyncSession,
    raw_document: RawDocument,
    *,
    source: Source,
    backend: JobExtractionBackend,
    embedding_backend: EmbeddingBackend,
    http_client: httpx.AsyncClient,
    model: str,
    force: bool = False,
) -> Job | None:
    """Transforme un `raw_document` en `Job` canonique. Idempotent : rejouer
    sur un document deja traite et inchange est un no-op (sauf `force=True`,
    utilise pour rejouer apres un bump de prompt_version)."""

    if not force and raw_document.processing_status != ProcessingStatus.PENDING:
        return None

    raw_text_extractor = get_raw_text_extractor(source.kind)
    raw_text = raw_text_extractor(raw_document.raw_payload)

    description_clean = clean_html(raw_text.description_html)
    language = detect_language(description_clean or raw_text.title or "")

    system_prompt = load_prompt(PROMPT_VERSION)
    user_text = _build_user_text(raw_text, description_clean)

    try:
        extracted = await extract_job_structured(
            db,
            backend=backend,
            content_hash=raw_document.content_hash,
            prompt_version=PROMPT_VERSION,
            system_prompt=system_prompt,
            user_text=user_text,
            model=model,
        )
    except Exception as exc:
        raw_document.processing_status = ProcessingStatus.FAILED
        raw_document.processed_at = datetime.now(UTC)
        await db.commit()
        log.error("normalization_failed", raw_document_id=str(raw_document.id), error=str(exc))
        raise NormalizationError(str(exc)) from exc

    company = None
    if extracted.company_name:
        company = await get_or_create_company(db, name=extracted.company_name)

    rate_min, rate_max, rate_currency, rate_period, rate_eur_normalized = await _normalize_rate(
        extracted, http_client=http_client
    )

    job = await db.scalar(
        select(Job).where(Job.source_id == source.id, Job.external_id == raw_document.external_id)
    )
    is_new = job is None
    if job is None:
        job = Job(source_id=source.id, external_id=raw_document.external_id)
        db.add(job)

    job.raw_document_id = raw_document.id
    job.company_id = company.id if company else None
    job.url = raw_document.url
    job.title = extracted.title or raw_text.title or ""
    job.description_clean = description_clean
    job.language = language
    job.contract_type = ContractType(extracted.contract_type) if extracted.contract_type else None
    job.seniority = SeniorityLevel(extracted.seniority) if extracted.seniority else None
    job.rate_min = rate_min
    job.rate_max = rate_max
    job.rate_currency = rate_currency
    job.rate_period = rate_period
    job.rate_eur_normalized = rate_eur_normalized
    job.duration_months = (
        Decimal(str(extracted.duration_months)) if extracted.duration_months is not None else None
    )
    job.workload_days_week = (
        Decimal(str(extracted.workload_days_per_week))
        if extracted.workload_days_per_week is not None
        else None
    )
    job.start_date = _parse_date(extracted.start_date)
    job.remote_type = RemoteType(extracted.remote_type) if extracted.remote_type else None
    job.timezone_constraint = extracted.timezone_constraint
    job.required_languages = extracted.required_languages
    job.billing_mode = extracted.billing_mode
    job.application_channel = extracted.application_channel
    job.posted_at = raw_document.fetched_at
    job.last_seen_at = datetime.now(UTC)
    if is_new:
        job.detected_at = datetime.now(UTC)
    job.quality_score = compute_quality_score(extracted, description_clean)
    job.prompt_version = PROMPT_VERSION

    await db.flush()
    await upsert_skills_for_job(db, job_id=job.id, tech_stack=extracted.tech_stack)

    embedding_text = build_embedding_text(
        title=job.title, description_clean=description_clean, tech_stack=extracted.tech_stack
    )
    job.embedding = (await embedding_backend.embed_documents([embedding_text]))[0]
    job.dedup_hash = compute_dedup_hash(job.title, extracted.company_name, description_clean)
    await db.execute(
        update(Job)
        .where(Job.id == job.id)
        .values(search_tsv=search_tsv_expression(job.title, description_clean))
    )
    await db.flush()
    await deduplicate_job(db, job)

    raw_document.processing_status = ProcessingStatus.PROCESSED
    raw_document.processed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(job)
    log.info("job_normalized", job_id=str(job.id), source=source.slug, is_new=is_new)
    return job


async def normalize_pending_documents(
    db: AsyncSession,
    *,
    backend: JobExtractionBackend,
    embedding_backend: EmbeddingBackend,
    http_client: httpx.AsyncClient,
    model: str,
    limit: int = 100,
    source_id: uuid.UUID | None = None,
) -> NormalizationSummary:
    query = (
        select(RawDocument)
        .where(RawDocument.processing_status == ProcessingStatus.PENDING)
        .order_by(RawDocument.fetched_at)
        .limit(limit)
    )
    if source_id is not None:
        query = query.where(RawDocument.source_id == source_id)

    raw_documents = (await db.execute(query)).scalars().all()

    summary = NormalizationSummary()
    sources_cache: dict[uuid.UUID, Source] = {}

    for raw_document in raw_documents:
        source = sources_cache.get(raw_document.source_id)
        if source is None:
            source = await db.get(Source, raw_document.source_id)
            sources_cache[raw_document.source_id] = source
        assert source is not None

        try:
            job = await normalize_raw_document(
                db,
                raw_document,
                source=source,
                backend=backend,
                embedding_backend=embedding_backend,
                http_client=http_client,
                model=model,
            )
        except NormalizationError:
            summary.failed += 1
            continue

        if job is not None:
            summary.processed += 1
        else:
            summary.skipped += 1

    return summary


def _build_user_text(raw_text: RawText, description_clean: str) -> str:
    lines: list[str] = []
    if raw_text.title:
        lines.append(f"Titre : {raw_text.title}")
    if raw_text.company_name:
        lines.append(f"Entreprise : {raw_text.company_name}")
    lines.extend(raw_text.context_lines)
    lines.append("")
    lines.append("Description :")
    lines.append(description_clean or "(vide)")
    return "\n".join(lines)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


async def _normalize_rate(
    extracted: ExtractedJobLLM, *, http_client: httpx.AsyncClient
) -> tuple[Decimal | None, Decimal | None, str | None, RatePeriod | None, Decimal | None]:
    if extracted.rate is None:
        return None, None, None, None, None

    rate_period = RatePeriod(extracted.rate.period) if extracted.rate.period else None
    rate_currency = extracted.rate.currency.upper()[:3] if extracted.rate.currency else None
    rate_min = _to_decimal(extracted.rate.min)
    rate_max = _to_decimal(extracted.rate.max)

    rate_eur_normalized = None
    if rate_currency and (rate_max is not None or rate_min is not None):
        fx_rate = await get_rate_to_eur(rate_currency, http_client=http_client)
        if fx_rate is not None:
            reference = rate_max if rate_max is not None else rate_min
            assert reference is not None
            rate_eur_normalized = (reference * fx_rate).quantize(Decimal("0.01"))

    return rate_min, rate_max, rate_currency, rate_period, rate_eur_normalized


def _to_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
