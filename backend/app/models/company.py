import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Company(Base):
    """Resolution minimale (nom -> entreprise). `domain` est renseigne quand le
    LLM le detecte explicitement dans une annonce (phase 5) ; sert de cle de
    recherche pour la reputation Trustpilot (voir app/reputation/). Un
    enrichissement plus riche (taille, secteur) resterait a implementer et
    n'a volontairement pas de source de donnees assignee dans ce projet."""

    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_companies_normalized_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
