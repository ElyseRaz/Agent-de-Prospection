import uuid

import pytest

from app.api.deps import get_embedding_backend, get_reputation_provider, get_risk_backend
from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source
from tests.conftest import (
    FakeEmbeddingBackend,
    FakeRiskAssessmentBackend,
    make_risk_assessment,
    promote_to_admin,
)

pytestmark = pytest.mark.asyncio

REGISTER_PAYLOAD = {"email": "jobs-user@example.com", "password": "S3curePassw0rd!"}


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
        description_clean="Mission freelance FastAPI, full remote.",
        prompt_version="extract_job_v1",
        status=JobStatus.ACTIVE,
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


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


async def test_search_requires_authentication(client, app):
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    try:
        response = await client.get("/api/v1/jobs/search")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


async def test_search_returns_results_for_authenticated_user(client, db_session, app):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    token = await _login(client)

    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    try:
        response = await client.get(
            "/api/v1/jobs/search", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["results"]) == 1
    finally:
        app.dependency_overrides.clear()


async def test_get_job_returns_404_for_unknown_id(client, app):
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    try:
        token = await _login(client)
        response = await client.get(
            f"/api/v1/jobs/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_get_job_lists_duplicate_urls(client, db_session, app):
    source = await _make_source(db_session)
    canonical = await _make_job(db_session, source, url="https://example.com/canonical")
    await _make_job(
        db_session,
        source,
        url="https://another-source.com/dup",
        external_id=str(uuid.uuid4()),
        canonical_id=canonical.id,
    )
    token = await _login(client)

    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    try:
        response = await client.get(
            f"/api/v1/jobs/{canonical.id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["duplicate_urls"] == ["https://another-source.com/dup"]
    finally:
        app.dependency_overrides.clear()


async def test_backfill_embeddings_forbidden_for_non_admin(client, app):
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()
    try:
        token = await _login(client)
        response = await client.post(
            "/api/v1/jobs/backfill-embeddings", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_backfill_embeddings_populates_missing_embeddings(client, db_session, app):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    assert job.embedding is None

    token = await _login_as_admin(client, db_session)
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()

    try:
        response = await client.post(
            "/api/v1/jobs/backfill-embeddings", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json() == {"embedded": 1, "skipped": 0}

        refreshed = await db_session.get(Job, job.id)
        assert refreshed.embedding is not None
        assert refreshed.dedup_hash is not None
    finally:
        app.dependency_overrides.clear()


async def test_mark_expired_forbidden_for_non_admin(client):
    token = await _login(client)
    response = await client.post(
        "/api/v1/jobs/mark-expired", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


async def test_assess_risk_forbidden_for_non_admin(client, app):
    app.dependency_overrides[get_risk_backend] = lambda: FakeRiskAssessmentBackend([])
    app.dependency_overrides[get_reputation_provider] = lambda: None
    try:
        token = await _login(client)
        response = await client.post(
            "/api/v1/jobs/assess-risk", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_assess_risk_evaluates_pending_jobs(client, db_session, app):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    token = await _login_as_admin(client, db_session)

    app.dependency_overrides[get_risk_backend] = lambda: FakeRiskAssessmentBackend(
        [make_risk_assessment(risk_score=42)]
    )
    app.dependency_overrides[get_reputation_provider] = lambda: None

    try:
        response = await client.post(
            "/api/v1/jobs/assess-risk", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json() == {"assessed": 1, "failed": 0}
    finally:
        app.dependency_overrides.clear()
