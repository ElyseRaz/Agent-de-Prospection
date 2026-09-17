from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingBackend
from app.models.alert import AlertFrequency, AlertNotification, SavedSearch
from app.models.job import ContractType, Job, JobStatus, RemoteType, SeniorityLevel
from app.models.user import User
from app.notifications.base import NotificationChannel, NotificationError
from app.services.search import JobSearchFilters, hybrid_search_jobs

log = structlog.get_logger(__name__)


@dataclass(slots=True)
class AlertEvaluationResult:
    jobs_considered: int
    new_notifications: int


@dataclass(slots=True)
class AlertRunSummary:
    evaluated: int
    notifications_sent: int


def _filters_from_json(data: dict) -> JobSearchFilters:
    def _decimal(key: str) -> Decimal | None:
        value = data.get(key)
        return Decimal(str(value)) if value not in (None, "") else None

    return JobSearchFilters(
        rate_min_eur=_decimal("rate_min_eur"),
        rate_max_eur=_decimal("rate_max_eur"),
        rate_currency=data.get("rate_currency"),
        skill_slugs=list(data.get("skill") or []),
        seniority=SeniorityLevel(data["seniority"]) if data.get("seniority") else None,
        language=data.get("language"),
        remote_type=RemoteType(data["remote_type"]) if data.get("remote_type") else None,
        contract_type=ContractType(data["contract_type"]) if data.get("contract_type") else None,
        source_slug=data.get("source_slug"),
        status=JobStatus.ACTIVE,
    )


def _format_alert_body(saved_search: SavedSearch, job: Job) -> str:
    if job.rate_min or job.rate_max:
        rate = f"{job.rate_min or '?'}-{job.rate_max or '?'} {job.rate_currency or ''}".strip()
    else:
        rate = "TJM non precise"
    return (
        f'Nouvelle offre pour votre recherche sauvegardee "{saved_search.name}" :\n\n'
        f"{job.title}\n{rate}\n{job.url}"
    )


def _is_due(saved_search: SavedSearch, *, now: datetime) -> bool:
    if not saved_search.is_active:
        return False
    if saved_search.last_run_at is None:
        return True
    if saved_search.frequency == AlertFrequency.DAILY:
        return now - saved_search.last_run_at >= timedelta(hours=24)
    return True


async def evaluate_saved_search(
    db: AsyncSession,
    saved_search: SavedSearch,
    *,
    embedding_backend: EmbeddingBackend | None,
    channels: dict[str, NotificationChannel],
    user_email: str,
    now: datetime | None = None,
    limit: int = 20,
) -> AlertEvaluationResult:
    """Cherche les offres nouvelles depuis le dernier passage (memes filtres
    que `GET /jobs/search`, triees par fraicheur), notifie celles pas encore
    vues (idempotence via `uq_alert_notifications_search_job`), avance
    `last_run_at`. Une panne d'un canal n'empeche jamais les autres canaux
    ni les autres offres d'etre traites (voir `NotificationError`)."""

    now = now or datetime.now(UTC)
    filters = _filters_from_json(saved_search.filters)
    query = saved_search.filters.get("q")

    results, _ = await hybrid_search_jobs(
        db,
        query=query,
        filters=filters,
        embedding_backend=embedding_backend,
        sort="freshness",
        limit=limit,
    )

    candidates = results
    if saved_search.last_run_at is not None:
        candidates = [r for r in candidates if r.job.detected_at > saved_search.last_run_at]

    new_notifications = 0

    for result in candidates:
        job = result.job
        already_notified = await db.scalar(
            select(AlertNotification.id).where(
                AlertNotification.saved_search_id == saved_search.id,
                AlertNotification.job_id == job.id,
            )
        )
        if already_notified is not None:
            continue

        sent_channels: list[str] = []
        for channel_kind in saved_search.channels:
            channel = channels.get(channel_kind)
            if channel is None:
                log.warning(
                    "alert_channel_not_configured",
                    channel=channel_kind,
                    saved_search_id=str(saved_search.id),
                )
                continue
            try:
                await channel.send(
                    to=user_email,
                    subject=f"RemoteRadar - nouvelle offre : {job.title}",
                    body=_format_alert_body(saved_search, job),
                )
                sent_channels.append(channel_kind)
            except NotificationError:
                log.warning(
                    "alert_notification_failed",
                    channel=channel_kind,
                    job_id=str(job.id),
                    saved_search_id=str(saved_search.id),
                )

        if sent_channels:
            db.add(
                AlertNotification(
                    saved_search_id=saved_search.id, job_id=job.id, channels_sent=sent_channels
                )
            )
            new_notifications += 1

    saved_search.last_run_at = now
    db.add(saved_search)
    await db.commit()

    return AlertEvaluationResult(
        jobs_considered=len(candidates), new_notifications=new_notifications
    )


async def evaluate_due_saved_searches(
    db: AsyncSession,
    *,
    embedding_backend: EmbeddingBackend | None,
    channels: dict[str, NotificationChannel],
    now: datetime | None = None,
) -> AlertRunSummary:
    """Evalue toutes les recherches sauvegardees actives dont la frequence
    est echue (INSTANT : a chaque passage du beat : DAILY : au moins 24h
    depuis le dernier passage). Destinee a la tache Celery Beat periodique."""

    now = now or datetime.now(UTC)
    rows = (
        await db.execute(
            select(SavedSearch, User.email)
            .join(User, User.id == SavedSearch.user_id)
            .where(SavedSearch.is_active.is_(True))
        )
    ).all()

    evaluated = 0
    notifications_sent = 0
    for saved_search, user_email in rows:
        if not _is_due(saved_search, now=now):
            continue
        result = await evaluate_saved_search(
            db,
            saved_search,
            embedding_backend=embedding_backend,
            channels=channels,
            user_email=user_email,
            now=now,
        )
        evaluated += 1
        notifications_sent += result.new_notifications

    return AlertRunSummary(evaluated=evaluated, notifications_sent=notifications_sent)
