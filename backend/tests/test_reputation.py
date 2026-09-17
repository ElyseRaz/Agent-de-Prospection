from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import update

from app.models.company import Company
from app.models.reputation import CompanyReputation
from app.reputation.base import ReputationLookupError, ReputationResult
from app.reputation.trustpilot import TrustpilotReputationProvider
from app.services.reputation import get_or_fetch_reputation
from tests.conftest import FakeReputationProvider

pytestmark = pytest.mark.asyncio


FIND_RESPONSE = {
    "id": "507f191e810c19729de860ea",
    "displayName": "Acme",
    "name": {"identifying": "acme.com", "referring": ["acme.com"]},
    "websiteUrl": "http://www.acme.com",
    "country": "US",
    "numberOfReviews": {"total": 42},
    "status": "active",
    "score": {"trustScore": 4.2, "stars": 4.0},
}


async def test_fetch_by_domain_parses_confirmed_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["name"] == "acme.com"
        assert request.headers["apikey"] == "test-key"
        return httpx.Response(200, json=FIND_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = TrustpilotReputationProvider(api_key="test-key", http_client=client)

    result = await provider.fetch_by_domain("acme.com")

    assert result is not None
    assert result.rating == 4.2
    assert result.review_count == 42
    assert result.country == "US"
    assert result.website_url == "http://www.acme.com"
    assert result.raw == FIND_RESPONSE
    await client.aclose()


async def test_fetch_by_domain_falls_back_to_detail_endpoint_when_score_missing():
    without_score = {"id": "abc123"}
    detail_calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/find"):
            return httpx.Response(200, json=without_score)
        detail_calls.append(request.url.path)
        return httpx.Response(200, json=FIND_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = TrustpilotReputationProvider(api_key="test-key", http_client=client)

    result = await provider.fetch_by_domain("acme.com")

    assert result is not None
    assert result.rating == 4.2
    assert len(detail_calls) == 1
    assert "abc123" in detail_calls[0]
    await client.aclose()


async def test_fetch_by_domain_returns_none_on_404():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    provider = TrustpilotReputationProvider(api_key="test-key", http_client=client)

    result = await provider.fetch_by_domain("unknown-company.example")

    assert result is None
    await client.aclose()


async def test_fetch_by_domain_raises_lookup_error_on_server_error():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    provider = TrustpilotReputationProvider(api_key="test-key", http_client=client)

    with pytest.raises(ReputationLookupError):
        await provider.fetch_by_domain("acme.com")
    await client.aclose()


async def _make_company(db_session, **overrides) -> Company:
    defaults = dict(name="Acme", normalized_name="acme", domain="acme.com")
    defaults.update(overrides)
    company = Company(**defaults)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


def _sample_result(**overrides) -> ReputationResult:
    defaults = dict(rating=4.2, review_count=42, country="US", website_url=None, raw={})
    defaults.update(overrides)
    return ReputationResult(**defaults)


async def test_get_or_fetch_reputation_returns_none_without_domain(db_session):
    company = await _make_company(db_session, domain=None)
    provider = FakeReputationProvider({})

    result = await get_or_fetch_reputation(db_session, company, provider=provider)

    assert result is None
    assert provider.calls == []


async def test_get_or_fetch_reputation_persists_result(db_session):
    company = await _make_company(db_session)
    provider = FakeReputationProvider({"acme.com": _sample_result()})

    reputation = await get_or_fetch_reputation(db_session, company, provider=provider)

    assert reputation is not None
    assert reputation.rating == 4.2
    assert provider.calls == ["acme.com"]


async def test_get_or_fetch_reputation_uses_cache_within_max_age(db_session):
    company = await _make_company(db_session)
    provider = FakeReputationProvider({"acme.com": _sample_result()})

    await get_or_fetch_reputation(db_session, company, provider=provider)
    await get_or_fetch_reputation(db_session, company, provider=provider)

    assert provider.calls == ["acme.com"]  # un seul appel, la 2e fois vient du cache


async def test_get_or_fetch_reputation_refetches_after_max_age(db_session):
    company = await _make_company(db_session)
    provider = FakeReputationProvider({"acme.com": _sample_result()})

    first = await get_or_fetch_reputation(db_session, company, provider=provider)
    await db_session.execute(
        update(CompanyReputation)
        .where(CompanyReputation.id == first.id)
        .values(fetched_at=datetime.now(UTC) - timedelta(days=31))
    )
    await db_session.commit()

    await get_or_fetch_reputation(db_session, company, provider=provider, max_age_days=30)

    assert provider.calls == ["acme.com", "acme.com"]


async def test_get_or_fetch_reputation_records_not_found_distinctly(db_session):
    company = await _make_company(db_session)
    provider = FakeReputationProvider({"acme.com": None})

    reputation = await get_or_fetch_reputation(db_session, company, provider=provider)

    assert reputation is not None
    assert reputation.rating is None  # verifie, absent - distinct de "jamais verifie"


async def test_get_or_fetch_reputation_keeps_cache_on_transient_error(db_session):
    company = await _make_company(db_session)
    provider = FakeReputationProvider({"acme.com": _sample_result()})
    first = await get_or_fetch_reputation(db_session, company, provider=provider)

    failing_provider = FakeReputationProvider({"acme.com": ReputationLookupError("panne")})
    await db_session.execute(
        update(CompanyReputation)
        .where(CompanyReputation.id == first.id)
        .values(fetched_at=datetime.now(UTC) - timedelta(days=31))
    )
    await db_session.commit()

    result = await get_or_fetch_reputation(
        db_session, company, provider=failing_provider, max_age_days=30
    )

    assert result is not None
    assert result.rating == 4.2  # ancienne valeur conservee malgre la panne
