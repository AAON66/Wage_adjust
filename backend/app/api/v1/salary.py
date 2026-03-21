from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db
from backend.app.schemas.salary import (
    SalaryLockResponse,
    SalaryRecommendationRead,
    SalaryRecommendationUpdateRequest,
    SalaryRecommendRequest,
    SalarySimulationItem,
    SalarySimulationRequest,
    SalarySimulationResponse,
)
from backend.app.services.salary_service import SalaryService

router = APIRouter(prefix='/salary', tags=['salary'])


def serialize_recommendation(recommendation) -> SalaryRecommendationRead:
    return SalaryRecommendationRead(
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


@router.post('/recommend', response_model=SalaryRecommendationRead, status_code=status.HTTP_201_CREATED)
def recommend_salary(
    payload: SalaryRecommendRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SalaryRecommendationRead:
    service = SalaryService(db)
    try:
        recommendation = service.recommend_salary(payload.evaluation_id)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    return serialize_recommendation(recommendation)


@router.get('/by-evaluation/{evaluation_id}', response_model=SalaryRecommendationRead)
def get_recommendation_by_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SalaryRecommendationRead:
    service = SalaryService(db)
    recommendation = service.get_recommendation_by_evaluation(evaluation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return serialize_recommendation(recommendation)


@router.get('/{recommendation_id}', response_model=SalaryRecommendationRead)
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SalaryRecommendationRead:
    service = SalaryService(db)
    recommendation = service.get_recommendation(recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return serialize_recommendation(recommendation)


@router.post('/simulate', response_model=SalarySimulationResponse)
def simulate_salary(
    payload: SalarySimulationRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SalarySimulationResponse:
    service = SalaryService(db)
    items, budget_amount, total_recommended_amount, over_budget = service.simulate_cycle(
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


@router.patch('/{recommendation_id}', response_model=SalaryRecommendationRead)
def update_recommendation(
    recommendation_id: str,
    payload: SalaryRecommendationUpdateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> SalaryRecommendationRead:
    service = SalaryService(db)
    recommendation = service.update_recommendation(
        recommendation_id,
        final_adjustment_ratio=payload.final_adjustment_ratio,
        status=payload.status,
    )
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return serialize_recommendation(recommendation)


@router.post('/{recommendation_id}/lock', response_model=SalaryLockResponse)
def lock_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SalaryLockResponse:
    service = SalaryService(db)
    recommendation = service.lock_recommendation(recommendation_id, current_user)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Salary recommendation not found.')
    return SalaryLockResponse(id=recommendation.id, status=recommendation.status)
