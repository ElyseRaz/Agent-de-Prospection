from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration centrale, entierement lue depuis les variables d'environnement."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "RemoteRadar"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173"

    # Securite / JWT
    secret_key: str = Field(..., description="Cle de signature JWT, obligatoire")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14

    # Base de donnees
    database_url: str = Field(
        ..., description="URL asyncpg, ex: postgresql+asyncpg://user:pass@db:5432/remoteradar"
    )
    database_url_sync: str | None = Field(
        default=None,
        description="URL psycopg2 utilisee par Alembic. Derivee de database_url si absente.",
    )

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # LLM (extraction structuree, phase 3). La cle API est lue directement par
    # le SDK Anthropic depuis ANTHROPIC_API_KEY, jamais stockee ici.
    llm_model: str = "claude-sonnet-5"

    # Embeddings (phase 4). Modele local sentence-transformers, aucune cle API.
    embedding_model_name: str = "paraphrase-multilingual-mpnet-base-v2"

    @property
    def sync_database_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def resolved_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
