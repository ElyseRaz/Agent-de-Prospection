import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_settings, get_user_by_email, require_role
from app.core.config import Settings
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    get_totp_provisioning_uri,
    hash_password,
    verify_password,
    verify_totp_code,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])
log = structlog.get_logger(__name__)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    existing = await get_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Un compte existe deja pour cet email"
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log.info("user_registered", user_id=str(user.id))
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    user = await get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect"
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte desactive")

    if user.totp_enabled:
        if not payload.totp_code or not verify_totp_code(
            secret=user.totp_secret, code=payload.totp_code
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Code 2FA manquant ou invalide"
            )

    access = create_access_token(user_id=str(user.id), settings=settings)
    refresh = create_refresh_token(user_id=str(user.id), settings=settings)
    log.info("user_logged_in", user_id=str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=AccessToken)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AccessToken:
    try:
        claims = decode_token(
            payload.refresh_token, expected_type=TokenType.REFRESH, settings=settings
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide ou expire"
        ) from exc

    user = await db.get(User, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable ou inactif"
        )

    return AccessToken(access_token=create_access_token(user_id=str(user.id), settings=settings))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> TOTPSetupResponse:
    secret = generate_totp_secret()
    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.add(current_user)
    await db.commit()

    uri = get_totp_provisioning_uri(secret=secret, email=current_user.email)
    return TOTPSetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/2fa/verify", response_model=UserRead)
async def totp_verify(
    payload: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun secret 2FA en attente"
        )

    if not verify_totp_code(secret=current_user.totp_secret, code=payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code 2FA invalide")

    current_user.totp_enabled = True
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    log.info("totp_enabled", user_id=str(current_user.id))
    return current_user


@router.get("/admin/ping")
async def admin_ping(_: User = Depends(require_role(UserRole.ADMIN))) -> dict:
    return {"status": "ok", "scope": "admin"}
