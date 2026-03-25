from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.submission import SubmissionEnsureRequest, SubmissionListResponse, SubmissionRead
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.submission_service import SubmissionService

router = APIRouter(prefix='/submissions', tags=['submissions'])


@router.post('/ensure', response_model=SubmissionRead)
def ensure_submission(
    payload: SubmissionEnsureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionRead:
    try:
        employee = AccessScopeService(db).ensure_employee_access(current_user, payload.employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found.')
    submission = SubmissionService(db).ensure_submission(employee_id=payload.employee_id, cycle_id=payload.cycle_id)
    return SubmissionRead.model_validate(submission)


@router.get('/employee/{employee_id}', response_model=SubmissionListResponse)
def list_employee_submissions(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubmissionListResponse:
    try:
        employee = AccessScopeService(db).ensure_employee_access(current_user, employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found.')
    items = SubmissionService(db).list_employee_submissions(employee_id)
    return SubmissionListResponse(items=[SubmissionRead.model_validate(item) for item in items], total=len(items))
