from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings


class Base(DeclarativeBase):
    """Classe declarative de base partagee par tous les modeles ORM."""


def create_engine_and_session(settings: Settings):
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    return engine, session_factory


async def session_scope(session_factory: async_sessionmaker) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
