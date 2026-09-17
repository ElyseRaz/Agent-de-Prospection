from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class ReputationResult:
    rating: float | None
    review_count: int | None
    country: str | None
    website_url: str | None
    raw: dict[str, Any] = field(default_factory=dict)


class ReputationLookupError(Exception):
    """Echec transitoire (reseau, erreur serveur) : a distinguer d'un
    'entreprise non trouvee' confirme. Ne doit jamais etre interprete comme un
    signal de risque - juste comme une verification inconcluante."""


class ReputationProvider(Protocol):
    async def fetch_by_domain(self, domain: str) -> ReputationResult | None:
        """Retourne None si l'entreprise a ete cherchee et n'existe pas chez
        le fournisseur. Leve ReputationLookupError si la verification n'a pas
        pu aboutir (erreur reseau/serveur)."""
        ...
