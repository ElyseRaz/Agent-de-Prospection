from app.normalization.raw_text.base import RawText
from app.normalization.raw_text.registry import register_raw_text_extractor


@register_raw_text_extractor("remotive")
def extract_remotive_raw_text(payload: dict) -> RawText:
    context_lines: list[str] = []

    if payload.get("candidate_required_location"):
        context_lines.append(f"Localisation requise : {payload['candidate_required_location']}")
    if payload.get("salary"):
        context_lines.append(f"Remuneration indiquee par la source : {payload['salary']}")
    if payload.get("job_type"):
        context_lines.append(f"Type de contrat indique par la source : {payload['job_type']}")
    if payload.get("category"):
        context_lines.append(f"Categorie : {payload['category']}")
    tags = payload.get("tags") or []
    if tags:
        context_lines.append(f"Tags : {', '.join(tags)}")

    return RawText(
        title=payload.get("title"),
        company_name=payload.get("company_name"),
        description_html=payload.get("description"),
        context_lines=context_lines,
    )
