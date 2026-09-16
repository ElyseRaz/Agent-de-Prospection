import httpx
import pytest

from app.collectors.http import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    InMemoryCounterStore,
    fetch_with_retry,
)

pytestmark = pytest.mark.asyncio


async def test_retries_on_429_then_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    breaker = CircuitBreaker(InMemoryCounterStore(), failure_threshold=10)

    response = await fetch_with_retry(
        client, "https://example.com/api", circuit_breaker=breaker, base_delay_seconds=0.01
    )

    assert response.status_code == 200
    assert calls["count"] == 3
    await client.aclose()


async def test_gives_up_after_max_attempts_and_returns_last_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    breaker = CircuitBreaker(InMemoryCounterStore(), failure_threshold=10)

    response = await fetch_with_retry(
        client,
        "https://example.com/api",
        circuit_breaker=breaker,
        max_attempts=2,
        base_delay_seconds=0.01,
    )

    assert response.status_code == 503
    await client.aclose()


async def test_circuit_opens_after_threshold_and_blocks_further_requests():
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    breaker = CircuitBreaker(InMemoryCounterStore(), failure_threshold=2, cooldown_seconds=60)

    await fetch_with_retry(
        client,
        "https://example.com/api",
        circuit_breaker=breaker,
        max_attempts=2,
        base_delay_seconds=0.01,
    )
    assert call_count["n"] == 2

    with pytest.raises(CircuitBreakerOpenError):
        await fetch_with_retry(
            client, "https://example.com/api", circuit_breaker=breaker, max_attempts=1
        )

    # Le circuit ouvert empeche toute nouvelle requete HTTP.
    assert call_count["n"] == 2
    await client.aclose()


async def test_success_resets_failure_counter():
    responses = iter([httpx.Response(500), httpx.Response(200, json={"ok": True})])

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    breaker = CircuitBreaker(InMemoryCounterStore(), failure_threshold=1, cooldown_seconds=60)

    # max_attempts=2 : le premier essai (500) echoue, le second (200) reussit
    # et doit reinitialiser le compteur d'echecs malgre l'echec intermediaire.
    response = await fetch_with_retry(
        client,
        "https://example.com/api",
        circuit_breaker=breaker,
        max_attempts=2,
        base_delay_seconds=0.01,
    )

    assert response.status_code == 200
    await breaker.ensure_closed("https://example.com/api")  # ne leve pas
    await client.aclose()
