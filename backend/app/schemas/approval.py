from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

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
    comment: Optional[str] = Field(default=None, max_length=2000)


class ApprovalSubmitRequest(BaseModel):
    recommendation_id: str
    steps: List[ApprovalStepCreate] = Field(min_length=1)


class ApprovalRouteUpdateRequest(BaseModel):
    steps: List[ApprovalStepCreate] = Field(min_length=1)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=32)
    comment: Optional[str] = Field(default=None, max_length=2000)
    defer_until: Optional[datetime] = None
    defer_target_score: Optional[float] = Field(default=None, ge=0, le=100)


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
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    defer_until: Optional[datetime] = None
    defer_target_score: Optional[float] = None
    defer_reason: Optional[str] = None
    dimension_scores: List[DimensionScoreRead] = []
    project_contributors: List[ProjectContributorSummary] = []


class ApprovalListResponse(BaseModel):
    items: List[ApprovalRecordRead]
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
    route_preview: List[str] = []
    route_error: Optional[str] = None
    can_edit_route: bool = False
    route_edit_error: Optional[str] = None
    defer_until: Optional[datetime] = None
    defer_target_score: Optional[float] = None
    defer_reason: Optional[str] = None


class ApprovalCandidateListResponse(BaseModel):
    items: List[ApprovalCandidateRead]
    total: int


class ApprovalStatusResponse(BaseModel):
    approval_id: str
    recommendation_id: str
    decision: str
    recommendation_status: str
    defer_until: Optional[datetime] = None
    defer_target_score: Optional[float] = None
    defer_reason: Optional[str] = None


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
    items: List[CalibrationQueueItem]
    total: int

