import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_role
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserRead,
    AdminUserUpdate,
    LLMUsageBucket,
    LLMUsageResponse,
)
from app.services.admin import get_llm_usage, get_stats, list_users, update_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/llm-usage", response_model=LLMUsageResponse)
async def llm_usage(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> LLMUsageResponse:
    result = await get_llm_usage(db, days=days)
    return LLMUsageResponse(
        buckets=[
            LLMUsageBucket(
                day=bucket.day.date(),
                purpose=bucket.purpose,
                model=bucket.model,
                calls=bucket.calls,
                cache_hits=bucket.cache_hits,
                input_tokens=bucket.input_tokens,
                output_tokens=bucket.output_tokens,
                cost_usd=bucket.cost_usd,
            )
            for bucket in result.buckets
        ],
        total_calls=result.total_calls,
        total_cost_usd=result.total_cost_usd,
    )


@router.get("/users", response_model=list[AdminUserRead])
async def admin_list_users(
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> list[User]:
    return await list_users(db, search=q)


@router.patch("/users/{user_id}", response_model=AdminUserRead)
async def admin_update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> User:
    if user_id == current_user.id and (
        payload.is_active is False or (payload.role is not None and payload.role != UserRole.ADMIN)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas retirer vos propres droits admin ou vous desactiver",
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")

    return await update_user(db, user, role=payload.role, is_active=payload.is_active)


@router.get("/stats", response_model=AdminStatsResponse)
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
) -> AdminStatsResponse:
    result = await get_stats(db)
    return AdminStatsResponse(
        users_total=result.users_total,
        jobs_total=result.jobs_total,
        jobs_active=result.jobs_active,
        applications_total=result.applications_total,
        saved_searches_total=result.saved_searches_total,
    )
