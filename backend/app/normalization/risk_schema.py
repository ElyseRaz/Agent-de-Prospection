from typing import Literal

from pydantic import BaseModel, Field

# Codes autorises pour le LLM (voir prompts/detect_scam_v1.md). "BLACKLISTED"
# n'y figure pas : il est reserve au court-circuit Python (liste noire), jamais
# genere par le LLM, donc jamais construit via ce modele.
RiskCode = Literal[
    "NO_BUDGET",
    "UNDERPAID",
    "UNPAID_TEST",
    "PERSONAL_CONTACT_ONLY",
    "COMPANY_NOT_FOUND",
    "BAD_REPUTATION",
    "DUPLICATE_SPAM",
    "UPFRONT_PAYMENT",
    "VAGUE_SCOPE",
]


class RiskReason(BaseModel):
    code: RiskCode
    label: str
    severity: Literal["low", "medium", "high"]


class RiskAssessment(BaseModel):
    """Schema strict de sortie du LLM de detection d'arnaque (voir
    prompts/detect_scam_v1.md). Le LLM ne signale que ce qui est explicitement
    etaye par l'offre et les signaux structures fournis en contexte."""

    risk_score: int = Field(ge=0, le=100)
    reasons: list[RiskReason] = Field(default_factory=list)
