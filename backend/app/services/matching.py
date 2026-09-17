import math
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobSkill, JobStatus
from app.models.matching import Match, MatchFeedback, MatchFeedbackAction
from app.models.profile import DEFAULT_PROFILE_WEIGHTS, Profile, ProfileSkill
from app.models.skill import Skill

log = structlog.get_logger(__name__)

CANDIDATE_LIMIT = 100
MIN_FEEDBACK_SAMPLES = 3
LEARNING_RATE = 0.15
MIN_WEIGHT = 5.0
MAX_WEIGHT = 50.0


@dataclass(slots=True)
class ScoreBreakdownItem:
    criterion: str
    points: int
    label: str


@dataclass(slots=True)
class MatchResult:
    job: Job
    score: int
    breakdown: list[ScoreBreakdownItem] = field(default_factory=list)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def compute_top_matches(
    db: AsyncSession, profile: Profile, *, limit: int = 20, candidate_limit: int = CANDIDATE_LIMIT
) -> list[MatchResult]:
    """Recupere un pool de candidats (ANN semantique si le profil a un
    embedding, sinon les plus recentes), score chacun, met en cache dans
    `matches` (upsert), retourne le top `limit`."""

    base_conditions = [Job.status == JobStatus.ACTIVE, Job.canonical_id.is_(None)]
    if profile.embedding is not None:
        stmt = (
            select(Job)
            .where(*base_conditions)
            .order_by(Job.embedding.cosine_distance(profile.embedding))
            .limit(candidate_limit)
        )
    else:
        stmt = (
            select(Job)
            .where(*base_conditions)
            .order_by(Job.detected_at.desc())
            .limit(candidate_limit)
        )
    candidates = (await db.execute(stmt)).scalars().all()

    job_skills_map = await _fetch_job_skills_map(db, [job.id for job in candidates])
    required_skills = await _get_required_profile_skills(db, profile.id)

    results = [
        _score_job(
            profile,
            job,
            job_skill_slugs=job_skills_map.get(job.id, set()),
            required_skills=required_skills,
        )
        for job in candidates
    ]
    results.sort(key=lambda r: r.score, reverse=True)
    top = results[:limit]

    for result in top:
        await _upsert_match(db, profile.id, result)
    await db.commit()

    return top


async def _fetch_job_skills_map(
    db: AsyncSession, job_ids: list[uuid.UUID]
) -> dict[uuid.UUID, set[str]]:
    if not job_ids:
        return {}
    rows = await db.execute(
        select(JobSkill.job_id, Skill.slug)
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(JobSkill.job_id.in_(job_ids))
    )
    mapping: dict[uuid.UUID, set[str]] = defaultdict(set)
    for job_id, slug in rows:
        mapping[job_id].add(slug)
    return dict(mapping)


async def _get_required_profile_skills(
    db: AsyncSession, profile_id: uuid.UUID
) -> list[tuple[str, str]]:
    rows = await db.execute(
        select(Skill.slug, Skill.label)
        .join(ProfileSkill, ProfileSkill.skill_id == Skill.id)
        .where(ProfileSkill.profile_id == profile_id, ProfileSkill.is_required.is_(True))
    )
    return list(rows.all())


def _score_job(
    profile: Profile,
    job: Job,
    *,
    job_skill_slugs: set[str],
    required_skills: list[tuple[str, str]],
) -> MatchResult:
    weights = {**DEFAULT_PROFILE_WEIGHTS, **(profile.weights or {})}
    breakdown: list[ScoreBreakdownItem] = []
    total = 0.0

    points, label = _semantic_contribution(profile.embedding, job.embedding, weights["semantic"])
    breakdown.append(ScoreBreakdownItem("semantic", round(points), label))
    total += points

    points, label = _skills_contribution(job_skill_slugs, required_skills, weights["skills"])
    breakdown.append(ScoreBreakdownItem("skills", round(points), label))
    total += points

    points, label = _rate_contribution(
        job.rate_eur_normalized, profile.target_rate, profile.floor_rate, weights["rate"]
    )
    breakdown.append(ScoreBreakdownItem("rate", round(points), label))
    total += points

    points, label = _timezone_contribution(
        profile.timezone, job.timezone_constraint, weights["timezone"]
    )
    breakdown.append(ScoreBreakdownItem("timezone", round(points), label))
    total += points

    points, label = _reliability_contribution(job.risk_score, weights["reliability"])
    breakdown.append(ScoreBreakdownItem("reliability", round(points), label))
    total += points

    score = max(0, min(100, round(total)))
    return MatchResult(job=job, score=score, breakdown=breakdown)


