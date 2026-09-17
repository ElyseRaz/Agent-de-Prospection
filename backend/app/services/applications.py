import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import (
    Application,
    ApplicationEvent,
    ApplicationEventType,
    ApplicationStage,
)


async def create_application(
    db: AsyncSession, *, profile_id: uuid.UUID, job_id: uuid.UUID
) -> Application:
    """Cree le suivi d'une offre pour un profil (idempotent : reutilise le
    suivi existant si l'offre est deja repere pour ce profil)."""

    existing = await db.scalar(
        select(Application).where(
            Application.profile_id == profile_id, Application.job_id == job_id
        )
    )
    if existing is not None:
        return existing

    stmt = (
        pg_insert(Application)
        .values(profile_id=profile_id, job_id=job_id, stage=ApplicationStage.SPOTTED)
        .on_conflict_do_nothing(constraint="uq_applications_profile_job")
        .returning(Application.id)
    )
    result = await db.execute(stmt)
    application_id = result.scalar_one_or_none()
    if application_id is None:
        existing = await db.scalar(
            select(Application).where(
                Application.profile_id == profile_id, Application.job_id == job_id
            )
        )
        assert existing is not None
        return existing

    await db.commit()
    application = await db.get(Application, application_id)
    assert application is not None
    return application


async def list_applications(db: AsyncSession, *, profile_id: uuid.UUID) -> list[Application]:
    result = await db.execute(
        select(Application)
        .where(Application.profile_id == profile_id)
        .order_by(Application.updated_at.desc())
    )
    return list(result.scalars())


async def update_application_stage(
    db: AsyncSession, application: Application, *, new_stage: ApplicationStage
) -> Application:
    previous_stage = application.stage
    application.stage = new_stage
    if new_stage == ApplicationStage.APPLIED and application.applied_at is None:
        application.applied_at = datetime.now(UTC)
    if new_stage in (ApplicationStage.IN_DISCUSSION, ApplicationStage.PROPOSAL):
        application.last_contact_at = datetime.now(UTC)

    db.add(
        ApplicationEvent(
            application_id=application.id,
            type=ApplicationEventType.STAGE_CHANGED,
            payload={"from": previous_stage.value, "to": new_stage.value},
        )
    )
    await db.commit()
    await db.refresh(application)
    return application


async def update_application_details(
    db: AsyncSession,
    application: Application,
    *,
    notes: str | None = None,
    next_followup_at: datetime | None = None,
    expected_value: Decimal | None = None,
    outcome: str | None = None,
) -> Application:
    if notes is not None and notes != application.notes:
        application.notes = notes
        db.add(
            ApplicationEvent(
                application_id=application.id,
                type=ApplicationEventType.NOTE_UPDATED,
                payload={"notes": notes},
            )
        )
    if next_followup_at is not None:
        application.next_followup_at = next_followup_at
        db.add(
            ApplicationEvent(
                application_id=application.id,
                type=ApplicationEventType.FOLLOWUP_SCHEDULED,
                payload={"next_followup_at": next_followup_at.isoformat()},
            )
        )
    if expected_value is not None:
        application.expected_value = expected_value
    if outcome is not None:
        application.outcome = outcome

    await db.commit()
    await db.refresh(application)
    return application


async def delete_application(db: AsyncSession, application: Application) -> None:
    await db.delete(application)
    await db.commit()
