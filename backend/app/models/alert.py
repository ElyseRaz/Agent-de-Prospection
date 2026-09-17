import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ARRAY, Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enum_types import enum_values


class AlertFrequency(StrEnum):
    INSTANT = "instant"
    DAILY = "daily"


class NotificationChannelKind(StrEnum):
    EMAIL = "email"
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"


class SavedSearch(Base):
    """Recherche sauvegardee declenchant des alertes. `filters` reprend les
    memes champs que `GET /jobs/search` (voir `app/schemas/alert.py`),
    serialises tels quels pour reconstruire un `JobSearchFilters` a chaque
    evaluation (`app/services/alerts.py`)."""

    __tablename__ = "saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    frequency: Mapped[AlertFrequency] = mapped_column(
        Enum(AlertFrequency, name="alert_frequency", values_callable=enum_values),
        nullable=False,
        default=AlertFrequency.INSTANT,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AlertNotification(Base):
    """Trace qu'une offre a deja ete notifiee pour une recherche sauvegardee
    donnee (idempotence : une offre n'est jamais notifiee deux fois pour la
    meme recherche), et alimente le flux `GET /notifications/stream`."""

    __tablename__ = "alert_notifications"
    __table_args__ = (
        UniqueConstraint("saved_search_id", "job_id", name="uq_alert_notifications_search_job"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    saved_search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("saved_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channels_sent: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
