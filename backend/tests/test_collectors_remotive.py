import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.collectors.http import CircuitBreaker, InMemoryCounterStore
from app.collectors.remotive import RemotiveConnector

pytestmark = pytest.mark.asyncio

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "remotive_response.json"


def _mock_client() -> httpx.AsyncClient:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_yields_all_jobs_from_fixture():
    client = _mock_client()
    breaker = CircuitBreaker(InMemoryCounterStore())
    connector = RemotiveConnector(
        base_url="https://remotive.com/api/remote-jobs",
        config={},
        http_client=client,
        circuit_breaker=breaker,
    )

    docs = [doc async for doc in connector.fetch()]

    assert len(docs) == 3
    assert docs[0].external_id == "1234567"
    assert docs[0].raw_payload["title"] == "Senior Backend Engineer"
    assert docs[0].url.startswith("https://remotive.com/remote-jobs/")
    await client.aclose()


async def test_fetch_filters_by_since():
    client = _mock_client()
    breaker = CircuitBreaker(InMemoryCounterStore())
    connector = RemotiveConnector(
        base_url="https://remotive.com/api/remote-jobs",
        config={},
        http_client=client,
        circuit_breaker=breaker,
    )

    since = datetime(2026, 9, 1, tzinfo=UTC)
    docs = [doc async for doc in connector.fetch(since=since)]

    assert {d.external_id for d in docs} == {"1234567", "1234569"}
    await client.aclose()


async def test_fetch_passes_config_filters_as_query_params():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"jobs": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    breaker = CircuitBreaker(InMemoryCounterStore())
    connector = RemotiveConnector(
        base_url="https://remotive.com/api/remote-jobs",
        config={"category": "software-dev", "search": "python"},
        http_client=client,
        circuit_breaker=breaker,
    )

    _ = [doc async for doc in connector.fetch()]

    assert captured["params"] == {"category": "software-dev", "search": "python"}
    await client.aclose()
