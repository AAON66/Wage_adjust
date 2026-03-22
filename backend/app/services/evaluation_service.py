from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.engines.evaluation_engine import EvaluationEngine
from backend.app.models.dimension_score import DimensionScore
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.submission import EmployeeSubmission

MANAGER_ALIGNMENT_THRESHOLD = 10.0


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = EvaluationEngine()

    def _query_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(
                selectinload(AIEvaluation.dimension_scores),
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.evidence_items),
            )
            .where(AIEvaluation.id == evaluation_id)
        )
        return self.db.scalar(query)

    def get_evaluation_by_submission(self, submission_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(
                selectinload(AIEvaluation.dimension_scores),
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.evidence_items),
            )
            .where(AIEvaluation.submission_id == submission_id)
        )
        return self.db.scalar(query)

    def get_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        return self._query_evaluation(evaluation_id)

    def generate_evaluation(self, submission_id: str, *, force: bool = False) -> AIEvaluation:
        submission = self.db.get(EmployeeSubmission, submission_id)
        if submission is None:
            raise ValueError('Submission not found.')
        if not submission.evidence_items:
            raise ValueError('Submission evidence is required before evaluation.')

        existing = self.get_evaluation_by_submission(submission_id)
        if existing is not None and not force:
            raise ValueError('Evaluation already exists for submission.')

        result = self.engine.evaluate(list(submission.evidence_items))
        evaluation = existing or AIEvaluation(submission_id=submission_id)
        evaluation.overall_score = result.overall_score
        evaluation.ai_overall_score = result.overall_score
        evaluation.manager_score = None
        evaluation.score_gap = None
        evaluation.ai_level = result.ai_level
        evaluation.confidence_score = result.confidence_score
        evaluation.explanation = f'{result.explanation} 当前等待主管评分。'
        evaluation.manager_comment = None
        evaluation.hr_comment = None
        evaluation.hr_decision = None
        evaluation.status = 'generated'
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)

        if existing is not None:
            for dimension in list(existing.dimension_scores):
                self.db.delete(dimension)
            self.db.commit()

        for dimension in result.dimensions:
            self.db.add(
                DimensionScore(
                    evaluation_id=evaluation.id,
                    dimension_code=dimension.code,
                    weight=dimension.weight,
                    raw_score=dimension.raw_score,
                    weighted_score=dimension.weighted_score,
                    rationale=dimension.rationale,
                )
            )
        submission.status = 'evaluated'
        self.db.add(submission)
        self.db.commit()
        return self.get_evaluation(evaluation.id)  # type: ignore[return-value]

    def manual_review(
        self,
        evaluation_id: str,
        *,
        ai_level: str | None,
        overall_score: float | None,
        explanation: str | None,
        dimension_updates: list[dict[str, object]],
    ) -> AIEvaluation | None:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            return None

        if dimension_updates:
            score_map = {item.dimension_code: item for item in evaluation.dimension_scores}
            for update in dimension_updates:
                dimension = score_map.get(str(update['dimension_code']))
                if dimension is None:
                    continue
                dimension.raw_score = float(update['raw_score'])
                dimension.weighted_score = round(float(update['raw_score']) * dimension.weight, 2)
                dimension.rationale = str(update['rationale'])
                self.db.add(dimension)
            self.db.flush()

        derived_manager_score = overall_score
        if derived_manager_score is None and dimension_updates:
            relevant_scores = [float(update['raw_score']) for update in dimension_updates]
            derived_manager_score = round(sum(relevant_scores) / len(relevant_scores), 2) if relevant_scores else None
        if derived_manager_score is None:
            raise ValueError('Manager score is required for review.')

        evaluation.manager_score = round(float(derived_manager_score), 2)
        evaluation.score_gap = round(abs(evaluation.ai_overall_score - evaluation.manager_score), 2)
        evaluation.manager_comment = explanation

        if evaluation.score_gap <= MANAGER_ALIGNMENT_THRESHOLD:
            final_score = round((evaluation.ai_overall_score + evaluation.manager_score) / 2, 2)
            evaluation.overall_score = final_score
            evaluation.ai_level = ai_level or self.engine.map_level(final_score)
            evaluation.status = 'confirmed'
            evaluation.hr_decision = 'not_required'
            evaluation.explanation = explanation or (
                f'AI 评分 {evaluation.ai_overall_score:.2f}，主管评分 {evaluation.manager_score:.2f}，差值 {evaluation.score_gap:.2f}，'
                f'已按平均分 {final_score:.2f} 确认最终评分。'
            )
        else:
            evaluation.overall_score = round((evaluation.ai_overall_score + evaluation.manager_score) / 2, 2)
            evaluation.status = 'pending_hr'
            evaluation.hr_decision = 'pending'
            evaluation.explanation = explanation or (
                f'AI 评分 {evaluation.ai_overall_score:.2f}，主管评分 {evaluation.manager_score:.2f}，差值 {evaluation.score_gap:.2f}，'
                '已转交 HR 审核。'
            )

        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)

    def hr_review(
        self,
        evaluation_id: str,
        *,
        decision: str,
        comment: str | None,
        final_score: float | None,
    ) -> AIEvaluation | None:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            return None
        if evaluation.status not in {'pending_hr', 'returned'}:
            raise ValueError('Evaluation is not waiting for HR review.')
        if evaluation.manager_score is None:
            raise ValueError('Manager score is required before HR review.')

        normalized_decision = decision.strip().lower()
        if normalized_decision not in {'approved', 'returned'}:
            raise ValueError('HR decision must be approved or returned.')

        evaluation.hr_comment = comment
        evaluation.hr_decision = normalized_decision

        if normalized_decision == 'approved':
            next_score = round(float(final_score), 2) if final_score is not None else round((evaluation.ai_overall_score + evaluation.manager_score) / 2, 2)
            evaluation.overall_score = next_score
            evaluation.ai_level = self.engine.map_level(next_score)
            evaluation.status = 'confirmed'
            evaluation.explanation = comment or (
                f'HR 已审核通过。AI 评分 {evaluation.ai_overall_score:.2f}，主管评分 {evaluation.manager_score:.2f}，最终评分 {next_score:.2f}。'
            )
        else:
            evaluation.status = 'returned'
            evaluation.explanation = comment or 'HR 已打回本次评分，请主管重新评估。'

        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)

    def confirm_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            return None
        if evaluation.status == 'pending_hr' and evaluation.manager_score is not None:
            final_score = round((evaluation.ai_overall_score + evaluation.manager_score) / 2, 2)
            evaluation.overall_score = final_score
            evaluation.ai_level = self.engine.map_level(final_score)
            evaluation.hr_decision = 'approved'
            evaluation.hr_comment = evaluation.hr_comment or 'HR 通过快速确认接口同意该评分。'
        evaluation.status = 'confirmed'
        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)
