import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationEventType, ApplicationStage
from app.schemas.job import JobRead


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID


class ApplicationStageUpdate(BaseModel):
    stage: ApplicationStage


class ApplicationUpdate(BaseModel):
    notes: str | None = None
    next_followup_at: datetime | None = None
    expected_value: Decimal | None = None
    outcome: str | None = None


class ApplicationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ApplicationEventType
    payload: dict
    occurred_at: datetime


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: uuid.UUID
    job_id: uuid.UUID
    stage: ApplicationStage
    applied_at: datetime | None
    last_contact_at: datetime | None
    next_followup_at: datetime | None
    expected_value: Decimal | None
    outcome: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailRead(ApplicationRead):
    job: JobRead
    events: list[ApplicationEventRead]
