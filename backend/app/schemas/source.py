import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.source import AccessType, ScrapeRunStatus


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    kind: str
    base_url: str
    access_type: AccessType
    is_active: bool
    schedule_cron: str
    rate_limit_rpm: int
    compliance_note: str
    created_at: datetime


class ScrapeRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    started_at: datetime
    finished_at: datetime | None
    status: ScrapeRunStatus
    items_fetched: int
    items_new: int
    items_updated: int
    error_message: str | None


class DryRunResultRead(BaseModel):
    source_slug: str
    items_fetched: int
    sample: list[dict]


class CollectResponse(BaseModel):
    dry_run: bool
    run: ScrapeRunRead | None = None
    dry_run_result: DryRunResultRead | None = None
