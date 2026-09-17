from typing import Literal

from pydantic import BaseModel, Field


class ExtractedRate(BaseModel):
    min: float | None = None
    max: float | None = None
    currency: str | None = None
    period: Literal["hour", "day", "month", "year", "fixed"] | None = None


class ExtractedJobLLM(BaseModel):
    """Schema strict de sortie de l'extraction LLM (voir prompts/extract_job_v1.md).
    Tous les champs sont optionnels : le LLM ne doit jamais inventer une valeur
    absente du texte source."""

    title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    contract_type: Literal["freelance", "cdi", "mission"] | None = None
    rate: ExtractedRate | None = None
    duration_months: float | None = None
    start_date: str | None = None
    workload_days_per_week: float | None = None
    tech_stack: list[str] = Field(default_factory=list)
    seniority: Literal["junior", "intermediate", "senior", "lead", "expert"] | None = None
    required_languages: list[str] = Field(default_factory=list)
    remote_type: Literal["full_remote", "remote_zone_restricted", "hybrid", "onsite"] | None = None
    timezone_constraint: str | None = None
    billing_mode: str | None = None
    application_channel: str | None = None
