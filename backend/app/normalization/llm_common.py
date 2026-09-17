from dataclasses import dataclass

# Tarifs officiels $/1M tokens (entree, sortie) pour les modeles Claude. Un
# modele absent de cette table (ex: expose par une passerelle tierce sans
# tarif public connu, comme un modele OpenAI-compatible personnalise) retombe
# sur (0.0, 0.0) : le cout journalise sera 0$ jusqu'a completion manuelle de
# cette table.
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
