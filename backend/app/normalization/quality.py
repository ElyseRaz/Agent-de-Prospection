from app.normalization.schema import ExtractedJobLLM


def compute_quality_score(extracted: ExtractedJobLLM, description_clean: str) -> int:
    """Score de completude 0-100 : presence des champs cles d'une annonce
    exploitable. Deterministe, independant du LLM (pas de nouvel appel)."""

    has_rate = extracted.rate is not None and (
        extracted.rate.min is not None or extracted.rate.max is not None
    )

    checks = [
        bool(extracted.title),
        len(description_clean) >= 200,
        bool(extracted.company_name),
        has_rate,
        extracted.contract_type is not None,
        extracted.remote_type is not None,
        bool(extracted.tech_stack),
        extracted.seniority is not None,
    ]
    return round(100 * sum(checks) / len(checks))
