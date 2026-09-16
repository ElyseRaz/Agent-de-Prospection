import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    totp_enabled: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
