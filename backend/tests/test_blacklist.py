import pytest

from app.models.blacklist import BlacklistEntityType
from app.services.blacklist import (
    add_blacklist_entry,
    find_shared_blacklist_entry,
    list_blacklist_entries,
)
from tests.conftest import promote_to_admin

pytestmark = pytest.mark.asyncio

REGISTER_PAYLOAD = {"email": "blacklist-user@example.com", "password": "S3curePassw0rd!"}


async def test_normalized_value_matches_company_normalization(db_session):
    await add_blacklist_entry(
        db_session,
        entity_type=BlacklistEntityType.COMPANY,
        value="  Écoles & Cie  ",
        reason="Test",
        user_id=None,
    )

    entry = await find_shared_blacklist_entry(
        db_session, entity_type=BlacklistEntityType.COMPANY, value="ecoles cie"
    )
    assert entry is not None


async def test_personal_entry_not_returned_by_shared_lookup(db_session):
    from app.models.user import User, UserRole

    user = User(
        email="owner@example.com", password_hash="x", role=UserRole.USER, is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await add_blacklist_entry(
        db_session,
        entity_type=BlacklistEntityType.RECRUITER,
        value="shady@example.com",
        reason=None,
        user_id=user.id,
    )

    shared = await find_shared_blacklist_entry(
        db_session, entity_type=BlacklistEntityType.RECRUITER, value="shady@example.com"
    )
    assert shared is None

    personal = await list_blacklist_entries(db_session, user_id=user.id)
    assert len(personal) == 1


async def _login(client) -> str:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    return response.json()["access_token"]


async def test_create_personal_entry_via_api(client):
    token = await _login(client)

    response = await client.post(
        "/api/v1/blacklist",
        json={"entity_type": "company", "value": "Bad Corp", "reason": "Non paye"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["value"] == "bad corp"
    assert body["user_id"] is not None


async def test_create_shared_entry_forbidden_for_non_admin(client):
    token = await _login(client)

    response = await client.post(
        "/api/v1/blacklist",
        json={"entity_type": "company", "value": "Bad Corp", "shared": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_create_shared_entry_allowed_for_admin(client, db_session):
    token = await _login(client)
    await promote_to_admin(db_session, REGISTER_PAYLOAD["email"])

    response = await client.post(
        "/api/v1/blacklist",
        json={"entity_type": "company", "value": "Bad Corp", "shared": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] is None


async def test_list_blacklist_requires_authentication(client):
    response = await client.get("/api/v1/blacklist")
    assert response.status_code == 401
