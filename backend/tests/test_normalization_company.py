import pytest
from sqlalchemy import select

from app.models.company import Company
from app.normalization.company import get_or_create_company, normalize_company_name

pytestmark = pytest.mark.asyncio


def test_normalize_company_name_strips_accents_and_case():
    assert normalize_company_name("Écoles & Cie") == "ecoles cie"
    assert normalize_company_name("  Acme Corp  ") == "acme corp"


async def test_get_or_create_company_creates_once(db_session):
    company1 = await get_or_create_company(db_session, name="Acme Corp")
    await db_session.commit()

    company2 = await get_or_create_company(db_session, name="ACME CORP")
    await db_session.commit()

    assert company1.id == company2.id

    rows = (await db_session.execute(select(Company))).scalars().all()
    assert len(rows) == 1


async def test_get_or_create_company_distinguishes_different_names(db_session):
    acme = await get_or_create_company(db_session, name="Acme Corp")
    await db_session.commit()
    beta = await get_or_create_company(db_session, name="Beta Studio")
    await db_session.commit()

    assert acme.id != beta.id
