from __future__ import annotations

import json
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.dependencies import get_db, require_roles
from backend.app.models.feishu_sync_log import FeishuSyncLog
from backend.app.models.user import User
from backend.app.scheduler.feishu_scheduler import reload_scheduler
from backend.app.schemas.feishu import (
    FeishuConfigCreate,
    FeishuConfigExistsResponse,
    FeishuConfigRead,
    FeishuConfigUpdate,
    FieldMappingItem,
    SyncLogRead,
    SyncTriggerRequest,
    SyncTriggerResponse,
    SyncTypeLiteral,
)
from backend.app.services.feishu_service import FeishuConfigValidationError, FeishuService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/feishu', tags=['feishu'])


def _config_to_read(config) -> FeishuConfigRead:
    """Convert a FeishuConfig ORM object to FeishuConfigRead schema."""
    field_mapping_raw = config.field_mapping
    if isinstance(field_mapping_raw, str):
        mapping_dict = json.loads(field_mapping_raw)
    else:
        mapping_dict = field_mapping_raw or {}

    mapping_list = [
        FieldMappingItem(feishu_field=k, system_field=v)
        for k, v in mapping_dict.items()
    ]

    return FeishuConfigRead(
        id=config.id,
        app_id=config.app_id,
        app_secret_masked=config.get_masked_secret(),
        bitable_app_token=config.bitable_app_token,
        bitable_table_id=config.bitable_table_id,
        field_mapping=mapping_list,
        sync_hour=config.sync_hour,
        sync_minute=config.sync_minute,
        sync_timezone=config.sync_timezone,
        is_active=config.is_active,
    )


def _sync_log_to_read(log) -> SyncLogRead:
    """Convert a FeishuSyncLog ORM object to SyncLogRead schema."""
    unmatched = None
    if log.unmatched_employee_nos:
        try:
            unmatched = json.loads(log.unmatched_employee_nos)
        except (json.JSONDecodeError, TypeError):
            unmatched = None

    return SyncLogRead(
        id=log.id,
        sync_type=log.sync_type,  # Phase 31 / D-01
        mode=log.mode,
        status=log.status,
        total_fetched=log.total_fetched,
        synced_count=log.synced_count,
        updated_count=log.updated_count,
        skipped_count=log.skipped_count,
        unmatched_count=log.unmatched_count,
        mapping_failed_count=log.mapping_failed_count,  # Phase 31 / D-02
        failed_count=log.failed_count,
        leading_zero_fallback_count=log.leading_zero_fallback_count,
        error_message=log.error_message,
        unmatched_employee_nos=unmatched,
        started_at=log.started_at,
        finished_at=log.finished_at,
        triggered_by=log.triggered_by,
    )


# ------------------------------------------------------------------
# Config endpoints
# ------------------------------------------------------------------


