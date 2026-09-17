import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.alert import AlertFrequency, NotificationChannelKind
from app.models.job import ContractType, RemoteType, SeniorityLevel

ALLOWED_CHANNELS = {member.value for member in NotificationChannelKind}


class SavedSearchFilters(BaseModel):
    """Memes champs que les parametres de `GET /jobs/search` (voir
    `app/services/search.py:JobSearchFilters`), reconstruits a chaque
    evaluation par `app/services/alerts.py`."""

    q: str | None = None
    rate_min_eur: Decimal | None = None
    rate_max_eur: Decimal | None = None
    rate_currency: str | None = None
    skill: list[str] = Field(default_factory=list)
    seniority: SeniorityLevel | None = None
    language: str | None = None
    remote_type: RemoteType | None = None
    contract_type: ContractType | None = None
    source_slug: str | None = None


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    filters: SavedSearchFilters = Field(default_factory=SavedSearchFilters)
    channels: list[str] = Field(default_factory=list)
    frequency: AlertFrequency = AlertFrequency.INSTANT

    @field_validator("channels")
    @classmethod
    def _validate_channels(cls, value: list[str]) -> list[str]:
        unknown = set(value) - ALLOWED_CHANNELS
        if unknown:
            raise ValueError(f"Canal(aux) inconnu(s): {sorted(unknown)}")
        return value


class SavedSearchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    filters: SavedSearchFilters | None = None
    channels: list[str] | None = None
    frequency: AlertFrequency | None = None
    is_active: bool | None = None

    @field_validator("channels")
    @classmethod
    def _validate_channels(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unknown = set(value) - ALLOWED_CHANNELS
        if unknown:
            raise ValueError(f"Canal(aux) inconnu(s): {sorted(unknown)}")
        return value


class SavedSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    filters: dict
    channels: list[str]
    frequency: AlertFrequency
    is_active: bool
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SavedSearchRunResponse(BaseModel):
    jobs_considered: int
    new_notifications: int


class AlertNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    saved_search_id: uuid.UUID
    job_id: uuid.UUID
    channels_sent: list[str]
    sent_at: datetime
