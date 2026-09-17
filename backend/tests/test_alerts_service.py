import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.alert import AlertFrequency, AlertNotification, SavedSearch
from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source
from app.models.user import User, UserRole
from app.services.alerts import evaluate_due_saved_searches, evaluate_saved_search
from tests.conftest import FakeNotificationChannel

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


async def _make_user(db_session, email: str = "alert-user@example.com") -> User:
    user = User(email=email, password_hash=hash_password("S3curePassw0rd!"), role=UserRole.USER)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_saved_search(db_session, user, **overrides) -> SavedSearch:
    defaults = dict(
        user_id=user.id,
        name="Python remote",
        filters={},
        channels=["email"],
        frequency=AlertFrequency.INSTANT,
    )
    defaults.update(overrides)
    saved_search = SavedSearch(**defaults)
    db_session.add(saved_search)
    await db_session.commit()
    await db_session.refresh(saved_search)
    return saved_search


async def test_evaluate_saved_search_notifies_new_job(db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    user = await _make_user(db_session)
    saved_search = await _make_saved_search(db_session, user)

    channel = FakeNotificationChannel()
    result = await evaluate_saved_search(
        db_session,
        saved_search,
        embedding_backend=None,
        channels={"email": channel},
        user_email=user.email,
    )

    assert result.new_notifications == 1
    assert len(channel.sent) == 1
    assert channel.sent[0]["to"] == user.email
    assert job.title in channel.sent[0]["body"]

    notifications = (await db_session.execute(select(AlertNotification))).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].channels_sent == ["email"]
    assert notifications[0].job_id == job.id


async def test_evaluate_saved_search_is_idempotent(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    user = await _make_user(db_session)
    saved_search = await _make_saved_search(db_session, user)

    channel = FakeNotificationChannel()
    first = await evaluate_saved_search(
        db_session,
        saved_search,
        embedding_backend=None,
        channels={"email": channel},
        user_email=user.email,
        now=datetime.now(UTC),
    )
    # Second passage : meme offre, pas de nouveau detected_at depuis le
    # premier passage -> aucun candidat, et de toute facon deja notifiee.
    second = await evaluate_saved_search(
        db_session,
        saved_search,
        embedding_backend=None,
        channels={"email": channel},
        user_email=user.email,
        now=datetime.now(UTC),
    )

    assert first.new_notifications == 1
    assert second.new_notifications == 0
    assert len(channel.sent) == 1


async def test_evaluate_saved_search_channel_failure_does_not_block_others(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    user = await _make_user(db_session)
    saved_search = await _make_saved_search(db_session, user, channels=["email", "slack"])

    failing_channel = FakeNotificationChannel(fail=True)
    working_channel = FakeNotificationChannel()
    result = await evaluate_saved_search(
        db_session,
        saved_search,
        embedding_backend=None,
        channels={"email": failing_channel, "slack": working_channel},
        user_email=user.email,
    )

    assert result.new_notifications == 1
    assert len(failing_channel.sent) == 0
    assert len(working_channel.sent) == 1

    notification = (await db_session.execute(select(AlertNotification))).scalars().one()
    assert notification.channels_sent == ["slack"]


async def test_evaluate_saved_search_unconfigured_channel_is_skipped(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    user = await _make_user(db_session)
    saved_search = await _make_saved_search(db_session, user, channels=["telegram"])

    result = await evaluate_saved_search(
        db_session,
        saved_search,
        embedding_backend=None,
        channels={},
        user_email=user.email,
    )

    assert result.new_notifications == 0
    notifications = (await db_session.execute(select(AlertNotification))).scalars().all()
    assert notifications == []


async def test_evaluate_due_saved_searches_skips_daily_not_yet_due(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    user = await _make_user(db_session)
    await _make_saved_search(
        db_session,
        user,
        frequency=AlertFrequency.DAILY,
        last_run_at=datetime.now(UTC) - timedelta(hours=1),
    )

    channel = FakeNotificationChannel()
    summary = await evaluate_due_saved_searches(
        db_session, embedding_backend=None, channels={"email": channel}
    )

    assert summary.evaluated == 0
    assert summary.notifications_sent == 0
    assert channel.sent == []


async def test_evaluate_due_saved_searches_runs_instant_immediately(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    user = await _make_user(db_session)
    await _make_saved_search(db_session, user, frequency=AlertFrequency.INSTANT)

    channel = FakeNotificationChannel()
    summary = await evaluate_due_saved_searches(
        db_session, embedding_backend=None, channels={"email": channel}
    )

    assert summary.evaluated == 1
    assert summary.notifications_sent == 1
    assert len(channel.sent) == 1


async def test_evaluate_due_saved_searches_ignores_inactive(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    user = await _make_user(db_session)
    await _make_saved_search(db_session, user, is_active=False)

    channel = FakeNotificationChannel()
    summary = await evaluate_due_saved_searches(
        db_session, embedding_backend=None, channels={"email": channel}
    )

    assert summary.evaluated == 0
    assert channel.sent == []
