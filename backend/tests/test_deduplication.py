import uuid

import pytest
from sqlalchemy import select, update

from app.models.company import Company
from app.models.dedup import JobDuplicateLink
from app.models.job import Job, JobStatus
from app.models.source import AccessType, Source
from app.normalization.search_index import search_tsv_expression
from app.services.deduplication import compute_dedup_hash, deduplicate_job
from tests.conftest import cosine_test_vector

pytestmark = pytest.mark.asyncio


async def _make_source(db_session) -> Source:
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
    return source


async def _make_job(db_session, source, **overrides) -> Job:
    defaults = dict(
        source_id=source.id,
        external_id=str(uuid.uuid4()),
        url="https://example.com/job",
        title="Senior Backend Engineer",
        description_clean="Nous cherchons un ingenieur backend Python experimente.",
        prompt_version="extract_job_v1",
        status=JobStatus.ACTIVE,
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    await db_session.flush()
    await db_session.execute(
        update(Job)
        .where(Job.id == job.id)
        .values(search_tsv=search_tsv_expression(job.title, job.description_clean))
    )
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_exact_hash_match_marks_duplicate(db_session):
    source = await _make_source(db_session)
    dedup_hash = compute_dedup_hash("Senior Backend Engineer", "Acme Corp", "Description identique")

    original = await _make_job(db_session, source, dedup_hash=dedup_hash)
    duplicate = await _make_job(
        db_session,
        source,
        title="Autre titre",
        external_id=str(uuid.uuid4()),
        dedup_hash=dedup_hash,
    )

    match = await deduplicate_job(db_session, duplicate)
    await db_session.commit()

    assert match is not None
    assert match.id == original.id
    assert duplicate.canonical_id == original.id

    link = await db_session.scalar(
        select(JobDuplicateLink).where(JobDuplicateLink.duplicate_job_id == duplicate.id)
    )
    assert link is not None
    assert link.method == "exact_hash"
    assert float(link.similarity_score) == 1.0


async def _make_company(db_session, name: str) -> Company:
    company = Company(name=name, normalized_name=name.lower())
    db_session.add(company)
    await db_session.flush()
    return company


async def test_trigram_match_requires_same_company(db_session):
    source = await _make_source(db_session)
    company_a = (await _make_company(db_session, "Acme Corp")).id
    company_b = (await _make_company(db_session, "Beta Studio")).id

    original = await _make_job(
        db_session, source, title="Senior Python Backend Engineer", company_id=None
    )
    # Meme entreprise -> doit matcher malgre un titre legerement different.
    same_company_duplicate = await _make_job(
        db_session,
        source,
        title="Senior Python Backend Engineer ",
        external_id=str(uuid.uuid4()),
    )

    # On force manuellement des company_id identiques pour le test (la
    # resolution d'entreprise complete est hors-scope ici).
    original.company_id = company_a
    same_company_duplicate.company_id = company_a
    await db_session.commit()

    match = await deduplicate_job(db_session, same_company_duplicate)
    await db_session.commit()
    assert match is not None
    assert match.id == original.id

    # Entreprise differente, titre tres proche : ne doit PAS matcher.
    different_company_job = await _make_job(
        db_session,
        source,
        title="Senior Python Backend Engineer",
        external_id=str(uuid.uuid4()),
    )
    different_company_job.company_id = company_b
    await db_session.commit()

    no_match = await deduplicate_job(db_session, different_company_job)
    await db_session.commit()
    assert no_match is None


async def test_embedding_similarity_match_above_threshold(db_session):
    source = await _make_source(db_session)
    vector = cosine_test_vector(768)  # vecteur "plein" -> similarite 1.0 avec lui-meme

    original = await _make_job(db_session, source, title="Data Engineer")
    original.embedding = vector
    await db_session.commit()

    near_duplicate = await _make_job(
        db_session, source, title="Data Engineer (repost)", external_id=str(uuid.uuid4())
    )
    near_duplicate.embedding = vector
    await db_session.commit()

    match = await deduplicate_job(db_session, near_duplicate)
    await db_session.commit()

    assert match is not None
    assert match.id == original.id


async def test_embedding_dissimilar_does_not_match(db_session):
    source = await _make_source(db_session)

    original = await _make_job(db_session, source, title="Data Engineer")
    original.embedding = cosine_test_vector(768)
    await db_session.commit()

    different_job = await _make_job(
        db_session, source, title="Product Designer", external_id=str(uuid.uuid4())
    )
    different_job.embedding = cosine_test_vector(384)  # orthogonal, similarite ~0
    await db_session.commit()

    match = await deduplicate_job(db_session, different_job)
    await db_session.commit()

    assert match is None


async def test_distinct_jobs_stay_unique(db_session):
    source = await _make_source(db_session)

    job_a = await _make_job(db_session, source, title="Frontend Developer")
    job_b = await _make_job(
        db_session,
        source,
        title="Accounting Manager",
        external_id=str(uuid.uuid4()),
        description_clean="Gestion comptable et fiscale d'une PME.",
    )

    match = await deduplicate_job(db_session, job_b)
    await db_session.commit()

    assert match is None
    assert job_a.canonical_id is None
    assert job_b.canonical_id is None


async def test_duplicate_link_upserts_on_rerun(db_session):
    source = await _make_source(db_session)
    dedup_hash = compute_dedup_hash("Titre", "Entreprise", "Description")

    original = await _make_job(db_session, source, dedup_hash=dedup_hash)
    duplicate = await _make_job(
        db_session, source, external_id=str(uuid.uuid4()), dedup_hash=dedup_hash
    )

    await deduplicate_job(db_session, duplicate)
    await db_session.commit()
    # Rejouer la deduplication ne doit pas creer un second lien (contrainte
    # UNIQUE sur duplicate_job_id geree via ON CONFLICT DO UPDATE).
    await deduplicate_job(db_session, duplicate)
    await db_session.commit()

    links = (
        (
            await db_session.execute(
                select(JobDuplicateLink).where(JobDuplicateLink.duplicate_job_id == duplicate.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(links) == 1
    assert links[0].canonical_job_id == original.id
