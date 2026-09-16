import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_embedding_backend, require_role
from app.embeddings.base import EmbeddingBackend
from app.models.job import ContractType, Job, JobStatus, RemoteType, SeniorityLevel
from app.models.user import User, UserRole
from app.schemas.job import (
    BackfillResponse,
    JobDetailRead,
    JobRead,
    JobSearchResponse,
    JobSearchResultRead,
    MarkExpiredResponse,
)
from app.services.backfill import backfill_embeddings_and_dedup
from app.services.expiry import mark_expired_jobs
from app.services.search import JobSearchFilters, hybrid_search_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    q: str | None = Query(default=None),
    rate_min_eur: Decimal | None = Query(default=None),
    rate_max_eur: Decimal | None = Query(default=None),
    rate_currency: str | None = Query(default=None),
    skill: list[str] = Query(default=[]),
    seniority: SeniorityLevel | None = Query(default=None),
    language: str | None = Query(default=None),
    remote_type: RemoteType | None = Query(default=None),
    contract_type: ContractType | None = Query(default=None),
    source_slug: str | None = Query(default=None),
    status_filter: JobStatus = Query(default=JobStatus.ACTIVE, alias="status"),
    sort: Literal["relevance", "freshness", "rate"] = Query(default="relevance"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    embedding_backend: EmbeddingBackend = Depends(get_embedding_backend),
    _: User = Depends(get_current_user),
) -> JobSearchResponse:
    filters = JobSearchFilters(
        rate_min_eur=rate_min_eur,
        rate_max_eur=rate_max_eur,
        rate_currency=rate_currency,
        skill_slugs=skill,
        seniority=seniority,
        language=language,
        remote_type=remote_type,
        contract_type=contract_type,
        source_slug=source_slug,
        status=status_filter,
    )

    results, total = await hybrid_search_jobs(
        db,
        query=q,
        filters=filters,
        embedding_backend=embedding_backend,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    return JobSearchResponse(
        results=[
            JobSearchResultRead(job=JobRead.model_validate(r.job), score=r.score) for r in results
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/backfill-embeddings", response_model=BackfillResponse)
async def backfill_embeddings(
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    embedding_backend: EmbeddingBackend = Depends(get_embedding_backend),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> BackfillResponse:
    summary = await backfill_embeddings_and_dedup(
        db, embedding_backend=embedding_backend, limit=limit
    )
    return BackfillResponse(embedded=summary.embedded, skipped=summary.skipped)


@router.post("/mark-expired", response_model=MarkExpiredResponse)
async def mark_expired(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> MarkExpiredResponse:
    count = await mark_expired_jobs(db)
    return MarkExpiredResponse(expired=count)


@router.get("/{job_id}", response_model=JobDetailRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> JobDetailRead:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre introuvable")

    duplicate_urls = (
        (await db.execute(select(Job.url).where(Job.canonical_id == job.id))).scalars().all()
    )

    return JobDetailRead(
        **JobRead.model_validate(job).model_dump(), duplicate_urls=list(duplicate_urls)
    )
