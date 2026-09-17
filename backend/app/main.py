from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis_asyncio
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.admin import router as admin_router
from app.api.routes.applications import router as applications_router
from app.api.routes.auth import router as auth_router
from app.api.routes.blacklist import router as blacklist_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.normalization import router as normalization_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.saved_searches import router as saved_searches_router
from app.api.routes.sources import router as sources_router
from app.collectors.registry import discover_connectors
from app.core.config import get_settings
from app.core.db import create_engine_and_session
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.embeddings.sentence_transformer_backend import SentenceTransformerEmbeddingBackend
from app.normalization.llm_extraction import build_job_extraction_backend
from app.normalization.raw_text.registry import discover_raw_text_extractors
from app.normalization.risk_extraction import build_risk_assessment_backend
from app.notifications.factory import build_notification_channels
from app.reputation.trustpilot import TrustpilotReputationProvider

log = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env)
    discover_connectors()
    discover_raw_text_extractors()

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn, environment=settings.app_env, traces_sample_rate=0.1
        )

    engine, session_factory = create_engine_and_session(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.http_client = httpx.AsyncClient(timeout=20.0)
        app.state.redis = redis_asyncio.from_url(settings.redis_url, decode_responses=True)
        app.state.llm_backend = build_job_extraction_backend(
            settings, http_client=app.state.http_client
        )
        app.state.embedding_backend = SentenceTransformerEmbeddingBackend(
            model_name=settings.embedding_model_name
        )
        app.state.risk_backend = build_risk_assessment_backend(
            settings, http_client=app.state.http_client
        )
        app.state.reputation_provider = (
            TrustpilotReputationProvider(
                api_key=settings.trustpilot_api_key, http_client=app.state.http_client
            )
            if settings.trustpilot_api_key
            else None
        )
        app.state.notification_channels = build_notification_channels(
            settings, http_client=app.state.http_client
        )

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("startup_db_check_ok", app_env=settings.app_env)

        yield

        await app.state.http_client.aclose()
        await app.state.redis.aclose()
        await engine.dispose()
        log.info("shutdown_complete")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Agent IA d'agregation, normalisation, enrichissement et scoring "
        "d'offres freelance remote.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(sources_router, prefix=settings.api_v1_prefix)
    app.include_router(normalization_router, prefix=settings.api_v1_prefix)
    app.include_router(jobs_router, prefix=settings.api_v1_prefix)
    app.include_router(blacklist_router, prefix=settings.api_v1_prefix)
    app.include_router(profiles_router, prefix=settings.api_v1_prefix)
    app.include_router(applications_router, prefix=settings.api_v1_prefix)
    app.include_router(saved_searches_router, prefix=settings.api_v1_prefix)
    app.include_router(notifications_router, prefix=settings.api_v1_prefix)
    app.include_router(admin_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
