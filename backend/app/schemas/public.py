from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PublicDimensionScoreRead(BaseModel):
    dimension_code: str
    display_score: float
    raw_score: float
    weighted_contribution: float
    weighted_score: float
    rationale: str


class PublicSalaryRecommendationRead(BaseModel):
    recommendation_id: str
    status: str
    current_salary: str
    recommended_salary: str
    final_adjustment_ratio: float


class PublicLatestEvaluationResponse(BaseModel):
    employee_id: str
    employee_no: str
    employee_name: str
    department: str
    job_family: str
    job_level: str
    cycle_id: str
    cycle_name: str
    cycle_status: str
    submission_id: str
    evaluation_id: str
    evaluation_status: str
    ai_level: str
    overall_score: float
    confidence_score: float
    explanation: str
    evaluated_at: datetime
    dimension_scores: list[PublicDimensionScoreRead]
    salary_recommendation: PublicSalaryRecommendationRead | None = None


class PublicSalaryResultItem(BaseModel):
    employee_id: str
    employee_no: str
    employee_name: str
    department: str
    job_family: str
    job_level: str
    evaluation_id: str
    ai_level: str
    evaluation_status: str
    recommendation_id: str | None = None
    recommendation_status: str | None = None
    current_salary: str | None = None
    recommended_salary: str | None = None
    final_adjustment_ratio: float | None = None


class PublicSalaryResultsResponse(BaseModel):
    cycle_id: str
    cycle_name: str
    cycle_status: str
    items: list[PublicSalaryResultItem]
    total: int


class PublicApprovalStatusItem(BaseModel):
    recommendation_id: str
    employee_no: str
    employee_name: str
    recommendation_status: str
    total_steps: int
    approved_steps: int
    pending_steps: int
    rejected_steps: int
    latest_decision_at: datetime | None = None


class PublicApprovalStatusResponse(BaseModel):
    cycle_id: str
    cycle_name: str
    cycle_status: str
    items: list[PublicApprovalStatusItem]
    total: int


class PublicDashboardSummaryResponse(BaseModel):
    generated_at: datetime
    overview: list[dict[str, str]]
    ai_level_distribution: list[dict[str, int | str]]
    roi_distribution: list[dict[str, int | str]]
    heatmap: list[dict[str, int | str]]
