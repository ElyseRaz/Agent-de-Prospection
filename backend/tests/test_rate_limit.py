import pytest

from app.api.deps import get_rate_limit_store
from app.collectors.http import InMemoryCounterStore

pytestmark = pytest.mark.asyncio


async def test_login_is_rate_limited_after_threshold(client, app):
    # `get_rate_limit_store` est par defaut remplace par un store frais a
    # chaque appel (voir conftest.py:app) pour ne pas perturber les autres
    # tests : ici on le fixe volontairement a une instance unique et
    # partagee pour observer l'effet cumulatif du limiteur (10 req / 5 min
    # sur /auth/login, voir app/api/routes/auth.py).
    shared_store = InMemoryCounterStore()
    app.dependency_overrides[get_rate_limit_store] = lambda: shared_store
    try:
        for _ in range(10):
            response = await client.post(
                "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
            )
            assert response.status_code == 401

        limited_response = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert limited_response.status_code == 429
    finally:
        app.dependency_overrides.clear()


async def test_register_is_rate_limited_after_threshold(client, app):
    shared_store = InMemoryCounterStore()
    app.dependency_overrides[get_rate_limit_store] = lambda: shared_store
    try:
        for i in range(5):
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": f"bulk-{i}@example.com", "password": "S3curePassw0rd!"},
            )
            assert response.status_code == 201

        limited_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "bulk-overflow@example.com", "password": "S3curePassw0rd!"},
        )
        assert limited_response.status_code == 429
    finally:
        app.dependency_overrides.clear()
