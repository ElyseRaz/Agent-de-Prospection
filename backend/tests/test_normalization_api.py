import json
import uuid
from pathlib import Path

import httpx
import pytest

from app.api.deps import get_embedding_backend, get_http_client, get_llm_backend
from app.models.source import AccessType, ProcessingStatus, RawDocument, Source
from tests.conftest import (
    FakeEmbeddingBackend,
    FakeJobExtractionBackend,
    make_extracted_job,
    promote_to_admin,
)

pytestmark = pytest.mark.asyncio

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "remotive_response.json"
REGISTER_PAYLOAD = {"email": "normalization-user@example.com", "password": "S3curePassw0rd!"}


def _frankfurter_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"base": "EUR", "rates": {"USD": 1.1}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _seed_source_and_raw_document(db_session) -> tuple[Source, RawDocument]:
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

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["jobs"][0]
    raw_document = RawDocument(
        source_id=source.id,
        external_id=str(payload["id"]),
        url=payload["url"],
        content_hash="c" * 64,
        raw_payload=payload,
        processing_status=ProcessingStatus.PENDING,
    )
    db_session.add(raw_document)
    await db_session.commit()
    await db_session.refresh(source)
    await db_session.refresh(raw_document)
    return source, raw_document


async def _login_as_admin(client, db_session) -> str:
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    token = response.json()["access_token"]
    await promote_to_admin(db_session, REGISTER_PAYLOAD["email"])
    return token


async def _login(client) -> str:
    payload = {"email": "regular-user@example.com", "password": "S3curePassw0rd!"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    return response.json()["access_token"]


async def test_run_normalization_forbidden_for_non_admin(client, db_session):
    await _seed_source_and_raw_document(db_session)
    token = await _login(client)

    response = await client.post(
        "/api/v1/normalization/run", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


async def test_run_normalization_processes_pending_documents(client, db_session, app):
    _, raw_document = await _seed_source_and_raw_document(db_session)
    token = await _login_as_admin(client, db_session)

    backend = FakeJobExtractionBackend([make_extracted_job()])
    http_client = _frankfurter_client()
    app.dependency_overrides[get_llm_backend] = lambda: backend
    app.dependency_overrides[get_http_client] = lambda: http_client
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()

    try:
        response = await client.post(
            "/api/v1/normalization/run", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body == {"processed": 1, "failed": 0, "skipped": 0}

        refreshed = await db_session.get(RawDocument, raw_document.id)
        assert refreshed.processing_status == ProcessingStatus.PROCESSED
    finally:
        await http_client.aclose()
        app.dependency_overrides.clear()


async def test_run_normalization_unknown_source_slug_returns_404(client, db_session, app):
    token = await _login_as_admin(client, db_session)

    backend = FakeJobExtractionBackend([])
    http_client = _frankfurter_client()
    app.dependency_overrides[get_llm_backend] = lambda: backend
    app.dependency_overrides[get_http_client] = lambda: http_client
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()

    try:
        response = await client.post(
            "/api/v1/normalization/run?source_slug=does-not-exist",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        await http_client.aclose()
        app.dependency_overrides.clear()


async def test_reprocess_raw_document_returns_job_id(client, db_session, app):
    _, raw_document = await _seed_source_and_raw_document(db_session)
    token = await _login_as_admin(client, db_session)

    backend = FakeJobExtractionBackend([make_extracted_job()])
    http_client = _frankfurter_client()
    app.dependency_overrides[get_llm_backend] = lambda: backend
    app.dependency_overrides[get_http_client] = lambda: http_client
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()

    try:
        response = await client.post(
            f"/api/v1/raw-documents/{raw_document.id}/reprocess",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "processed"
        assert body["job_id"] is not None
    finally:
        await http_client.aclose()
        app.dependency_overrides.clear()


async def test_reprocess_unknown_raw_document_returns_404(client, db_session, app):
    token = await _login_as_admin(client, db_session)

    backend = FakeJobExtractionBackend([])
    http_client = _frankfurter_client()
    app.dependency_overrides[get_llm_backend] = lambda: backend
    app.dependency_overrides[get_http_client] = lambda: http_client
    app.dependency_overrides[get_embedding_backend] = lambda: FakeEmbeddingBackend()

    try:
        response = await client.post(
            f"/api/v1/raw-documents/{uuid.uuid4()}/reprocess",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
    finally:
        await http_client.aclose()
        app.dependency_overrides.clear()
