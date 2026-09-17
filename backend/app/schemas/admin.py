import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class LLMUsageBucket(BaseModel):
    day: date
    purpose: str
    model: str
    calls: int
    cache_hits: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class LLMUsageResponse(BaseModel):
    buckets: list[LLMUsageBucket]
    total_calls: int
    total_cost_usd: Decimal


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    totp_enabled: bool
    created_at: datetime


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AdminStatsResponse(BaseModel):
    users_total: int
    jobs_total: int
    jobs_active: int
    applications_total: int
    saved_searches_total: int
