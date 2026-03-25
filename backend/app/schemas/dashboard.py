from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class OverviewMetricRead(BaseModel):
    label: str
    value: str
    note: str


class CycleSummaryRead(BaseModel):
    cycle_id: str | None = None
    cycle_name: str
    review_period: str
    status: str
    budget_amount: Decimal


class DashboardOverviewResponse(BaseModel):
    items: list[OverviewMetricRead]


class DistributionItemRead(BaseModel):
    label: str
    value: int


class DistributionResponse(BaseModel):
    items: list[DistributionItemRead]
    total: int


class HeatmapCellRead(BaseModel):
    department: str
    level: str
    intensity: int


class HeatmapResponse(BaseModel):
    items: list[HeatmapCellRead]
    total: int


class DepartmentInsightRead(BaseModel):
    department: str
    employee_count: int
    avg_score: float
    high_potential_count: int
    pending_review_count: int
    approved_count: int
    budget_used: Decimal
    avg_increase_ratio: float


class TalentSpotlightRead(BaseModel):
    employee_id: str
    employee_name: str
    department: str
    ai_level: str
    overall_score: float
    recommendation_status: str | None = None
    final_adjustment_ratio: float | None = None


class ActionItemRead(BaseModel):
    title: str
    value: str
    note: str
    severity: str


class DashboardSnapshotResponse(BaseModel):
    cycle_summary: CycleSummaryRead | None = None
    overview: DashboardOverviewResponse
    ai_level_distribution: DistributionResponse
    roi_distribution: DistributionResponse
    heatmap: HeatmapResponse
    department_insights: list[DepartmentInsightRead]
    top_talents: list[TalentSpotlightRead]
    action_items: list[ActionItemRead]
