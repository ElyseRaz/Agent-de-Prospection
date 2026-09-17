import uuid

import pytest

from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source

pytestmark = pytest.mark.asyncio

OWNER_PAYLOAD = {"email": "app-owner@example.com", "password": "S3curePassw0rd!"}
OTHER_PAYLOAD = {"email": "app-other@example.com", "password": "S3curePassw0rd!"}


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
        title="Senior Backend Engineer",
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


async def _create_profile(client, token: str) -> str:
    response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


async def test_create_application_and_list(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)
    profile_id = await _create_profile(client, token)

    create_response = await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201
    assert create_response.json()["stage"] == "spotted"

    list_response = await client.get(
        f"/api/v1/profiles/{profile_id}/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_create_application_is_idempotent(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)
    profile_id = await _create_profile(client, token)

    first = await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    second = await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.json()["id"] == second.json()["id"]


async def test_update_stage_records_event_and_sets_applied_at(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)
    profile_id = await _create_profile(client, token)

    create_response = await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    application_id = create_response.json()["id"]

    stage_response = await client.patch(
        f"/api/v1/profiles/{profile_id}/applications/{application_id}/stage",
        json={"stage": "applied"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stage_response.status_code == 200
    assert stage_response.json()["stage"] == "applied"
    assert stage_response.json()["applied_at"] is not None

    detail_response = await client.get(
        f"/api/v1/profiles/{profile_id}/applications/{application_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    events = detail_response.json()["events"]
    assert len(events) == 1
    assert events[0]["type"] == "stage_changed"
    assert events[0]["payload"] == {"from": "spotted", "to": "applied"}


async def test_update_notes(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)
    profile_id = await _create_profile(client, token)

    create_response = await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    application_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/profiles/{profile_id}/applications/{application_id}",
        json={"notes": "Contact envoye par email"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["notes"] == "Contact envoye par email"


async def test_application_not_visible_to_other_user(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    owner_token = await _register_and_login(client, OWNER_PAYLOAD)
    profile_id = await _create_profile(client, owner_token)

    await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    other_token = await _register_and_login(client, OTHER_PAYLOAD)
    response = await client.get(
        f"/api/v1/profiles/{profile_id}/applications",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_delete_application(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)
    profile_id = await _create_profile(client, token)

    create_response = await client.post(
        f"/api/v1/profiles/{profile_id}/applications",
        json={"job_id": str(job.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    application_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/profiles/{profile_id}/applications/{application_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204

    list_response = await client.get(
        f"/api/v1/profiles/{profile_id}/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.json() == []


async def test_applications_require_authentication(client):
    response = await client.get(f"/api/v1/profiles/{uuid.uuid4()}/applications")
    assert response.status_code == 401
