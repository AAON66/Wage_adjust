"""Phase 34 D-15：绩效管理 REST API（5 端点 + 1 Phase 35 保留位）。

  - GET  /performance/records           列表分页 + year/department filter
  - POST /performance/records           单条新增
  - GET  /performance/tier-summary      档次摘要（cache → snapshot → 404）
  - POST /performance/recompute-tiers   手动重算（D-05 行锁 + 409 撞锁）
  - GET  /performance/available-years   B-3 年份下拉源

  - GET  /performance/me/tier           Phase 35 ESELF-03 保留位（本期不挂 handler）

全部 require_roles('admin', 'hrbp')；employee/manager 触发 403（dependency 兜底）。
Service 层抛 ValueError / TierRecompute*Error → 在此层 catch 转 HTTP 状态码。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.core.redis import get_redis
from backend.app.dependencies import get_app_settings, get_current_user, get_db, require_roles
from backend.app.models.employee import Employee
from backend.app.models.user import User
from backend.app.schemas.performance import (
    AvailableYearsResponse,
    MyTierResponse,
    PerformanceHistoryResponse,
    PerformanceRecordCreateRequest,
    PerformanceRecordRead,
    PerformanceRecordsListResponse,
    RecomputeTriggerResponse,
    TierSummaryResponse,
)
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.exceptions import (
    TierRecomputeBusyError,
    TierRecomputeFailedError,
)
from backend.app.services.performance_service import PerformanceService
from backend.app.services.tier_cache import TierCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/performance', tags=['performance'])


def _make_service(db: Session, settings: Settings) -> PerformanceService:
    """构造注入了 Redis cache（或 None 降级）的 PerformanceService。"""
    try:
        redis_client = get_redis()
    except Exception as exc:  # noqa: BLE001 — Redis 不可达走 None 降级
        logger.warning('Redis unavailable for tier cache: %s', exc)
        redis_client = None
    cache = TierCache(redis_client=redis_client, settings=settings)
    return PerformanceService(db, settings=settings, cache=cache)


# ---------------------------------------------------------------------------
# GET /performance/records — 列表分页（D-14）
# ---------------------------------------------------------------------------

@router.get('/records', response_model=PerformanceRecordsListResponse)
def list_performance_records(
    year: int | None = Query(None, ge=2000, le=2100),
    department: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _u=Depends(require_roles('admin', 'hrbp')),
) -> PerformanceRecordsListResponse:
    service = _make_service(db, settings)
    items, total = service.list_records(
        year=year,
        department=department,
        page=page,
        page_size=page_size,
    )
    total_pages = max(1, -(-total // page_size)) if total > 0 else 1
    return PerformanceRecordsListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# GET /performance/records/by-employee/{employee_id} — Phase 36 D-04 / D-05 / D-06
# ---------------------------------------------------------------------------

@router.get(
    '/records/by-employee/{employee_id}',
    response_model=PerformanceHistoryResponse,
)
def list_performance_records_by_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> PerformanceHistoryResponse:
    """按员工返回历史绩效记录，角色与部门范围受限。"""
    try:
        employee = AccessScopeService(db).ensure_employee_access(
            current_user,
            employee_id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='无权查看该员工的历史绩效',
        ) from exc
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='员工不存在',
        )

    service = _make_service(db, settings)
    items = service.list_records_by_employee(employee_id)
    return PerformanceHistoryResponse(items=items)


# ---------------------------------------------------------------------------
# POST /performance/records — 单条新增 / UPSERT（D-08）
# ---------------------------------------------------------------------------

@router.post(
    '/records',
    response_model=PerformanceRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_performance_record(
    payload: PerformanceRecordCreateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _u=Depends(require_roles('admin', 'hrbp')),
) -> PerformanceRecordRead:
    service = _make_service(db, settings)
    try:
        record = service.create_record(
            employee_id=payload.employee_id,
            year=payload.year,
            grade=payload.grade,
            source=payload.source,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return PerformanceRecordRead.model_validate(record)


# ---------------------------------------------------------------------------
# GET /performance/tier-summary — 档次摘要（D-09 / D-10）
# ---------------------------------------------------------------------------

@router.get('/tier-summary', response_model=TierSummaryResponse)
def get_tier_summary(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _u=Depends(require_roles('admin', 'hrbp')),
) -> TierSummaryResponse:
    service = _make_service(db, settings)
    summary = service.get_tier_summary(year)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                'error': 'no_snapshot',
                'message': '该年度尚无档次快照',
                'year': year,
                'hint': (
                    f'POST /api/v1/performance/recompute-tiers?year={year} '
                    '触发重算'
                ),
            },
        )
    return summary


# ---------------------------------------------------------------------------
# POST /performance/recompute-tiers — 手动重算（D-05 / D-06）
# ---------------------------------------------------------------------------

@router.post('/recompute-tiers', response_model=RecomputeTriggerResponse)
def recompute_tiers(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _u=Depends(require_roles('admin', 'hrbp')),
) -> RecomputeTriggerResponse:
    service = _make_service(db, settings)
    try:
        summary = service.recompute_tiers(year)
    except TierRecomputeBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'error': 'tier_recompute_busy',
                'message': '该年度档次正在重算，请稍后重试',
                'year': exc.year,
                'retry_after_seconds': 5,
            },
        ) from exc
    except TierRecomputeFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'error': 'tier_recompute_failed',
                'message': f'档次重算失败：{exc.cause}',
                'year': exc.year,
            },
        ) from exc
    return RecomputeTriggerResponse(
        year=summary.year,
        computed_at=summary.computed_at,
        sample_size=summary.sample_size,
        insufficient_sample=summary.insufficient_sample,
        distribution_warning=summary.distribution_warning,
    )


# ---------------------------------------------------------------------------
# GET /performance/available-years — B-3 年份下拉源
# ---------------------------------------------------------------------------

@router.get('/available-years', response_model=AvailableYearsResponse)
def get_available_years(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _u=Depends(require_roles('admin', 'hrbp')),
) -> AvailableYearsResponse:
    """B-3：替代前端「拉 200 条 records 凑 distinct」的 hack。"""
    service = _make_service(db, settings)
    years = service.list_available_years()
    return AvailableYearsResponse(years=years)


# ---------------------------------------------------------------------------
# GET /performance/me/tier — Phase 35 ESELF-03 员工自助档次查询
#
# 无参数路由：actor 由 JWT subject（current_user.employee_id）决定；
# 横向越权天然不可达（ESELF-04 红线；T-35-02-01 mitigation）。
# 任意已登录角色均可调用（admin/hrbp/manager/employee）；
# 不需要 require_roles —— 无 `{employee_id}` 变体即无越权面。
# ---------------------------------------------------------------------------

@router.get('/me/tier', response_model=MyTierResponse)
def get_my_tier(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> MyTierResponse:
    """员工自助查询本人绩效档次（Phase 35 ESELF-03）。

    响应 200 + MyTierResponse，覆盖 4 语义分支：
      - tier in {1,2,3} + reason=None：员工有档次
      - tier=None + reason='insufficient_sample'：样本不足
      - tier=None + reason='no_snapshot'：HR 从未录入绩效
      - tier=None + reason='not_ranked'：命中快照但本员工未录绩效

    错误态（D-06）：
      - 未绑定员工 → 422 + '您尚未绑定员工信息'
      - 员工档案被删 → 404 + '员工档案缺失'
      - 其他异常 → 500（main.py 全局 handler）
    """
    # D-06: 未绑定员工（current_user.employee_id is None）
    if current_user.employee_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='您尚未绑定员工信息，请前往「账号设置」完成绑定',
        )

    # D-06: JWT 有效但 Employee 行已被删
    employee = db.get(Employee, current_user.employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='员工档案缺失，请联系 HR 核对',
        )

    service = _make_service(db, settings)
    return service.get_my_tier(current_user.employee_id)
