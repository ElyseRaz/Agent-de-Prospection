from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.collectors.base import AccessType, ConnectorMetadata, RawDocumentPayload, SourceConnector
from app.collectors.http import fetch_with_retry
from app.collectors.registry import register_connector


@register_connector("remotive")
class RemotiveConnector(SourceConnector):
    """Connecteur pour l'API JSON publique de Remotive.

    Acces : API dediee et documentee (https://remotive.com/api/remote-jobs),
    sans authentification, prevue pour un usage programmatique. Aucun
    scraping HTML, aucun contournement de protection anti-bot ; robots.txt
    n'est pas applicable a un endpoint d'API dedie a la consommation
    programmatique (il ne s'agit pas de crawler des pages web).
    """

    metadata = ConnectorMetadata(
        access_type=AccessType.API,
        default_rate_limit_rpm=20,
        default_schedule_cron="*/30 * * * *",
        compliance_note=(
            "API publique documentee par Remotive (https://remotive.com/api/remote-jobs), "
            "sans authentification, destinee a un usage programmatique. Aucun scraping HTML, "
            "aucun contournement de protection anti-bot."
        ),
    )

    async def fetch(self, *, since: datetime | None = None) -> AsyncIterator[RawDocumentPayload]:
        params: dict[str, str] = {}
        category = self.config.get("category")
        if category:
            params["category"] = category
        search = self.config.get("search")
        if search:
            params["search"] = search

        response = await fetch_with_retry(
            self.http_client,
            self.base_url,
            circuit_breaker=self.circuit_breaker,
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

        fetched_at = datetime.now(UTC)
        for job in payload.get("jobs", []):
            if since is not None:
                published = _parse_publication_date(job.get("publication_date"))
                if published is not None and published < since:
                    continue

            yield RawDocumentPayload(
                external_id=str(job["id"]),
                url=job["url"],
                raw_payload=job,
                fetched_at=fetched_at,
            )


def _parse_publication_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
