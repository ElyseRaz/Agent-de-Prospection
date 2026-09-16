import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enum_types import enum_values


class AccessType(StrEnum):
    API = "api"
    RSS = "rss"
    HTML_PUBLIC = "html_public"


class ScrapeRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    access_type: Mapped[AccessType] = mapped_column(
        Enum(AccessType, name="access_type", values_callable=enum_values), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schedule_cron: Mapped[str] = mapped_column(String(100), nullable=False, default="0 * * * *")
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    compliance_note: Mapped[str] = mapped_column(Text, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["ScrapeRun"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    raw_documents: Mapped[list["RawDocument"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ScrapeRunStatus] = mapped_column(
        Enum(ScrapeRunStatus, name="scrape_run_status", values_callable=enum_values),
        nullable=False,
        default=ScrapeRunStatus.RUNNING,
    )
    items_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    source: Mapped["Source"] = relationship(back_populates="runs")
    raw_documents: Mapped[list["RawDocument"]] = relationship(back_populates="run")


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_raw_documents_source_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scrape_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status", values_callable=enum_values),
        nullable=False,
        default=ProcessingStatus.PENDING,
    )

    source: Mapped["Source"] = relationship(back_populates="raw_documents")
    run: Mapped["ScrapeRun | None"] = relationship(back_populates="raw_documents")
