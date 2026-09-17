from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.reputation import CompanyReputation
from app.reputation.base import ReputationLookupError, ReputationProvider

log = structlog.get_logger(__name__)

PROVIDER_TRUSTPILOT = "trustpilot"
DEFAULT_MAX_AGE_DAYS = 30


async def get_or_fetch_reputation(
    db: AsyncSession,
    company: Company,
    *,
    provider: ReputationProvider,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> CompanyReputation | None:
    """Retourne la reputation Trustpilot de `company`, en cache `max_age_days`.

    Retourne None si aucun domaine n'est connu (jamais verifiable) ou si la
    verification echoue de maniere transitoire (on garde alors l'ancienne
    valeur en cache si elle existe). Une ligne existante avec `rating=None`
    signifie "verifie, absent de Trustpilot" - a ne jamais confondre avec
    "jamais verifie" (aucune ligne du tout)."""

    if not company.domain:
        return None

    existing = await db.scalar(
        select(CompanyReputation).where(
            CompanyReputation.company_id == company.id,
            CompanyReputation.provider == PROVIDER_TRUSTPILOT,
        )
    )
    if existing is not None and datetime.now(UTC) - existing.fetched_at < timedelta(
        days=max_age_days
    ):
        return existing

    try:
        result = await provider.fetch_by_domain(company.domain)
    except ReputationLookupError as exc:
        log.warning("reputation_lookup_failed", company_id=str(company.id), error=str(exc))
        return existing

    if result is None:
        rating, review_count, country, website_url, raw = None, None, None, None, {"found": False}
    else:
        rating = result.rating
        review_count = result.review_count
        country = result.country
        website_url = result.website_url
        raw = result.raw

    stmt = (
        pg_insert(CompanyReputation)
        .values(
            company_id=company.id,
            provider=PROVIDER_TRUSTPILOT,
            rating=rating,
            review_count=review_count,
            country=country,
            website_url=website_url,
            raw=raw,
        )
        .on_conflict_do_update(
            index_elements=["company_id", "provider"],
            set_={
                "rating": rating,
                "review_count": review_count,
                "country": country,
                "website_url": website_url,
                "raw": raw,
                "fetched_at": func.now(),
            },
        )
        .returning(CompanyReputation.id)
    )
    reputation_id = (await db.execute(stmt)).scalar_one()
    await db.commit()
    reputation = await db.get(CompanyReputation, reputation_id)
    assert reputation is not None
    return reputation
