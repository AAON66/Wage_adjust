from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class OverviewMetricRead(BaseModel):
    label: str
    value: str
    note: str


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


class DashboardSnapshotResponse(BaseModel):
    overview: DashboardOverviewResponse
    ai_level_distribution: DistributionResponse
    roi_distribution: DistributionResponse
    heatmap: HeatmapResponse
