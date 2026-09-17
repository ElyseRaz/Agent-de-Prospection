import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blacklist import Blacklist, BlacklistEntityType
from app.normalization.company import normalize_company_name


def normalize_blacklist_value(entity_type: BlacklistEntityType, value: str) -> str:
    """Meme normalisation que la resolution d'entreprise pour les entrees de
    type COMPANY, afin qu'une valeur ajoutee via l'API matche bien
    `company.normalized_name` lors de la verification du score de risque."""

    if entity_type == BlacklistEntityType.COMPANY:
        return normalize_company_name(value)
    return value.strip().lower()


async def find_shared_blacklist_entry(
    db: AsyncSession, *, entity_type: BlacklistEntityType, value: str
) -> Blacklist | None:
    """Cherche uniquement une entree PARTAGEE (user_id NULL) : c'est la seule
    qui doit influencer le risk_score public d'un job, visible de tous."""

    stmt = select(Blacklist).where(
        Blacklist.entity_type == entity_type,
        Blacklist.value == normalize_blacklist_value(entity_type, value),
        Blacklist.user_id.is_(None),
    )
    return await db.scalar(stmt)


async def list_blacklist_entries(db: AsyncSession, *, user_id: uuid.UUID) -> list[Blacklist]:
    """Entrees partagees + entrees personnelles de `user_id`."""

    stmt = (
        select(Blacklist)
        .where(or_(Blacklist.user_id.is_(None), Blacklist.user_id == user_id))
        .order_by(Blacklist.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def add_blacklist_entry(
    db: AsyncSession,
    *,
    entity_type: BlacklistEntityType,
    value: str,
    reason: str | None,
    user_id: uuid.UUID | None,
) -> Blacklist:
    entry = Blacklist(
        entity_type=entity_type,
        value=normalize_blacklist_value(entity_type, value),
        reason=reason,
        user_id=user_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
