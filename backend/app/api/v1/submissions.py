from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db
from backend.app.schemas.submission import SubmissionEnsureRequest, SubmissionListResponse, SubmissionRead
from backend.app.services.submission_service import SubmissionService

router = APIRouter(prefix='/submissions', tags=['submissions'])


@router.post('/ensure', response_model=SubmissionRead)
def ensure_submission(
    payload: SubmissionEnsureRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SubmissionRead:
    submission = SubmissionService(db).ensure_submission(employee_id=payload.employee_id, cycle_id=payload.cycle_id)
    return SubmissionRead.model_validate(submission)


@router.get('/employee/{employee_id}', response_model=SubmissionListResponse)
def list_employee_submissions(
    employee_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SubmissionListResponse:
    items = SubmissionService(db).list_employee_submissions(employee_id)
    return SubmissionListResponse(items=[SubmissionRead.model_validate(item) for item in items], total=len(items))