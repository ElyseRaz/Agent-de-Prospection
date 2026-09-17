import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.job import ContractType, Job, JobSkill, JobStatus
from app.models.matching import Match, MatchFeedbackAction
from app.models.profile import Profile, ProfileSkill, SkillLevel
from app.models.skill import Skill
from app.models.source import AccessType, Source
from app.models.user import User, UserRole
from app.services.matching import (
    _rate_contribution,
    _reliability_contribution,
    _semantic_contribution,
    _skills_contribution,
    _timezone_contribution,
    compute_top_matches,
    record_match_feedback,
)
from tests.conftest import cosine_test_vector

pytestmark = pytest.mark.asyncio


async def _make_user(db_session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="x", role=UserRole.USER)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


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


async def _make_skill(db_session, slug: str, label: str | None = None) -> Skill:
    skill = Skill(slug=slug, label=label or slug, category=None, aliases=[])
    db_session.add(skill)
    await db_session.flush()
    return skill


async def _make_profile(db_session, user, **overrides) -> Profile:
    defaults = dict(user_id=user.id, name="Data Engineer")
    defaults.update(overrides)
    profile = Profile(**defaults)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


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
    )
    defaults.update(overrides)
    job = Job(**defaults)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


# --- Axes de score isoles -----------------------------------------------


def test_semantic_contribution_without_embeddings_is_neutral():
    points, label = _semantic_contribution(None, None, weight=25)
    assert points == 12.5
    assert "non calculee" in label


def test_semantic_contribution_identical_vectors_gets_full_weight():
    vector = cosine_test_vector(768)
    points, _label = _semantic_contribution(vector, vector, weight=25)
    assert points == pytest.approx(25.0)


def test_skills_contribution_full_coverage():
    points, label = _skills_contribution(
        {"python", "fastapi"}, [("python", "Python"), ("fastapi", "FastAPI")], weight=30
    )
    assert points == 30
    assert "Python" in label and "FastAPI" in label


def test_skills_contribution_partial_coverage():
    points, label = _skills_contribution(
        {"python"}, [("python", "Python"), ("fastapi", "FastAPI")], weight=30
    )
    assert points == 15
    assert "manquantes" in label


def test_skills_contribution_no_required_skills_is_neutral():
    points, label = _skills_contribution({"python"}, [], weight=30)
    assert points == 15
    assert "Aucune competence requise" in label


def test_rate_contribution_above_target():
    points, label = _rate_contribution(Decimal("600"), Decimal("500"), Decimal("400"), weight=25)
    assert points == 25
    assert "au-dessus" in label


def test_rate_contribution_between_floor_and_target():
    points, _label = _rate_contribution(Decimal("450"), Decimal("500"), Decimal("400"), weight=25)
    assert points == pytest.approx(25 * 0.5)


def test_rate_contribution_below_floor_is_negative():
    points, label = _rate_contribution(Decimal("250"), Decimal("500"), Decimal("400"), weight=25)
    assert points < 0
    assert "sous votre plancher" in label


def test_rate_contribution_missing_rate_is_neutral():
    points, label = _rate_contribution(None, Decimal("500"), Decimal("400"), weight=25)
    assert points == 12.5
    assert "non precise" in label


def test_reliability_contribution_low_risk_is_positive():
    points, label = _reliability_contribution(0, weight=10)
    assert points == 10
    assert "faible" in label


def test_reliability_contribution_high_risk_is_negative():
    points, label = _reliability_contribution(100, weight=10)
    assert points == -10
    assert "eleve" in label


def test_timezone_contribution_no_constraint_is_full_weight():
    points, label = _timezone_contribution("Europe/Paris", None, weight=10)
    assert points == 10
    assert "Aucune contrainte" in label


def test_timezone_contribution_matching_region():
    points, _label = _timezone_contribution(
        "Europe/Paris", "Chevauchement avec Paris/CET", weight=10
    )
    assert points == 10


def test_timezone_contribution_uncertain():
    points, _label = _timezone_contribution("Europe/Paris", "UTC-5 a UTC-8", weight=10)
    assert points == pytest.approx(3.0)


# --- Bout-en-bout ---------------------------------------------------------


async def test_compute_top_matches_ranks_and_persists(db_session):
    user = await _make_user(db_session)
    source = await _make_source(db_session)
    python_skill = await _make_skill(db_session, "python", "Python")

    profile = await _make_profile(db_session, user)
    db_session.add(
        ProfileSkill(
            profile_id=profile.id,
            skill_id=python_skill.id,
            level=SkillLevel.EXPERT,
            is_required=True,
        )
    )
    await db_session.commit()

    matching_job = await _make_job(
        db_session, source, title="Python freelance mission", rate_eur_normalized=Decimal("600")
    )
    db_session.add(
        JobSkill(job_id=matching_job.id, skill_id=python_skill.id, is_required=True, weight=1.0)
    )
    other_job = await _make_job(
        db_session,
        source,
        title="Comptable",
        external_id=str(uuid.uuid4()),
        rate_eur_normalized=Decimal("100"),
    )
    await db_session.commit()

    results = await compute_top_matches(db_session, profile, limit=10)

    assert len(results) == 2
    assert results[0].job.id == matching_job.id
    assert results[0].score > results[1].score

    stored = (
        (await db_session.execute(select(Match).where(Match.profile_id == profile.id)))
        .scalars()
        .all()
    )
    assert len(stored) == 2
    assert {m.job_id for m in stored} == {matching_job.id, other_job.id}


async def test_weight_learning_adjusts_after_enough_feedback(db_session):
    user = await _make_user(db_session)
    source = await _make_source(db_session)
    profile = await _make_profile(db_session, user)

    # 3 offres bien payees "sauvegardees", 3 mal payees "rejetees" : le
    # critere TJM devrait voir son poids augmenter.
    saved_jobs = []
    for _ in range(3):
        job = await _make_job(
            db_session,
            source,
            external_id=str(uuid.uuid4()),
            rate_eur_normalized=Decimal("900"),
        )
        saved_jobs.append(job)

    rejected_jobs = []
    for _ in range(3):
        job = await _make_job(
            db_session,
            source,
            external_id=str(uuid.uuid4()),
            rate_eur_normalized=Decimal("100"),
        )
        rejected_jobs.append(job)

    profile.target_rate = Decimal("500")
    profile.floor_rate = Decimal("300")
    await db_session.commit()

    # Calcule et persiste les matches (necessaire pour que le breakdown existe
    # avant de pouvoir apprendre dessus).
    await compute_top_matches(db_session, profile, limit=10)

    initial_rate_weight = profile.weights["rate"]

    for job in saved_jobs:
        await record_match_feedback(db_session, profile, job.id, MatchFeedbackAction.SAVED)
    for job in rejected_jobs:
        await record_match_feedback(db_session, profile, job.id, MatchFeedbackAction.REJECTED)

    await db_session.refresh(profile)
    assert profile.weights["rate"] > initial_rate_weight
    assert sum(profile.weights.values()) == pytest.approx(100.0, abs=0.1)


async def test_weight_learning_does_nothing_below_sample_threshold(db_session):
    user = await _make_user(db_session)
    source = await _make_source(db_session)
    profile = await _make_profile(db_session, user)
    job = await _make_job(db_session, source)

    await compute_top_matches(db_session, profile, limit=10)
    initial_weights = dict(profile.weights)

    await record_match_feedback(db_session, profile, job.id, MatchFeedbackAction.SAVED)

    await db_session.refresh(profile)
    assert profile.weights == initial_weights
