from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import SavedSearch
from app.models.application import Application
from app.models.job import Job, JobStatus
from app.models.llm import LLMCall
from app.models.user import User, UserRole


@dataclass(slots=True)
class LLMUsageBucketResult:
    day: datetime
    purpose: str
    model: str
    calls: int
    cache_hits: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


@dataclass(slots=True)
class LLMUsageResult:
    buckets: list[LLMUsageBucketResult]
    total_calls: int
    total_cost_usd: Decimal


async def get_llm_usage(db: AsyncSession, *, days: int = 30) -> LLMUsageResult:
    """Agrege `llm_calls` par jour/purpose/modele - base de l'ecran de
    consommation admin (couts phase 3/5, aucune donnee nouvelle a collecter,
    tout est deja journalise a chaque appel/hit de cache)."""

    cutoff = datetime.now(UTC) - timedelta(days=days)
    day_bucket = func.date_trunc("day", LLMCall.created_at)

    stmt = (
        select(
            day_bucket.label("day"),
            LLMCall.purpose,
            LLMCall.model,
            func.count().label("calls"),
            func.sum(case((LLMCall.cache_hit.is_(True), 1), else_=0)).label("cache_hits"),
            func.sum(LLMCall.input_tokens).label("input_tokens"),
            func.sum(LLMCall.output_tokens).label("output_tokens"),
            func.sum(LLMCall.cost_usd).label("cost_usd"),
        )
        .where(LLMCall.created_at >= cutoff)
        .group_by(day_bucket, LLMCall.purpose, LLMCall.model)
        .order_by(day_bucket.desc())
    )
    rows = (await db.execute(stmt)).all()

    buckets = [
        LLMUsageBucketResult(
            day=row.day,
            purpose=row.purpose,
            model=row.model,
            calls=row.calls,
            cache_hits=row.cache_hits or 0,
            input_tokens=row.input_tokens or 0,
            output_tokens=row.output_tokens or 0,
            cost_usd=row.cost_usd or Decimal(0),
        )
        for row in rows
    ]
    total_calls = sum(bucket.calls for bucket in buckets)
    total_cost = sum((bucket.cost_usd for bucket in buckets), Decimal(0))

    return LLMUsageResult(buckets=buckets, total_calls=total_calls, total_cost_usd=total_cost)


async def list_users(db: AsyncSession, *, search: str | None = None) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if search:
        stmt = stmt.where(User.email.ilike(f"%{search}%"))
    return list((await db.execute(stmt)).scalars().all())


async def update_user(
    db: AsyncSession, user: User, *, role: UserRole | None, is_active: bool | None
) -> User:
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@dataclass(slots=True)
class AdminStatsResult:
    users_total: int
    jobs_total: int
    jobs_active: int
    applications_total: int
    saved_searches_total: int


async def get_stats(db: AsyncSession) -> AdminStatsResult:
    users_total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    jobs_total = (await db.execute(select(func.count()).select_from(Job))).scalar_one()
    jobs_active = (
        await db.execute(
            select(func.count()).select_from(Job).where(Job.status == JobStatus.ACTIVE)
        )
    ).scalar_one()
    applications_total = (
        await db.execute(select(func.count()).select_from(Application))
    ).scalar_one()
    saved_searches_total = (
        await db.execute(select(func.count()).select_from(SavedSearch))
    ).scalar_one()

    return AdminStatsResult(
        users_total=users_total,
        jobs_total=jobs_total,
        jobs_active=jobs_active,
        applications_total=applications_total,
        saved_searches_total=saved_searches_total,
    )
