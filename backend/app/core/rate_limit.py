from fastapi import Depends, HTTPException, Request, status

from app.collectors.http import CounterStore


class RateLimitExceededError(Exception):
    """Leve quand le nombre de requetes autorisees est depasse dans la fenetre."""


class RateLimiter:
    """Limiteur a fenetre fixe, par cle, reposant sur `CounterStore` (meme
    interface que le circuit breaker des collecteurs - phase 2) : Redis en
    production/dev, `InMemoryCounterStore` dans les tests, aucune dependance
    nouvelle."""

    def __init__(self, store: CounterStore, *, max_requests: int, window_seconds: int) -> None:
        self._store = store
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def check(self, key: str) -> None:
        full_key = f"rate_limit:{key}"
        count = await self._store.incr(full_key)
        if count == 1:
            await self._store.expire(full_key, self._window_seconds)
        if count > self._max_requests:
            raise RateLimitExceededError(
                f"Limite de {self._max_requests} requetes / {self._window_seconds}s "
                f"depassee pour {key}"
            )


def get_rate_limit_store(request: Request) -> CounterStore:
    return request.app.state.redis


def rate_limit(key_prefix: str, *, max_requests: int, window_seconds: int):
    """Factory de dependance FastAPI : limite par IP cliente, cle
    `{key_prefix}:{ip}`. Utilisee sur les endpoints sensibles (login,
    inscription) pour freiner le bruteforce sans bloquer les tests (le
    `CounterStore` reste injectable via `app.dependency_overrides`)."""

    async def _dependency(
        request: Request, store: CounterStore = Depends(get_rate_limit_store)
    ) -> None:
        client_host = request.client.host if request.client else "unknown"
        limiter = RateLimiter(store, max_requests=max_requests, window_seconds=window_seconds)
        try:
            await limiter.check(f"{key_prefix}:{client_host}")
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives, reessayez plus tard",
            ) from exc

    return _dependency
