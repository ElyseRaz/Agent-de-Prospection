import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source
from app.services.expiry import mark_expired_jobs

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
        title="Job",
        prompt_version="extract_job_v1",
        status=JobStatus.ACTIVE,
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_mark_expired_jobs_flags_stale_active_jobs(db_session):
    source = await _make_source(db_session)
    stale_job = await _make_job(db_session, source)
    fresh_job = await _make_job(db_session, source, external_id=str(uuid.uuid4()))

    stale_date = datetime.now(UTC) - timedelta(days=30)
    await db_session.execute(
        update(Job).where(Job.id == stale_job.id).values(last_seen_at=stale_date)
    )
    await db_session.commit()

    count = await mark_expired_jobs(db_session, stale_days=14)

    assert count == 1

    await db_session.refresh(stale_job)
    await db_session.refresh(fresh_job)
    assert stale_job.status == JobStatus.EXPIRED
    assert stale_job.expires_at is not None
    assert fresh_job.status == JobStatus.ACTIVE


async def test_mark_expired_jobs_ignores_already_expired(db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source, status=JobStatus.EXPIRED)

    stale_date = datetime.now(UTC) - timedelta(days=30)
    await db_session.execute(update(Job).where(Job.id == job.id).values(last_seen_at=stale_date))
    await db_session.commit()

    count = await mark_expired_jobs(db_session, stale_days=14)

    assert count == 0
