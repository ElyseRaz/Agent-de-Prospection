from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.blacklist import BlacklistCreate, BlacklistRead
from app.services.blacklist import add_blacklist_entry, list_blacklist_entries

router = APIRouter(prefix="/blacklist", tags=["blacklist"])


@router.get("", response_model=list[BlacklistRead])
async def list_blacklist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BlacklistRead]:
    entries = await list_blacklist_entries(db, user_id=current_user.id)
    return [BlacklistRead.model_validate(entry) for entry in entries]


@router.post("", response_model=BlacklistRead, status_code=status.HTTP_201_CREATED)
async def create_blacklist_entry(
    payload: BlacklistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlacklistRead:
    if payload.shared and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un administrateur peut ajouter une entree partagee",
        )

    entry = await add_blacklist_entry(
        db,
        entity_type=payload.entity_type,
        value=payload.value,
        reason=payload.reason,
        user_id=None if payload.shared else current_user.id,
    )
    return BlacklistRead.model_validate(entry)
