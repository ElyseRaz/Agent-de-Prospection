import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog

log = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 3600
_cache: dict[str, tuple[float, RobotFileParser]] = {}


async def is_allowed(
    client: httpx.AsyncClient, url: str, *, user_agent: str = "RemoteRadarBot"
) -> bool:
    """Verifie robots.txt pour `url` avant toute collecte HTML/RSS.

    Repli permissif si robots.txt est inaccessible (404, timeout, erreur
    reseau) : on ne bloque pas une collecte legitime a cause d'une panne, mais
    le controle effectue est toujours trace (log structure)."""

    parsed = urlparse(url)
    domain_key = f"{parsed.scheme}://{parsed.netloc}"

    cached = _cache.get(domain_key)
    now = time.monotonic()
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        parser = cached[1]
    else:
        parser = RobotFileParser()
        robots_url = f"{domain_key}/robots.txt"
        try:
            response = await client.get(robots_url, timeout=5.0)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                parser.parse([])
        except httpx.HTTPError:
            log.warning("robots_txt_unreachable", domain=domain_key)
            parser.parse([])
        _cache[domain_key] = (now, parser)

    allowed = parser.can_fetch(user_agent, url)
    log.info("robots_txt_checked", url=url, allowed=allowed)
    return allowed
