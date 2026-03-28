from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.evaluation import DimensionScoreRead


class ProjectContributorSummary(BaseModel):
    employee_id: str
    employee_name: str
    contribution_pct: float
    file_name: str
    is_owner: bool = False


class ApprovalStepCreate(BaseModel):
    step_name: str = Field(min_length=1, max_length=64)
    approver_id: str
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalSubmitRequest(BaseModel):
    recommendation_id: str
    steps: list[ApprovalStepCreate] = Field(min_length=1)


class ApprovalRouteUpdateRequest(BaseModel):
    steps: list[ApprovalStepCreate] = Field(min_length=1)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=32)
    comment: str | None = Field(default=None, max_length=2000)
    defer_until: datetime | None = None
    defer_target_score: float | None = Field(default=None, ge=0, le=100)


class ApprovalRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recommendation_id: str
    evaluation_id: str
    employee_id: str
    employee_name: str
    department: str
    cycle_id: str
    cycle_name: str
    ai_level: str
    current_salary: Decimal
    recommended_salary: Decimal
    final_adjustment_ratio: float
    recommendation_status: str
    approver_id: str
    approver_email: str
    approver_role: str
    step_name: str
    step_order: int
    is_current_step: bool = False
    decision: str
    comment: str | None = None
    decided_at: datetime | None = None
    created_at: datetime
    defer_until: datetime | None = None
    defer_target_score: float | None = None
    defer_reason: str | None = None
    dimension_scores: list[DimensionScoreRead] = []
    project_contributors: list[ProjectContributorSummary] = []


class ApprovalListResponse(BaseModel):
    items: list[ApprovalRecordRead]
    total: int


class ApprovalCandidateRead(BaseModel):
    recommendation_id: str
    evaluation_id: str
    employee_id: str
    employee_name: str
    department: str
    cycle_id: str
    cycle_name: str
    ai_level: str
    current_salary: Decimal
    recommended_salary: Decimal
    final_adjustment_ratio: float
    recommendation_status: str
    route_preview: list[str] = []
    route_error: str | None = None
    can_edit_route: bool = False
    route_edit_error: str | None = None
    defer_until: datetime | None = None
    defer_target_score: float | None = None
    defer_reason: str | None = None


class ApprovalCandidateListResponse(BaseModel):
    items: list[ApprovalCandidateRead]
    total: int


class ApprovalStatusResponse(BaseModel):
    approval_id: str
    recommendation_id: str
    decision: str
    recommendation_status: str
    defer_until: datetime | None = None
    defer_target_score: float | None = None
    defer_reason: str | None = None


class CalibrationQueueItem(BaseModel):
    evaluation_id: str
    submission_id: str
    employee_id: str
    employee_name: str
    department: str
    cycle_id: str
    cycle_name: str
    ai_level: str
    overall_score: float
    confidence_score: float
    status: str
    needs_manual_review: bool
    updated_at: datetime


class CalibrationQueueResponse(BaseModel):
    items: list[CalibrationQueueItem]
    total: int

