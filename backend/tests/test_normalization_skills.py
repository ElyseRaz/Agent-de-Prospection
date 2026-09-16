import uuid

import pytest
from sqlalchemy import select

from app.models.job import ContractType, Job, JobSkill
from app.models.skill import Skill
from app.models.source import AccessType, Source
from app.normalization.skills import slugify_skill, upsert_skills_for_job

pytestmark = pytest.mark.asyncio


def test_slugify_skill_normalizes_case_and_accents():
    assert slugify_skill("Python") == "python"
    assert slugify_skill("Node.js") == "node"
    assert slugify_skill("  FastAPI  ") == "fastapi"


def test_slugify_skill_applies_aliases():
    assert slugify_skill("JS") == "javascript"
    assert slugify_skill("k8s") == "kubernetes"
    assert slugify_skill("Postgres") == "postgresql"


async def _make_job(db_session) -> Job:
    source = Source(
        slug="remotive",
        name="Remotive",
        kind="remotive",
        base_url="https://remotive.com/api/remote-jobs",
        access_type=AccessType.API,
        schedule_cron="*/30 * * * *",
        rate_limit_rpm=20,
        compliance_note="API publique.",
        config={},
    )
    db_session.add(source)
    await db_session.flush()

    job = Job(
        source_id=source.id,
        external_id=str(uuid.uuid4()),
        url="https://example.com/job",
        title="Test job",
        contract_type=ContractType.FREELANCE,
        prompt_version="extract_job_v1",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def _job_skill_links(db_session, job_id):
    result = await db_session.execute(select(JobSkill).where(JobSkill.job_id == job_id))
    return result.scalars().all()


async def test_upsert_skills_creates_referential_entries(db_session):
    job = await _make_job(db_session)

    await upsert_skills_for_job(db_session, job_id=job.id, tech_stack=["Python", "FastAPI", "JS"])
    await db_session.commit()

    skills = (await db_session.execute(select(Skill))).scalars().all()
    slugs = {s.slug for s in skills}
    assert slugs == {"python", "fastapi", "javascript"}

    links = await _job_skill_links(db_session, job.id)
    assert len(links) == 3


async def test_upsert_skills_deduplicates_aliases(db_session):
    job = await _make_job(db_session)
    tech_stack = ["Postgres", "postgres", "PostgreSQL"]

    await upsert_skills_for_job(db_session, job_id=job.id, tech_stack=tech_stack)
    await db_session.commit()

    skills = (await db_session.execute(select(Skill))).scalars().all()
    assert len(skills) == 1
    assert skills[0].slug == "postgresql"


async def test_upsert_skills_replaces_previous_links(db_session):
    job = await _make_job(db_session)

    await upsert_skills_for_job(db_session, job_id=job.id, tech_stack=["Python"])
    await db_session.commit()
    await upsert_skills_for_job(db_session, job_id=job.id, tech_stack=["Go"])
    await db_session.commit()

    links = await _job_skill_links(db_session, job.id)
    assert len(links) == 1
