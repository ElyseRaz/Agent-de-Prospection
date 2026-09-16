import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings

_hasher = PasswordHasher()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Leve quand un JWT est invalide, expire, ou du mauvais type."""


def hash_password(raw_password: str) -> str:
    return _hasher.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, raw_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _create_token(
    *, subject: str, token_type: TokenType, expires_delta: timedelta, settings: Settings
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: str, settings: Settings) -> str:
    return _create_token(
        subject=user_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        settings=settings,
    )


def create_refresh_token(*, user_id: str, settings: Settings) -> str:
    return _create_token(
        subject=user_id,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        settings=settings,
    )


def decode_token(token: str, *, expected_type: TokenType, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Type de token invalide, attendu {expected_type.value}")

    return payload


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_provisioning_uri(*, secret: str, email: str, issuer: str = "RemoteRadar") -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def verify_totp_code(*, secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)
