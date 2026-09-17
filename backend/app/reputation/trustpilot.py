import httpx
import structlog

from app.reputation.base import ReputationLookupError, ReputationResult

log = structlog.get_logger(__name__)

# API Business Units (publique) de Trustpilot. Champs confirmes dans la
# documentation publique (developers.trustpilot.com/business-units-api-(public)) :
# `/find?name=<domaine>` prend un DOMAINE (pas un nom en texte libre - cette
# API publique n'expose pas de recherche floue par nom), et renvoie deja
# `score.trustScore`, `score.stars`, `numberOfReviews.total`, `country`,
# `websiteUrl`. `/{id}` renvoie la meme forme, utilise en repli defensif si
# `/find` ne les inclut pas.
FIND_URL = "https://api.trustpilot.com/v1/business-units/find"
DETAIL_URL_TEMPLATE = "https://api.trustpilot.com/v1/business-units/{business_unit_id}"


class TrustpilotReputationProvider:
    def __init__(self, *, api_key: str, http_client: httpx.AsyncClient) -> None:
        self._api_key = api_key
        self._http_client = http_client

    async def fetch_by_domain(self, domain: str) -> ReputationResult | None:
        headers = {"apikey": self._api_key}

        try:
            response = await self._http_client.get(
                FIND_URL, params={"name": domain}, headers=headers, timeout=10.0
            )
        except httpx.HTTPError as exc:
            raise ReputationLookupError(f"Erreur reseau Trustpilot: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ReputationLookupError(
                f"Erreur Trustpilot ({response.status_code}) pour le domaine {domain!r}"
            )

        data = response.json()
        if not data.get("id"):
            return None

        if "score" not in data:
            data = await self._fetch_detail(data["id"], headers=headers)
            if data is None:
                return None

        score = data.get("score") or {}
        number_of_reviews = data.get("numberOfReviews") or {}

        return ReputationResult(
            rating=score.get("trustScore"),
            review_count=number_of_reviews.get("total"),
            country=data.get("country"),
            website_url=data.get("websiteUrl"),
            raw=data,
        )

    async def _fetch_detail(self, business_unit_id: str, *, headers: dict[str, str]) -> dict | None:
        try:
            response = await self._http_client.get(
                DETAIL_URL_TEMPLATE.format(business_unit_id=business_unit_id),
                headers=headers,
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise ReputationLookupError(f"Erreur reseau Trustpilot: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ReputationLookupError(
                f"Erreur Trustpilot ({response.status_code}) pour l'id {business_unit_id!r}"
            )
        return response.json()
