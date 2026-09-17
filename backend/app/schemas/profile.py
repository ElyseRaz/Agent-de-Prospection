import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.profile import SkillLevel


class ProfileSkillInput(BaseModel):
    skill_slug: str
    level: SkillLevel = SkillLevel.INTERMEDIATE
    years: Decimal | None = None
    is_required: bool = True


class ProfileSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_slug: str
    skill_label: str
    level: SkillLevel
    years: Decimal | None
    is_required: bool


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_rate: Decimal | None = None
    floor_rate: Decimal | None = None
    currency: str | None = None
    availability_date: date | None = None
    timezone: str | None = None
    languages: list[str] = Field(default_factory=list)
    excluded_industries: list[str] = Field(default_factory=list)
    desired_contract_types: list[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    name: str | None = None
    target_rate: Decimal | None = None
    floor_rate: Decimal | None = None
    currency: str | None = None
    availability_date: date | None = None
    timezone: str | None = None
    languages: list[str] | None = None
    excluded_industries: list[str] | None = None
    desired_contract_types: list[str] | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    target_rate: Decimal | None
    floor_rate: Decimal | None
    currency: str | None
    availability_date: date | None
    timezone: str | None
    languages: list[str]
    excluded_industries: list[str]
    desired_contract_types: list[str]
    weights: dict[str, float]
    created_at: datetime
    updated_at: datetime


class ProfileDetailRead(ProfileRead):
    skills: list[ProfileSkillRead] = Field(default_factory=list)
