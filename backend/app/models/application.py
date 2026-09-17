import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enum_types import enum_values


class ApplicationStage(StrEnum):
    SPOTTED = "spotted"
    TO_APPLY = "to_apply"
    APPLIED = "applied"
    IN_DISCUSSION = "in_discussion"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class ApplicationEventType(StrEnum):
    STAGE_CHANGED = "stage_changed"
    NOTE_UPDATED = "note_updated"
    FOLLOWUP_SCHEDULED = "followup_scheduled"


class Application(Base):
    """Suivi de candidature (CRM freelance, colonnes du Kanban = `stage`).
    Une seule ligne de suivi par (profil, offre)."""

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("profile_id", "job_id", name="uq_applications_profile_job"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage, name="application_stage", values_callable=enum_values),
        nullable=False,
        default=ApplicationStage.SPOTTED,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_followup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.occurred_at",
    )


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[ApplicationEventType] = mapped_column(
        Enum(ApplicationEventType, name="application_event_type", values_callable=enum_values),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    application: Mapped["Application"] = relationship(back_populates="events")
