import re
import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobSkill
from app.models.skill import Skill

# Alias vers la forme canonique retenue par la taxonomie 'maison'.
_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "golang": "go",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "py": "python",
    "reactjs": "react",
    "nodejs": "node",
    "node-js": "node",
    "vuejs": "vue",
}


def slugify_skill(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw.strip().lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return _ALIASES.get(normalized, normalized)


async def upsert_skills_for_job(
    db: AsyncSession, *, job_id: uuid.UUID, tech_stack: list[str]
) -> None:
    """Normalise `tech_stack` vers le referentiel `skills` (get-or-create par
    slug) et remplace les liaisons `job_skills` du job."""

    await db.execute(JobSkill.__table__.delete().where(JobSkill.job_id == job_id))

    seen_slugs: set[str] = set()
    for raw in tech_stack:
        slug = slugify_skill(raw)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        skill_id = await _get_or_create_skill_id(db, slug=slug, label=raw.strip())

        link_stmt = (
            pg_insert(JobSkill)
            .values(job_id=job_id, skill_id=skill_id, is_required=True, weight=1.0)
            .on_conflict_do_nothing(index_elements=["job_id", "skill_id"])
        )
        await db.execute(link_stmt)


async def _get_or_create_skill_id(db: AsyncSession, *, slug: str, label: str) -> uuid.UUID:
    existing = await db.scalar(select(Skill).where(Skill.slug == slug))
    if existing is not None:
        return existing.id

    stmt = (
        pg_insert(Skill)
        .values(slug=slug, label=label, category=None, aliases=[])
        .on_conflict_do_nothing(constraint="uq_skills_slug")
        .returning(Skill.id)
    )
    result = await db.execute(stmt)
    skill_id = result.scalar_one_or_none()
    if skill_id is not None:
        return skill_id

    existing = await db.scalar(select(Skill).where(Skill.slug == slug))
    assert existing is not None
    return existing.id
