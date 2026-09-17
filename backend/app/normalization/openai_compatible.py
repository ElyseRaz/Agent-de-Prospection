import json

import httpx
import structlog
from pydantic import BaseModel, ValidationError

from app.normalization.llm_common import ExtractionValidationError, LLMUsage, compute_cost_usd

log = structlog.get_logger(__name__)


async def call_openai_compatible_json[T: BaseModel](
    http_client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_text: str,
    output_type: type[T],
) -> tuple[T, LLMUsage]:
    """Appelle une passerelle compatible OpenAI (`POST {base_url}/chat/completions`,
    mode JSON via `response_format: {type: json_object}`) et valide la sortie
    contre `output_type`.

    Implemente en HTTP direct (httpx), pas via le SDK officiel `openai` : le
    contrat REST "chat completions" est le standard de facto que toute
    passerelle "OpenAI-compatible" (ex: opencode.ai) s'engage a respecter,
    et s'appuyer dessus directement evite toute hypothese non verifiee sur
    les internals d'un SDK tiers - coherent avec le reste du projet
    (Frankfurter, Trustpilot, appeles en HTTP direct pour la meme raison).

    ATTENTION cout : `compute_cost_usd` n'a de tarif que pour les modeles
    listes dans PRICING_USD_PER_MTOK (modeles Claude). Un modele inconnu (ex:
    un modele expose par une passerelle tierce sans tarif public) renvoie un
    cout de 0$ - a completer manuellement si le cout doit etre suivi avec
    precision pour ce modele.
    """

    schema_hint = json.dumps(output_type.model_json_schema())
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    f"Schema JSON strict attendu, renvoie UNIQUEMENT ce JSON "
                    f"(aucun texte hors JSON) :\n{schema_hint}"
                ),
            },
            {"role": "user", "content": user_text},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        response = await http_client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        raise ExtractionValidationError(
            f"Erreur reseau (endpoint OpenAI-compatible): {exc}"
        ) from exc

    if response.status_code >= 400:
        raise ExtractionValidationError(
            f"Erreur API OpenAI-compatible ({response.status_code}): {response.text[:500]}"
        )

    body = response.json()
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise ExtractionValidationError(
            "Reponse OpenAI-compatible sans contenu exploitable"
        ) from exc

    if not content:
        raise ExtractionValidationError("Reponse OpenAI-compatible vide")

    try:
        data = json.loads(content)
        parsed = output_type.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ExtractionValidationError(f"Sortie JSON invalide: {exc}") from exc

    usage_raw = body.get("usage") or {}
    input_tokens = usage_raw.get("prompt_tokens", 0)
    output_tokens = usage_raw.get("completion_tokens", 0)
    cost_usd = compute_cost_usd(model, input_tokens, output_tokens)

    usage = LLMUsage(input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost_usd)
    return parsed, usage
