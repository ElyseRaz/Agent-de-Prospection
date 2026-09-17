import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingBackend
from app.embeddings.text_builder import build_profile_embedding_text
from app.models.profile import Profile, ProfileSkill
from app.models.skill import Skill
from app.normalization.skills import get_or_create_skill_id, slugify_skill
from app.schemas.profile import ProfileSkillInput


async def set_profile_skills(
    db: AsyncSession,
    profile: Profile,
    skills: list[ProfileSkillInput],
    *,
    embedding_backend: EmbeddingBackend,
) -> None:
    """Remplace les competences du profil et recalcule son embedding (meme
    modele que les offres, pour comparer dans le meme espace vectoriel)."""

    await db.execute(delete(ProfileSkill).where(ProfileSkill.profile_id == profile.id))

    skill_labels: list[str] = []
    seen_slugs: set[str] = set()
    for item in skills:
        slug = slugify_skill(item.skill_slug)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        skill_id = await get_or_create_skill_id(db, slug=slug, label=item.skill_slug.strip())
        db.add(
            ProfileSkill(
                profile_id=profile.id,
                skill_id=skill_id,
                level=item.level,
                years=item.years,
                is_required=item.is_required,
            )
        )
        skill_labels.append(item.skill_slug.strip())

    text = build_profile_embedding_text(name=profile.name, skill_labels=skill_labels)
    profile.embedding = (await embedding_backend.embed_documents([text]))[0]
    await db.commit()


async def get_profile_skills(db: AsyncSession, profile_id: uuid.UUID):
    return await db.execute(
        select(
            Skill.slug,
            Skill.label,
            ProfileSkill.level,
            ProfileSkill.years,
            ProfileSkill.is_required,
        )
        .join(ProfileSkill, ProfileSkill.skill_id == Skill.id)
        .where(ProfileSkill.profile_id == profile_id)
    )
