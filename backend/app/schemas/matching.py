
from pydantic import BaseModel

from app.models.matching import MatchFeedbackAction
from app.schemas.job import JobRead


class ScoreBreakdownItemRead(BaseModel):
    criterion: str
    points: int
    label: str


class MatchRead(BaseModel):
    job: JobRead
    score: int
    breakdown: list[ScoreBreakdownItemRead]


class MatchListResponse(BaseModel):
    results: list[MatchRead]


class MatchFeedbackCreate(BaseModel):
    action: MatchFeedbackAction
