import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_embedding_backend, get_notification_channels
from app.embeddings.base import EmbeddingBackend
from app.models.alert import SavedSearch
from app.models.user import User
from app.notifications.base import NotificationChannel
from app.schemas.alert import (
    SavedSearchCreate,
    SavedSearchRead,
    SavedSearchRunResponse,
    SavedSearchUpdate,
)
from app.services.alerts import evaluate_saved_search

router = APIRouter(prefix="/saved-searches", tags=["alerts"])


async def _get_owned_saved_search(
    db: AsyncSession, saved_search_id: uuid.UUID, current_user: User
) -> SavedSearch:
    saved_search = await db.get(SavedSearch, saved_search_id)
    if saved_search is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recherche sauvegardee introuvable"
        )
    if saved_search.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette recherche sauvegardee ne vous appartient pas",
        )
    return saved_search


@router.post("", response_model=SavedSearchRead, status_code=status.HTTP_201_CREATED)
async def create_saved_search(
    payload: SavedSearchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSearch:
    saved_search = SavedSearch(
        user_id=current_user.id,
        name=payload.name,
        filters=payload.filters.model_dump(mode="json", exclude_none=True),
        channels=payload.channels,
        frequency=payload.frequency,
    )
    db.add(saved_search)
    await db.commit()
    await db.refresh(saved_search)
    return saved_search


@router.get("", response_model=list[SavedSearchRead])
async def list_saved_searches(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SavedSearch]:
    rows = (
        await db.execute(
            select(SavedSearch)
            .where(SavedSearch.user_id == current_user.id)
            .order_by(SavedSearch.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/{saved_search_id}", response_model=SavedSearchRead)
async def get_saved_search(
    saved_search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSearch:
    return await _get_owned_saved_search(db, saved_search_id, current_user)


@router.patch("/{saved_search_id}", response_model=SavedSearchRead)
async def update_saved_search(
    saved_search_id: uuid.UUID,
    payload: SavedSearchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SavedSearch:
    saved_search = await _get_owned_saved_search(db, saved_search_id, current_user)

    if payload.name is not None:
        saved_search.name = payload.name
    if payload.filters is not None:
        saved_search.filters = payload.filters.model_dump(mode="json", exclude_none=True)
    if payload.channels is not None:
        saved_search.channels = payload.channels
    if payload.frequency is not None:
        saved_search.frequency = payload.frequency
    if payload.is_active is not None:
        saved_search.is_active = payload.is_active

    db.add(saved_search)
    await db.commit()
    await db.refresh(saved_search)
    return saved_search


@router.delete("/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_search(
    saved_search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    saved_search = await _get_owned_saved_search(db, saved_search_id, current_user)
    await db.delete(saved_search)
    await db.commit()


@router.post("/{saved_search_id}/run", response_model=SavedSearchRunResponse)
async def run_saved_search(
    saved_search_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    embedding_backend: EmbeddingBackend = Depends(get_embedding_backend),
    channels: dict[str, NotificationChannel] = Depends(get_notification_channels),
) -> SavedSearchRunResponse:
    saved_search = await _get_owned_saved_search(db, saved_search_id, current_user)
    result = await evaluate_saved_search(
        db,
        saved_search,
        embedding_backend=embedding_backend,
        channels=channels,
        user_email=current_user.email,
    )
    return SavedSearchRunResponse(
        jobs_considered=result.jobs_considered, new_notifications=result.new_notifications
    )
