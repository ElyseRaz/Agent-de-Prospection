import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.blacklist import BlacklistEntityType
from app.models.company import Company
from app.models.job import ContractType, Job, JobStatus, SeniorityLevel
from app.models.llm import LLMCall
from app.models.source import AccessType, Source
from app.services.blacklist import add_blacklist_entry
from app.services.risk import (
    assess_job_risk,
    assess_pending_jobs_risk,
    compute_deterministic_signals,
)
from tests.conftest import FakeRiskAssessmentBackend, make_risk_assessment

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


async def _make_company(db_session, **overrides) -> Company:
    defaults = dict(name="Acme", normalized_name="acme")
    defaults.update(overrides)
    company = Company(**defaults)
    db_session.add(company)
    await db_session.flush()
    return company


async def _make_job(db_session, source, **overrides) -> Job:
    defaults = dict(
        source_id=source.id,
        external_id=str(uuid.uuid4()),
        url="https://example.com/job",
        title="Senior Backend Engineer",
        description_clean="Mission freelance Python, full remote.",
        prompt_version="extract_job_v1",
        status=JobStatus.ACTIVE,
        contract_type=ContractType.FREELANCE,
        seniority=SeniorityLevel.SENIOR,
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def test_compute_signals_flags_no_budget(db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source, rate_min=None, rate_max=None)

    signals = await compute_deterministic_signals(db_session, job, company=None)

    assert signals.has_budget is False
    assert signals.is_blacklisted is False
    assert signals.company_domain_known is False


async def test_compute_signals_underpaid_ratio_against_median(db_session):
    source = await _make_source(db_session)
    # 3 offres de reference a 1000 EUR/jour -> mediane = 1000
    for _ in range(3):
        await _make_job(
            db_session,
            source,
            external_id=str(uuid.uuid4()),
            rate_eur_normalized=Decimal("1000.00"),
        )
    underpaid_job = await _make_job(
        db_session,
        source,
        external_id=str(uuid.uuid4()),
        rate_eur_normalized=Decimal("200.00"),
    )

    signals = await compute_deterministic_signals(db_session, underpaid_job, company=None)

    assert signals.market_median_eur == pytest.approx(1000.0)
    assert signals.underpaid_ratio == pytest.approx(0.2)


async def test_compute_signals_counts_distinct_companies_in_duplicate_cluster(db_session):
    source = await _make_source(db_session)
    company_a = await _make_company(db_session, normalized_name="company a")
    company_b = await _make_company(db_session, normalized_name="company b")

    canonical = await _make_job(db_session, source, company_id=company_a.id)
    await _make_job(
        db_session,
        source,
        external_id=str(uuid.uuid4()),
        company_id=company_b.id,
        canonical_id=canonical.id,
    )

    signals = await compute_deterministic_signals(db_session, canonical, company=company_a)

    assert signals.duplicate_company_count == 2


async def test_compute_signals_detects_shared_blacklist(db_session):
    source = await _make_source(db_session)
    company = await _make_company(db_session, normalized_name="scam company")
    job = await _make_job(db_session, source, company_id=company.id)

    await add_blacklist_entry(
        db_session,
        entity_type=BlacklistEntityType.COMPANY,
        value="Scam Company",
        reason="Signale par 3 freelances",
        user_id=None,
    )

    signals = await compute_deterministic_signals(db_session, job, company=company)

    assert signals.is_blacklisted is True
    assert signals.blacklist_reason == "Signale par 3 freelances"


async def test_assess_job_risk_shortcuts_on_blacklist(db_session):
    source = await _make_source(db_session)
    company = await _make_company(db_session, normalized_name="scam company")
    job = await _make_job(db_session, source, company_id=company.id)
    await add_blacklist_entry(
        db_session,
        entity_type=BlacklistEntityType.COMPANY,
        value="scam company",
        reason="Arnaque connue",
        user_id=None,
    )

    backend = FakeRiskAssessmentBackend([])  # ne doit jamais etre appele

    risk_score, reasons = await assess_job_risk(
        db_session, job, backend=backend, model="claude-sonnet-5"
    )

    assert risk_score == 100
    assert reasons == [{"code": "BLACKLISTED", "label": "Arnaque connue", "severity": "high"}]
    assert backend.calls == 0
    assert job.risk_assessed_at is not None


async def test_assess_job_risk_calls_llm_and_caches(db_session):
    source = await _make_source(db_session)
    job = await _make_job(db_session, source)
    assessment = make_risk_assessment(
        risk_score=70,
        reasons=[{"code": "NO_BUDGET", "label": "Aucun budget indique", "severity": "medium"}],
    )
    backend = FakeRiskAssessmentBackend([assessment])

    risk_score, reasons = await assess_job_risk(
        db_session, job, backend=backend, model="claude-sonnet-5"
    )

    assert risk_score == 70
    assert reasons[0]["code"] == "NO_BUDGET"
    assert backend.calls == 1

    calls = (
        (await db_session.execute(select(LLMCall).where(LLMCall.purpose == "detect_scam")))
        .scalars()
        .all()
    )
    assert len(calls) == 1
    assert calls[0].cache_hit is False


async def test_assess_pending_jobs_risk_skips_already_assessed(db_session):
    source = await _make_source(db_session)
    await _make_job(db_session, source)
    backend = FakeRiskAssessmentBackend([make_risk_assessment()])

    summary = await assess_pending_jobs_risk(db_session, backend=backend, model="claude-sonnet-5")
    assert summary.assessed == 1

    backend_second_run = FakeRiskAssessmentBackend([])
    summary2 = await assess_pending_jobs_risk(
        db_session, backend=backend_second_run, model="claude-sonnet-5"
    )
    assert summary2.assessed == 0  # deja evalue, pas de force=True
