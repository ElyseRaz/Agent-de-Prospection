import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CompanyReputation(Base):
    """Reputation entreprise par fournisseur (Trustpilot pour l'instant).

    `rating`/`review_count` restent NULL quand l'entreprise a ete recherchee
    mais n'a pas ete trouvee (voir app/services/reputation.py) : `fetched_at`
    non-null distingue alors "verifie, absent" de "jamais verifie" (ligne
    inexistante). `trend_90d` et `profile_age_days` restent non calcules :
    l'API publique Trustpilot ne documente pas d'historique exploitable sans
    paginer les avis un par un (voir README/architecture)."""

    __tablename__ = "company_reputation"
    __table_args__ = (
        UniqueConstraint("company_id", "provider", name="uq_company_reputation_company_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trend_90d: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    profile_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
