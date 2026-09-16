import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.collectors.http import CircuitBreaker, InMemoryCounterStore
from app.models.source import AccessType, RawDocument, ScrapeRunStatus, Source
from app.services.collection import DryRunResult, run_collection

pytestmark = pytest.mark.asyncio

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "remotive_response.json"


def _mock_client() -> httpx.AsyncClient:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


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
    await db_session.commit()
    await db_session.refresh(source)
    return source


async def test_collection_inserts_raw_documents(db_session):
    source = await _make_source(db_session)
    client = _mock_client()
    breaker = CircuitBreaker(InMemoryCounterStore())

    run = await run_collection(db_session, source, http_client=client, circuit_breaker=breaker)

    assert run.status == ScrapeRunStatus.SUCCESS
    assert run.items_fetched == 3
    assert run.items_new == 3
    assert run.items_updated == 0

    rows = (
        (await db_session.execute(select(RawDocument).where(RawDocument.source_id == source.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 3
    assert {row.processing_status.value for row in rows} == {"pending"}
    await client.aclose()


async def test_collection_is_idempotent_on_replay(db_session):
    source = await _make_source(db_session)
    breaker = CircuitBreaker(InMemoryCounterStore())

    client1 = _mock_client()
    await run_collection(db_session, source, http_client=client1, circuit_breaker=breaker)
    await client1.aclose()

    client2 = _mock_client()
    run2 = await run_collection(db_session, source, http_client=client2, circuit_breaker=breaker)
    await client2.aclose()

    assert run2.items_new == 0
    assert run2.items_updated == 0

    rows = (
        (await db_session.execute(select(RawDocument).where(RawDocument.source_id == source.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 3  # toujours 3, aucun doublon apres la deuxieme collecte


async def test_collection_updates_changed_content(db_session):
    source = await _make_source(db_session)
    breaker = CircuitBreaker(InMemoryCounterStore())

    client1 = _mock_client()
    await run_collection(db_session, source, http_client=client1, circuit_breaker=breaker)
    await client1.aclose()

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["jobs"][0]["title"] = "Staff Backend Engineer"  # contenu modifie

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client2 = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    run2 = await run_collection(db_session, source, http_client=client2, circuit_breaker=breaker)
    await client2.aclose()

    assert run2.items_new == 0
    assert run2.items_updated == 1

    updated = await db_session.scalar(
        select(RawDocument).where(
            RawDocument.source_id == source.id, RawDocument.external_id == "1234567"
        )
    )
    assert updated.raw_payload["title"] == "Staff Backend Engineer"


async def test_dry_run_does_not_write_to_db(db_session):
    source = await _make_source(db_session)
    client = _mock_client()
    breaker = CircuitBreaker(InMemoryCounterStore())

    result = await run_collection(
        db_session, source, dry_run=True, http_client=client, circuit_breaker=breaker
    )

    assert isinstance(result, DryRunResult)
    assert result.items_fetched == 3
    assert len(result.sample) == 3

    rows = (
        (await db_session.execute(select(RawDocument).where(RawDocument.source_id == source.id)))
        .scalars()
        .all()
    )
    assert rows == []
    await client.aclose()
