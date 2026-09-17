import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.application import Application, ApplicationEvent
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User, UserRole
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDetailRead,
    ApplicationRead,
    ApplicationStageUpdate,
    ApplicationUpdate,
)
from app.schemas.job import JobRead
from app.services.applications import (
    create_application,
    delete_application,
    list_applications,
    update_application_details,
    update_application_stage,
)

router = APIRouter(prefix="/profiles/{profile_id}/applications", tags=["applications"])


async def _get_owned_profile(
    db: AsyncSession, profile_id: uuid.UUID, current_user: User
) -> Profile:
    profile = await db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil introuvable")
    if profile.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Ce profil ne vous appartient pas"
        )
    return profile


async def _get_owned_application(
    db: AsyncSession, profile_id: uuid.UUID, application_id: uuid.UUID, current_user: User
) -> Application:
    await _get_owned_profile(db, profile_id, current_user)
    application = await db.get(Application, application_id)
    if application is None or application.profile_id != profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suivi de candidature introuvable"
        )
    return application


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application_route(
    profile_id: uuid.UUID,
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    await _get_owned_profile(db, profile_id, current_user)
    job = await db.get(Job, payload.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offre introuvable")
    return await create_application(db, profile_id=profile_id, job_id=payload.job_id)


@router.get("", response_model=list[ApplicationRead])
async def list_applications_route(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Application]:
    await _get_owned_profile(db, profile_id, current_user)
    return await list_applications(db, profile_id=profile_id)


@router.get("/{application_id}", response_model=ApplicationDetailRead)
async def get_application_route(
    profile_id: uuid.UUID,
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationDetailRead:
    application = await _get_owned_application(db, profile_id, application_id, current_user)
    job = await db.get(Job, application.job_id)
    assert job is not None
    events = (
        (
            await db.execute(
                select(ApplicationEvent)
                .where(ApplicationEvent.application_id == application.id)
                .order_by(ApplicationEvent.occurred_at)
            )
        )
        .scalars()
        .all()
    )
    return ApplicationDetailRead(
        **ApplicationRead.model_validate(application).model_dump(),
        job=JobRead.model_validate(job),
        events=list(events),
    )


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application_route(
    profile_id: uuid.UUID,
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    application = await _get_owned_application(db, profile_id, application_id, current_user)
    return await update_application_details(
        db,
        application,
        notes=payload.notes,
        next_followup_at=payload.next_followup_at,
        expected_value=payload.expected_value,
        outcome=payload.outcome,
    )


@router.patch("/{application_id}/stage", response_model=ApplicationRead)
async def update_application_stage_route(
    profile_id: uuid.UUID,
    application_id: uuid.UUID,
    payload: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    application = await _get_owned_application(db, profile_id, application_id, current_user)
    return await update_application_stage(db, application, new_stage=payload.stage)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_route(
    profile_id: uuid.UUID,
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    application = await _get_owned_application(db, profile_id, application_id, current_user)
    await delete_application(db, application)
