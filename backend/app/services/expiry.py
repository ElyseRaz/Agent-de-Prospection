from datetime import UTC, datetime, timedelta

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus

DEFAULT_STALE_DAYS = 14


async def mark_expired_jobs(db: AsyncSession, *, stale_days: int = DEFAULT_STALE_DAYS) -> int:
    """Marque EXPIRED les jobs ACTIVE non reconfirmes par une collecte depuis
    `stale_days`. Verification deliberement simple (basee sur `last_seen_at`) ;
    un controle HTTP reel (404 sur l'URL) est hors scope de cette phase."""

    cutoff = datetime.now(UTC) - timedelta(days=stale_days)
    stmt = (
        update(Job)
        .where(Job.status == JobStatus.ACTIVE, Job.last_seen_at < cutoff)
        .values(status=JobStatus.EXPIRED, expires_at=func.now())
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0
