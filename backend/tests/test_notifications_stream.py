import uuid

import pytest

from app.api.routes.notifications import _stream_notifications
from app.core.security import hash_password
from app.models.alert import AlertFrequency, AlertNotification, SavedSearch
from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


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


async def _make_user(db_session, email: str) -> User:
    user = User(email=email, password_hash=hash_password("S3curePassw0rd!"), role=UserRole.USER)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_stream_notifications_yields_existing_notification(db_session, engine_and_session):
    _, session_factory = engine_and_session
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    user = await _make_user(db_session, "stream-user@example.com")

    saved_search = SavedSearch(
        user_id=user.id, name="x", filters={}, channels=["email"], frequency=AlertFrequency.INSTANT
    )
    db_session.add(saved_search)
    await db_session.commit()
    await db_session.refresh(saved_search)

    db_session.add(
        AlertNotification(saved_search_id=saved_search.id, job_id=job.id, channels_sent=["email"])
    )
    await db_session.commit()

    chunks = [
        chunk
        async for chunk in _stream_notifications(
            session_factory, user.id, poll_interval=0, max_polls=1
        )
    ]

    assert any("event: notification" in chunk for chunk in chunks)
    assert any(job.title in chunk for chunk in chunks)
    assert any(": keep-alive" in chunk for chunk in chunks)


async def test_stream_notifications_does_not_leak_other_users(db_session, engine_and_session):
    _, session_factory = engine_and_session
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    owner = await _make_user(db_session, "stream-owner@example.com")
    outsider = await _make_user(db_session, "stream-outsider@example.com")

    saved_search = SavedSearch(
        user_id=owner.id, name="x", filters={}, channels=["email"], frequency=AlertFrequency.INSTANT
    )
    db_session.add(saved_search)
    await db_session.commit()
    await db_session.refresh(saved_search)

    db_session.add(
        AlertNotification(saved_search_id=saved_search.id, job_id=job.id, channels_sent=["email"])
    )
    await db_session.commit()

    chunks = [
        chunk
        async for chunk in _stream_notifications(
            session_factory, outsider.id, poll_interval=0, max_polls=1
        )
    ]

    assert not any("event: notification" in chunk for chunk in chunks)
    assert any(": keep-alive" in chunk for chunk in chunks)


async def test_stream_notifications_does_not_repeat_across_polls(db_session, engine_and_session):
    _, session_factory = engine_and_session
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    user = await _make_user(db_session, "stream-repeat@example.com")

    saved_search = SavedSearch(
        user_id=user.id, name="x", filters={}, channels=["email"], frequency=AlertFrequency.INSTANT
    )
    db_session.add(saved_search)
    await db_session.commit()
    await db_session.refresh(saved_search)

    db_session.add(
        AlertNotification(saved_search_id=saved_search.id, job_id=job.id, channels_sent=["email"])
    )
    await db_session.commit()

    chunks = [
        chunk
        async for chunk in _stream_notifications(
            session_factory, user.id, poll_interval=0, max_polls=3
        )
    ]

    assert sum(1 for chunk in chunks if "event: notification" in chunk) == 1
    assert sum(1 for chunk in chunks if ": keep-alive" in chunk) == 3
