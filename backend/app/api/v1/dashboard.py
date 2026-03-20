from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db
from backend.app.schemas.dashboard import DashboardOverviewResponse, DashboardSnapshotResponse, DistributionResponse, HeatmapResponse
from backend.app.services.dashboard_service import DashboardService

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('/overview', response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> DashboardOverviewResponse:
    service = DashboardService(db)
    return DashboardOverviewResponse(items=service.get_overview(cycle_id))


@router.get('/ai-level-distribution', response_model=DistributionResponse)
def get_ai_level_distribution(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> DistributionResponse:
    service = DashboardService(db)
    items = service.get_ai_level_distribution(cycle_id)
    return DistributionResponse(items=items, total=sum(int(item['value']) for item in items))


@router.get('/department-heatmap', response_model=HeatmapResponse)
def get_department_heatmap(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> HeatmapResponse:
    service = DashboardService(db)
    items = service.get_heatmap(cycle_id)
    return HeatmapResponse(items=items, total=len(items))


@router.get('/roi-distribution', response_model=DistributionResponse)
def get_roi_distribution(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> DistributionResponse:
    service = DashboardService(db)
    items = service.get_roi_distribution(cycle_id)
    return DistributionResponse(items=items, total=sum(int(item['value']) for item in items))


@router.get('/snapshot', response_model=DashboardSnapshotResponse)
def get_dashboard_snapshot(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> DashboardSnapshotResponse:
    service = DashboardService(db)
    overview_items = service.get_overview(cycle_id)
    ai_items = service.get_ai_level_distribution(cycle_id)
    roi_items = service.get_roi_distribution(cycle_id)
    heatmap_items = service.get_heatmap(cycle_id)
    return DashboardSnapshotResponse(
        overview=DashboardOverviewResponse(items=overview_items),
        ai_level_distribution=DistributionResponse(items=ai_items, total=sum(int(item['value']) for item in ai_items)),
        roi_distribution=DistributionResponse(items=roi_items, total=sum(int(item['value']) for item in roi_items)),
        heatmap=HeatmapResponse(items=heatmap_items, total=len(heatmap_items)),
    )
