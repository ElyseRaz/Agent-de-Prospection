import httpx
import pytest

import app.collectors.robots as robots_module
from app.collectors.robots import is_allowed

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_robots_cache():
    robots_module._cache.clear()
    yield
    robots_module._cache.clear()


async def test_disallowed_path_is_blocked():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, text="ok")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    allowed_public = await is_allowed(client, "https://example.com/public/page")
    allowed_private = await is_allowed(client, "https://example.com/private/page")

    assert allowed_public is True
    assert allowed_private is False
    await client.aclose()


async def test_missing_robots_txt_defaults_to_allowed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    allowed = await is_allowed(client, "https://example.org/anything")

    assert allowed is True
    await client.aclose()


async def test_unreachable_robots_txt_defaults_to_allowed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    allowed = await is_allowed(client, "https://example.net/anything")

    assert allowed is True
    await client.aclose()
