from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.dependencies import get_app_settings, get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.file import (
    EvidenceListResponse,
    EvidenceRead,
    FileDeleteResponse,
    FilePreviewResponse,
    GitHubImportRequest,
    ParseResultResponse,
    UploadedFileListResponse,
    UploadedFileRead,
)
from backend.app.services.evidence_service import RequiredLLMError
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.file_service import FileService
from backend.app.services.parse_service import ParseService

logger = logging.getLogger(__name__)

router = APIRouter(tags=['files'])


def ensure_submission_access(db: Session, current_user: User, submission_id: str) -> None:
    try:
        submission = AccessScopeService(db).ensure_submission_access(current_user, submission_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found.')


def ensure_file_access(db: Session, current_user: User, file_id: str):
    try:
        file_record = AccessScopeService(db).ensure_uploaded_file_access(current_user, file_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if file_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found.')
    return file_record


@router.post('/submissions/{submission_id}/files', response_model=UploadedFileListResponse, status_code=status.HTTP_201_CREATED)
def upload_submission_files(
    submission_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> UploadedFileListResponse:
    ensure_submission_access(db, current_user, submission_id)
    service = FileService(db, settings)
    try:
        items = service.upload_files(submission_id, files)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return UploadedFileListResponse(items=[UploadedFileRead.model_validate(item) for item in items], total=len(items))


@router.post('/submissions/{submission_id}/github-import', response_model=UploadedFileRead, status_code=status.HTTP_201_CREATED)
def import_github_submission_file(
    submission_id: str,
    payload: GitHubImportRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> UploadedFileRead:
    ensure_submission_access(db, current_user, submission_id)
    file_service = FileService(db, settings)
    parse_service = ParseService(db, settings)
    try:
        file_record = file_service.import_github_file(submission_id, str(payload.url))
        parsed_file, _ = parse_service.parse_file(file_record)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        logger.exception('GitHub import failed for submission %s', submission_id, exc_info=exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc) or 'Failed to import GitHub file.') from exc
    return UploadedFileRead.model_validate(parsed_file)


@router.get('/submissions/{submission_id}/files', response_model=UploadedFileListResponse)
def list_submission_files(
    submission_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> UploadedFileListResponse:
    ensure_submission_access(db, current_user, submission_id)
    service = FileService(db, settings)
    items = service.list_files(submission_id)
    return UploadedFileListResponse(items=[UploadedFileRead.model_validate(item) for item in items], total=len(items))


@router.put('/files/{file_id}', response_model=UploadedFileRead)
def replace_uploaded_file(
    file_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> UploadedFileRead:
    ensure_file_access(db, current_user, file_id)
    service = FileService(db, settings)
    try:
        updated = service.replace_file(file_id, file)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return UploadedFileRead.model_validate(updated)


@router.delete('/files/{file_id}', response_model=FileDeleteResponse)
def delete_uploaded_file(
    file_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> FileDeleteResponse:
    ensure_file_access(db, current_user, file_id)
    service = FileService(db, settings)
    try:
        deleted_file_id = service.delete_file(file_id)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    return FileDeleteResponse(deleted_file_id=deleted_file_id)


@router.post('/files/{file_id}/parse', response_model=ParseResultResponse)
def parse_single_file(
    file_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> ParseResultResponse:
    file_record = ensure_file_access(db, current_user, file_id)
    parse_service = ParseService(db, settings)
    try:
        updated_file, evidence_count = parse_service.parse_file(file_record)
    except RequiredLLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ParseResultResponse(file_id=updated_file.id, parse_status=updated_file.parse_status, evidence_count=evidence_count)


@router.post('/submissions/{submission_id}/parse-all', response_model=UploadedFileListResponse)
def parse_all_submission_files(
    submission_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> UploadedFileListResponse:
    ensure_submission_access(db, current_user, submission_id)
    file_service = FileService(db, settings)
    parse_service = ParseService(db, settings)
    files = file_service.list_files(submission_id)
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No files found for submission.')
    try:
        updated_files, _ = parse_service.parse_submission_files(files)
    except RequiredLLMError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return UploadedFileListResponse(items=[UploadedFileRead.model_validate(item) for item in updated_files], total=len(updated_files))


@router.get('/files/{file_id}/preview', response_model=FilePreviewResponse)
def preview_file(
    file_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> FilePreviewResponse:
    ensure_file_access(db, current_user, file_id)
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
    current_user: User = Depends(get_current_user),
) -> EvidenceListResponse:
    ensure_submission_access(db, current_user, submission_id)
    service = FileService(db, settings)
    items = service.list_evidence(submission_id)
    return EvidenceListResponse(items=[EvidenceRead.model_validate(item) for item in items], total=len(items))
