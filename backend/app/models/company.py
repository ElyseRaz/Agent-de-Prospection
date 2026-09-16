import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Company(Base):
    """Resolution minimale (nom -> entreprise) pour cette phase. L'enrichissement
    (domaine, taille, secteur, reputation Trustpilot) arrive en phase 5."""

    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_companies_normalized_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
