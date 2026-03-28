from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.schemas.import_job import (
    BulkImportJobDeleteRequest,
    BulkImportJobDeleteResponse,
    ImportJobDeleteResponse,
    ImportJobListResponse,
    ImportJobRead,
)
from backend.app.services.import_service import ImportService

router = APIRouter(prefix='/imports', tags=['imports'])


@router.post('/jobs')
def create_import_job(
    import_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles('admin', 'hrbp', 'manager')),
):
    service = ImportService(db, operator_id=current_user.id, operator_role=current_user.role)
    try:
        job = service.run_import(import_type=import_type, upload=file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    data = ImportJobRead.model_validate(job).model_dump(mode='json')
    # IMP-02: HTTP 207 Multi-Status when partial failure
    if job.failed_rows > 0:
        return JSONResponse(content=data, status_code=207)
    return JSONResponse(content=data, status_code=201)


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
