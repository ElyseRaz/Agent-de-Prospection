from typing import TYPE_CHECKING, Protocol

import anthropic
import httpx
import structlog
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import LLMCall, LLMExtractionCache
from app.normalization.llm_common import ExtractionValidationError, LLMUsage, compute_cost_usd
from app.normalization.openai_compatible import call_openai_compatible_json
from app.normalization.risk_schema import RiskAssessment

if TYPE_CHECKING:
    from app.core.config import Settings

log = structlog.get_logger(__name__)

PURPOSE_DETECT_SCAM = "detect_scam"


class RiskAssessmentBackend(Protocol):
    """Seam injectable, meme principe que JobExtractionBackend (phase 3) :
    la vraie implementation appelle l'API Anthropic, les tests injectent un
    double sans reseau ni cle API."""

    async def assess(
        self, *, system_prompt: str, user_text: str
    ) -> tuple[RiskAssessment, LLMUsage]: ...


class AnthropicRiskAssessmentBackend:
    """Implementation reelle : Structured Outputs de l'API Claude, meme
    mecanisme que AnthropicJobExtractionBackend mais schema de sortie
    different (RiskAssessment)."""

    def __init__(self, *, model: str, api_key: str | None = None) -> None:
        self._model = model
        self._client = (
            anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()
        )

    async def assess(
        self, *, system_prompt: str, user_text: str
    ) -> tuple[RiskAssessment, LLMUsage]:
        try:
            response = await self._client.messages.parse(
                model=self._model,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_text}],
                output_format=RiskAssessment,
            )
        except anthropic.APIStatusError as exc:
            raise ExtractionValidationError(f"Erreur API Anthropic: {exc}") from exc
        except anthropic.APIConnectionError as exc:
            raise ExtractionValidationError(f"Erreur reseau Anthropic: {exc}") from exc
        except ValidationError as exc:
            raise ExtractionValidationError(f"Sortie LLM invalide: {exc}") from exc

        if response.parsed_output is None:
            raise ExtractionValidationError("Le LLM n'a pas produit de sortie structuree valide")

        usage = LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=compute_cost_usd(
                self._model, response.usage.input_tokens, response.usage.output_tokens
            ),
        )
        return response.parsed_output, usage


class OpenAICompatibleRiskAssessmentBackend:
    """Implementation alternative : meme passerelle OpenAI-compatible que
    OpenAICompatibleJobExtractionBackend, schema de sortie RiskAssessment."""

    def __init__(
        self, *, model: str, base_url: str, api_key: str, http_client: httpx.AsyncClient
    ) -> None:
        self._model = model
        self._base_url = base_url
        self._api_key = api_key
        self._http_client = http_client

    async def assess(
        self, *, system_prompt: str, user_text: str
    ) -> tuple[RiskAssessment, LLMUsage]:
        return await call_openai_compatible_json(
            self._http_client,
            base_url=self._base_url,
            api_key=self._api_key,
            model=self._model,
            system_prompt=system_prompt,
            user_text=user_text,
            output_type=RiskAssessment,
        )


def build_risk_assessment_backend(
    settings: "Settings", *, http_client: httpx.AsyncClient
) -> RiskAssessmentBackend:
    """Choisit l'implementation selon `settings.llm_provider` (defaut
    'anthropic', jamais change automatiquement)."""

    if settings.llm_provider == "openai_compatible":
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY est requis quand LLM_PROVIDER=openai_compatible"
            )
        return OpenAICompatibleRiskAssessmentBackend(
            model=settings.llm_model,
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            http_client=http_client,
        )
    return AnthropicRiskAssessmentBackend(model=settings.llm_model)


async def assess_risk_structured(
    db: AsyncSession,
    *,
    backend: RiskAssessmentBackend,
    content_hash: str,
    prompt_version: str,
    system_prompt: str,
    user_text: str,
    model: str,
    max_retries: int = 2,
) -> RiskAssessment:
    """Meme logique de cache/retry/cout que extract_job_structured (phase 3),
    dupliquee ici volontairement plutot que generalisee : les deux fonctions
    restent independantes et ne risquent pas de se casser mutuellement."""

    cached = await db.scalar(
        select(LLMExtractionCache).where(
            LLMExtractionCache.content_hash == content_hash,
            LLMExtractionCache.prompt_version == prompt_version,
            LLMExtractionCache.purpose == PURPOSE_DETECT_SCAM,
        )
    )
    if cached is not None:
        db.add(
            LLMCall(
                purpose=PURPOSE_DETECT_SCAM,
                model=cached.model,
                prompt_version=prompt_version,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0,
                cache_hit=True,
                content_hash=content_hash,
            )
        )
        await db.flush()
        log.info("risk_cache_hit", content_hash=content_hash, prompt_version=prompt_version)
        return RiskAssessment.model_validate(cached.response_json)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):
        try:
            parsed, usage = await backend.assess(system_prompt=system_prompt, user_text=user_text)
        except ExtractionValidationError as exc:
            last_error = exc
            log.warning(
                "risk_assessment_attempt_failed",
                attempt=attempt,
                content_hash=content_hash,
                error=str(exc),
            )
            continue

        db.add(
            LLMCall(
                purpose=PURPOSE_DETECT_SCAM,
                model=model,
                prompt_version=prompt_version,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost_usd=usage.cost_usd,
                cache_hit=False,
                content_hash=content_hash,
            )
        )
        cache_stmt = (
            pg_insert(LLMExtractionCache)
            .values(
                content_hash=content_hash,
                prompt_version=prompt_version,
                purpose=PURPOSE_DETECT_SCAM,
                response_json=parsed.model_dump(mode="json"),
                model=model,
            )
            .on_conflict_do_nothing(constraint="uq_llm_cache_key")
        )
        await db.execute(cache_stmt)
        await db.flush()
        return parsed

    assert last_error is not None
    raise last_error
