import pyotp
import pytest

from tests.conftest import promote_to_admin

pytestmark = pytest.mark.asyncio

REGISTER_PAYLOAD = {"email": "freelance@example.com", "password": "S3curePassw0rd!"}


async def _register_and_login(client, payload=None):
    payload = payload or REGISTER_PAYLOAD
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    return response


async def test_register_creates_user(client):
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == REGISTER_PAYLOAD["email"]
    assert body["role"] == "user"
    assert body["totp_enabled"] is False
    assert "password" not in body


async def test_register_duplicate_email_rejected(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 409


async def test_login_success_returns_token_pair(client):
    response = await _register_and_login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password_rejected(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_me_requires_authentication(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user_with_valid_token(client):
    login_response = await _register_and_login(client)
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == REGISTER_PAYLOAD["email"]


async def test_refresh_token_issues_new_access_token(client):
    login_response = await _register_and_login(client)
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token_used_as_refresh(client):
    login_response = await _register_and_login(client)
    access_token = login_response.json()["access_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


async def test_totp_setup_then_verify_enables_2fa_and_login_requires_code(client):
    login_response = await _register_and_login(client)
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    setup_response = await client.post("/api/v1/auth/2fa/setup", headers=headers)
    assert setup_response.status_code == 200
    secret = setup_response.json()["secret"]

    code = pyotp.TOTP(secret).now()
    verify_response = await client.post(
        "/api/v1/auth/2fa/verify", json={"code": code}, headers=headers
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["totp_enabled"] is True

    login_without_code = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert login_without_code.status_code == 401

    login_with_code = await client.post(
        "/api/v1/auth/login",
        json={
            "email": REGISTER_PAYLOAD["email"],
            "password": REGISTER_PAYLOAD["password"],
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    assert login_with_code.status_code == 200


async def test_admin_route_forbidden_for_regular_user(client):
    login_response = await _register_and_login(client)
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/admin/ping", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 403


async def test_admin_route_allowed_for_admin_user(client, db_session):
    await _register_and_login(client)
    await promote_to_admin(db_session, REGISTER_PAYLOAD["email"])

    relogin_response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    access_token = relogin_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/admin/ping", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "admin"}
