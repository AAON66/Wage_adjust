from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.core.rate_limit import get_api_key_identifier, limiter
from backend.app.dependencies import get_db, require_public_api_key
from backend.app.models.api_key import ApiKey
from backend.app.schemas.public import (
    PaginatedSalaryResultsResponse,
    PublicApprovalStatusItem,
    PublicApprovalStatusResponse,
    PublicDashboardSummaryResponse,
    PublicDimensionScoreRead,
    PublicLatestEvaluationResponse,
    PublicSalaryRecommendationRead,
    PublicSalaryResultItem,
    PublicSalaryResultsResponse,
)
from backend.app.services.integration_service import IntegrationService

router = APIRouter(prefix='/public', tags=['public'])

_ERROR_RESPONSES = {
    401: {
        'description': 'Missing or invalid API key',
        'content': {'application/json': {'example': {'detail': 'X-API-Key header is required.'}}},
    },
    403: {
        'description': 'Forbidden',
        'content': {'application/json': {'example': {'detail': 'Insufficient permissions.'}}},
    },
    404: {
        'description': 'Resource not found',
        'content': {'application/json': {'example': {'detail': 'Resource not found.'}}},
    },
    429: {
        'description': 'Rate limit exceeded',
        'content': {'application/json': {'example': {'detail': 'Rate limit exceeded.'}}},
    },
}


def _audit_detail(api_key: ApiKey, request: Request, extra: dict | None = None, *, duration_ms: float | None = None) -> dict:
    """Build audit log detail dict with key_id, key_name, IP, path, duration (per D-15)."""
    detail: dict = {
        'key_id': api_key.id,
        'key_name': api_key.name,
        'client_ip': request.client.host if request.client else None,
        'path': str(request.url.path),
    }
    if duration_ms is not None:
        detail['duration_ms'] = round(duration_ms, 2)
    if extra:
        detail.update(extra)
    return detail


@router.get(
    '/employees/{employee_no}/latest-evaluation',
    response_model=PublicLatestEvaluationResponse,
    responses={k: _ERROR_RESPONSES[k] for k in (401, 404, 429)},
    summary='Get Latest Employee Evaluation',
    description='Retrieve the most recent AI evaluation for an employee by employee number.',
)
@limiter.limit(lambda: '1000/hour', key_func=get_api_key_identifier)
def get_latest_employee_evaluation(
    request: Request,
    employee_no: str,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(require_public_api_key),
) -> PublicLatestEvaluationResponse:
    start = time.monotonic()
    request.state.api_key = api_key

    service = IntegrationService(db)
    submission = service.get_latest_employee_evaluation(employee_no)
    if submission is None or submission.ai_evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Latest evaluation not found.')
    evaluation = submission.ai_evaluation
    recommendation = evaluation.salary_recommendation

    duration_ms = (time.monotonic() - start) * 1000
    service.log_public_access(
        action='public.latest_evaluation.read',
        target_type='employee',
        target_id=submission.employee.id,
        detail=_audit_detail(api_key, request, {'employee_no': employee_no, 'submission_id': submission.id}, duration_ms=duration_ms),
    )
    return PublicLatestEvaluationResponse(
        employee_id=submission.employee.id,
        employee_no=submission.employee.employee_no,
        employee_name=submission.employee.name,
        department=submission.employee.department,
        job_family=submission.employee.job_family,
        job_level=submission.employee.job_level,
        cycle_id=submission.cycle.id,
        cycle_name=submission.cycle.name,
        cycle_status=submission.cycle.status,
        submission_id=submission.id,
        evaluation_id=evaluation.id,
        evaluation_status=evaluation.status,
        ai_level=evaluation.ai_level,
        overall_score=evaluation.overall_score,
        confidence_score=evaluation.confidence_score,
        explanation=evaluation.explanation,
        evaluated_at=evaluation.updated_at,
        dimension_scores=[
            PublicDimensionScoreRead(
                dimension_code=item.dimension_code,
                display_score=item.raw_score,
                raw_score=item.raw_score,
                weighted_contribution=item.weighted_score,
                weighted_score=item.weighted_score,
                rationale=item.rationale,
            )
            for item in evaluation.dimension_scores
        ],
        salary_recommendation=(
            PublicSalaryRecommendationRead(
                recommendation_id=recommendation.id,
                status=recommendation.status,
                current_salary=str(recommendation.current_salary),
                recommended_salary=str(recommendation.recommended_salary),
                final_adjustment_ratio=recommendation.final_adjustment_ratio,
            )
            if recommendation is not None
            else None
        ),
    )


