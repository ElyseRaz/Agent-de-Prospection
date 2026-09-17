import uuid
from collections.abc import AsyncIterator

import httpx
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.collectors.http import CircuitBreaker
from app.core.config import Settings
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.embeddings.base import EmbeddingBackend
from app.models.user import User, UserRole
from app.normalization.llm_extraction import JobExtractionBackend
from app.normalization.risk_extraction import RiskAssessmentBackend
from app.notifications.base import NotificationChannel
from app.reputation.base import ReputationProvider

_bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_session_factory(request: Request) -> async_sessionmaker:
    return request.app.state.session_factory


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_circuit_breaker(request: Request) -> CircuitBreaker:
    return CircuitBreaker(request.app.state.redis)


def get_llm_backend(request: Request) -> JobExtractionBackend:
    return request.app.state.llm_backend


def get_embedding_backend(request: Request) -> EmbeddingBackend:
    return request.app.state.embedding_backend


def get_risk_backend(request: Request) -> RiskAssessmentBackend:
    return request.app.state.risk_backend


def get_reputation_provider(request: Request) -> ReputationProvider | None:
    return request.app.state.reputation_provider


def get_notification_channels(request: Request) -> dict[str, NotificationChannel]:
    return request.app.state.notification_channels


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


async def get_current_user_sse(
    request: Request,
    access_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """Variante de `get_current_user` acceptant le token en parametre de
    requete (`?access_token=...`) en plus de l'en-tete `Authorization` :
    l'API `EventSource` du navigateur ne permet pas d'envoyer d'en-tetes
    personnalises, ce qui rend le header Bearer inutilisable pour le flux
    SSE de notifications (`GET /notifications/stream`)."""

    token = access_token
    if token is None:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS, settings=settings)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide ou expire"
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
