import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Skill(Base):
    """Referentiel de competences 'maison' (slug normalise + alias). Une
    integration ESCO complete est hors scope de cette phase."""

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("slug", name="uq_skills_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
