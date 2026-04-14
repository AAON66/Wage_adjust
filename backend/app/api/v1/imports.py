from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.schemas.import_job import (
    BulkImportJobDeleteRequest,
    BulkImportJobDeleteResponse,
    ImportJobDeleteResponse,
    ImportJobListResponse,
    ImportJobRead,
)
from backend.app.schemas.task import TaskTriggerResponse
from backend.app.services.import_service import ImportService
from backend.app.tasks.import_tasks import run_import_task

router = APIRouter(prefix='/imports', tags=['imports'])


@router.post('/jobs', status_code=status.HTTP_202_ACCEPTED)
def create_import_job(
    import_type: str,
    file: UploadFile = File(...),
    current_user=Depends(require_roles('admin', 'hrbp', 'manager')),
) -> TaskTriggerResponse:
    normalized_type = import_type.strip().lower()
    if normalized_type not in ImportService.SUPPORTED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported import type.')
    raw_bytes = file.file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded file is empty.')
    file_bytes_b64 = base64.b64encode(raw_bytes).decode('ascii')
    file_name = file.filename or f'{normalized_type}.csv'
    task = run_import_task.delay(
        normalized_type,
        file_bytes_b64,
        file_name,
        operator_id=str(current_user.id),
        operator_role=current_user.role,
    )
    return TaskTriggerResponse(task_id=task.id, status='pending')


@router.get('/jobs', response_model=ImportJobListResponse)
def list_import_jobs(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> ImportJobListResponse:
    service = ImportService(db)
    items = service.list_jobs()
    return ImportJobListResponse(items=[ImportJobRead.model_validate(item) for item in items], total=len(items))


@router.get('/jobs/{job_id}', response_model=ImportJobRead)
def get_import_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> ImportJobRead:
    service = ImportService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Import job not found.')
    return ImportJobRead.model_validate(job)


@router.delete('/jobs/{job_id}', response_model=ImportJobDeleteResponse)
def delete_import_job(
    job_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ImportJobDeleteResponse:
    service = ImportService(db)
    try:
        deleted_job_id = service.delete_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ImportJobDeleteResponse(deleted_job_id=deleted_job_id)


@router.post('/jobs/bulk-delete', response_model=BulkImportJobDeleteResponse)
def bulk_delete_import_jobs(
    payload: BulkImportJobDeleteRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> BulkImportJobDeleteResponse:
    service = ImportService(db)
    deleted_job_ids = service.bulk_delete_jobs(payload.job_ids)
    return BulkImportJobDeleteResponse(deleted_job_ids=deleted_job_ids)


@router.get('/templates/{import_type}')
def download_template(
    import_type: str,
    format: str = 'xlsx',
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    service = ImportService(db)
    try:
        if format == 'xlsx':
            file_name, content, media_type = service.build_template_xlsx(import_type)
        else:
            file_name, content, media_type = service.build_template(import_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename={file_name}'},
    )


@router.get('/jobs/{job_id}/export')
def export_import_job(
    job_id: str,
    format: str = 'xlsx',
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    service = ImportService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Import job not found.')
    if format == 'xlsx':
        file_name, content, media_type = service.build_export_report_xlsx(job)
    else:
        file_name, content, media_type = service.build_export_report(job)
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename={file_name}'},
    )
