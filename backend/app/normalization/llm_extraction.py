from dataclasses import dataclass
from typing import Protocol

import anthropic
import structlog
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import LLMCall, LLMExtractionCache
from app.normalization.schema import ExtractedJobLLM

log = structlog.get_logger(__name__)

PURPOSE_EXTRACT_JOB = "extract_job"

# Tarifs officiels $/1M tokens (entree, sortie). Mettre a jour si les prix
# changent ; voir la documentation du modele utilise.
PRICING_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


def compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICING_USD_PER_MTOK.get(model, (0.0, 0.0))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class ExtractionValidationError(Exception):
    """Leve quand la sortie du LLM ne valide pas le schema Pydantic attendu,
    ou quand l'appel API echoue. Declenche le retry automatique."""


@dataclass(slots=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float


class JobExtractionBackend(Protocol):
    """Seam injectable : la vraie implementation appelle l'API Anthropic: les
    tests injectent un double sans reseau ni cle API."""

    async def extract(
        self, *, system_prompt: str, user_text: str
    ) -> tuple[ExtractedJobLLM, LLMUsage]: ...


class AnthropicJobExtractionBackend:
    """Implementation reelle : appelle l'API Anthropic via le SDK officiel
    (Structured Outputs, `messages.parse` + `output_format`)."""

    def __init__(self, *, model: str, api_key: str | None = None) -> None:
        self._model = model
        self._client = (
            anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()
        )

    async def extract(
        self, *, system_prompt: str, user_text: str
    ) -> tuple[ExtractedJobLLM, LLMUsage]:
        try:
            response = await self._client.messages.parse(
                model=self._model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_text}],
                output_format=ExtractedJobLLM,
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


async def extract_job_structured(
    db: AsyncSession,
    *,
    backend: JobExtractionBackend,
    content_hash: str,
    prompt_version: str,
    system_prompt: str,
    user_text: str,
    model: str,
    max_retries: int = 2,
) -> ExtractedJobLLM:
    """Extrait une offre structuree, en passant par le cache (content_hash +
    prompt_version + purpose) et en journalisant chaque tentative dans
    llm_calls. Retente jusqu'a `max_retries` fois si la sortie est invalide."""

    cached = await db.scalar(
        select(LLMExtractionCache).where(
            LLMExtractionCache.content_hash == content_hash,
            LLMExtractionCache.prompt_version == prompt_version,
            LLMExtractionCache.purpose == PURPOSE_EXTRACT_JOB,
        )
    )
    if cached is not None:
        db.add(
            LLMCall(
                purpose=PURPOSE_EXTRACT_JOB,
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
        log.info("llm_cache_hit", content_hash=content_hash, prompt_version=prompt_version)
        return ExtractedJobLLM.model_validate(cached.response_json)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):
        try:
            parsed, usage = await backend.extract(system_prompt=system_prompt, user_text=user_text)
        except ExtractionValidationError as exc:
            last_error = exc
            log.warning(
                "llm_extraction_attempt_failed",
                attempt=attempt,
                content_hash=content_hash,
                error=str(exc),
            )
            continue

        db.add(
            LLMCall(
                purpose=PURPOSE_EXTRACT_JOB,
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
                purpose=PURPOSE_EXTRACT_JOB,
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
