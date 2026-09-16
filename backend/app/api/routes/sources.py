import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_circuit_breaker,
    get_current_user,
    get_db,
    get_http_client,
    require_role,
)
from app.collectors.http import CircuitBreaker
from app.models.source import Source
from app.models.user import User, UserRole
from app.schemas.source import CollectResponse, DryRunResultRead, ScrapeRunRead, SourceRead
from app.services.collection import CollectionError, DryRunResult, run_collection

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceRead])
async def list_sources(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Source]:
    result = await db.execute(select(Source).order_by(Source.slug))
    return list(result.scalars())


@router.get("/{slug}", response_model=SourceRead)
async def get_source(
    slug: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)
) -> Source:
    return await _get_source_or_404(db, slug)


@router.post("/{slug}/collect", response_model=CollectResponse)
async def collect_source(
    slug: str,
    dry_run: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> CollectResponse:
    source = await _get_source_or_404(db, slug)
    if not source.is_active and not dry_run:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Source desactivee"
        )

    try:
        result = await run_collection(
            db, source, dry_run=dry_run, http_client=http_client, circuit_breaker=circuit_breaker
        )
    except CollectionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if isinstance(result, DryRunResult):
        return CollectResponse(
            dry_run=True,
            dry_run_result=DryRunResultRead(
                source_slug=result.source_slug,
                items_fetched=result.items_fetched,
                sample=result.sample,
            ),
        )

    return CollectResponse(dry_run=False, run=ScrapeRunRead.model_validate(result))


async def _get_source_or_404(db: AsyncSession, slug: str) -> Source:
    source = await db.scalar(select(Source).where(Source.slug == slug))
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source introuvable")
    return source
