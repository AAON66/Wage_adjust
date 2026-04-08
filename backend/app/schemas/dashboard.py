from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class OverviewMetricRead(BaseModel):
    label: str
    value: str
    note: str


class CycleSummaryRead(BaseModel):
    cycle_id: Optional[str] = None
    cycle_name: str
    review_period: str
    status: str
    budget_amount: Decimal


class DashboardOverviewResponse(BaseModel):
    items: list[OverviewMetricRead]


class DistributionItemRead(BaseModel):
    label: str
    value: int
    percentage: float = 0.0


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
    recommendation_status: Optional[str] = None
    final_adjustment_ratio: Optional[float] = None


class ActionItemRead(BaseModel):
    title: str
    value: str
    note: str
    severity: str


class KpiSummaryResponse(BaseModel):
    pending_approvals: int
    total_employees: int
    evaluated_employees: int
    avg_adjustment_ratio: float
    level_summary: list[DistributionItemRead]


class ApprovalPipelineResponse(BaseModel):
    items: list[DistributionItemRead]
    total: int


class DepartmentDrilldownResponse(BaseModel):
    department: str
    level_distribution: list[DistributionItemRead]
    avg_adjustment_ratio: float
    employee_count: int


class DashboardSnapshotResponse(BaseModel):
    cycle_summary: Optional[CycleSummaryRead] = None
    overview: DashboardOverviewResponse
    ai_level_distribution: DistributionResponse
    roi_distribution: DistributionResponse
    heatmap: HeatmapResponse
    department_insights: list[DepartmentInsightRead]
    top_talents: list[TalentSpotlightRead]
    action_items: list[ActionItemRead]
