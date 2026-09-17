import uuid

import pytest

from app.api.deps import get_embedding_backend, get_notification_channels
from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source
from tests.conftest import FakeEmbeddingBackend, FakeNotificationChannel

pytestmark = pytest.mark.asyncio

OWNER_PAYLOAD = {"email": "alerts-owner@example.com", "password": "S3curePassw0rd!"}
OTHER_PAYLOAD = {"email": "alerts-other@example.com", "password": "S3curePassw0rd!"}


async def _register_and_login(client, payload: dict) -> str:
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    return response.json()["access_token"]


async def _make_source(db_session) -> Source:
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
    await db_session.flush()
    return source


async def _make_job(db_session, source, **overrides) -> Job:
    defaults = dict(
        source_id=source.id,
        external_id=str(uuid.uuid4()),
        url="https://example.com/job",
        title="Ingenieur Python remote",
        description_clean="Mission freelance Python, full remote.",
        prompt_version="extract_job_v1",
        status=JobStatus.ACTIVE,
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_create_and_list_saved_search(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)

    create_response = await client.post(
        "/api/v1/saved-searches",
        json={"name": "Python remote", "filters": {"language": "en"}, "channels": ["email"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["name"] == "Python remote"
    assert body["frequency"] == "instant"

    list_response = await client.get(
        "/api/v1/saved-searches", headers={"Authorization": f"Bearer {token}"}
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_create_saved_search_rejects_unknown_channel(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)

    response = await client.post(
        "/api/v1/saved-searches",
        json={"name": "Python remote", "channels": ["carrier-pigeon"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


async def test_update_saved_search(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/saved-searches",
        json={"name": "Python remote", "channels": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    saved_search_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/saved-searches/{saved_search_id}",
        json={"is_active": False, "frequency": "daily"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False
    assert update_response.json()["frequency"] == "daily"


async def test_saved_search_not_visible_to_other_user(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/saved-searches",
        json={"name": "Python remote", "channels": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    saved_search_id = create_response.json()["id"]

    other_token = await _register_and_login(client, OTHER_PAYLOAD)
    response = await client.get(
        f"/api/v1/saved-searches/{saved_search_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_delete_saved_search(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/saved-searches",
        json={"name": "Python remote", "channels": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    saved_search_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/saved-searches/{saved_search_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    list_response = await client.get(
        "/api/v1/saved-searches", headers={"Authorization": f"Bearer {token}"}
    )
    assert list_response.json() == []


async def test_run_saved_search_sends_notification(client, db_session, app):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)

    create_response = await client.post(
        "/api/v1/saved-searches",
        json={"name": "Python remote", "channels": ["email"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    saved_search_id = create_response.json()["id"]

    channel = FakeNotificationChannel()
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    app.dependency_overrides[get_notification_channels] = lambda: {"email": channel}
    try:
        run_response = await client.post(
            f"/api/v1/saved-searches/{saved_search_id}/run",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert run_response.status_code == 200
        assert run_response.json()["new_notifications"] == 1
        assert len(channel.sent) == 1
    finally:
        app.dependency_overrides.clear()


async def test_saved_searches_require_authentication(client):
    response = await client.get("/api/v1/saved-searches")
    assert response.status_code == 401
