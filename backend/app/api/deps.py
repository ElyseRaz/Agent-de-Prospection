import uuid
from collections.abc import AsyncIterator

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.http import CircuitBreaker
from app.core.config import Settings
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.embeddings.base import EmbeddingBackend
from app.models.user import User, UserRole
from app.normalization.llm_extraction import JobExtractionBackend

_bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_circuit_breaker(request: Request) -> CircuitBreaker:
    return CircuitBreaker(request.app.state.redis)


def get_llm_backend(request: Request) -> JobExtractionBackend:
    return request.app.state.llm_backend


def get_embedding_backend(request: Request) -> EmbeddingBackend:
    return request.app.state.embedding_backend


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(
            credentials.credentials, expected_type=TokenType.ACCESS, settings=settings
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expire",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide"
        ) from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable ou inactif"
        )

    return user


def require_role(*allowed_roles: UserRole):
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Droits insuffisants pour cette action",
            )
        return current_user

    return _dependency


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
