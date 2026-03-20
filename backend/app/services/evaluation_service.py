from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.engines.evaluation_engine import EvaluationEngine
from backend.app.models.dimension_score import DimensionScore
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.submission import EmployeeSubmission


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = EvaluationEngine()

    def _query_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.dimension_scores))
            .where(AIEvaluation.id == evaluation_id)
        )
        return self.db.scalar(query)

    def get_evaluation_by_submission(self, submission_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.dimension_scores))
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
        evaluation.ai_level = result.ai_level
        evaluation.confidence_score = result.confidence_score
        evaluation.explanation = result.explanation
        evaluation.status = 'needs_review' if result.needs_manual_review else 'generated'
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

        if ai_level is not None:
            evaluation.ai_level = ai_level
        if overall_score is not None:
            evaluation.overall_score = overall_score
        if explanation is not None:
            evaluation.explanation = explanation
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
            evaluation.overall_score = round(sum(item.weighted_score for item in evaluation.dimension_scores), 2)
        evaluation.status = 'reviewed'
        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)

    def confirm_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            return None
        evaluation.status = 'confirmed'
        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)