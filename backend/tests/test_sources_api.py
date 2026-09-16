import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.api.deps import get_circuit_breaker, get_http_client
from app.collectors.http import CircuitBreaker, InMemoryCounterStore
from app.models.source import AccessType, RawDocument, Source
from tests.conftest import promote_to_admin

pytestmark = pytest.mark.asyncio

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "remotive_response.json"
REGISTER_PAYLOAD = {"email": "sources-user@example.com", "password": "S3curePassw0rd!"}


def _mock_remotive_client() -> httpx.AsyncClient:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _seed_source(db_session) -> Source:
    source = Source(
        slug="remotive",
        name="Remotive",
        kind="remotive",
        base_url="https://remotive.com/api/remote-jobs",
        access_type=AccessType.API,
        schedule_cron="*/30 * * * *",
        rate_limit_rpm=20,
        compliance_note="API publique.",
        config={},
    )
    db_session.add(source)
    await db_session.commit()
    return source


async def _login(client) -> str:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    return response.json()["access_token"]


async def _login_as_admin(client, db_session) -> str:
    token = await _login(client)
    await promote_to_admin(db_session, REGISTER_PAYLOAD["email"])
    return token


async def test_list_sources_requires_authentication(client):
    response = await client.get("/api/v1/sources")
    assert response.status_code == 401


async def test_list_sources_returns_seeded_source(client, db_session):
    await _seed_source(db_session)
    token = await _login(client)

    response = await client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    slugs = [s["slug"] for s in response.json()]
    assert "remotive" in slugs


async def test_get_unknown_source_returns_404(client):
    token = await _login(client)
    response = await client.get(
        "/api/v1/sources/does-not-exist", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


async def test_collect_forbidden_for_non_admin(client, db_session):
    await _seed_source(db_session)
    token = await _login(client)

    response = await client.post(
        "/api/v1/sources/remotive/collect", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


async def test_collect_dry_run_does_not_persist(client, db_session, app):
    await _seed_source(db_session)
    token = await _login_as_admin(client, db_session)

    mock_client = _mock_remotive_client()
    app.dependency_overrides[get_http_client] = lambda: mock_client
    app.dependency_overrides[get_circuit_breaker] = lambda: CircuitBreaker(InMemoryCounterStore())

    try:
        response = await client.post(
            "/api/v1/sources/remotive/collect?dry_run=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is True
        assert body["dry_run_result"]["items_fetched"] == 3
        assert body["run"] is None

        rows = (await db_session.execute(select(RawDocument))).scalars().all()
        assert rows == []
    finally:
        await mock_client.aclose()
        app.dependency_overrides.clear()


async def test_collect_persists_raw_documents(client, db_session, app):
    await _seed_source(db_session)
    token = await _login_as_admin(client, db_session)

    mock_client = _mock_remotive_client()
    app.dependency_overrides[get_http_client] = lambda: mock_client
    app.dependency_overrides[get_circuit_breaker] = lambda: CircuitBreaker(InMemoryCounterStore())

    try:
        response = await client.post(
            "/api/v1/sources/remotive/collect", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is False
        assert body["run"]["status"] == "success"
        assert body["run"]["items_new"] == 3

        rows = (await db_session.execute(select(RawDocument))).scalars().all()
        assert len(rows) == 3
    finally:
        await mock_client.aclose()
        app.dependency_overrides.clear()
