import time
from decimal import Decimal

import httpx
import structlog

log = structlog.get_logger(__name__)

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"
PIVOT_CURRENCY = "EUR"
_CACHE_TTL_SECONDS = 24 * 3600

# Repli statique (taux approximatifs) si l'API est injoignable : une panne
# reseau ne doit jamais bloquer toute la normalisation des TJM.
FALLBACK_RATES_TO_EUR: dict[str, Decimal] = {
    "EUR": Decimal("1"),
    "USD": Decimal("0.92"),
    "GBP": Decimal("1.17"),
    "CHF": Decimal("1.04"),
    "CAD": Decimal("0.68"),
}

_cache: dict[str, tuple[float, dict[str, Decimal]]] = {}


async def get_rate_to_eur(currency: str, *, http_client: httpx.AsyncClient) -> Decimal | None:
    """Taux de conversion de `currency` vers EUR (taux du jour, cache 24h)."""

    currency = currency.upper()
    if currency == PIVOT_CURRENCY:
        return Decimal("1")

    rates = await _get_rates(http_client)
    if currency in rates:
        return rates[currency]
    return FALLBACK_RATES_TO_EUR.get(currency)


async def _get_rates(http_client: httpx.AsyncClient) -> dict[str, Decimal]:
    cached = _cache.get("rates")
    now = time.monotonic()
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        response = await http_client.get(
            FRANKFURTER_URL, params={"base": PIVOT_CURRENCY}, timeout=10.0
        )
        response.raise_for_status()
        payload = response.json()
        rates_to_pivot = {
            code: Decimal("1") / Decimal(str(value))
            for code, value in payload.get("rates", {}).items()
            if value
        }
        rates_to_pivot[PIVOT_CURRENCY] = Decimal("1")
        _cache["rates"] = (now, rates_to_pivot)
        return rates_to_pivot
    except (httpx.HTTPError, ValueError, KeyError, ArithmeticError) as exc:
        log.warning("frankfurter_unreachable_using_fallback", error=str(exc))
        return FALLBACK_RATES_TO_EUR