def _semantic_contribution(
    profile_embedding: list[float] | None, job_embedding: list[float] | None, weight: float
) -> tuple[float, str]:
    if profile_embedding is None or job_embedding is None:
        return weight * 0.5, "Similarite semantique non calculee (profil ou offre sans embedding)"

    similarity = max(0.0, min(1.0, cosine_similarity(profile_embedding, job_embedding)))
    contribution = weight * similarity
    if similarity >= 0.6:
        label = "Offre semantiquement tres proche du profil"
    elif similarity >= 0.35:
        label = "Offre semantiquement proche du profil"
    else:
        label = "Faible similarite semantique avec le profil"
    return contribution, label


def _skills_contribution(
    job_skill_slugs: set[str], required_skills: list[tuple[str, str]], weight: float
) -> tuple[float, str]:
    if not required_skills:
        return weight * 0.5, "Aucune competence requise definie dans le profil"

    matched = [label for slug, label in required_skills if slug in job_skill_slugs]
    missing = [label for slug, label in required_skills if slug not in job_skill_slugs]
    coverage = len(matched) / len(required_skills)
    contribution = weight * coverage

    if matched and not missing:
        label = f"Toutes vos competences requises correspondent : {', '.join(matched)}"
    elif matched:
        label = (
            f"Competences correspondantes : {', '.join(matched)} "
            f"(manquantes : {', '.join(missing)})"
        )
    else:
        label = f"Aucune competence requise trouvee (manquantes : {', '.join(missing)})"
    return contribution, label


def _rate_contribution(
    job_rate: Decimal | None, target: Decimal | None, floor: Decimal | None, weight: float
) -> tuple[float, str]:
    if job_rate is None:
        return weight * 0.5, "TJM non precise dans l'annonce"

    if target is None and floor is None:
        return (
            weight * 0.5,
            f"TJM de l'offre : {job_rate:.0f} EUR (pas de cible definie dans le profil)",
        )

    if floor is not None and job_rate < floor:
        ratio = min(1.0, float((floor - job_rate) / floor)) if floor > 0 else 1.0
        return -weight * ratio, f"TJM {job_rate:.0f} EUR sous votre plancher de {floor:.0f} EUR"

    if target is not None and job_rate >= target:
        return weight, f"TJM {job_rate:.0f} EUR au-dessus de votre cible de {target:.0f} EUR"

    if target is not None and floor is not None and target > floor:
        ratio = float((job_rate - floor) / (target - floor))
        return weight * ratio, f"TJM {job_rate:.0f} EUR entre votre plancher et votre cible"

    return weight * 0.5, f"TJM de l'offre : {job_rate:.0f} EUR"


def _timezone_contribution(
    profile_timezone: str | None, constraint: str | None, weight: float
) -> tuple[float, str]:
    if not constraint:
        return weight, "Aucune contrainte de fuseau horaire dans l'annonce"

    if not profile_timezone:
        return (
            weight * 0.5,
            f"Contrainte de fuseau declaree ({constraint}), fuseau du profil non renseigne",
        )

    # Heuristique simple (pas un parseur de plages UTC) : le nom de la region
    # du fuseau du profil apparait-il dans le texte de la contrainte ?
    region = profile_timezone.rsplit("/", maxsplit=1)[-1].replace("_", " ").lower()
    if region and region in constraint.lower():
        return weight, f"Fuseau compatible avec la contrainte ({constraint})"
    return weight * 0.3, f"Compatibilite du fuseau incertaine avec la contrainte ({constraint})"


