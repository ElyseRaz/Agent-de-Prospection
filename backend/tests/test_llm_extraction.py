import pytest
from sqlalchemy import select

from app.models.llm import LLMCall, LLMExtractionCache
from app.normalization.llm_extraction import (
    ExtractionValidationError,
    LLMUsage,
    extract_job_structured,
)
from tests.conftest import FakeJobExtractionBackend, make_extracted_job

pytestmark = pytest.mark.asyncio

CONTENT_HASH = "a" * 64


async def test_first_call_hits_backend_and_writes_cache_and_log(db_session):
    expected = make_extracted_job()
    backend = FakeJobExtractionBackend([expected])

    result = await extract_job_structured(
        db_session,
        backend=backend,
        content_hash=CONTENT_HASH,
        prompt_version="extract_job_v1",
        system_prompt="system",
        user_text="user text",
        model="claude-sonnet-5",
    )
    await db_session.commit()

    assert result.title == expected.title
    assert backend.calls == 1

    cache_rows = (await db_session.execute(select(LLMExtractionCache))).scalars().all()
    assert len(cache_rows) == 1
    assert cache_rows[0].content_hash == CONTENT_HASH

    call_rows = (await db_session.execute(select(LLMCall))).scalars().all()
    assert len(call_rows) == 1
    assert call_rows[0].cache_hit is False
    assert call_rows[0].cost_usd > 0


async def test_second_call_with_same_content_hash_hits_cache(db_session):
    expected = make_extracted_job()
    backend = FakeJobExtractionBackend([expected])

    await extract_job_structured(
        db_session,
        backend=backend,
        content_hash=CONTENT_HASH,
        prompt_version="extract_job_v1",
        system_prompt="system",
        user_text="user text",
        model="claude-sonnet-5",
    )
    await db_session.commit()

    # Le deuxieme appel ne doit JAMAIS toucher le backend (pas de second cout).
    backend_second_call = FakeJobExtractionBackend([])
    result = await extract_job_structured(
        db_session,
        backend=backend_second_call,
        content_hash=CONTENT_HASH,
        prompt_version="extract_job_v1",
        system_prompt="system",
        user_text="user text",
        model="claude-sonnet-5",
    )
    await db_session.commit()

    assert backend_second_call.calls == 0
    assert result.title == expected.title

    call_rows = (await db_session.execute(select(LLMCall))).scalars().all()
    assert len(call_rows) == 2
    assert call_rows[1].cache_hit is True
    assert call_rows[1].cost_usd == 0


async def test_retries_on_invalid_output_then_succeeds(db_session):
    expected = make_extracted_job()
    backend = FakeJobExtractionBackend(
        [ExtractionValidationError("JSON invalide"), expected]
    )

    result = await extract_job_structured(
        db_session,
        backend=backend,
        content_hash=CONTENT_HASH,
        prompt_version="extract_job_v1",
        system_prompt="system",
        user_text="user text",
        model="claude-sonnet-5",
        max_retries=2,
    )
    await db_session.commit()

    assert backend.calls == 2
    assert result.title == expected.title


async def test_raises_after_exhausting_retries(db_session):
    backend = FakeJobExtractionBackend(
        [
            ExtractionValidationError("echec 1"),
            ExtractionValidationError("echec 2"),
            ExtractionValidationError("echec 3"),
        ]
    )

    with pytest.raises(ExtractionValidationError):
        await extract_job_structured(
            db_session,
            backend=backend,
            content_hash=CONTENT_HASH,
            prompt_version="extract_job_v1",
            system_prompt="system",
            user_text="user text",
            model="claude-sonnet-5",
            max_retries=2,
        )

    assert backend.calls == 3

    cache_rows = (await db_session.execute(select(LLMExtractionCache))).scalars().all()
    assert cache_rows == []


def test_llm_usage_dataclass_fields():
    usage = LLMUsage(input_tokens=10, output_tokens=5, cost_usd=0.0001)
    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
