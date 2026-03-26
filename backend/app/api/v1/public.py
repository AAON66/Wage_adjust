from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings as _get_settings
from backend.app.core.rate_limit import limiter
from backend.app.dependencies import get_app_settings, get_db
from backend.app.schemas.public import (
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

_RATE_LIMIT = _get_settings().public_api_rate_limit


def require_public_api_key(
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    settings: Settings = Depends(get_app_settings),
) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='X-API-Key header is required.')
    if x_api_key != settings.public_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid public API key.')
    return x_api_key


@router.get('/employees/{employee_no}/latest-evaluation', response_model=PublicLatestEvaluationResponse)
@limiter.limit(_RATE_LIMIT)
def get_latest_employee_evaluation(
    request: Request,
    employee_no: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_public_api_key),
) -> PublicLatestEvaluationResponse:
    service = IntegrationService(db)
    submission = service.get_latest_employee_evaluation(employee_no)
    if submission is None or submission.ai_evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Latest evaluation not found.')
    evaluation = submission.ai_evaluation
    recommendation = evaluation.salary_recommendation
    service.log_public_access(
        action='public.latest_evaluation.read',
        target_type='employee',
        target_id=submission.employee.id,
        detail={'employee_no': employee_no, 'submission_id': submission.id},
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


@router.get('/cycles/{cycle_id}/salary-results', response_model=PublicSalaryResultsResponse)
@limiter.limit(_RATE_LIMIT)
def get_cycle_salary_results(
    request: Request,
    cycle_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_public_api_key),
) -> PublicSalaryResultsResponse:
    service = IntegrationService(db)
    cycle, submissions = service.get_cycle_salary_results(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Cycle not found.')
    service.log_public_access(
        action='public.salary_results.read',
        target_type='cycle',
        target_id=cycle_id,
        detail={'submission_count': len(submissions)},
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
    return PublicSalaryResultsResponse(
        cycle_id=cycle.id,
        cycle_name=cycle.name,
        cycle_status=cycle.status,
        items=items,
        total=len(items),
    )


@router.get('/cycles/{cycle_id}/approval-status', response_model=PublicApprovalStatusResponse)
@limiter.limit(_RATE_LIMIT)
def get_cycle_approval_status(
    request: Request,
    cycle_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_public_api_key),
) -> PublicApprovalStatusResponse:
    service = IntegrationService(db)
    cycle, submissions = service.get_cycle_approval_status(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Cycle not found.')
    service.log_public_access(
        action='public.approval_status.read',
        target_type='cycle',
        target_id=cycle_id,
        detail={'submission_count': len(submissions)},
    )
    items = []
    for submission in submissions:
        evaluation = submission.ai_evaluation
        recommendation = evaluation.salary_recommendation if evaluation is not None else None
        if recommendation is None:
            continue
        decisions = [record.decision for record in recommendation.approval_records]
        latest_decision_at = max((record.decided_at for record in recommendation.approval_records if record.decided_at is not None), default=None)
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
    return PublicApprovalStatusResponse(
        cycle_id=cycle.id,
        cycle_name=cycle.name,
        cycle_status=cycle.status,
        items=items,
        total=len(items),
    )


@router.get('/dashboard/summary', response_model=PublicDashboardSummaryResponse)
@limiter.limit(_RATE_LIMIT)
def get_public_dashboard_summary(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(require_public_api_key),
) -> PublicDashboardSummaryResponse:
    service = IntegrationService(db)
    summary = service.get_dashboard_summary()
    service.log_public_access(
        action='public.dashboard_summary.read',
        target_type='dashboard',
        target_id='summary',
        detail={'overview_count': len(summary['overview'])},
    )
    return PublicDashboardSummaryResponse(**summary)
