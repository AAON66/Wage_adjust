from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar('T')


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
    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'employee_id': 'e1a2b3c4',
            'employee_no': 'EMP001',
            'employee_name': 'Zhang San',
            'department': 'Engineering',
            'job_family': 'Software',
            'job_level': 'P6',
            'evaluation_id': 'eval-abc123',
            'ai_level': 'Level 3',
            'evaluation_status': 'confirmed',
            'recommendation_id': 'rec-xyz789',
            'recommendation_status': 'approved',
            'current_salary': '25000.00',
            'recommended_salary': '28750.00',
            'final_adjustment_ratio': 0.15,
        }],
    })

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


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """游标分页通用 wrapper（per D-05, D-06）"""
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class PaginatedSalaryResultsResponse(BaseModel):
    """游标分页版调薪结果（替代原 PublicSalaryResultsResponse 用于分页端点）"""
    model_config = ConfigDict(json_schema_extra={
        'examples': [{
            'cycle_id': 'cycle-2026Q1',
            'cycle_name': '2026 Q1 Evaluation',
            'cycle_status': 'completed',
            'items': [],
            'next_cursor': 'eyJpZCI6Imxhc3QtaWQiLCJzb3J0IjpudWxsfQ==',
            'has_more': True,
            'total': 5,
        }],
    })

    cycle_id: str
    cycle_name: str
    cycle_status: str
    items: list[PublicSalaryResultItem]
    next_cursor: str | None = Field(None, description='Opaque cursor for next page')
    has_more: bool = Field(False, description='Whether more pages exist')
    total: int | None = Field(None, description='Item count in this page (backward compat)')
