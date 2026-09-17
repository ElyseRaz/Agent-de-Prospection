import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.job import ContractType, JobStatus, RatePeriod, RemoteType, SeniorityLevel


class RiskReasonRead(BaseModel):
    code: str
    label: str
    severity: str


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID | None
    source_id: uuid.UUID
    url: str
    title: str
    description_clean: str
    language: str
    contract_type: ContractType | None
    seniority: SeniorityLevel | None
    rate_min: Decimal | None
    rate_max: Decimal | None
    rate_currency: str | None
    rate_period: RatePeriod | None
    rate_eur_normalized: Decimal | None
    duration_months: Decimal | None
    workload_days_week: Decimal | None
    remote_type: RemoteType | None
    timezone_constraint: str | None
    required_languages: list[str]
    billing_mode: str | None
    application_channel: str | None
    posted_at: datetime | None
    detected_at: datetime
    last_seen_at: datetime
    status: JobStatus
    quality_score: int
    risk_score: int
    risk_reasons: list[RiskReasonRead]
    risk_assessed_at: datetime | None


class JobDetailRead(JobRead):
    duplicate_urls: list[str] = []


class JobSearchResultRead(BaseModel):
    job: JobRead
    score: float


class JobSearchResponse(BaseModel):
    results: list[JobSearchResultRead]
    total: int
    limit: int
    offset: int


class BackfillResponse(BaseModel):
    embedded: int
    skipped: int


class MarkExpiredResponse(BaseModel):
    expired: int


class RiskBatchResponse(BaseModel):
    assessed: int
    failed: int
