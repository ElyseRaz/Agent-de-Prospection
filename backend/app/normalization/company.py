import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


def normalize_company_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip().lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return normalized


async def get_or_create_company(db: AsyncSession, *, name: str) -> Company:
    """Resolution minimale par nom normalise. La resolution avancee (domaine,
    dedup fuzzy multi-sources) est explicitement hors scope (phase 5)."""

    normalized = normalize_company_name(name)

    existing = await db.scalar(select(Company).where(Company.normalized_name == normalized))
    if existing is not None:
        return existing

    stmt = (
        pg_insert(Company)
        .values(name=name.strip(), normalized_name=normalized)
        .on_conflict_do_nothing(constraint="uq_companies_normalized_name")
        .returning(Company.id)
    )
    result = await db.execute(stmt)
    company_id = result.scalar_one_or_none()
    if company_id is None:
        existing = await db.scalar(select(Company).where(Company.normalized_name == normalized))
        assert existing is not None
        return existing

    company = await db.get(Company, company_id)
    assert company is not None
    return company
