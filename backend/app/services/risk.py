import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blacklist import BlacklistEntityType
from app.models.company import Company
from app.models.job import Job, JobStatus, SeniorityLevel
from app.models.reputation import CompanyReputation
from app.normalization.prompt_loader import load_prompt
from app.normalization.risk_extraction import RiskAssessmentBackend, assess_risk_structured
from app.reputation.base import ReputationProvider
from app.services.blacklist import find_shared_blacklist_entry
from app.services.reputation import get_or_fetch_reputation

log = structlog.get_logger(__name__)

PROMPT_VERSION = "detect_scam_v1"
UNDERPAID_RATIO_THRESHOLD = 0.5
BAD_REPUTATION_RATING_THRESHOLD = 2.5
DUPLICATE_COMPANY_THRESHOLD = 3


@dataclass(slots=True)
class RiskSignals:
    has_budget: bool
    market_median_eur: float | None
    underpaid_ratio: float | None
    company_domain_known: bool
    company_checked_on_trustpilot: bool
    company_found_on_trustpilot: bool | None
    company_rating: float | None
    company_review_count: int | None
    duplicate_company_count: int
    is_blacklisted: bool
    blacklist_reason: str | None


@dataclass(slots=True)
class RiskBatchSummary:
    assessed: int = 0
    failed: int = 0


async def compute_deterministic_signals(
    db: AsyncSession, job: Job, *, company: Company | None
) -> RiskSignals:
    has_budget = job.rate_min is not None or job.rate_max is not None

    market_median_eur: float | None = None
    underpaid_ratio: float | None = None
    if job.rate_eur_normalized is not None and job.seniority is not None:
        median = await _median_rate_for_seniority(db, job.seniority, exclude_job_id=job.id)
        if median is not None and median > 0:
            market_median_eur = float(median)
            underpaid_ratio = float(job.rate_eur_normalized) / float(median)

    company_domain_known = bool(company and company.domain)
    company_checked_on_trustpilot = False
    company_found_on_trustpilot: bool | None = None
    company_rating: float | None = None
    company_review_count: int | None = None

    if company is not None:
        reputation = await db.scalar(
            select(CompanyReputation).where(
                CompanyReputation.company_id == company.id,
                CompanyReputation.provider == "trustpilot",
            )
        )
        if reputation is not None:
            company_checked_on_trustpilot = True
            company_found_on_trustpilot = reputation.rating is not None
            company_rating = float(reputation.rating) if reputation.rating is not None else None
            company_review_count = reputation.review_count

    duplicate_company_count = await _count_distinct_companies_in_cluster(db, job)

    is_blacklisted = False
    blacklist_reason: str | None = None
    if company is not None:
        entry = await find_shared_blacklist_entry(
            db, entity_type=BlacklistEntityType.COMPANY, value=company.normalized_name
        )
        if entry is not None:
            is_blacklisted = True
            blacklist_reason = entry.reason

    return RiskSignals(
        has_budget=has_budget,
        market_median_eur=market_median_eur,
        underpaid_ratio=underpaid_ratio,
        company_domain_known=company_domain_known,
        company_checked_on_trustpilot=company_checked_on_trustpilot,
        company_found_on_trustpilot=company_found_on_trustpilot,
        company_rating=company_rating,
        company_review_count=company_review_count,
        duplicate_company_count=duplicate_company_count,
        is_blacklisted=is_blacklisted,
        blacklist_reason=blacklist_reason,
    )


async def _median_rate_for_seniority(
    db: AsyncSession, seniority: SeniorityLevel, *, exclude_job_id: uuid.UUID
) -> Decimal | None:
    stmt = select(func.percentile_cont(0.5).within_group(Job.rate_eur_normalized)).where(
        Job.seniority == seniority,
        Job.status == JobStatus.ACTIVE,
        Job.rate_eur_normalized.is_not(None),
        Job.id != exclude_job_id,
    )
    result = await db.scalar(stmt)
    return Decimal(str(result)) if result is not None else None


async def _count_distinct_companies_in_cluster(db: AsyncSession, job: Job) -> int:
    cluster_root_id = job.canonical_id or job.id
    stmt = select(func.count(func.distinct(Job.company_id))).where(
        or_(Job.id == cluster_root_id, Job.canonical_id == cluster_root_id),
        Job.company_id.is_not(None),
    )
    result = await db.scalar(stmt)
    return result or 0


