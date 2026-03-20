from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DimensionScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dimension_code: str
    weight: float
    raw_score: float
    weighted_score: float
    rationale: str
    created_at: datetime


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    overall_score: float
    ai_level: str
    confidence_score: float
    explanation: str
    status: str
    created_at: datetime
    updated_at: datetime
    needs_manual_review: bool = False
    dimension_scores: list[DimensionScoreRead] = Field(default_factory=list)


class EvaluationGenerateRequest(BaseModel):
    submission_id: str


class EvaluationManualReviewRequest(BaseModel):
    ai_level: str | None = None
    overall_score: float | None = Field(default=None, ge=0, le=100)
    explanation: str | None = None
    dimension_scores: list['DimensionScoreManualUpdate'] = Field(default_factory=list)


class DimensionScoreManualUpdate(BaseModel):
    dimension_code: str
    raw_score: float = Field(ge=0, le=100)
    rationale: str = Field(min_length=1)


class EvaluationConfirmResponse(BaseModel):
    id: str
    status: str