import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class JobDuplicateLink(Base):
    """Journal d'audit des fusions de doublons : un job dupliquele pointe vers
    exactement un job canonique. Les URLs de toutes les sources restent
    accessibles nativement via `jobs.url` sur chaque ligne dupliquee."""

    __tablename__ = "job_duplicate_links"
    __table_args__ = (
        UniqueConstraint("duplicate_job_id", name="uq_job_duplicate_links_duplicate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duplicate_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    similarity_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
