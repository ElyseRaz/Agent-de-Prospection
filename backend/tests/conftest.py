import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://remoteradar:remoteradar@localhost:5432/remoteradar_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("APP_ENV", "test")

import pytest_asyncio  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db import Base, create_engine_and_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def engine_and_session():
    """Cree le schema une fois pour la session de test via create_all.

    Choix delibere : Alembic gere les migrations en production/dev, mais un
    create_all sur une base ephemere de test est plus rapide et suffisant ici.
    """
    settings = get_settings()
    engine, session_factory = create_engine_and_session(settings)

    async with engine.begin() as conn:
        # `create_all` ne cree que les tables : les extensions Postgres sont
        # normalement posees par la migration 0001, contournee ici (voir
        # docstring). Necessaires des cette fixture : `vector` (colonne
        # jobs.embedding), `pg_trgm` (similarite trigramme), `unaccent`
        # (recherche plein texte).
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine, session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(engine_and_session):
    yield
    _, session_factory = engine_and_session
    async with session_factory() as session:
        await session.execute(
            sa.text(
                "TRUNCATE TABLE match_feedback, matches, profile_skills, profiles, "
                "job_duplicate_links, job_skills, jobs, "
                "company_reputation, companies, skills, blacklist, "
                "llm_extraction_cache, llm_calls, "
                "raw_documents, scrape_runs, sources, users CASCADE"
            )
        )
        await session.commit()


@pytest_asyncio.fixture
async def app(engine_and_session):
    engine, session_factory = engine_and_session
    fastapi_app = create_app()
    fastapi_app.state.settings = get_settings()
    fastapi_app.state.engine = engine
    fastapi_app.state.session_factory = session_factory
    return fastapi_app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session(engine_and_session) -> AsyncSession:
    _, session_factory = engine_and_session
    async with session_factory() as session:
        yield session


async def promote_to_admin(db_session: AsyncSession, email: str) -> None:
    result = await db_session.execute(sa.select(User).where(User.email == email))
    user = result.scalar_one()
    user.role = UserRole.ADMIN
    db_session.add(user)
    await db_session.commit()


class FakeJobExtractionBackend:
    """Double de test pour JobExtractionBackend : ne fait aucun appel reseau.

    `responses` est consomme dans l'ordre a chaque appel de `extract()` ; une
    entree `Exception` est levee (utile pour tester le retry)."""

    def __init__(self, responses: list) -> None:
        from app.normalization.llm_extraction import LLMUsage

        self._responses = list(responses)
        self._llm_usage_cls = LLMUsage
        self.calls = 0

    async def extract(self, *, system_prompt: str, user_text: str):
        self.calls += 1
        if not self._responses:
            raise AssertionError("FakeJobExtractionBackend: plus de reponses disponibles")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item, self._llm_usage_cls(input_tokens=120, output_tokens=60, cost_usd=0.0006)


def make_extracted_job(**overrides):
    from app.normalization.schema import ExtractedJobLLM, ExtractedRate

    defaults = dict(
        title="Ingenieur Backend Python",
        company_name="Acme Corp",
        contract_type="freelance",
        rate=ExtractedRate(min=500, max=600, currency="USD", period="day"),
        duration_months=6,
        start_date="2026-10-01",
        workload_days_per_week=5,
        tech_stack=["Python", "FastAPI", "PostgreSQL"],
        seniority="senior",
        required_languages=["English"],
        remote_type="full_remote",
        timezone_constraint=None,
        billing_mode="TJM",
        application_channel="lien Remotive",
    )
    defaults.update(overrides)
    return ExtractedJobLLM(**defaults)


EMBEDDING_TEST_DIMENSION = 768


def cosine_test_vector(positive_dims: int, dim: int = EMBEDDING_TEST_DIMENSION) -> list[float]:
    """Vecteur de test a similarite cosinus controlee : deux vecteurs generes
    avec `positive_dims=dim` sont identiques (similarite 1.0) ; `positive_dims
    = dim // 2` produit un vecteur orthogonal a celui-la (similarite ~0.0)."""

    return [1.0] * positive_dims + [-1.0] * (dim - positive_dims)


class FakeEmbeddingBackend:
    """Double de test pour EmbeddingBackend : aucun modele charge, aucun appel
    reseau. `vectors` associe un texte exact a un vecteur precis (utile pour
    forcer une similarite donnee entre deux jobs) ; tout texte non liste
    recoit un vecteur de repli deterministe (derive du texte)."""

    def __init__(self, vectors: dict[str, list[float]] | None = None) -> None:
        self._vectors = vectors or {}
        self.calls = 0

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector_for(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        return self._vector_for(text)

    def _vector_for(self, text: str) -> list[float]:
        if text in self._vectors:
            return self._vectors[text]
        seed = (sum(ord(c) for c in text) % (EMBEDDING_TEST_DIMENSION // 2)) or 1
        return cosine_test_vector(seed)


class FakeRiskAssessmentBackend:
    """Double de test pour RiskAssessmentBackend : ne fait aucun appel reseau.

    `responses` est consomme dans l'ordre a chaque appel de `assess()` ; une
    entree `Exception` est levee (utile pour tester le retry)."""

    def __init__(self, responses: list) -> None:
        from app.normalization.llm_extraction import LLMUsage

        self._responses = list(responses)
        self._llm_usage_cls = LLMUsage
        self.calls = 0

    async def assess(self, *, system_prompt: str, user_text: str):
        self.calls += 1
        if not self._responses:
            raise AssertionError("FakeRiskAssessmentBackend: plus de reponses disponibles")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item, self._llm_usage_cls(input_tokens=80, output_tokens=40, cost_usd=0.0004)


def make_risk_assessment(**overrides):
    from app.normalization.risk_schema import RiskAssessment

    defaults = dict(risk_score=10, reasons=[])
    defaults.update(overrides)
    return RiskAssessment(**defaults)


class FakeReputationProvider:
    """Double de test pour ReputationProvider : aucun appel reseau.

    `results` associe un domaine exact a un ReputationResult (ou None pour
    'recherche et non trouve', ou une Exception pour simuler une panne)."""

    def __init__(self, results: dict[str, object] | None = None) -> None:
        self._results = results or {}
        self.calls: list[str] = []

    async def fetch_by_domain(self, domain: str):
        self.calls.append(domain)
        if domain not in self._results:
            return None
        item = self._results[domain]
        if isinstance(item, Exception):
            raise item
        return item