@router.get('/config', response_model=FeishuConfigRead)
def get_config(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> FeishuConfigRead:
    """获取当前飞书配置（admin + hrbp 可见）。"""
    service = FeishuService(db)
    config = service.get_config()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No Feishu configuration found')
    return _config_to_read(config)


@router.get('/config-exists', response_model=FeishuConfigExistsResponse)
def config_exists(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> FeishuConfigExistsResponse:
    """配置是否存在（admin + hrbp，前端用于条件渲染）。"""
    service = FeishuService(db)
    config = service.get_config()
    return FeishuConfigExistsResponse(exists=config is not None)


@router.post('/config', response_model=FeishuConfigRead, status_code=status.HTTP_201_CREATED)
def create_config(
    data: FeishuConfigCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin')),
) -> FeishuConfigRead:
    """创建飞书配置（仅 admin）。创建后自动重载调度器。

    EMPNO-03 / D-01: 配置保存前会校验飞书端 employee_no 字段类型必须为 text；
    非 text 类型返回 422 + 结构化错误 body。
    """
    service = FeishuService(db)
    # Exception handler 透传路径: X
    # main.py http_exception_handler 已对 HTTPException.detail 为 dict 时透传 (content=exc.detail)，
    # 因此用 raise HTTPException(detail=exc.detail) 即可直接返回结构化 body。
    try:
        config = service.create_config(data)
    except FeishuConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    try:
        reload_scheduler(config.sync_hour, config.sync_minute, config.sync_timezone)
    except Exception:
        logger.warning('Failed to reload scheduler after config creation', exc_info=True)
    return _config_to_read(config)


@router.put('/config/{config_id}', response_model=FeishuConfigRead)
def update_config(
    config_id: str,
    data: FeishuConfigUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin')),
) -> FeishuConfigRead:
    """更新飞书配置（仅 admin）。更新后自动重载调度器。

    EMPNO-03 / D-01: 若 HR 修改了 field_mapping / bitable_app_token / bitable_table_id，
    保存前会重新校验字段类型；非 text 类型返回 422 + 结构化错误 body。
    """
    service = FeishuService(db)
    # Exception handler 透传路径: X (main.py 已支持 dict detail 透传)
    try:
        config = service.update_config(config_id, data)
    except FeishuConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.detail,
        ) from exc
    try:
        reload_scheduler(config.sync_hour, config.sync_minute, config.sync_timezone)
    except Exception:
        logger.warning('Failed to reload scheduler after config update', exc_info=True)
    return _config_to_read(config)


# ------------------------------------------------------------------
# Sync endpoints
# ------------------------------------------------------------------


def _run_sync_in_background(mode: str, triggered_by: str | None) -> None:
    """在独立 session 中执行同步（后台线程）。"""
    db = SessionLocal()
    try:
        service = FeishuService(db)
        service.sync_with_retry(mode=mode, triggered_by=triggered_by)
    except Exception:
        logger.exception('Background sync failed')
    finally:
        db.close()


@router.post('/sync', response_model=SyncTriggerResponse)
def trigger_sync(
    data: SyncTriggerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> SyncTriggerResponse:
    """手动触发同步（admin + hrbp），支持 full/incremental 模式。"""
    if data.mode not in ('full', 'incremental'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='mode must be "full" or "incremental"',
        )

    service = FeishuService(db)

    # Concurrent sync guard — also expire stale 'running' logs older than 30 min
    service.expire_stale_running_logs(timeout_minutes=30)

    if service.is_sync_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={'error': 'sync_in_progress', 'message': '同步正在进行中，请稍后再试'},
        )

    # Launch background thread (sync_attendance creates its own log)
    thread = threading.Thread(
        target=_run_sync_in_background,
        args=(data.mode, current_user.id),
        daemon=True,
    )
    thread.start()

    return SyncTriggerResponse(
        sync_log_id='pending',
        status='running',
        message='同步已启动',
    )


@router.get('/sync-logs', response_model=list[SyncLogRead])
def get_sync_logs(
    sync_type: SyncTypeLiteral | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> list[SyncLogRead]:
    """Phase 31 / D-05 / D-06: 同步日志列表（admin + hrbp）。

    Query params:
    - sync_type: 可选，按 SyncTypeLiteral 白名单过滤；非白名单值由 Pydantic 返回 422
    - page: 页码，默认 1（ge=1）
    - page_size: 页大小，默认 20（ge=1 le=100，防 DoS）
    """
    service = FeishuService(db)
    logs = service.get_sync_logs(sync_type=sync_type, page=page, page_size=page_size)
    return [_sync_log_to_read(log) for log in logs]


@router.get('/sync-status', response_model=SyncLogRead | None)
def get_sync_status(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> SyncLogRead | None:
    """最新同步状态（admin + hrbp）。"""
    from backend.app.services.attendance_service import AttendanceService
    att_service = AttendanceService(db)
    log = att_service.get_latest_sync_status()
    if log is None:
        return None
    return _sync_log_to_read(log)
