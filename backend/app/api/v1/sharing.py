from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.models.user import User
from backend.app.schemas.sharing import (
    SharingRequestApproveRequest,
    SharingRequestListResponse,
    SharingRequestRead,
)
from backend.app.services.sharing_service import SharingService

router = APIRouter(tags=['sharing'])


def _enrich_sharing_request(db: Session, sr) -> SharingRequestRead:
    """Populate denormalized display fields for UI."""
    req_file = db.get(UploadedFile, sr.requester_file_id) if sr.requester_file_id else None
    orig_file = db.get(UploadedFile, sr.original_file_id)
    req_sub = db.get(EmployeeSubmission, sr.requester_submission_id)
    orig_sub = db.get(EmployeeSubmission, sr.original_submission_id)
    base = {c.name: getattr(sr, c.name) for c in sr.__table__.columns}
    # Determine if the original submission's cycle is archived (下架)
    cycle_archived = False
    if orig_sub is not None and orig_sub.cycle_id:
        cycle = db.get(EvaluationCycle, orig_sub.cycle_id)
        if cycle is not None and cycle.status == 'archived':
            cycle_archived = True
    return SharingRequestRead(
        **base,
        requester_name=(req_sub.employee.name if req_sub and req_sub.employee else ''),
        file_name=(
            orig_file.file_name
            if orig_file
            else (sr.requester_file_name_snapshot or (req_file.file_name if req_file else ''))
        ),
        original_uploader_name=(orig_sub.employee.name if orig_sub and orig_sub.employee else ''),
        cycle_archived=cycle_archived,
    )


@router.get('/sharing-requests', response_model=SharingRequestListResponse)
def list_sharing_requests(
    direction: str = Query(default='incoming', pattern='^(incoming|outgoing)$'),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingRequestListResponse:
    employee_id = current_user.employee_id
    if not employee_id:
        return SharingRequestListResponse(items=[], total=0)
    svc = SharingService(db)
    items = svc.list_requests(employee_id=employee_id, direction=direction)
    db.commit()  # persist any lazy-expiry updates
    result = [_enrich_sharing_request(db, sr) for sr in items]
    return SharingRequestListResponse(items=result, total=len(result))


@router.get('/sharing-requests/pending-count')
def get_pending_sharing_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    employee_id = current_user.employee_id
    if not employee_id:
        return {'count': 0}
    count = SharingService(db).get_pending_count(employee_id=employee_id)
    db.commit()
    return {'count': count}


@router.post('/sharing-requests/{request_id}/approve', response_model=SharingRequestRead)
def approve_sharing_request(
    request_id: str,
    payload: SharingRequestApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingRequestRead:
    employee_id = current_user.employee_id
    if not employee_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User not bound to employee')
    try:
        sr = SharingService(db).approve_request(
            request_id,
            approver_employee_id=employee_id,
            final_pct=payload.final_pct,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    db.commit()
    return _enrich_sharing_request(db, sr)


@router.post('/sharing-requests/{request_id}/reject', response_model=SharingRequestRead)
def reject_sharing_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingRequestRead:
    employee_id = current_user.employee_id
    if not employee_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User not bound to employee')
    try:
        sr = SharingService(db).reject_request(request_id, rejector_employee_id=employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    db.commit()
    return _enrich_sharing_request(db, sr)


@router.post('/sharing-requests/{request_id}/revoke-rejection', response_model=SharingRequestRead)
def revoke_sharing_rejection(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingRequestRead:
    """Compat route kept only to reject the deprecated revoke action."""
    employee_id = current_user.employee_id
    if not employee_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User not bound to employee')
    try:
        sr = SharingService(db).revoke_rejection(request_id, revoker_employee_id=employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    db.commit()
    return _enrich_sharing_request(db, sr)


@router.post('/sharing-requests/{request_id}/revoke', response_model=SharingRequestRead)
def revoke_sharing_approval(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SharingRequestRead:
    """Revoke a previously approved sharing request. Restores status to pending,
    removes contributor record, and restores owner_contribution_pct."""
    employee_id = current_user.employee_id
    if not employee_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='User not bound to employee')
    try:
        sr = SharingService(db).revoke_approval(request_id, revoker_employee_id=employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    db.commit()
    return _enrich_sharing_request(db, sr)
