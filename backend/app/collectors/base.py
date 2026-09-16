import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar

import httpx

from app.collectors.http import CircuitBreaker


class AccessType(StrEnum):
    API = "api"
    RSS = "rss"
    HTML_PUBLIC = "html_public"


@dataclass(frozen=True, slots=True)
class ConnectorMetadata:
    """Declaration statique portee par chaque connecteur, independamment de sa
    configuration en base (table `sources`)."""

    access_type: AccessType
    default_rate_limit_rpm: int
    default_schedule_cron: str
    compliance_note: str


@dataclass(frozen=True, slots=True)
class RawDocumentPayload:
    """Document brut produit par un connecteur, avant tout enregistrement en
    base. Le hash de contenu et la persistance sont geres par le noyau
    (app.services.collection), jamais par le connecteur lui-meme."""

    external_id: str
    url: str
    raw_payload: dict[str, Any]
    fetched_at: datetime


class SourceConnector(abc.ABC):
    """Interface commune a tous les connecteurs de collecte.

    Un connecteur ne connait que sa source (config JSON de `sources.config`)
    et un client HTTP + circuit breaker partages fournis par l'appelant. Il ne
    doit jamais ecrire en base ni gerer sa propre planification.
    """

    metadata: ClassVar[ConnectorMetadata]

    def __init__(
        self,
        *,
        base_url: str,
        config: dict[str, Any],
        http_client: httpx.AsyncClient,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        self.base_url = base_url
        self.config = config
        self.http_client = http_client
        self.circuit_breaker = circuit_breaker

    @abc.abstractmethod
    def fetch(self, *, since: datetime | None = None) -> AsyncIterator[RawDocumentPayload]:
        """Retourne les documents bruts disponibles depuis `since` (collecte
        incrementale). Implemente comme generateur asynchrone par les
        sous-classes (`async def fetch(...): yield ...`)."""
        raise NotImplementedError
