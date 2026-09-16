import asyncio
import random
from typing import Protocol
from urllib.parse import urlparse

import httpx
import structlog

log = structlog.get_logger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class CounterStore(Protocol):
    """Backend de stockage des compteurs d'echecs du circuit breaker.

    `redis.asyncio.Redis` implemente deja cette interface (incr/expire/get/delete
    sont des coroutines compatibles), ce qui permet de brancher directement un
    client Redis partage entre processus en production, tout en gardant les
    tests unitaires independants de tout service externe via InMemoryCounterStore.
    """

    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> object: ...
    async def get(self, key: str) -> object: ...
    async def delete(self, key: str) -> object: ...


class InMemoryCounterStore:
    """CounterStore en memoire de processus, sans dependance externe.

    Utilise en test et comme repli si aucun client Redis n'est fourni.
    """

    def __init__(self) -> None:
        self._values: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._values[key] = self._values.get(key, 0) + 1
        return self._values[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        value = self._values.get(key)
        return None if value is None else str(value)

    async def delete(self, key: str) -> int:
        return 1 if self._values.pop(key, None) is not None else 0


class CircuitBreakerOpenError(Exception):
    """Leve quand trop d'echecs consecutifs ont ete detectes pour un domaine."""


class CircuitBreaker:
    """Circuit breaker par domaine : ouvre apres `failure_threshold` echecs
    consecutifs et reste ouvert pendant `cooldown_seconds` (via l'expiration
    de la cle dans le CounterStore)."""

    def __init__(
        self,
        store: CounterStore,
        *,
        failure_threshold: int = 5,
        cooldown_seconds: int = 300,
    ) -> None:
        self._store = store
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc

    def _key(self, url: str) -> str:
        return f"circuit_breaker:failures:{self._domain(url)}"

    async def ensure_closed(self, url: str) -> None:
        raw = await self._store.get(self._key(url))
        failures = int(raw) if raw is not None else 0
        if failures >= self._failure_threshold:
            raise CircuitBreakerOpenError(
                f"Circuit ouvert pour {self._domain(url)} ({failures} echecs consecutifs)"
            )

    async def record_success(self, url: str) -> None:
        await self._store.delete(self._key(url))

    async def record_failure(self, url: str) -> None:
        key = self._key(url)
        failures = await self._store.incr(key)
        await self._store.expire(key, self._cooldown_seconds)
        if failures >= self._failure_threshold:
            log.warning("circuit_breaker_opened", domain=self._domain(url), failures=failures)


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    circuit_breaker: CircuitBreaker,
    max_attempts: int = 4,
    base_delay_seconds: float = 1.0,
    **kwargs: object,
) -> httpx.Response:
    """GET avec backoff exponentiel, respect du header Retry-After, et
    circuit breaker par domaine. Leve CircuitBreakerOpenError si le circuit
    est deja ouvert pour ce domaine (aucune requete n'est alors emise)."""

    await circuit_breaker.ensure_closed(url)

    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.get(url, **kwargs)
        except httpx.TransportError as exc:
            last_exception = exc
            await circuit_breaker.record_failure(url)
            if attempt == max_attempts:
                raise
            await asyncio.sleep(_backoff_delay(attempt, base_delay_seconds))
            continue

        if response.status_code not in RETRYABLE_STATUS_CODES:
            if response.is_success:
                await circuit_breaker.record_success(url)
            else:
                await circuit_breaker.record_failure(url)
            return response

        await circuit_breaker.record_failure(url)
        if attempt == max_attempts:
            return response

        delay = _retry_after_seconds(response) or _backoff_delay(attempt, base_delay_seconds)
        log.warning(
            "http_retry", url=url, status_code=response.status_code, attempt=attempt, delay=delay
        )
        await asyncio.sleep(delay)

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("fetch_with_retry: sortie de boucle inattendue")  # pragma: no cover


def _backoff_delay(attempt: int, base_delay_seconds: float) -> float:
    return base_delay_seconds * (2 ** (attempt - 1)) + random.uniform(0, 0.5)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None
