from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.dependencies import get_db, get_current_user, require_roles
from backend.app.dependencies import get_app_settings
from backend.app.models.user import User
from backend.app.schemas.evaluation import (
    EvaluationConfirmResponse,
    EvaluationGenerateRequest,
    EvaluationHrReviewRequest,
    EvaluationManualReviewRequest,
    EvaluationRead,
)
from backend.app.services.evaluation_service import EvaluationService
from backend.app.services.access_scope_service import AccessScopeService

router = APIRouter(prefix='/evaluations', tags=['evaluations'])


def _build_integrity_summary(evaluation) -> tuple[bool, int, list[str]]:
    submission = evaluation.submission
    if submission is None:
        return False, 0, []

    examples: list[str] = []
    issue_count = 0
    for evidence in submission.evidence_items:
        metadata = evidence.metadata_json if isinstance(evidence.metadata_json, dict) else {}
        if metadata.get('prompt_manipulation_detected'):
            issue_count += 1
            blocked_examples = metadata.get('blocked_instruction_examples') or []
            if isinstance(blocked_examples, list):
                for item in blocked_examples:
                    text = str(item).strip()
                    if text and text not in examples:
                        examples.append(text)
    return issue_count > 0, issue_count, examples[:3]


def serialize_evaluation(evaluation) -> EvaluationRead:
    integrity_flagged, integrity_issue_count, integrity_examples = _build_integrity_summary(evaluation)
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
        integrity_flagged=integrity_flagged,
        integrity_issue_count=integrity_issue_count,
        integrity_examples=integrity_examples,
        dimension_scores=evaluation.dimension_scores,
    )


@router.post('/generate', response_model=EvaluationRead, status_code=status.HTTP_201_CREATED)
def generate_evaluation(
    payload: EvaluationGenerateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> EvaluationRead:
    try:
        submission = AccessScopeService(db).ensure_submission_access(current_user, payload.submission_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found.')
    service = EvaluationService(db, settings)
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
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> EvaluationRead:
    try:
        submission = AccessScopeService(db).ensure_submission_access(current_user, payload.submission_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found.')
    service = EvaluationService(db, settings)
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
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> EvaluationRead:
    try:
        evaluation = AccessScopeService(db).ensure_evaluation_access_by_submission(current_user, submission_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    service = EvaluationService(db, settings)
    evaluation = service.get_evaluation_by_submission(submission_id)
    return serialize_evaluation(evaluation)


@router.get('/{evaluation_id}', response_model=EvaluationRead)
def get_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> EvaluationRead:
    try:
        scoped_evaluation = AccessScopeService(db).ensure_evaluation_access(current_user, evaluation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if scoped_evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    service = EvaluationService(db, settings)
    evaluation = service.get_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return serialize_evaluation(evaluation)


@router.patch('/{evaluation_id}/manual-review', response_model=EvaluationRead)
def manual_review_evaluation(
    evaluation_id: str,
    payload: EvaluationManualReviewRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> EvaluationRead:
    try:
        scoped_evaluation = AccessScopeService(db).ensure_evaluation_access(current_user, evaluation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if scoped_evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    service = EvaluationService(db, settings)
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
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> EvaluationRead:
    try:
        scoped_evaluation = AccessScopeService(db).ensure_evaluation_access(current_user, evaluation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if scoped_evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    service = EvaluationService(db, settings)
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
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> EvaluationConfirmResponse:
    try:
        scoped_evaluation = AccessScopeService(db).ensure_evaluation_access(current_user, evaluation_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if scoped_evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    service = EvaluationService(db, settings)
    evaluation = service.confirm_evaluation(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found.')
    return EvaluationConfirmResponse(id=evaluation.id, status=evaluation.status)
