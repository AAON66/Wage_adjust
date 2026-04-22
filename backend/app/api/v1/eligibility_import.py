from __future__ import annotations

import base64
import logging
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.schemas.eligibility_import import (
    ELIGIBILITY_IMPORT_TYPES,
    BitableParseRequest,
    BitableParseResponse,
    FeishuFieldsRequest,
    FeishuFieldsResponse,
    FeishuSyncRequest,
)
from backend.app.schemas.import_preview import (
    ActiveJobResponse,
    ConfirmRequest,
    ConfirmResponse,
    PreviewResponse,
)
from backend.app.schemas.task import TaskTriggerResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/eligibility-import', tags=['eligibility-import'])

# Regex for extracting app_token and table_id from a feishu bitable URL
# Example: https://xxx.feishu.cn/base/XXX?table=YYY
_BITABLE_URL_RE = re.compile(
    r'https?://[^/]*feishu\.cn/(?:base|wiki)/([A-Za-z0-9]+)(?:\?.*table=([A-Za-z0-9]+))?'
)


@router.post('/excel', status_code=status.HTTP_202_ACCEPTED, deprecated=True)
def import_excel(
    import_type: str,
    file: UploadFile = File(...),
    current_user=Depends(require_roles('admin', 'hrbp')),
) -> TaskTriggerResponse:
    """**Deprecated (Phase 32):** 一步上传立即落库。

    请改用两阶段端点：
      1. POST /excel/preview?import_type=X → 拿到 PreviewResponse
      2. POST /excel/{job_id}/confirm → 确认落库

    保留本端点以维持旧客户端兼容性（决议 Open Question 4）。
    新前端代码不应再调用此端点。
    """
    normalized_type = import_type.strip().lower()
    if normalized_type not in ELIGIBILITY_IMPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported import type. Must be one of: {sorted(ELIGIBILITY_IMPORT_TYPES)}',
        )
    raw_bytes = file.file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded file is empty.')
    file_bytes_b64 = base64.b64encode(raw_bytes).decode('ascii')
    file_name = file.filename or f'{normalized_type}.xlsx'

    from backend.app.tasks.import_tasks import run_import_task

    task = run_import_task.delay(
        normalized_type,
        file_bytes_b64,
        file_name,
        operator_id=str(current_user.id),
        operator_role=current_user.role,
    )
    return TaskTriggerResponse(task_id=task.id, status='pending')


@router.post('/feishu/parse-url')
def parse_bitable_url(
    data: BitableParseRequest,
    _current_user=Depends(require_roles('admin', 'hrbp')),
) -> BitableParseResponse:
    match = _BITABLE_URL_RE.search(data.url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Invalid feishu bitable URL. Expected format: https://xxx.feishu.cn/base/{app_token}?table={table_id}',
        )
    app_token = match.group(1)
    table_id = match.group(2)
    if not table_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Could not extract table_id from URL. Ensure the URL contains a table= parameter.',
        )
    return BitableParseResponse(app_token=app_token, table_id=table_id)


@router.post('/feishu/fields')
def list_bitable_fields(
    data: FeishuFieldsRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles('admin', 'hrbp')),
) -> FeishuFieldsResponse:
    from backend.app.services.feishu_service import FeishuService

    service = FeishuService(db)
    try:
        fields = service.list_bitable_fields(app_token=data.app_token, table_id=data.table_id)
    except Exception as exc:
        logger.exception('Failed to list bitable fields')
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Failed to fetch fields from feishu: {exc}',
        ) from exc
    return FeishuFieldsResponse(fields=fields)


@router.post('/feishu/sync', status_code=status.HTTP_202_ACCEPTED)
def trigger_feishu_sync(
    data: FeishuSyncRequest,
    _current_user=Depends(require_roles('admin', 'hrbp')),
) -> TaskTriggerResponse:
    if data.sync_type not in ELIGIBILITY_IMPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported sync type. Must be one of: {sorted(ELIGIBILITY_IMPORT_TYPES)}',
        )

    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    task = feishu_sync_eligibility_task.delay(
        sync_type=data.sync_type,
        app_token=data.app_token,
        table_id=data.table_id,
        field_mapping=data.field_mapping,
        operator_id=str(_current_user.id),
    )
    return TaskTriggerResponse(task_id=task.id, status='pending')


