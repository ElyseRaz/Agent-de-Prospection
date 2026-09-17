import uuid
from decimal import Decimal

import pytest

from app.models.llm import LLMCall
from tests.conftest import promote_to_admin

pytestmark = pytest.mark.asyncio

ADMIN_PAYLOAD = {"email": "admin-user@example.com", "password": "S3curePassw0rd!"}
REGULAR_PAYLOAD = {"email": "regular-user@example.com", "password": "S3curePassw0rd!"}


async def _register_and_login(client, payload: dict) -> str:
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    return response.json()["access_token"]


async def _login_as_admin(client, db_session) -> str:
    token = await _register_and_login(client, ADMIN_PAYLOAD)
    await promote_to_admin(db_session, ADMIN_PAYLOAD["email"])
    return token


async def _make_llm_call(db_session, **overrides) -> LLMCall:
    defaults = dict(
        purpose="extract_job",
        model="claude-sonnet-5",
        prompt_version="extract_job_v1",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.001"),
        cache_hit=False,
        content_hash="a" * 64,
    )
    defaults.update(overrides)
    call = LLMCall(**defaults)
    db_session.add(call)
    await db_session.commit()
    return call


async def test_llm_usage_requires_admin(client):
    token = await _register_and_login(client, REGULAR_PAYLOAD)
    response = await client.get(
        "/api/v1/admin/llm-usage", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_llm_usage_aggregates_calls(client, db_session):
    await _make_llm_call(db_session, cost_usd=Decimal("0.0010"))
    await _make_llm_call(db_session, cost_usd=Decimal("0.0020"), cache_hit=True)
    token = await _login_as_admin(client, db_session)

    response = await client.get(
        "/api/v1/admin/llm-usage", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_calls"] == 2
    assert len(body["buckets"]) == 1
    bucket = body["buckets"][0]
    assert bucket["calls"] == 2
    assert bucket["cache_hits"] == 1
    assert Decimal(bucket["cost_usd"]) == Decimal("0.0030")


async def test_admin_list_and_update_user(client, db_session):
    other_token = await _register_and_login(client, REGULAR_PAYLOAD)
    admin_token = await _login_as_admin(client, db_session)

    list_response = await client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert list_response.status_code == 200
    emails = {user["email"] for user in list_response.json()}
    assert REGULAR_PAYLOAD["email"] in emails
    assert ADMIN_PAYLOAD["email"] in emails

    regular_user_id = next(
        user["id"] for user in list_response.json() if user["email"] == REGULAR_PAYLOAD["email"]
    )
    update_response = await client.patch(
        f"/api/v1/admin/users/{regular_user_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    # L'utilisateur desactive ne peut plus se reconnecter (verifie le durcissement).
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGULAR_PAYLOAD["email"], "password": REGULAR_PAYLOAD["password"]},
    )
    assert login_response.status_code == 403
    assert other_token  # ancien token deja emis, non revoque retroactivement (JWT stateless)


async def test_admin_cannot_demote_self(client, db_session):
    admin_token = await _login_as_admin(client, db_session)
    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    admin_id = me_response.json()["id"]

    response = await client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


async def test_admin_stats(client, db_session):
    token = await _login_as_admin(client, db_session)
    response = await client.get(
        "/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["users_total"] >= 1
    assert "jobs_total" in body


async def test_admin_update_user_not_found(client, db_session):
    token = await _login_as_admin(client, db_session)
    response = await client.patch(
        f"/api/v1/admin/users/{uuid.uuid4()}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