@router.get(
    '/cycles/{cycle_id}/salary-results',
    response_model=PaginatedSalaryResultsResponse,
    responses={k: _ERROR_RESPONSES[k] for k in (401, 404, 429)},
    summary='Get Cycle Salary Results (Paginated)',
    description='Retrieve approved salary results for a cycle with cursor-based pagination (per D-05, D-07, API-01, API-02).',
)
@limiter.limit(lambda: '1000/hour', key_func=get_api_key_identifier)
def get_cycle_salary_results(
    request: Request,
    cycle_id: str,
    cursor: str | None = Query(None, description='Pagination cursor from previous response'),
    page_size: int = Query(20, ge=1, le=100, description='Items per page (max 100)'),
    department: str | None = Query(None, description='Filter by department'),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(require_public_api_key),
) -> PaginatedSalaryResultsResponse:
    start = time.monotonic()
    request.state.api_key = api_key

    service = IntegrationService(db)

    # Verify cycle exists
    from backend.app.models.evaluation_cycle import EvaluationCycle
    cycle = db.get(EvaluationCycle, cycle_id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Cycle not found.')

    submissions, next_cursor, has_more = service.get_approved_salary_results_paginated(
        cycle_id=cycle_id,
        department=department,
        cursor=cursor,
        page_size=page_size,
    )

    items = []
    for submission in submissions:
        evaluation = submission.ai_evaluation
        recommendation = evaluation.salary_recommendation if evaluation is not None else None
        items.append(
            PublicSalaryResultItem(
                employee_id=submission.employee.id,
                employee_no=submission.employee.employee_no,
                employee_name=submission.employee.name,
                department=submission.employee.department,
                job_family=submission.employee.job_family,
                job_level=submission.employee.job_level,
                evaluation_id=evaluation.id,
                ai_level=evaluation.ai_level,
                evaluation_status=evaluation.status,
                recommendation_id=recommendation.id if recommendation is not None else None,
                recommendation_status=recommendation.status if recommendation is not None else None,
                current_salary=str(recommendation.current_salary) if recommendation is not None else None,
                recommended_salary=str(recommendation.recommended_salary) if recommendation is not None else None,
                final_adjustment_ratio=recommendation.final_adjustment_ratio if recommendation is not None else None,
            )
        )

    duration_ms = (time.monotonic() - start) * 1000
    service.log_public_access(
        action='public.salary_results.read',
        target_type='cycle',
        target_id=cycle_id,
        detail=_audit_detail(api_key, request, {'item_count': len(items), 'has_more': has_more, 'department': department}, duration_ms=duration_ms),
    )
    return PaginatedSalaryResultsResponse(
        cycle_id=cycle.id,
        cycle_name=cycle.name,
        cycle_status=cycle.status,
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total=len(items),
    )


@router.get(
    '/cycles/{cycle_id}/approval-status',
    response_model=PublicApprovalStatusResponse,
    responses={k: _ERROR_RESPONSES[k] for k in (401, 404, 429)},
    summary='Get Cycle Approval Status',
    description='Retrieve approval status for all recommendations in a cycle.',
)
@limiter.limit(lambda: '1000/hour', key_func=get_api_key_identifier)
def get_cycle_approval_status(
    request: Request,
    cycle_id: str,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(require_public_api_key),
) -> PublicApprovalStatusResponse:
    start = time.monotonic()
    request.state.api_key = api_key

    service = IntegrationService(db)
    cycle, submissions = service.get_cycle_approval_status(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Cycle not found.')

    items = []
    for submission in submissions:
        evaluation = submission.ai_evaluation
        recommendation = evaluation.salary_recommendation if evaluation is not None else None
        if recommendation is None:
            continue
        decisions = [record.decision for record in recommendation.approval_records]
        latest_decision_at = max(
            (record.decided_at for record in recommendation.approval_records if record.decided_at is not None),
            default=None,
        )
        items.append(
            PublicApprovalStatusItem(
                recommendation_id=recommendation.id,
                employee_no=submission.employee.employee_no,
                employee_name=submission.employee.name,
                recommendation_status=recommendation.status,
                total_steps=len(recommendation.approval_records),
                approved_steps=sum(1 for item in decisions if item == 'approved'),
                pending_steps=sum(1 for item in decisions if item == 'pending'),
                rejected_steps=sum(1 for item in decisions if item == 'rejected'),
                latest_decision_at=latest_decision_at,
            )
        )

    duration_ms = (time.monotonic() - start) * 1000
    service.log_public_access(
        action='public.approval_status.read',
        target_type='cycle',
        target_id=cycle_id,
        detail=_audit_detail(api_key, request, {'item_count': len(items)}, duration_ms=duration_ms),
    )
    return PublicApprovalStatusResponse(
        cycle_id=cycle.id,
        cycle_name=cycle.name,
        cycle_status=cycle.status,
        items=items,
        total=len(items),
    )


@router.get(
    '/dashboard/summary',
    response_model=PublicDashboardSummaryResponse,
    responses={k: _ERROR_RESPONSES[k] for k in (401, 429)},
    summary='Get Dashboard Summary',
    description='Retrieve aggregated dashboard summary data.',
)
@limiter.limit(lambda: '1000/hour', key_func=get_api_key_identifier)
def get_public_dashboard_summary(
    request: Request,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(require_public_api_key),
) -> PublicDashboardSummaryResponse:
    start = time.monotonic()
    request.state.api_key = api_key

    service = IntegrationService(db)
    summary = service.get_dashboard_summary()

    duration_ms = (time.monotonic() - start) * 1000
    service.log_public_access(
        action='public.dashboard_summary.read',
        target_type='dashboard',
        target_id='summary',
        detail=_audit_detail(api_key, request, {'overview_count': len(summary['overview'])}, duration_ms=duration_ms),
    )
    return PublicDashboardSummaryResponse(**summary)