async def assess_job_risk(
    db: AsyncSession,
    job: Job,
    *,
    backend: RiskAssessmentBackend,
    model: str,
    reputation_provider: ReputationProvider | None = None,
) -> tuple[int, list[dict]]:
    """Evalue le risque d'un job : court-circuite sur liste noire partagee,
    sinon signaux deterministes + jugement LLM sur le texte.

    Si `reputation_provider` est fourni et que l'entreprise a un domaine
    connu, rafraichit d'abord sa reputation Trustpilot (cache 30 jours, voir
    get_or_fetch_reputation) avant de calculer les signaux."""

    company = await db.get(Company, job.company_id) if job.company_id else None
    if company is not None and company.domain and reputation_provider is not None:
        await get_or_fetch_reputation(db, company, provider=reputation_provider)

    signals = await compute_deterministic_signals(db, job, company=company)

    if signals.is_blacklisted:
        risk_score = 100
        reasons = [
            {
                "code": "BLACKLISTED",
                "label": signals.blacklist_reason or "Entreprise dans la liste noire partagee",
                "severity": "high",
            }
        ]
    else:
        system_prompt = load_prompt(PROMPT_VERSION)
        user_text = _build_risk_user_text(job, signals)
        content_hash = _compute_risk_content_hash(job, signals)

        assessment = await assess_risk_structured(
            db,
            backend=backend,
            content_hash=content_hash,
            prompt_version=PROMPT_VERSION,
            system_prompt=system_prompt,
            user_text=user_text,
            model=model,
        )
        risk_score = assessment.risk_score
        reasons = [r.model_dump() for r in assessment.reasons]

    job.risk_score = risk_score
    job.risk_reasons = reasons
    job.risk_assessed_at = datetime.now(UTC)
    await db.commit()
    log.info("job_risk_assessed", job_id=str(job.id), risk_score=risk_score)
    return risk_score, reasons


async def assess_pending_jobs_risk(
    db: AsyncSession,
    *,
    backend: RiskAssessmentBackend,
    model: str,
    reputation_provider: ReputationProvider | None = None,
    limit: int = 100,
    force: bool = False,
) -> RiskBatchSummary:
    query = select(Job).where(Job.status == JobStatus.ACTIVE).order_by(Job.detected_at).limit(limit)
    if not force:
        query = query.where(Job.risk_assessed_at.is_(None))

    jobs = (await db.execute(query)).scalars().all()

    summary = RiskBatchSummary()
    for job in jobs:
        try:
            await assess_job_risk(
                db, job, backend=backend, model=model, reputation_provider=reputation_provider
            )
            summary.assessed += 1
        except Exception as exc:  # isole l'echec d'un job du reste du lot
            log.error("job_risk_assessment_failed", job_id=str(job.id), error=str(exc))
            summary.failed += 1

    return summary


def _build_risk_user_text(job: Job, signals: RiskSignals) -> str:
    lines = [
        f"Titre : {job.title}",
        f"Description : {job.description_clean[:2000] or '(vide)'}",
        "",
        "Signaux verifies (ne pas depasser ce qui est ecrit ici, les seuils sont deja appliques) :",
        f"- Budget declare dans l'annonce : {signals.has_budget}",
    ]

    if signals.market_median_eur is not None and signals.underpaid_ratio is not None:
        is_underpaid = signals.underpaid_ratio < UNDERPAID_RATIO_THRESHOLD
        verdict = "SOUS-PAYE (sous le seuil)" if is_underpaid else "dans la norme du marche"
        lines.append(
            f"- TJM de l'offre / mediane du marche (meme seniorite) : "
            f"ratio={signals.underpaid_ratio:.2f}, seuil={UNDERPAID_RATIO_THRESHOLD} -> {verdict}"
        )
    else:
        lines.append("- Comparaison au marche : non disponible (pas assez de donnees)")

    if signals.company_checked_on_trustpilot:
        if signals.company_found_on_trustpilot:
            rating = signals.company_rating
            is_bad = rating is not None and rating < BAD_REPUTATION_RATING_THRESHOLD
            verdict = "NOTE BASSE (sous le seuil)" if is_bad else "note correcte"
            lines.append(
                f"- Entreprise recherchee et trouvee sur Trustpilot : note={rating}, "
                f"nombre d'avis={signals.company_review_count}, "
                f"seuil={BAD_REPUTATION_RATING_THRESHOLD} -> {verdict}"
            )
        else:
            lines.append("- Entreprise recherchee sur Trustpilot et NON trouvee (confirme)")
    else:
        lines.append("- Reputation Trustpilot : non verifiee (aucun domaine connu, pas de verdict)")

    is_duplicate_spam = signals.duplicate_company_count >= DUPLICATE_COMPANY_THRESHOLD
    verdict = "SEUIL ATTEINT" if is_duplicate_spam else "sous le seuil"
    lines.append(
        f"- Entreprises distinctes ayant publie une annonce quasi identique : "
        f"{signals.duplicate_company_count}, seuil={DUPLICATE_COMPANY_THRESHOLD} -> {verdict}"
    )

    return "\n".join(lines)


def _compute_risk_content_hash(job: Job, signals: RiskSignals) -> str:
    payload = {
        "job_id": str(job.id),
        "description_hash": hashlib.sha256((job.description_clean or "").encode()).hexdigest(),
        "signals": asdict(signals),
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
