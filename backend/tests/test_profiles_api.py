import uuid

import pytest
from sqlalchemy import select

from app.api.deps import get_embedding_backend
from app.models.job import Job, JobStatus
from app.models.skill import Skill
from app.models.source import AccessType, Source
from tests.conftest import FakeEmbeddingBackend

pytestmark = pytest.mark.asyncio

OWNER_PAYLOAD = {"email": "owner@example.com", "password": "S3curePassw0rd!"}
OTHER_PAYLOAD = {"email": "other@example.com", "password": "S3curePassw0rd!"}


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


async def test_create_and_list_profile(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)

    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer", "target_rate": "500", "floor_rate": "350"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201

    list_response = await client.get(
        "/api/v1/profiles", headers={"Authorization": f"Bearer {token}"}
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_profile_not_visible_to_other_user(client, db_session):
    owner_token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    profile_id = create_response.json()["id"]

    other_token = await _register_and_login(client, OTHER_PAYLOAD)
    response = await client.get(
        f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert response.status_code == 403


async def test_update_and_delete_profile(client):
    token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/profiles/{profile_id}",
        json={"target_rate": "600"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["target_rate"] == "600.00"

    delete_response = await client.delete(
        f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404


async def test_set_profile_skills_recomputes_embedding(client, db_session, app):
    token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = create_response.json()["id"]

    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    try:
        response = await client.put(
            f"/api/v1/profiles/{profile_id}/skills",
            json=[
                {"skill_slug": "Python", "level": "expert", "is_required": True},
                {"skill_slug": "FastAPI", "level": "advanced", "is_required": False},
            ],
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["skills"]) == 2
        slugs = {s["skill_slug"] for s in body["skills"]}
        assert slugs == {"python", "fastapi"}
    finally:
        app.dependency_overrides.clear()

    skills = (await db_session.execute(select(Skill))).scalars().all()
    assert len(skills) == 2


async def test_get_matches_returns_ranked_results(client, db_session, app):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)

    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/profiles/{profile_id}/matches", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 1
    assert "breakdown" in body["results"][0]
    assert len(body["results"][0]["breakdown"]) == 5


async def test_matches_forbidden_for_non_owner(client, db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    owner_token = await _register_and_login(client, OWNER_PAYLOAD)
    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    profile_id = create_response.json()["id"]

    other_token = await _register_and_login(client, OTHER_PAYLOAD)
    response = await client.get(
        f"/api/v1/profiles/{profile_id}/matches",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_post_match_feedback(client, db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    token = await _register_and_login(client, OWNER_PAYLOAD)

    create_response = await client.post(
        "/api/v1/profiles",
        json={"name": "Data Engineer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    profile_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/profiles/{profile_id}/matches/{job.id}/feedback",
        json={"action": "saved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


async def test_profiles_require_authentication(client):
    response = await client.get("/api/v1/profiles")
    assert response.status_code == 401
