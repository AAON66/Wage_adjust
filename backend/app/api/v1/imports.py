from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.schemas.import_job import ImportJobListResponse, ImportJobRead
from backend.app.services.import_service import ImportService

router = APIRouter(prefix='/imports', tags=['imports'])


@router.post('/jobs', response_model=ImportJobRead, status_code=status.HTTP_201_CREATED)
def create_import_job(
    import_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ImportJobRead:
    service = ImportService(db)
    try:
        job = service.run_import(import_type=import_type, upload=file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ImportJobRead.model_validate(job)


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


@router.get('/templates/{import_type}')
def download_template(
    import_type: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    service = ImportService(db)
    try:
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
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    service = ImportService(db)
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Import job not found.')
    file_name, content, media_type = service.build_export_report(job)
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename={file_name}'},
    )
