import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.models.job import ContractType, Job, JobSkill, RemoteType
from app.models.source import AccessType, ProcessingStatus, RawDocument, Source
from app.normalization.llm_extraction import ExtractionValidationError
from app.services.normalization import (
    NormalizationError,
    normalize_pending_documents,
    normalize_raw_document,
)
from tests.conftest import FakeEmbeddingBackend, FakeJobExtractionBackend, make_extracted_job

pytestmark = pytest.mark.asyncio

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "remotive_response.json"


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
        content_hash="b" * 64,
        raw_payload=payload,
        processing_status=ProcessingStatus.PENDING,
    )
    db_session.add(raw_document)
    await db_session.commit()
    await db_session.refresh(source)
    await db_session.refresh(raw_document)
    return source, raw_document


async def test_normalize_raw_document_creates_job(db_session):
    source, raw_document = await _seed_source_and_raw_document(db_session)
    extracted = make_extracted_job()
    backend = FakeJobExtractionBackend([extracted])
    http_client = _frankfurter_client()

    job = await normalize_raw_document(
        db_session,
        raw_document,
        source=source,
        backend=backend,
        embedding_backend=FakeEmbeddingBackend(),
        http_client=http_client,
        model="claude-sonnet-5",
    )
    await http_client.aclose()

    assert job is not None
    assert job.title == extracted.title
    assert job.contract_type == ContractType.FREELANCE
    assert job.remote_type == RemoteType.FULL_REMOTE
    assert job.rate_currency == "USD"
    assert job.rate_max == 600
    assert job.rate_eur_normalized is not None
    assert job.quality_score > 0
    assert job.embedding is not None
    assert job.dedup_hash is not None

    refreshed_doc = await db_session.get(RawDocument, raw_document.id)
    assert refreshed_doc.processing_status == ProcessingStatus.PROCESSED
    assert refreshed_doc.processed_at is not None

    links = (
        (await db_session.execute(select(JobSkill).where(JobSkill.job_id == job.id)))
        .scalars()
        .all()
    )
    assert len(links) == 3  # Python, FastAPI, PostgreSQL


async def test_normalize_skips_already_processed_document(db_session):
    source, raw_document = await _seed_source_and_raw_document(db_session)
    raw_document.processing_status = ProcessingStatus.PROCESSED
    await db_session.commit()

    backend = FakeJobExtractionBackend([])
    http_client = _frankfurter_client()

    result = await normalize_raw_document(
        db_session,
        raw_document,
        source=source,
        backend=backend,
        embedding_backend=FakeEmbeddingBackend(),
        http_client=http_client,
        model="claude-sonnet-5",
    )
    await http_client.aclose()

    assert result is None
    assert backend.calls == 0


async def test_normalize_force_reprocesses_already_processed_document(db_session):
    source, raw_document = await _seed_source_and_raw_document(db_session)
    raw_document.processing_status = ProcessingStatus.PROCESSED
    await db_session.commit()

    extracted = make_extracted_job(title="Titre mis a jour")
    backend = FakeJobExtractionBackend([extracted])
    http_client = _frankfurter_client()

    job = await normalize_raw_document(
        db_session,
        raw_document,
        source=source,
        backend=backend,
        embedding_backend=FakeEmbeddingBackend(),
        http_client=http_client,
        model="claude-sonnet-5",
        force=True,
    )
    await http_client.aclose()

    assert job is not None
    assert job.title == "Titre mis a jour"


async def test_normalize_marks_document_failed_after_exhausted_retries(db_session):
    source, raw_document = await _seed_source_and_raw_document(db_session)
    backend = FakeJobExtractionBackend(
        [
            ExtractionValidationError("echec 1"),
            ExtractionValidationError("echec 2"),
            ExtractionValidationError("echec 3"),
        ]
    )
    http_client = _frankfurter_client()

    with pytest.raises(NormalizationError):
        await normalize_raw_document(
            db_session,
            raw_document,
            source=source,
            backend=backend,
            embedding_backend=FakeEmbeddingBackend(),
            http_client=http_client,
            model="claude-sonnet-5",
        )
    await http_client.aclose()

    refreshed_doc = await db_session.get(RawDocument, raw_document.id)
    assert refreshed_doc.processing_status == ProcessingStatus.FAILED

    jobs = (await db_session.execute(select(Job))).scalars().all()
    assert jobs == []


async def test_normalize_pending_documents_processes_batch(db_session):
    _, raw_document = await _seed_source_and_raw_document(db_session)
    extracted = make_extracted_job()
    backend = FakeJobExtractionBackend([extracted])
    http_client = _frankfurter_client()

    summary = await normalize_pending_documents(
        db_session,
        backend=backend,
        embedding_backend=FakeEmbeddingBackend(),
        http_client=http_client,
        model="claude-sonnet-5",
        limit=10,
    )
    await http_client.aclose()

    assert summary.processed == 1
    assert summary.failed == 0
    assert summary.skipped == 0

    refreshed_doc = await db_session.get(RawDocument, raw_document.id)
    assert refreshed_doc.processing_status == ProcessingStatus.PROCESSED
