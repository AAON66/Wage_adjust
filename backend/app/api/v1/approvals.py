from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.approval import (
    ApprovalCandidateListResponse,
    ApprovalCandidateRead,
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalRecordRead,
    ApprovalRouteUpdateRequest,
    ApprovalStatusResponse,
    ApprovalSubmitRequest,
    CalibrationQueueItem,
    CalibrationQueueResponse,
)
from backend.app.schemas.evaluation import DimensionScoreRead
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.approval_service import ApprovalService

router = APIRouter(prefix='/approvals', tags=['approvals'])


def serialize_approval_with_service(record, service: ApprovalService) -> ApprovalRecordRead:
    recommendation = record.recommendation
    evaluation = recommendation.evaluation
    submission = evaluation.submission
    employee = submission.employee
    cycle = submission.cycle
    dimension_scores = [
        DimensionScoreRead.model_validate(ds)
        for ds in (evaluation.dimension_scores or [])
    ]
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
        step_order=record.step_order,
        is_current_step=service._is_current_step(record),
        decision=record.decision,
        comment=record.comment,
        decided_at=record.decided_at,
        created_at=record.created_at,
        defer_until=recommendation.defer_until,
        defer_target_score=recommendation.defer_target_score,
        defer_reason=recommendation.defer_reason,
        dimension_scores=dimension_scores,
    )


def serialize_candidate(recommendation, service: ApprovalService, current_user: User) -> ApprovalCandidateRead:
    evaluation = recommendation.evaluation
    submission = evaluation.submission
    employee = submission.employee
    cycle = submission.cycle
    route_preview: list[str] = []
    route_error: str | None = None
    can_edit_route, route_edit_error = service.can_edit_route(recommendation)
    try:
        if recommendation.approval_records:
            ordered_records = service._ordered_records(recommendation)
            route_preview = [
                f"{record.step_order}. {record.step_name} -> {record.approver.email if record.approver else record.approver_id}"
                for record in ordered_records
            ]
        else:
            steps = service.build_default_steps(recommendation=recommendation, initiator=current_user)
            approver_cache = {
                step['approver_id']: service.db.get(User, step['approver_id'])
                for step in steps
            }
            route_preview = [
                f"{index}. {step['step_name']} -> {approver_cache[step['approver_id']].email if approver_cache[step['approver_id']] else step['approver_id']}"
                for index, step in enumerate(steps, start=1)
            ]
    except ValueError as exc:
        route_error = str(exc)
    return ApprovalCandidateRead(
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
        route_preview=route_preview,
        route_error=route_error,
        can_edit_route=can_edit_route,
        route_edit_error=route_edit_error,
        defer_until=recommendation.defer_until,
        defer_target_score=recommendation.defer_target_score,
        defer_reason=recommendation.defer_reason,
    )


def ensure_recommendation_access(db: Session, current_user: User, recommendation_id: str) -> None:
    try:
        recommendation = AccessScopeService(db).ensure_recommendation_access(current_user, recommendation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')


def ensure_approval_access(db: Session, current_user: User, approval_id: str) -> None:
    try:
        approval = AccessScopeService(db).ensure_approval_access(current_user, approval_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Approval record not found.')


@router.get('', response_model=ApprovalListResponse)
def list_approvals(
    include_all: bool = Query(default=False),
    decision: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalListResponse:
    service = ApprovalService(db)
    items = service.list_approvals(current_user=current_user, include_all=include_all, decision=decision)
    return ApprovalListResponse(items=[serialize_approval_with_service(item, service) for item in items], total=len(items))


@router.get('/submission-candidates', response_model=ApprovalCandidateListResponse)
def list_submission_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ApprovalCandidateListResponse:
    service = ApprovalService(db)
    items = service.list_submission_candidates(current_user=current_user)
    return ApprovalCandidateListResponse(
        items=[serialize_candidate(item, service, current_user) for item in items],
        total=len(items),
    )


@router.post('/submit', response_model=ApprovalListResponse, status_code=status.HTTP_201_CREATED)
def submit_for_approval(
    payload: ApprovalSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ApprovalListResponse:
    ensure_recommendation_access(db, current_user, payload.recommendation_id)
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
    items = service.list_history(recommendation.id, current_user=current_user)
    return ApprovalListResponse(items=[serialize_approval_with_service(item, service) for item in items], total=len(items))


@router.post('/submit-default/{recommendation_id}', response_model=ApprovalListResponse, status_code=status.HTTP_201_CREATED)
def submit_default_for_approval(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ApprovalListResponse:
    ensure_recommendation_access(db, current_user, recommendation_id)
    service = ApprovalService(db)
    try:
        recommendation = service.submit_default_approval(recommendation_id=recommendation_id, current_user=current_user)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    items = service.list_history(recommendation.id, current_user=current_user)
    return ApprovalListResponse(items=[serialize_approval_with_service(item, service) for item in items], total=len(items))


@router.put('/recommendations/{recommendation_id}', response_model=ApprovalListResponse)
def update_approval_route(
    recommendation_id: str,
    payload: ApprovalRouteUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> ApprovalListResponse:
    ensure_recommendation_access(db, current_user, recommendation_id)
    service = ApprovalService(db)
    try:
        recommendation = service.update_approval_route(
            recommendation_id=recommendation_id,
            steps=[step.model_dump() for step in payload.steps],
        )
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    items = service.list_history(recommendation.id, current_user=current_user)
    return ApprovalListResponse(items=[serialize_approval_with_service(item, service) for item in items], total=len(items))


@router.patch('/{approval_id}', response_model=ApprovalStatusResponse)
def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalStatusResponse:
    ensure_approval_access(db, current_user, approval_id)
    service = ApprovalService(db)
    try:
        approval = service.decide_approval(
            approval_id,
            current_user=current_user,
            decision=payload.decision,
            comment=payload.comment,
            defer_until=payload.defer_until,
            defer_target_score=payload.defer_target_score,
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
        defer_until=approval.recommendation.defer_until,
        defer_target_score=approval.recommendation.defer_target_score,
        defer_reason=approval.recommendation.defer_reason,
    )


@router.get('/recommendations/{recommendation_id}/history', response_model=ApprovalListResponse)
def get_approval_history(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalListResponse:
    ensure_recommendation_access(db, current_user, recommendation_id)
    service = ApprovalService(db)
    items = service.list_history(recommendation_id, current_user=current_user)
    return ApprovalListResponse(items=[serialize_approval_with_service(item, service) for item in items], total=len(items))


@router.get('/calibration-queue', response_model=CalibrationQueueResponse)
def get_calibration_queue(
    include_completed: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> CalibrationQueueResponse:
    service = ApprovalService(db)
    evaluations = service.list_calibration_queue(current_user=current_user, include_completed=include_completed)
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

