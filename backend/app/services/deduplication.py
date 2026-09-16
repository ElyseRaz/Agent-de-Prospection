import hashlib
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dedup import JobDuplicateLink
from app.models.job import Job, JobStatus

log = structlog.get_logger(__name__)

DEFAULT_LOOKBACK_DAYS = 60
DEFAULT_TRIGRAM_THRESHOLD = 0.6
DEFAULT_VECTOR_THRESHOLD = 0.88


def compute_dedup_hash(
    title: str | None, company_name: str | None, description_clean: str | None
) -> str:
    normalized_title = _normalize_text(title or "")
    normalized_company = _normalize_text(company_name or "")
    normalized_desc = _normalize_text((description_clean or "")[:300])
    canonical = f"{normalized_title}|{normalized_company}|{normalized_desc}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", normalized)


async def deduplicate_job(
    db: AsyncSession,
    job: Job,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    trigram_threshold: float = DEFAULT_TRIGRAM_THRESHOLD,
    vector_threshold: float = DEFAULT_VECTOR_THRESHOLD,
) -> Job | None:
    """Cherche un job canonique existant qui duplique `job`, selon 3 niveaux
    (hash exact -> trigramme -> cosinus). Si trouve, `job.canonical_id` est
    positionne et l'evenement trace dans `job_duplicate_links`. Retourne le
    job canonique trouve, ou None si `job` reste unique (et donc canonique)."""

    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    base_conditions = (
        Job.id != job.id,
        Job.status == JobStatus.ACTIVE,
        Job.canonical_id.is_(None),
        Job.detected_at >= cutoff,
    )

    if job.dedup_hash:
        match = await db.scalar(
            select(Job)
            .where(*base_conditions, Job.dedup_hash == job.dedup_hash)
            .order_by(Job.detected_at)
            .limit(1)
        )
        if match is not None:
            await _record_duplicate(
                db, canonical=match, duplicate=job, method="exact_hash", score=1.0
            )
            return match

    if job.title and job.company_id is not None:
        similarity_expr = func.similarity(Job.title, job.title)
        trigram_stmt = (
            select(Job, similarity_expr.label("sim"))
            .where(*base_conditions, Job.company_id == job.company_id)
            .order_by(similarity_expr.desc())
            .limit(1)
        )
        row = (await db.execute(trigram_stmt)).first()
        if row is not None:
            match, similarity = row
            if similarity is not None and float(similarity) >= trigram_threshold:
                await _record_duplicate(
                    db, canonical=match, duplicate=job, method="trigram", score=float(similarity)
                )
                return match

    if job.embedding is not None:
        vector_stmt = (
            select(Job, (1 - Job.embedding.cosine_distance(job.embedding)).label("sim"))
            .where(*base_conditions, Job.embedding.is_not(None))
            .order_by(Job.embedding.cosine_distance(job.embedding))
            .limit(1)
        )
        row = (await db.execute(vector_stmt)).first()
        if row is not None:
            match, similarity = row
            if similarity is not None and float(similarity) >= vector_threshold:
                await _record_duplicate(
                    db, canonical=match, duplicate=job, method="embedding", score=float(similarity)
                )
                return match

    return None


async def _record_duplicate(
    db: AsyncSession, *, canonical: Job, duplicate: Job, method: str, score: float
) -> None:
    duplicate.canonical_id = canonical.id

    stmt = (
        pg_insert(JobDuplicateLink)
        .values(
            canonical_job_id=canonical.id,
            duplicate_job_id=duplicate.id,
            method=method,
            similarity_score=Decimal(str(round(score, 4))),
        )
        .on_conflict_do_update(
            index_elements=["duplicate_job_id"],
            set_={
                "canonical_job_id": canonical.id,
                "method": method,
                "similarity_score": Decimal(str(round(score, 4))),
            },
        )
    )
    await db.execute(stmt)
    log.info(
        "duplicate_detected",
        canonical_id=str(canonical.id),
        duplicate_id=str(duplicate.id),
        method=method,
        score=score,
    )
