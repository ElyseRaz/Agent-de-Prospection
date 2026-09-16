import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_embedding_backend,
    get_http_client,
    get_llm_backend,
    get_settings,
    require_role,
)
from app.core.config import Settings
from app.embeddings.base import EmbeddingBackend
from app.models.source import RawDocument, Source
from app.models.user import User, UserRole
from app.normalization.llm_extraction import JobExtractionBackend
from app.schemas.normalization import NormalizationSummaryRead, ReprocessResponse
from app.services.normalization import (
    NormalizationError,
    normalize_pending_documents,
    normalize_raw_document,
)

router = APIRouter(tags=["normalization"])


@router.post("/normalization/run", response_model=NormalizationSummaryRead)
async def run_normalization(
    limit: int = Query(default=100, ge=1, le=1000),
    source_slug: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    llm_backend: JobExtractionBackend = Depends(get_llm_backend),
    embedding_backend: EmbeddingBackend = Depends(get_embedding_backend),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> NormalizationSummaryRead:
    source_id: uuid.UUID | None = None
    if source_slug is not None:
        source = await db.scalar(select(Source).where(Source.slug == source_slug))
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable"
            )
        source_id = source.id

    summary = await normalize_pending_documents(
        db,
        backend=llm_backend,
        embedding_backend=embedding_backend,
        http_client=http_client,
        model=settings.llm_model,
        limit=limit,
        source_id=source_id,
    )
    return NormalizationSummaryRead(
        processed=summary.processed, failed=summary.failed, skipped=summary.skipped
    )


@router.post("/raw-documents/{raw_document_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_raw_document(
    raw_document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    llm_backend: JobExtractionBackend = Depends(get_llm_backend),
    embedding_backend: EmbeddingBackend = Depends(get_embedding_backend),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> ReprocessResponse:
    raw_document = await db.get(RawDocument, raw_document_id)
    if raw_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document brut introuvable"
        )

    source = await db.get(Source, raw_document.source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable")

    try:
        job = await normalize_raw_document(
            db,
            raw_document,
            source=source,
            backend=llm_backend,
            embedding_backend=embedding_backend,
            http_client=http_client,
            model=settings.llm_model,
            force=True,
        )
    except NormalizationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    assert job is not None
    return ReprocessResponse(job_id=job.id, status="processed")
