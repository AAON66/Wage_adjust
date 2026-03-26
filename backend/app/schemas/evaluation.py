from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DimensionScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dimension_code: str
    weight: float
    ai_raw_score: float
    ai_weighted_score: float
    raw_score: float
    weighted_score: float
    ai_rationale: str
    rationale: str
    created_at: datetime
    prompt_hash: str | None = None


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_id: str
    overall_score: float
    ai_overall_score: float
    manager_score: float | None = None
    score_gap: float | None = None
    ai_level: str
    confidence_score: float
    explanation: str
    manager_comment: str | None = None
    hr_comment: str | None = None
    hr_decision: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    needs_manual_review: bool = False
    integrity_flagged: bool = False
    integrity_issue_count: int = 0
    integrity_examples: list[str] = Field(default_factory=list)
    dimension_scores: list[DimensionScoreRead] = Field(default_factory=list)
    used_fallback: bool = False


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


class EvaluationHrReviewRequest(BaseModel):
    decision: Literal['approved', 'returned']
    comment: str | None = None
    final_score: float | None = Field(default=None, ge=0, le=100)


class EvaluationConfirmResponse(BaseModel):
    id: str
    status: str
