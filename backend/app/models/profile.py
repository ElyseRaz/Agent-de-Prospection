import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.enum_types import enum_values
from app.models.job import EMBEDDING_DIMENSION

# Poids par defaut du moteur de matching (somme = 100). Copiables/ajustables
# par profil via `profiles.weights` ; l'apprentissage implicite
# (app/services/matching.py) les fait evoluer avec le temps.
DEFAULT_PROFILE_WEIGHTS: dict[str, float] = {
    "semantic": 25,
    "skills": 30,
    "rate": 25,
    "timezone": 10,
    "reliability": 10,
}


class SkillLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Profile(Base):
    """Profil freelance (multi-profils par utilisateur, ex: 'Data Engineer' /
    'Automatisation IA'). `excluded_industries` est stocke mais non exploite
    dans le score : ni `jobs` ni `companies` n'ont de champ secteur (aucune
    source de donnees assignee, decision prise en phase 5) - champ reserve
    pour une extension future, pas un signal fabrique."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    floor_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    availability_date: Mapped[date | None] = mapped_column(nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    languages: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    excluded_industries: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    desired_contract_types: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=True
    )
    weights: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: dict(DEFAULT_PROFILE_WEIGHTS)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    skills: Mapped[list["ProfileSkill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class ProfileSkill(Base):
    __tablename__ = "profile_skills"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, name="skill_level", values_callable=enum_values),
        nullable=False,
        default=SkillLevel.INTERMEDIATE,
    )
    years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    profile: Mapped["Profile"] = relationship(back_populates="skills")