def _reliability_contribution(risk_score: int, weight: float) -> tuple[float, str]:
    normalized = max(-1.0, min(1.0, (50 - risk_score) / 50))
    contribution = weight * normalized
    if risk_score >= 70:
        label = f"Score de risque eleve de l'offre ({risk_score}/100)"
    elif risk_score <= 20:
        label = f"Score de risque faible de l'offre ({risk_score}/100)"
    else:
        label = f"Score de risque modere de l'offre ({risk_score}/100)"
    return contribution, label


async def _upsert_match(db: AsyncSession, profile_id: uuid.UUID, result: MatchResult) -> None:
    stmt = (
        pg_insert(Match)
        .values(
            profile_id=profile_id,
            job_id=result.job.id,
            score=result.score,
            breakdown=[asdict(item) for item in result.breakdown],
        )
        .on_conflict_do_update(
            constraint="uq_matches_profile_job",
            set_={
                "score": result.score,
                "breakdown": [asdict(item) for item in result.breakdown],
                "computed_at": func.now(),
            },
        )
    )
    await db.execute(stmt)


async def record_match_feedback(
    db: AsyncSession, profile: Profile, job_id: uuid.UUID, action: MatchFeedbackAction
) -> None:
    stmt = (
        pg_insert(MatchFeedback)
        .values(profile_id=profile.id, job_id=job_id, action=action)
        .on_conflict_do_update(
            constraint="uq_match_feedback_profile_job",
            set_={"action": action, "created_at": func.now()},
        )
    )
    await db.execute(stmt)
    await db.commit()
    await _adjust_profile_weights(db, profile)


async def _adjust_profile_weights(db: AsyncSession, profile: Profile) -> None:
    """Heuristique d'apprentissage implicite : compare, pour chaque critere,
    sa contribution moyenne (deja stockee dans `matches.breakdown`) entre les
    offres sauvegardees et rejetees de ce profil. Un critere systematiquement
    plus haut dans les offres sauvegardees voit son poids augmenter, et
    inversement. N'agit qu'a partir de `MIN_FEEDBACK_SAMPLES` de chaque cote,
    pour eviter de sur-reagir a un seul clic."""

    saved_ids = await _feedback_job_ids(db, profile.id, MatchFeedbackAction.SAVED)
    rejected_ids = await _feedback_job_ids(db, profile.id, MatchFeedbackAction.REJECTED)

    if len(saved_ids) < MIN_FEEDBACK_SAMPLES or len(rejected_ids) < MIN_FEEDBACK_SAMPLES:
        return

    saved_avg = await _average_breakdown_points(db, profile.id, saved_ids)
    rejected_avg = await _average_breakdown_points(db, profile.id, rejected_ids)

    weights = {**DEFAULT_PROFILE_WEIGHTS, **(profile.weights or {})}
    for criterion in weights:
        delta = saved_avg.get(criterion, 0.0) - rejected_avg.get(criterion, 0.0)
        adjusted = weights[criterion] + LEARNING_RATE * delta
        weights[criterion] = max(MIN_WEIGHT, min(MAX_WEIGHT, adjusted))

    total_weight = sum(weights.values()) or 1.0
    normalized_weights = {k: round(v * 100 / total_weight, 2) for k, v in weights.items()}

    profile.weights = normalized_weights
    await db.commit()
    log.info("profile_weights_adjusted", profile_id=str(profile.id), weights=normalized_weights)


async def _feedback_job_ids(
    db: AsyncSession, profile_id: uuid.UUID, action: MatchFeedbackAction
) -> list[uuid.UUID]:
    rows = await db.scalars(
        select(MatchFeedback.job_id).where(
            MatchFeedback.profile_id == profile_id, MatchFeedback.action == action
        )
    )
    return list(rows.all())


async def _average_breakdown_points(
    db: AsyncSession, profile_id: uuid.UUID, job_ids: list[uuid.UUID]
) -> dict[str, float]:
    if not job_ids:
        return {}

    rows = await db.scalars(
        select(Match.breakdown).where(Match.profile_id == profile_id, Match.job_id.in_(job_ids))
    )
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for breakdown in rows:
        for item in breakdown:
            sums[item["criterion"]] += item["points"]
            counts[item["criterion"]] += 1

    return {criterion: sums[criterion] / counts[criterion] for criterion in sums}