@router.get('/templates/{import_type}')
def download_template(
    import_type: str,
    format: str = 'xlsx',
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles('admin', 'hrbp')),
):
    normalized_type = import_type.strip().lower()
    if normalized_type not in ELIGIBILITY_IMPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported import type. Must be one of: {sorted(ELIGIBILITY_IMPORT_TYPES)}',
        )

    from backend.app.services.import_service import ImportService

    service = ImportService(db)
    try:
        if format == 'xlsx':
            file_name, content, media_type = service.build_template_xlsx(normalized_type)
        else:
            file_name, content, media_type = service.build_template(normalized_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename={file_name}'},
    )


# =====================================================================
# Phase 32-04: 两阶段提交 API（preview / confirm / cancel / active）
# 配套 ImportService.build_preview / confirm_import / cancel_import /
# get_active_job / is_import_running / expire_stale_import_jobs（Phase 32-03）
# =====================================================================

# 文件类型 + 大小白名单（T-32-02 / T-32-03 防护）
_ALLOWED_XLSX_EXTENSIONS = {'.xlsx', '.xls'}
_ALLOWED_XLSX_CONTENT_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    # 部分浏览器在拖拽上传时不带正确 mime；仅作软校验
    'application/octet-stream',
}
_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _validate_upload_file(file: UploadFile) -> bytes:
    """文件类型 + 大小 + 内容校验。

    防护：
      - T-32-02: 拒绝 .exe / .html / .svg / .csv / .xls 之外的非 xlsx 文件
      - T-32-03: 拒绝 > 10MB 文件防 DoS
      - 拒绝空文件
    """
    filename = (file.filename or '').lower()
    ext = '.' + filename.rsplit('.', 1)[-1] if '.' in filename else ''
    if ext not in _ALLOWED_XLSX_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'仅接受 .xlsx 或 .xls 文件（实际：{ext or "未知"}）',
        )
    # Content-Type 软校验（部分浏览器不准）
    ct = (file.content_type or '').lower()
    if ct and ct not in _ALLOWED_XLSX_CONTENT_TYPES:
        logger.warning('Unexpected content_type %s for filename %s', ct, filename)
    raw_bytes = file.file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Uploaded file is empty.',
        )
    if len(raw_bytes) > _MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f'文件超过大小限制（'
                f'{_MAX_UPLOAD_SIZE_BYTES // 1024 // 1024}MB）'
            ),
        )
    return raw_bytes


