from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.dependencies import get_app_settings, get_current_user, get_db
from backend.app.schemas.file import (
    EvidenceListResponse,
    EvidenceRead,
    FilePreviewResponse,
    ParseResultResponse,
    UploadedFileListResponse,
    UploadedFileRead,
)
from backend.app.services.file_service import FileService
from backend.app.services.parse_service import ParseService

router = APIRouter(tags=['files'])


@router.post('/submissions/{submission_id}/files', response_model=UploadedFileListResponse, status_code=status.HTTP_201_CREATED)
def upload_submission_files(
    submission_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: object = Depends(get_current_user),
) -> UploadedFileListResponse:
    service = FileService(db, settings)
    try:
        items = service.upload_files(submission_id, files)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return UploadedFileListResponse(items=[UploadedFileRead.model_validate(item) for item in items], total=len(items))


@router.get('/submissions/{submission_id}/files', response_model=UploadedFileListResponse)
def list_submission_files(
    submission_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: object = Depends(get_current_user),
) -> UploadedFileListResponse:
    service = FileService(db, settings)
    items = service.list_files(submission_id)
    return UploadedFileListResponse(items=[UploadedFileRead.model_validate(item) for item in items], total=len(items))


@router.post('/files/{file_id}/parse', response_model=ParseResultResponse)
def parse_single_file(
    file_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: object = Depends(get_current_user),
) -> ParseResultResponse:
    file_service = FileService(db, settings)
    parse_service = ParseService(db, settings)
    file_record = file_service.get_file(file_id)
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found.')
    updated_file, evidence_count = parse_service.parse_file(file_record)
    return ParseResultResponse(file_id=updated_file.id, parse_status=updated_file.parse_status, evidence_count=evidence_count)


@router.post('/submissions/{submission_id}/parse-all', response_model=UploadedFileListResponse)
def parse_all_submission_files(
    submission_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: object = Depends(get_current_user),
) -> UploadedFileListResponse:
    file_service = FileService(db, settings)
    parse_service = ParseService(db, settings)
    files = file_service.list_files(submission_id)
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No files found for submission.')
    updated_files, _ = parse_service.parse_submission_files(files)
    return UploadedFileListResponse(items=[UploadedFileRead.model_validate(item) for item in updated_files], total=len(updated_files))


@router.get('/files/{file_id}/preview', response_model=FilePreviewResponse)
def preview_file(
    file_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: object = Depends(get_current_user),
) -> FilePreviewResponse:
    service = FileService(db, settings)
    result = service.preview_file(file_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found.')
    file_record, preview_url = result
    return FilePreviewResponse(file_id=file_record.id, file_name=file_record.file_name, preview_url=preview_url, storage_key=file_record.storage_key)


@router.get('/submissions/{submission_id}/evidence', response_model=EvidenceListResponse)
def list_submission_evidence(
    submission_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: object = Depends(get_current_user),
) -> EvidenceListResponse:
    service = FileService(db, settings)
    items = service.list_evidence(submission_id)
    return EvidenceListResponse(items=[EvidenceRead.model_validate(item) for item in items], total=len(items))