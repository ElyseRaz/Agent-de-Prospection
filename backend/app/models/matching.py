import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enum_types import enum_values


class MatchFeedbackAction(StrEnum):
    SAVED = "saved"
    REJECTED = "rejected"


class Match(Base):
    """Score de compatibilite calcule (et mis en cache) pour un couple
    profil/offre. Recalcule et remplace (upsert) a chaque appel de
    `GET /profiles/{id}/matches`."""

    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("profile_id", "job_id", name="uq_matches_profile_job"),)

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
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    breakdown: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class MatchFeedback(Base):
    """Signal implicite (offre sauvegardee/rejetee pour un profil), utilise
    pour ajuster `profiles.weights` (voir app/services/matching.py)."""

    __tablename__ = "match_feedback"
    __table_args__ = (
        UniqueConstraint("profile_id", "job_id", name="uq_match_feedback_profile_job"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[MatchFeedbackAction] = mapped_column(
        Enum(MatchFeedbackAction, name="match_feedback_action", values_callable=enum_values),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