@router.post('/excel/preview', response_model=PreviewResponse)
def preview_excel_import(
    import_type: str,
    file: UploadFile = File(...),
    current_user=Depends(require_roles('admin', 'hrbp')),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    """D-06 + D-07 + IMPORT-07: 上传 + 解析 + 暂存 + 返回 PreviewResponse。

    流程：
      1) 校验 import_type 在 ELIGIBILITY_IMPORT_TYPES 中
      2) 校验文件类型 / 大小（T-32-02 / T-32-03）
      3) 清理僵尸 job（D-17）
      4) per-import_type 锁检查（D-16）；活跃则 409
      5) 调 service.build_preview 解析 + 暂存 + 算 sha256 + 返回 PreviewResponse
    """
    normalized_type = import_type.strip().lower()
    if normalized_type not in ELIGIBILITY_IMPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f'Unsupported import type. '
                f'Must be one of: {sorted(ELIGIBILITY_IMPORT_TYPES)}'
            ),
        )

    raw_bytes = _validate_upload_file(file)
    file_name = file.filename or f'{normalized_type}.xlsx'

    from backend.app.services.import_service import ImportService

    service = ImportService(db)

    # D-17: 先清理僵尸 job
    service.expire_stale_import_jobs()

    # D-16: per-import_type 锁
    if service.is_import_running(import_type=normalized_type):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'error': 'import_in_progress',
                'import_type': normalized_type,
                'message': '该类型导入正在进行中，请等待当前任务完成后再试',
            },
        )

    try:
        return service.build_preview(
            import_type=normalized_type,
            file_name=file_name,
            raw_bytes=raw_bytes,
            actor_id=str(current_user.id),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post('/excel/{job_id}/confirm', response_model=ConfirmResponse)
def confirm_excel_import(
    job_id: str,
    body: ConfirmRequest,
    current_user=Depends(require_roles('admin', 'hrbp')),
    db: Session = Depends(get_db),
) -> ConfirmResponse:
    """D-06 + D-13 + IMPORT-05/06/07: 确认导入。

    流程：
      1) 查 job 存在性（404）
      2) 检查同 import_type 是否有其他 processing job（409）
      3) 调 service.confirm_import 完成落库 + AuditLog 写入
      ValueError 映射：
        - '已确认' / '已取消' / '状态为' → 409（双 confirm 防护）
        - '替换模式' → 422（confirm_replace 校验失败）
        - 其他 → 400
    """
    from backend.app.models.import_job import ImportJob
    from backend.app.services.import_service import ImportService

    job = db.execute(
        select(ImportJob).where(ImportJob.id == job_id)
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'ImportJob {job_id} 不存在',
        )

    # 同 import_type 是否有其他 processing job（previewing 是当前 job 自己，不算冲突）
    other_running = db.execute(
        select(ImportJob)
        .where(
            ImportJob.import_type == job.import_type,
            ImportJob.status == 'processing',
            ImportJob.id != job_id,
        )
        .limit(1)
    ).scalar_one_or_none()
    if other_running is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'error': 'import_in_progress',
                'import_type': job.import_type,
                'message': '该类型导入正在进行中，请等待当前任务完成后再试',
            },
        )

    service = ImportService(db)
    try:
        return service.confirm_import(
            job_id=job_id,
            overwrite_mode=body.overwrite_mode,
            confirm_replace=body.confirm_replace,
            actor_id=str(current_user.id),
            actor_role=current_user.role,
        )
    except ValueError as exc:
        msg = str(exc)
        # 状态机异常（双 confirm / 已取消） → 409
        if '已确认' in msg or '已取消' in msg or '状态为' in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=msg,
            ) from exc
        # 替换模式未确认 → 422
        if '替换模式' in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg,
            ) from exc
        # 其他业务校验 → 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=msg,
        ) from exc


@router.post('/excel/{job_id}/cancel', status_code=status.HTTP_204_NO_CONTENT)
def cancel_excel_import(
    job_id: str,
    current_user=Depends(require_roles('admin', 'hrbp')),
    db: Session = Depends(get_db),
):
    """HR 取消 previewing 状态的 job（幂等：终态 job 直接 204 不报错）。"""
    from backend.app.services.import_service import ImportService
    service = ImportService(db)
    try:
        service.cancel_import(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc
    return None


@router.get('/excel/active', response_model=ActiveJobResponse)
def get_active_import(
    import_type: str,
    current_user=Depends(require_roles('admin', 'hrbp')),
    db: Session = Depends(get_db),
) -> ActiveJobResponse:
    """D-18: 进入 Tab 时查询活跃 job，前端据此禁用「选择文件」按钮。"""
    normalized_type = import_type.strip().lower()
    if normalized_type not in ELIGIBILITY_IMPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f'Unsupported import type. '
                f'Must be one of: {sorted(ELIGIBILITY_IMPORT_TYPES)}'
            ),
        )
    from backend.app.services.import_service import ImportService
    service = ImportService(db)
    # 顺手清理僵尸（HR 进入 Tab 即触发清理，无需等定时任务）
    service.expire_stale_import_jobs()
    active = service.get_active_job(normalized_type)
    if active is None:
        return ActiveJobResponse(active=False)
    return ActiveJobResponse(
        active=True,
        job_id=active.id,
        status=active.status,
        created_at=active.created_at,
        file_name=active.file_name,
    )
