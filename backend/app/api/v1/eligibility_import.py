from __future__ import annotations

import base64
import logging
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
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
from backend.app.schemas.task import TaskTriggerResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/eligibility-import', tags=['eligibility-import'])

# Regex for extracting app_token and table_id from a feishu bitable URL
# Example: https://xxx.feishu.cn/base/XXX?table=YYY
_BITABLE_URL_RE = re.compile(
    r'https?://[^/]*feishu\.cn/(?:base|wiki)/([A-Za-z0-9]+)(?:\?.*table=([A-Za-z0-9]+))?'
)


@router.post('/excel', status_code=status.HTTP_202_ACCEPTED)
def import_excel(
    import_type: str,
    file: UploadFile = File(...),
    current_user=Depends(require_roles('admin', 'hrbp')),
) -> TaskTriggerResponse:
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
