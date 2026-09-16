import uuid
from decimal import Decimal

import pytest
from sqlalchemy import update

from app.models.job import ContractType, Job, JobStatus, RemoteType, SeniorityLevel
from app.models.source import AccessType, Source
from app.normalization.search_index import search_tsv_expression
from app.services.search import JobSearchFilters, hybrid_search_jobs
from tests.conftest import FakeEmbeddingBackend, cosine_test_vector

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
        description_clean="Mission freelance FastAPI et PostgreSQL, full remote.",
        prompt_version="extract_job_v1",
        status=JobStatus.ACTIVE,
        contract_type=ContractType.FREELANCE,
        seniority=SeniorityLevel.SENIOR,
        remote_type=RemoteType.FULL_REMOTE,
        rate_eur_normalized=Decimal("500.00"),
        language="fr",
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


async def test_search_without_query_returns_filtered_results_sorted_by_freshness(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source, title="Job ancien")
    recent = await _make_job(db_session, source, title="Job recent", external_id=str(uuid.uuid4()))

    results, total = await hybrid_search_jobs(
        db_session,
        query=None,
        filters=JobSearchFilters(),
        embedding_backend=None,
        limit=10,
        offset=0,
    )

    assert total == 2
    assert results[0].job.id == recent.id  # le plus recent d'abord (detected_at desc)


async def test_search_full_text_matches_relevant_job(db_session):
    source = await _make_source(db_session)
    match = await _make_job(
        db_session,
        source,
        title="Senior FastAPI Developer",
        description_clean="Mission remote sur FastAPI et microservices Python.",
    )
    await _make_job(
        db_session,
        source,
        title="Comptable senior",
        description_clean="Gestion comptable et fiscale, sur site.",
        external_id=str(uuid.uuid4()),
    )

    results, _total = await hybrid_search_jobs(
        db_session,
        query="FastAPI remote",
        filters=JobSearchFilters(),
        embedding_backend=None,
        limit=10,
        offset=0,
    )

    result_ids = {r.job.id for r in results}
    assert match.id in result_ids
    assert results[0].job.id == match.id


async def test_search_vector_only_match_via_embedding(db_session):
    source = await _make_source(db_session)
    shared_vector = cosine_test_vector(768)

    # Titre/description tres differents du texte recherche : seul le canal
    # vectoriel peut le faire remonter.
    semantic_match = await _make_job(
        db_session,
        source,
        title="Zzzzz completement different",
        description_clean="Rien a voir avec la recherche.",
    )
    semantic_match.embedding = shared_vector
    await db_session.commit()

    backend = FakeEmbeddingBackend(vectors={"developpeur python freelance": shared_vector})

    results, _total = await hybrid_search_jobs(
        db_session,
        query="developpeur python freelance",
        filters=JobSearchFilters(),
        embedding_backend=backend,
        limit=10,
        offset=0,
    )

    result_ids = {r.job.id for r in results}
    assert semantic_match.id in result_ids


async def test_search_excludes_duplicates_and_non_active(db_session):
    source = await _make_source(db_session)
    canonical = await _make_job(db_session, source, title="Job unique")
    duplicate = await _make_job(
        db_session,
        source,
        title="Job unique",
        external_id=str(uuid.uuid4()),
        canonical_id=canonical.id,
    )
    expired = await _make_job(
        db_session,
        source,
        title="Job expire",
        external_id=str(uuid.uuid4()),
        status=JobStatus.EXPIRED,
    )

    results, total = await hybrid_search_jobs(
        db_session,
        query=None,
        filters=JobSearchFilters(),
        embedding_backend=None,
        limit=10,
        offset=0,
    )

    result_ids = {r.job.id for r in results}
    assert canonical.id in result_ids
    assert duplicate.id not in result_ids
    assert expired.id not in result_ids
    assert total == 1


async def test_search_applies_rate_filter(db_session):
    source = await _make_source(db_session)
    cheap = await _make_job(
        db_session, source, title="Job pas cher", rate_eur_normalized=Decimal("200.00")
    )
    expensive = await _make_job(
        db_session,
        source,
        title="Job cher",
        external_id=str(uuid.uuid4()),
        rate_eur_normalized=Decimal("800.00"),
    )

    results, _total = await hybrid_search_jobs(
        db_session,
        query=None,
        filters=JobSearchFilters(rate_min_eur=Decimal("500.00")),
        embedding_backend=None,
        limit=10,
        offset=0,
    )

    result_ids = {r.job.id for r in results}
    assert expensive.id in result_ids
    assert cheap.id not in result_ids
