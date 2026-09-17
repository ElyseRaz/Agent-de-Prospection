import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.blacklist import BlacklistEntityType


class BlacklistCreate(BaseModel):
    entity_type: BlacklistEntityType
    value: str
    reason: str | None = None
    shared: bool = False


class BlacklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    entity_type: BlacklistEntityType
    value: str
    reason: str | None
    created_at: datetime
