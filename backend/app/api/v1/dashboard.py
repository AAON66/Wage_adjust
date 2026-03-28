from __future__ import annotations

import logging

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.redis import get_redis
from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.dashboard import (
    ApprovalPipelineResponse,
    DashboardOverviewResponse,
    DashboardSnapshotResponse,
    DepartmentDrilldownResponse,
    DistributionResponse,
    HeatmapResponse,
    KpiSummaryResponse,
)
from backend.app.services.cache_service import (
    CacheService,
    TTL_AI_LEVEL,
    TTL_APPROVAL_PIPELINE,
    TTL_DEPARTMENT_DRILLDOWN,
    TTL_SALARY_DIST,
)
from backend.app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


def _get_redis_or_503() -> redis_lib.Redis:
    """Obtain Redis client; raise 503 if unavailable (per D-03)."""
    try:
        return get_redis()
    except redis_lib.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail='Redis 服务不可用，请启动 Redis 后重试。配置项: REDIS_URL',
        )


# ---------------------------------------------------------------
# Existing endpoints -- upgraded to require_roles
# ---------------------------------------------------------------


@router.get('/overview', response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DashboardOverviewResponse:
    service = DashboardService(db)
    return DashboardOverviewResponse(items=service.get_overview(current_user, cycle_id))


@router.get('/ai-level-distribution', response_model=DistributionResponse)
def get_ai_level_distribution(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DistributionResponse:
    redis_client = _get_redis_or_503()
    cache = CacheService(redis_client)
    user_id = str(current_user.id)

    try:
        cached = cache.get('ai_level', cycle_id, user_id)
    except redis_lib.ConnectionError:
        raise HTTPException(status_code=503, detail='Redis 服务不可用，请启动 Redis 后重试。配置项: REDIS_URL')

    if cached is not None:
        return DistributionResponse(items=cached, total=sum(item['value'] for item in cached))

    service = DashboardService(db)
    dept_filter = service._department_filter(current_user)
    items = service.get_ai_level_distribution_sql(cycle_id, dept_filter)
    try:
        cache.set('ai_level', cycle_id, user_id, items, TTL_AI_LEVEL)
    except redis_lib.ConnectionError:
        pass  # Write failure is non-critical
    return DistributionResponse(items=items, total=sum(item['value'] for item in items))


@router.get('/department-heatmap', response_model=HeatmapResponse)
def get_department_heatmap(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> HeatmapResponse:
    service = DashboardService(db)
    items = service.get_heatmap(current_user, cycle_id)
    return HeatmapResponse(items=items, total=len(items))


@router.get('/roi-distribution', response_model=DistributionResponse)
def get_roi_distribution(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DistributionResponse:
    service = DashboardService(db)
    items = service.get_roi_distribution(current_user, cycle_id)
    return DistributionResponse(items=items, total=sum(int(item['value']) for item in items))


@router.get('/snapshot', response_model=DashboardSnapshotResponse)
def get_dashboard_snapshot(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DashboardSnapshotResponse:
    service = DashboardService(db)
    overview_items = service.get_overview(current_user, cycle_id)
    ai_items = service.get_ai_level_distribution(current_user, cycle_id)
    roi_items = service.get_roi_distribution(current_user, cycle_id)
    heatmap_items = service.get_heatmap(current_user, cycle_id)
    cycle_summary = service.get_cycle_summary(current_user, cycle_id)
    department_insights = service.get_department_insights(current_user, cycle_id)
    top_talents = service.get_top_talents(current_user, cycle_id)
    action_items = service.get_action_items(current_user, cycle_id)
    return DashboardSnapshotResponse(
        cycle_summary=cycle_summary,
        overview=DashboardOverviewResponse(items=overview_items),
        ai_level_distribution=DistributionResponse(items=ai_items, total=sum(int(item['value']) for item in ai_items)),
        roi_distribution=DistributionResponse(items=roi_items, total=sum(int(item['value']) for item in roi_items)),
        heatmap=HeatmapResponse(items=heatmap_items, total=len(heatmap_items)),
        department_insights=department_insights,
        top_talents=top_talents,
        action_items=action_items,
    )


# ---------------------------------------------------------------
# New endpoints
# ---------------------------------------------------------------


@router.get('/kpi-summary', response_model=KpiSummaryResponse)
def get_kpi_summary(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> KpiSummaryResponse:
    """KPI summary -- does NOT use Redis cache (review fix #2).

    This endpoint supports 30-second frontend polling and returns real-time data.
    """
    service = DashboardService(db)
    dept_filter = service._department_filter(current_user)
    data = service.get_kpi_summary_sql(cycle_id, dept_filter)
    return KpiSummaryResponse(**data)


@router.get('/salary-distribution', response_model=DistributionResponse)
def get_salary_distribution(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DistributionResponse:
    redis_client = _get_redis_or_503()
    cache = CacheService(redis_client)
    user_id = str(current_user.id)

    try:
        cached = cache.get('salary_dist', cycle_id, user_id)
    except redis_lib.ConnectionError:
        raise HTTPException(status_code=503, detail='Redis 服务不可用，请启动 Redis 后重试。配置项: REDIS_URL')

    if cached is not None:
        return DistributionResponse(items=cached, total=sum(item['value'] for item in cached))

    service = DashboardService(db)
    dept_filter = service._department_filter(current_user)
    items = service.get_salary_distribution_sql(cycle_id, dept_filter)
    try:
        cache.set('salary_dist', cycle_id, user_id, items, TTL_SALARY_DIST)
    except redis_lib.ConnectionError:
        pass
    return DistributionResponse(items=items, total=sum(item['value'] for item in items))


@router.get('/approval-pipeline', response_model=ApprovalPipelineResponse)
def get_approval_pipeline(
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ApprovalPipelineResponse:
    redis_client = _get_redis_or_503()
    cache = CacheService(redis_client)
    user_id = str(current_user.id)

    try:
        cached = cache.get('approval_pipeline', cycle_id, user_id)
    except redis_lib.ConnectionError:
        raise HTTPException(status_code=503, detail='Redis 服务不可用，请启动 Redis 后重试。配置项: REDIS_URL')

    if cached is not None:
        return ApprovalPipelineResponse(items=cached, total=sum(item['value'] for item in cached))

    service = DashboardService(db)
    dept_filter = service._department_filter(current_user)
    items = service.get_approval_pipeline_sql(cycle_id, dept_filter)
    try:
        cache.set('approval_pipeline', cycle_id, user_id, items, TTL_APPROVAL_PIPELINE)
    except redis_lib.ConnectionError:
        pass
    return ApprovalPipelineResponse(items=items, total=sum(item['value'] for item in items))


@router.get('/department-drilldown', response_model=DepartmentDrilldownResponse)
def get_department_drilldown(
    department: str = Query(...),
    cycle_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> DepartmentDrilldownResponse:
    # Manager permission check: can only see own departments
    service = DashboardService(db)
    dept_filter = service._department_filter(current_user)
    if dept_filter is not None and department not in dept_filter:
        raise HTTPException(status_code=403, detail='无权查看该部门数据')

    redis_client = _get_redis_or_503()
    cache = CacheService(redis_client)
    user_id = str(current_user.id)
    chart_type = f'dept_drilldown_{department}'

    try:
        cached = cache.get(chart_type, cycle_id, user_id)
    except redis_lib.ConnectionError:
        raise HTTPException(status_code=503, detail='Redis 服务不可用，请启动 Redis 后重试。配置项: REDIS_URL')

    if cached is not None:
        return DepartmentDrilldownResponse(**cached)

    data = service.get_department_drilldown_sql(department, cycle_id)
    try:
        cache.set(chart_type, cycle_id, user_id, data, TTL_DEPARTMENT_DRILLDOWN)
    except redis_lib.ConnectionError:
        pass
    return DepartmentDrilldownResponse(**data)
