import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingBackend
from app.models.job import ContractType, Job, JobSkill, JobStatus, RemoteType, SeniorityLevel
from app.models.skill import Skill
from app.models.source import Source

CANDIDATE_LIMIT = 50
TEXT_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5

SortOption = Literal["relevance", "freshness", "rate"]


@dataclass(slots=True)
class JobSearchFilters:
    rate_min_eur: Decimal | None = None
    rate_max_eur: Decimal | None = None
    rate_currency: str | None = None
    skill_slugs: list[str] = field(default_factory=list)
    seniority: SeniorityLevel | None = None
    language: str | None = None
    remote_type: RemoteType | None = None
    contract_type: ContractType | None = None
    source_slug: str | None = None
    status: JobStatus = JobStatus.ACTIVE


@dataclass(slots=True)
class JobSearchResult:
    job: Job
    score: float


async def hybrid_search_jobs(
    db: AsyncSession,
    *,
    query: str | None,
    filters: JobSearchFilters,
    embedding_backend: EmbeddingBackend | None,
    sort: SortOption = "relevance",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[JobSearchResult], int]:
    """Recherche hybride : fusion (cote Python) des resultats plein texte
    (tsvector) et vectoriels (pgvector, ANN via l'index HNSW), score combine
    0.5*rang_texte + 0.5*similarite_cosinus. Sans `query`, simple parcours
    filtre/trie (pas d'appel au modele d'embedding, cout nul)."""

    base_stmt = select(Job).where(Job.status == filters.status, Job.canonical_id.is_(None))
    base_stmt = _apply_filters(base_stmt, filters)

    if not query:
        stmt = base_stmt.order_by(_sort_column(sort)).offset(offset).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        total = await _count(db, base_stmt)
        return [JobSearchResult(job=row, score=0.0) for row in rows], total

    tsquery = func.websearch_to_tsquery("simple", func.unaccent(query))
    text_score = func.ts_rank_cd(Job.search_tsv, tsquery)
    text_stmt = (
        base_stmt.where(Job.search_tsv.op("@@")(tsquery))
        .add_columns(text_score.label("text_score"))
        .order_by(text_score.desc())
        .limit(CANDIDATE_LIMIT)
    )
    text_rows = (await db.execute(text_stmt)).all()

    vector_rows: list[tuple[Job, float]] = []
    if embedding_backend is not None:
        query_embedding = await embedding_backend.embed_query(query)
        vector_score = 1 - Job.embedding.cosine_distance(query_embedding)
        vector_stmt = (
            base_stmt.where(Job.embedding.is_not(None))
            .add_columns(vector_score.label("vector_score"))
            .order_by(Job.embedding.cosine_distance(query_embedding))
            .limit(CANDIDATE_LIMIT)
        )
        vector_rows = (await db.execute(vector_stmt)).all()

    merged: dict[uuid.UUID, JobSearchResult] = {}

    if text_rows:
        max_text_score = max(float(row[1]) for row in text_rows) or 1.0
        for job, score in text_rows:
            normalized = float(score) / max_text_score
            merged[job.id] = JobSearchResult(job=job, score=TEXT_WEIGHT * normalized)

    for job, score in vector_rows:
        contribution = VECTOR_WEIGHT * float(score)
        existing = merged.get(job.id)
        if existing is None:
            merged[job.id] = JobSearchResult(job=job, score=contribution)
        else:
            existing.score += contribution

    ranked = sorted(merged.values(), key=lambda result: result.score, reverse=True)
    # `total` denombre le pool de candidats ranked (texte + vectoriel, capes a
    # CANDIDATE_LIMIT chacun), pas un COUNT(*) exhaustif de toutes les lignes
    # matchant potentiellement en base : limitation assumee du pattern
    # 'top-K candidats puis fusion', standard en recherche hybride.
    total = len(ranked)
    return ranked[offset : offset + limit], total


def _apply_filters(stmt, filters: JobSearchFilters):
    if filters.rate_min_eur is not None:
        stmt = stmt.where(Job.rate_eur_normalized >= filters.rate_min_eur)
    if filters.rate_max_eur is not None:
        stmt = stmt.where(Job.rate_eur_normalized <= filters.rate_max_eur)
    if filters.rate_currency:
        stmt = stmt.where(Job.rate_currency == filters.rate_currency.upper())
    if filters.seniority is not None:
        stmt = stmt.where(Job.seniority == filters.seniority)
    if filters.language:
        stmt = stmt.where(Job.language == filters.language)
    if filters.remote_type is not None:
        stmt = stmt.where(Job.remote_type == filters.remote_type)
    if filters.contract_type is not None:
        stmt = stmt.where(Job.contract_type == filters.contract_type)
    if filters.source_slug:
        stmt = stmt.where(
            Job.source_id.in_(select(Source.id).where(Source.slug == filters.source_slug))
        )
    if filters.skill_slugs:
        skill_subquery = (
            select(JobSkill.job_id)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(Skill.slug.in_(filters.skill_slugs))
        )
        stmt = stmt.where(Job.id.in_(skill_subquery))
    return stmt


def _sort_column(sort: SortOption):
    if sort == "rate":
        return Job.rate_eur_normalized.desc().nulls_last()
    return Job.detected_at.desc()


async def _count(db: AsyncSession, stmt) -> int:
    count_stmt = select(func.count()).select_from(stmt.subquery())
    return (await db.scalar(count_stmt)) or 0
