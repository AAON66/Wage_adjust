from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, get_current_user, require_roles
from backend.app.schemas.evaluation import (
    EvaluationConfirmResponse,
    EvaluationGenerateRequest,
    EvaluationHrReviewRequest,
    EvaluationManualReviewRequest,
    EvaluationRead,
)
from backend.app.services.evaluation_service import EvaluationService

router = APIRouter(prefix='/evaluations', tags=['evaluations'])


def serialize_evaluation(evaluation) -> EvaluationRead:
    return EvaluationRead(
        id=evaluation.id,
        submission_id=evaluation.submission_id,
        overall_score=evaluation.overall_score,
        ai_overall_score=evaluation.ai_overall_score,
        manager_score=evaluation.manager_score,
        score_gap=evaluation.score_gap,
        ai_level=evaluation.ai_level,
        confidence_score=evaluation.confidence_score,
        explanation=evaluation.explanation,
        manager_comment=evaluation.manager_comment,
        hr_comment=evaluation.hr_comment,
        hr_decision=evaluation.hr_decision,
        status=evaluation.status,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
        needs_manual_review=evaluation.status in {'pending_hr', 'returned'},
        dimension_scores=evaluation.dimension_scores,
    )


@router.post('/generate', response_model=EvaluationRead, status_code=status.HTTP_201_CREATED)
def generate_evaluation(
    payload: EvaluationGenerateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationRead:
    service = EvaluationService(db)
    try:
        evaluation = service.generate_evaluation(payload.submission_id)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    return serialize_evaluation(evaluation)


@router.post('/regenerate', response_model=EvaluationRead)
def regenerate_evaluation(
    payload: EvaluationGenerateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationRead:
    service = EvaluationService(db)
    try:
        evaluation = service.generate_evaluation(payload.submission_id, force=True)
    except ValueError as exc:
        message = str(exc)
        if 'not found' in message.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    return serialize_evaluation(evaluation)


@router.get('/by-submission/{submission_id}', response_model=EvaluationRead)
def get_evaluation_by_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationRead:
    service = EvaluationService(db)
    evaluation = service.get_evaluation_by_submission(submission_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return serialize_evaluation(evaluation)


@router.get('/{evaluation_id}', response_model=EvaluationRead)
def get_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationRead:
    service = EvaluationService(db)
    evaluation = service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return serialize_evaluation(evaluation)


@router.patch('/{evaluation_id}/manual-review', response_model=EvaluationRead)
def manual_review_evaluation(
    evaluation_id: str,
    payload: EvaluationManualReviewRequest,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationRead:
    service = EvaluationService(db)
    try:
        evaluation = service.manual_review(
            evaluation_id,
            ai_level=payload.ai_level,
            overall_score=payload.overall_score,
            explanation=payload.explanation,
            dimension_updates=[item.model_dump() for item in payload.dimension_scores],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return serialize_evaluation(evaluation)


@router.patch('/{evaluation_id}/hr-review', response_model=EvaluationRead)
def hr_review_evaluation(
    evaluation_id: str,
    payload: EvaluationHrReviewRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles('admin', 'hrbp')),
) -> EvaluationRead:
    service = EvaluationService(db)
    try:
        evaluation = service.hr_review(
            evaluation_id,
            decision=payload.decision,
            comment=payload.comment,
            final_score=payload.final_score,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if 'not found' in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return serialize_evaluation(evaluation)


@router.post('/{evaluation_id}/confirm', response_model=EvaluationConfirmResponse)
def confirm_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
) -> EvaluationConfirmResponse:
    service = EvaluationService(db)
    evaluation = service.confirm_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return EvaluationConfirmResponse(id=evaluation.id, status=evaluation.status)
