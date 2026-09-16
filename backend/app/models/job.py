import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enum_types import enum_values

EMBEDDING_DIMENSION = 768


class ContractType(StrEnum):
    FREELANCE = "freelance"
    CDI = "cdi"
    MISSION = "mission"


class SeniorityLevel(StrEnum):
    JUNIOR = "junior"
    INTERMEDIATE = "intermediate"
    SENIOR = "senior"
    LEAD = "lead"
    EXPERT = "expert"


class RemoteType(StrEnum):
    FULL_REMOTE = "full_remote"
    REMOTE_ZONE_RESTRICTED = "remote_zone_restricted"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class RatePeriod(StrEnum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    YEAR = "year"
    FIXED = "fixed"


class JobStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class Job(Base):
    """Offre canonique issue de la normalisation d'un raw_document.

    `risk_score` et `risk_reasons` restent hors de cette table jusqu'a la
    phase 5 (enrichissement entreprise).
    """

    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_jobs_source_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_documents.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description_clean: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="autre")

    contract_type: Mapped[ContractType | None] = mapped_column(
        Enum(ContractType, name="contract_type", values_callable=enum_values), nullable=True
    )
    seniority: Mapped[SeniorityLevel | None] = mapped_column(
        Enum(SeniorityLevel, name="seniority_level", values_callable=enum_values), nullable=True
    )

    rate_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    rate_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    rate_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    rate_period: Mapped[RatePeriod | None] = mapped_column(
        Enum(RatePeriod, name="rate_period", values_callable=enum_values), nullable=True
    )
    rate_eur_normalized: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    duration_months: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    workload_days_week: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    remote_type: Mapped[RemoteType | None] = mapped_column(
        Enum(RemoteType, name="remote_type", values_callable=enum_values), nullable=True
    )
    timezone_constraint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_languages: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    billing_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    application_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=enum_values),
        nullable=False,
        default=JobStatus.ACTIVE,
    )
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Phase 4 : embeddings, recherche plein texte, deduplication.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    search_tsv: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    dedup_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("1.0"))

    job: Mapped["Job"] = relationship(back_populates="skills")
