import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_user, get_current_user_sse, get_db, get_session_factory
from app.models.alert import AlertNotification, SavedSearch
from app.models.job import Job
from app.models.user import User
from app.schemas.alert import AlertNotificationRead

router = APIRouter(prefix="/notifications", tags=["alerts"])

NOTIFICATION_POLL_INTERVAL_SECONDS = 2.0
NOTIFICATION_STREAM_BACKLOG = 50


async def _stream_notifications(
    session_factory: async_sessionmaker,
    user_id: uuid.UUID,
    *,
    poll_interval: float = NOTIFICATION_POLL_INTERVAL_SECONDS,
    max_polls: int | None = None,
) -> AsyncGenerator[str, None]:
    """Genere des frames SSE en interrogeant `alert_notifications` a
    intervalle regulier (pas de bus d'evenements dedie : la table sert deja
    de journal idempotent, l'interroger evite d'introduire Redis Pub/Sub pour
    un seul flux). `max_polls` permet un arret deterministe en test ; `None`
    (defaut production) boucle jusqu'a la deconnexion du client."""

    seen_ids: set[uuid.UUID] = set()
    polls = 0

    while max_polls is None or polls < max_polls:
        async with session_factory() as db:
            rows = (
                await db.execute(
                    select(AlertNotification, Job.title, Job.url)
                    .join(SavedSearch, SavedSearch.id == AlertNotification.saved_search_id)
                    .join(Job, Job.id == AlertNotification.job_id)
                    .where(SavedSearch.user_id == user_id)
                    .order_by(AlertNotification.sent_at.desc())
                    .limit(NOTIFICATION_STREAM_BACKLOG)
                )
            ).all()

        for notification, job_title, job_url in reversed(rows):
            if notification.id in seen_ids:
                continue
            seen_ids.add(notification.id)
            payload = {
                "id": str(notification.id),
                "job_id": str(notification.job_id),
                "job_title": job_title,
                "job_url": job_url,
                "channels_sent": notification.channels_sent,
                "sent_at": notification.sent_at.isoformat(),
            }
            yield f"event: notification\ndata: {json.dumps(payload)}\n\n"

        yield ": keep-alive\n\n"
        polls += 1
        if max_polls is None or polls < max_polls:
            await asyncio.sleep(poll_interval)


@router.get("/stream")
async def stream_notifications(
    current_user: User = Depends(get_current_user_sse),
    session_factory: async_sessionmaker = Depends(get_session_factory),
) -> StreamingResponse:
    return StreamingResponse(
        _stream_notifications(session_factory, current_user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("", response_model=list[AlertNotificationRead])
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AlertNotification]:
    rows = (
        await db.execute(
            select(AlertNotification)
            .join(SavedSearch, SavedSearch.id == AlertNotification.saved_search_id)
            .where(SavedSearch.user_id == current_user.id)
            .order_by(AlertNotification.sent_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)
