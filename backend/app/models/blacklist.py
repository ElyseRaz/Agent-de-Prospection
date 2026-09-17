import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enum_types import enum_values


class BlacklistEntityType(StrEnum):
    COMPANY = "company"
    RECRUITER = "recruiter"


class Blacklist(Base):
    """Liste noire d'entreprises/recruteurs. `user_id` NULL = entree partagee
    (visible de tous, prise en compte dans le score de risque global) ;
    `user_id` renseigne = entree personnelle (visible seulement par son
    auteur, n'affecte pas le risk_score public d'un job pour les autres
    utilisateurs)."""

    __tablename__ = "blacklist"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    entity_type: Mapped[BlacklistEntityType] = mapped_column(
        Enum(BlacklistEntityType, name="blacklist_entity_type", values_callable=enum_values),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
