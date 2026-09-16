from decimal import Decimal

import httpx
import pytest

import app.services.currency as currency_module
from app.services.currency import get_rate_to_eur

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_currency_cache():
    currency_module._cache.clear()
    yield
    currency_module._cache.clear()


async def test_get_rate_to_eur_returns_one_for_eur():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    rate = await get_rate_to_eur("EUR", http_client=client)
    assert rate == Decimal("1")
    await client.aclose()


async def test_get_rate_to_eur_converts_via_frankfurter():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "frankfurter" in str(request.url)
        return httpx.Response(200, json={"base": "EUR", "rates": {"USD": 1.1, "GBP": 0.85}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    usd_rate = await get_rate_to_eur("USD", http_client=client)
    gbp_rate = await get_rate_to_eur("GBP", http_client=client)

    assert usd_rate == Decimal("1") / Decimal("1.1")
    assert gbp_rate == Decimal("1") / Decimal("0.85")
    await client.aclose()


async def test_get_rate_to_eur_falls_back_when_api_unreachable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    rate = await get_rate_to_eur("USD", http_client=client)

    assert rate == currency_module.FALLBACK_RATES_TO_EUR["USD"]
    await client.aclose()


async def test_get_rate_to_eur_unknown_currency_without_fallback_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"base": "EUR", "rates": {"USD": 1.1}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    rate = await get_rate_to_eur("XYZ", http_client=client)

    assert rate is None
    await client.aclose()
