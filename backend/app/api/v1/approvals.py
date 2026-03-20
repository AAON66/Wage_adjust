from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalRecordRead,
    ApprovalStatusResponse,
    ApprovalSubmitRequest,
    CalibrationQueueItem,
    CalibrationQueueResponse,
)
from backend.app.services.approval_service import ApprovalService

router = APIRouter(prefix='/approvals', tags=['approvals'])


def serialize_approval(record) -> ApprovalRecordRead:
    recommendation = record.recommendation
    evaluation = recommendation.evaluation
    submission = evaluation.submission
    employee = submission.employee
    cycle = submission.cycle
    return ApprovalRecordRead(
        id=record.id,
        recommendation_id=recommendation.id,
        evaluation_id=evaluation.id,
        employee_id=employee.id,
        employee_name=employee.name,
        department=employee.department,
        cycle_id=cycle.id,
        cycle_name=cycle.name,
        ai_level=evaluation.ai_level,
        current_salary=recommendation.current_salary,
        recommended_salary=recommendation.recommended_salary,
        final_adjustment_ratio=recommendation.final_adjustment_ratio,
        recommendation_status=recommendation.status,
        approver_id=record.approver.id,
        approver_email=record.approver.email,
        approver_role=record.approver.role,
        step_name=record.step_name,
        decision=record.decision,
        comment=record.comment,
        decided_at=record.decided_at,
        created_at=record.created_at,
    )


@router.get('', response_model=ApprovalListResponse)
def list_approvals(
    include_all: bool = Query(default=False),
    decision: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ApprovalListResponse:
    service = ApprovalService(db)
    items = service.list_approvals(current_user=current_user, include_all=include_all, decision=decision)
    return ApprovalListResponse(items=[serialize_approval(item) for item in items], total=len(items))


@router.post('/submit', response_model=ApprovalListResponse, status_code=status.HTTP_201_CREATED)
def submit_for_approval(
    payload: ApprovalSubmitRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ApprovalListResponse:
    service = ApprovalService(db)
    try:
        recommendation = service.submit_for_approval(
            recommendation_id=payload.recommendation_id,
            steps=[step.model_dump() for step in payload.steps],
        )
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    items = service.list_history(recommendation.id)
    return ApprovalListResponse(items=[serialize_approval(item) for item in items], total=len(items))


@router.patch('/{approval_id}', response_model=ApprovalStatusResponse)
def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ApprovalStatusResponse:
    service = ApprovalService(db)
    try:
        approval = service.decide_approval(
            approval_id,
            current_user=current_user,
            decision=payload.decision,
            comment=payload.comment,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Approval record not found.')
    return ApprovalStatusResponse(
        approval_id=approval.id,
        recommendation_id=approval.recommendation_id,
        decision=approval.decision,
        recommendation_status=approval.recommendation.status,
    )


@router.get('/recommendations/{recommendation_id}/history', response_model=ApprovalListResponse)
def get_approval_history(
    recommendation_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> ApprovalListResponse:
    service = ApprovalService(db)
    items = service.list_history(recommendation_id)
    return ApprovalListResponse(items=[serialize_approval(item) for item in items], total=len(items))


@router.get('/calibration-queue', response_model=CalibrationQueueResponse)
def get_calibration_queue(
    include_completed: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> CalibrationQueueResponse:
    service = ApprovalService(db)
    evaluations = service.list_calibration_queue(include_completed=include_completed)
    items = [
        CalibrationQueueItem(
            evaluation_id=evaluation.id,
            submission_id=evaluation.submission_id,
            employee_id=evaluation.submission.employee.id,
            employee_name=evaluation.submission.employee.name,
            department=evaluation.submission.employee.department,
            cycle_id=evaluation.submission.cycle.id,
            cycle_name=evaluation.submission.cycle.name,
            ai_level=evaluation.ai_level,
            overall_score=evaluation.overall_score,
            confidence_score=evaluation.confidence_score,
            status=evaluation.status,
            needs_manual_review=evaluation.status == 'needs_review',
            updated_at=evaluation.updated_at,
        )
        for evaluation in evaluations
    ]
    return CalibrationQueueResponse(items=items, total=len(items))

