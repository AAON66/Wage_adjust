from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.dependencies import get_app_settings
from backend.app.models.user import User
from backend.app.schemas.salary import (
    SalaryHistoryItemRead,
    SalaryHistoryResponse,
    SalaryLockResponse,
    SalaryRecommendationAdminRead,
    SalaryRecommendationEmployeeRead,
    SalaryRecommendationRead,
    SalaryRecommendationUpdateRequest,
    SalaryRecommendRequest,
    SalarySimulationItem,
    SalarySimulationRequest,
    SalarySimulationResponse,
)
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.salary_service import SalaryService

router = APIRouter(prefix='/salary', tags=['salary'])


def shape_recommendation_for_role(
    recommendation,
    role: str,
) -> SalaryRecommendationAdminRead | SalaryRecommendationEmployeeRead:
    """Return role-appropriate salary recommendation response per D-13.

    admin, hrbp -> full figures (SalaryRecommendationAdminRead)
    manager, employee -> adjustment percentage only (SalaryRecommendationEmployeeRead)
    """
    if role in ('admin', 'hrbp'):
        return SalaryRecommendationAdminRead(
            id=recommendation.id,
            evaluation_id=recommendation.evaluation_id,
            current_salary=recommendation.current_salary,
            recommended_ratio=recommendation.recommended_ratio,
            recommended_salary=recommendation.recommended_salary,
            ai_multiplier=recommendation.ai_multiplier,
            certification_bonus=recommendation.certification_bonus,
            final_adjustment_ratio=recommendation.final_adjustment_ratio,
            status=recommendation.status,
            created_at=recommendation.created_at,
            explanation=getattr(recommendation, 'explanation', None),
        )
    return SalaryRecommendationEmployeeRead(
        id=recommendation.id,
        evaluation_id=recommendation.evaluation_id,
        final_adjustment_ratio=recommendation.final_adjustment_ratio,
        status=recommendation.status,
        created_at=recommendation.created_at,
        explanation=getattr(recommendation, 'explanation', None),
    )


def ensure_evaluation_access(db: Session, current_user: User, evaluation_id: str) -> None:
    try:
        evaluation = AccessScopeService(db).ensure_evaluation_access(current_user, evaluation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')


def ensure_recommendation_access(db: Session, current_user: User, recommendation_id: str):
    try:
        recommendation = AccessScopeService(db).ensure_recommendation_access(current_user, recommendation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return recommendation


def ensure_employee_access(db: Session, current_user: User, employee_id: str) -> None:
    try:
        employee = AccessScopeService(db).ensure_employee_access(current_user, employee_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Employee not found.')


@router.post('/recommend', status_code=status.HTTP_201_CREATED)
def recommend_salary(
    payload: SalaryRecommendRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> SalaryRecommendationAdminRead | SalaryRecommendationEmployeeRead:
    ensure_evaluation_access(db, current_user, payload.evaluation_id)
    service = SalaryService(db, settings)
    try:
        recommendation = service.recommend_salary(payload.evaluation_id)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    return shape_recommendation_for_role(recommendation, current_user.role)


@router.get('/by-evaluation/{evaluation_id}')
def get_recommendation_by_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> SalaryRecommendationAdminRead | SalaryRecommendationEmployeeRead:
    ensure_evaluation_access(db, current_user, evaluation_id)
    service = SalaryService(db, settings)
    recommendation = service.get_recommendation_by_evaluation(evaluation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return shape_recommendation_for_role(recommendation, current_user.role)


@router.get('/{recommendation_id}')
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> SalaryRecommendationAdminRead | SalaryRecommendationEmployeeRead:
    ensure_recommendation_access(db, current_user, recommendation_id)
    service = SalaryService(db, settings)
    recommendation = service.get_recommendation(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return shape_recommendation_for_role(recommendation, current_user.role)


@router.get('/history/by-employee/{employee_id}', response_model=SalaryHistoryResponse)
def get_salary_history_by_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> SalaryHistoryResponse:
    ensure_employee_access(db, current_user, employee_id)
    service = SalaryService(db, settings)
    items = service.get_salary_history_by_employee(employee_id)
    return SalaryHistoryResponse(items=[SalaryHistoryItemRead(**item) for item in items], total=len(items))


@router.post('/simulate', response_model=SalarySimulationResponse)
def simulate_salary(
    payload: SalarySimulationRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> SalarySimulationResponse:
    if current_user.role in {'hrbp', 'manager'} and payload.department:
        allowed_departments = {department.name for department in current_user.departments}
        if payload.department not in allowed_departments:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You do not have access to this department.')
    service = SalaryService(db, settings)
    items, budget_amount, total_recommended_amount, over_budget = service.simulate_cycle(
        current_user=current_user,
        cycle_id=payload.cycle_id,
        department=payload.department,
        job_family=payload.job_family,
        budget_amount=payload.budget_amount,
    )
    return SalarySimulationResponse(
        cycle_id=payload.cycle_id,
        budget_amount=budget_amount,
        total_recommended_amount=total_recommended_amount,
        over_budget=over_budget,
        items=[SalarySimulationItem(**item) for item in items],
    )


@router.patch('/{recommendation_id}')
def update_recommendation(
    recommendation_id: str,
    payload: SalaryRecommendationUpdateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> SalaryRecommendationAdminRead | SalaryRecommendationEmployeeRead:
    ensure_recommendation_access(db, current_user, recommendation_id)
    service = SalaryService(db, settings)
    recommendation = service.update_recommendation(
        recommendation_id,
        final_adjustment_ratio=payload.final_adjustment_ratio,
        status=payload.status,
        operator=current_user,
    )
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return shape_recommendation_for_role(recommendation, current_user.role)


@router.post('/{recommendation_id}/lock', response_model=SalaryLockResponse)
def lock_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> SalaryLockResponse:
    ensure_recommendation_access(db, current_user, recommendation_id)
    service = SalaryService(db, settings)
    recommendation = service.lock_recommendation(recommendation_id, current_user)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return SalaryLockResponse(id=recommendation.id, status=recommendation.status)
