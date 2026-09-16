import uuid

from pydantic import BaseModel


class NormalizationSummaryRead(BaseModel):
    processed: int
    failed: int
    skipped: int


class ReprocessResponse(BaseModel):
    job_id: uuid.UUID | None
    status: str
