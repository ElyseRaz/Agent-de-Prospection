import re
import unicodedata

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


def normalize_company_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.strip().lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return normalized


def normalize_domain(domain: str) -> str:
    cleaned = domain.strip().lower()
    cleaned = re.sub(r"^https?://", "", cleaned)
    cleaned = re.sub(r"^www\.", "", cleaned)
    return cleaned.split("/")[0]


async def get_or_create_company(
    db: AsyncSession, *, name: str, domain: str | None = None
) -> Company:
    """Resolution minimale par nom normalise. La resolution avancee (dedup
    fuzzy multi-sources) est explicitement hors scope.

    `domain`, quand fourni (rarement present dans le texte source), est
    enregistre pour permettre la recherche de reputation Trustpilot (phase 5).
    Un domaine deja connu n'est jamais ecrase par une valeur ulterieure
    absente."""

    normalized = normalize_company_name(name)
    normalized_domain = normalize_domain(domain) if domain else None

    existing = await db.scalar(select(Company).where(Company.normalized_name == normalized))
    if existing is not None:
        if normalized_domain and not existing.domain:
            await db.execute(
                update(Company).where(Company.id == existing.id).values(domain=normalized_domain)
            )
            existing.domain = normalized_domain
        return existing

    stmt = (
        pg_insert(Company)
        .values(name=name.strip(), normalized_name=normalized, domain=normalized_domain)
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
