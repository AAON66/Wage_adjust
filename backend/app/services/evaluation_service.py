from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings, get_settings
from backend.app.engines.evaluation_engine import EvaluationEngine, EvaluatedDimension, EvaluationResult
from backend.app.models.dimension_score import DimensionScore
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evidence import EvidenceItem
from backend.app.models.submission import EmployeeSubmission
from backend.app.services.llm_service import DeepSeekService

MANAGER_ALIGNMENT_THRESHOLD = 10.0


class EvaluationService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        *,
        engine: EvaluationEngine | None = None,
        llm_service: DeepSeekService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.engine = engine or EvaluationEngine()
        self.llm = llm_service or DeepSeekService(self.settings)

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

        employee_profile = self._build_employee_profile(submission)
        baseline_result = self.engine.evaluate(list(submission.evidence_items), employee_profile=employee_profile)
        result, used_fallback, prompt_hash = self._generate_llm_backed_result(submission, baseline_result, employee_profile=employee_profile)

        evaluation = existing or AIEvaluation(submission_id=submission_id)
        evaluation.overall_score = result.overall_score
        evaluation.ai_overall_score = result.overall_score
        evaluation.manager_score = None
        evaluation.score_gap = None
        evaluation.ai_level = result.ai_level
        evaluation.confidence_score = result.confidence_score
        evaluation.explanation = f'{result.explanation} 当前待主管复核。'
        evaluation.manager_comment = None
        evaluation.hr_comment = None
        evaluation.hr_decision = None
        evaluation.status = 'generated'
        evaluation.used_fallback = used_fallback
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
                    ai_raw_score=dimension.raw_score,
                    ai_weighted_score=dimension.weighted_score,
                    raw_score=dimension.raw_score,
                    weighted_score=dimension.weighted_score,
                    ai_rationale=dimension.rationale,
                    rationale=dimension.rationale,
                    prompt_hash=prompt_hash,
                )
            )

        submission.status = 'evaluated'
        self.db.add(submission)
        self.db.commit()
        return self.get_evaluation(evaluation.id)  # type: ignore[return-value]

    def _build_employee_profile(self, submission: EmployeeSubmission) -> dict[str, Any]:
        employee = submission.employee
        base_profile = {
            'employee_id': submission.employee_id,
            'employee_name': employee.name if employee is not None else '',
            'department': employee.department if employee is not None else '',
            'job_family': employee.job_family if employee is not None else '',
            'job_level': employee.job_level if employee is not None else '',
            'submission_status': submission.status,
            'self_summary': submission.self_summary or '',
            'manager_summary': submission.manager_summary or '',
        }
        scoring_context = self.engine.build_scoring_context(base_profile)
        return {
            **base_profile,
            'department_scoring_context': scoring_context,
            'dimension_specs': scoring_context['dimension_specs'],
        }

    def _generate_llm_backed_result(
        self,
        submission: EmployeeSubmission,
        baseline_result: EvaluationResult,
        *,
        employee_profile: dict[str, Any] | None = None,
    ) -> tuple[EvaluationResult, bool, str | None]:
        """Return (EvaluationResult, used_fallback, prompt_hash)."""
        profile = employee_profile or self._build_employee_profile(submission)
        evidence_items = [self._serialize_evidence_item(item) for item in submission.evidence_items]
        llm_result = self.llm.generate_evaluation(
            profile,
            evidence_items,
            fallback_payload=self._serialize_evaluation_result(baseline_result),
        )
        evaluation_result = self._normalize_llm_evaluation_payload(llm_result.payload, baseline_result)
        return evaluation_result, llm_result.used_fallback, llm_result.prompt_hash

    def _serialize_evidence_item(self, item: EvidenceItem) -> dict[str, Any]:
        metadata = item.metadata_json if isinstance(item.metadata_json, dict) else {}
        return {
            'title': item.title,
            'content_excerpt': item.content[:700],
            'source_type': item.source_type,
            'confidence_score': item.confidence_score,
            'tags': metadata.get('tags', []),
            'archive_member_path': metadata.get('archive_member_path'),
            'credibility_notes': metadata.get('credibility_notes'),
        }

    def _serialize_evaluation_result(self, result: EvaluationResult) -> dict[str, Any]:
        return {
            'overall_score': result.overall_score,
            'ai_level': result.ai_level,
            'confidence_score': result.confidence_score,
            'explanation': result.explanation,
            'needs_manual_review': result.needs_manual_review,
            'dimensions': [
                {
                    'code': item.code,
                    'label': item.label,
                    'weight': item.weight,
                    'raw_score': item.raw_score,
                    'weighted_score': item.weighted_score,
                    'rationale': item.rationale,
                }
                for item in result.dimensions
            ],
        }

    def _normalize_llm_evaluation_payload(self, payload: dict[str, Any], baseline_result: EvaluationResult) -> EvaluationResult:
        dimensions_by_code = {
            str(item.get('code', '')).upper(): item
            for item in payload.get('dimensions', [])
            if isinstance(item, dict)
        }
        baseline_by_code = {item.code: item for item in baseline_result.dimensions}
        raw_dimension_scores = [
            self._safe_float(item.get('raw_score'))
            for item in dimensions_by_code.values()
            if self._safe_float(item.get('raw_score')) is not None
        ]
        # Require at least 3 dimension scores all ≤ 5.0 to activate five-point scale detection.
        # This avoids false positives when only 1-2 values happen to be small integers.
        use_five_point_scale = len(raw_dimension_scores) >= 3 and max(raw_dimension_scores) <= 5.0

        overall_value = self._safe_float(payload.get('overall_score'))
        if overall_value is not None:
            if use_five_point_scale and overall_value <= 5.0:
                # Consistently five-point context: scale overall to 100-point
                overall_value = min(overall_value * 20, 100.0)
            elif not use_five_point_scale and overall_value <= 5.0:
                # Ambiguous: dimensions are 100-point scale but overall looks like 5-point.
                # Discard overall_score; fall through to weighted_total path.
                overall_value = None

        normalized_dimensions: list[EvaluatedDimension] = []
        for baseline_dimension in baseline_result.dimensions:
            raw_item = dimensions_by_code.get(baseline_dimension.code, {})
            raw_score_value = self._safe_float(raw_item.get('raw_score'))
            if raw_score_value is not None and use_five_point_scale:
                raw_score_value *= 20
            raw_score = self._reconcile_dimension_score(
                llm_score=raw_score_value,
                baseline_score=baseline_dimension.raw_score,
            )
            rationale = str(raw_item.get('rationale') or baseline_dimension.rationale).strip() or baseline_dimension.rationale
            normalized_dimensions.append(
                EvaluatedDimension(
                    code=baseline_dimension.code,
                    label=baseline_dimension.label,
                    weight=baseline_dimension.weight,
                    raw_score=raw_score,
                    weighted_score=round(raw_score * baseline_dimension.weight, 2),
                    rationale=rationale,
                )
            )

        weighted_total = round(sum(item.weighted_score for item in normalized_dimensions), 2)
        suggested_overall = self._clamp_score(overall_value if overall_value is not None else weighted_total)
        if abs(suggested_overall - weighted_total) > 6:
            overall_score = weighted_total
        else:
            overall_score = round((suggested_overall + weighted_total) / 2, 2)
        if baseline_result.overall_score >= 66 and overall_score < baseline_result.overall_score - 3:
            overall_score = round(baseline_result.overall_score * 0.7 + overall_score * 0.3, 2)

        confidence_score = self._clamp_ratio(payload.get('confidence_score', baseline_result.confidence_score))
        explanation = str(payload.get('explanation') or baseline_result.explanation).strip() or baseline_result.explanation
        ai_level = self._normalize_ai_level(payload.get('ai_level'), overall_score)
        needs_manual_review = bool(payload.get('needs_manual_review', baseline_result.needs_manual_review))

        return EvaluationResult(
            overall_score=overall_score,
            ai_level=ai_level,
            confidence_score=confidence_score,
            explanation=explanation,
            needs_manual_review=needs_manual_review,
            dimensions=normalized_dimensions,
        )

    def _clamp_score(self, value: Any) -> float:
        numeric = self._safe_float(value) or 0.0
        return round(max(0.0, min(numeric, 100.0)), 2)

    def _clamp_ratio(self, value: Any) -> float:
        numeric = self._safe_float(value) or 0.0
        return round(max(0.0, min(numeric, 1.0)), 2)

    def _reconcile_dimension_score(self, *, llm_score: float | None, baseline_score: float) -> float:
        if llm_score is None:
            return self._clamp_score(baseline_score)

        normalized_llm_score = self._clamp_score(llm_score)
        baseline_score = self._clamp_score(baseline_score)

        if baseline_score >= 60 and normalized_llm_score < baseline_score - 6:
            return round(baseline_score * 0.8 + normalized_llm_score * 0.2, 2)
        return normalized_llm_score

    def _safe_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _normalize_ai_level(self, value: Any, overall_score: float) -> str:
        text = str(value or '').strip()
        if text in {'Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5'}:
            return text
        level_map = {
            '基础应用': 'Level 1',
            '初步应用': 'Level 2',
            '熟练应用': 'Level 3',
            '深度应用': 'Level 4',
            '战略引领': 'Level 5',
        }
        if text in level_map:
            return level_map[text]
        return self.engine.map_level(overall_score)

    def _normalize_dimension_code(self, value: object) -> str:
        return str(value or '').strip().upper()

    def _resolve_reviewed_manager_score(
        self,
        evaluation: AIEvaluation,
        *,
        overall_score: float | None,
        dimension_updates: list[dict[str, object]],
    ) -> float:
        if dimension_updates:
            weighted_total = sum(dimension.weighted_score for dimension in evaluation.dimension_scores)
            return self._clamp_score(weighted_total)
        if overall_score is None:
            raise ValueError('Manager score is required for review.')
        return self._clamp_score(overall_score)

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
            score_map = {
                self._normalize_dimension_code(item.dimension_code): item
                for item in evaluation.dimension_scores
            }
            for update in dimension_updates:
                dimension = score_map.get(self._normalize_dimension_code(update.get('dimension_code')))
                if dimension is None:
                    continue
                next_raw_score = self._clamp_score(update.get('raw_score'))
                dimension.raw_score = next_raw_score
                dimension.weighted_score = round(next_raw_score * dimension.weight, 2)
                dimension.rationale = str(update.get('rationale') or dimension.rationale).strip() or dimension.rationale
                self.db.add(dimension)
            self.db.flush()

        evaluation.manager_score = self._resolve_reviewed_manager_score(
            evaluation,
            overall_score=overall_score,
            dimension_updates=dimension_updates,
        )
        evaluation.score_gap = round(abs(evaluation.ai_overall_score - evaluation.manager_score), 2)
        evaluation.manager_comment = explanation

        if evaluation.score_gap <= MANAGER_ALIGNMENT_THRESHOLD:
            final_score = evaluation.manager_score
            evaluation.overall_score = final_score
            evaluation.ai_level = ai_level or self.engine.map_level(final_score)
            evaluation.status = 'confirmed'
            evaluation.hr_decision = 'not_required'
            evaluation.explanation = explanation or (
                f'主管按维度复核后已确认结果，最终得分 {final_score:.2f}，'
                f'与 AI 初评分差值为 {evaluation.score_gap:.2f}。'
            )
        else:
            evaluation.overall_score = evaluation.manager_score
            evaluation.status = 'pending_hr'
            evaluation.hr_decision = 'pending'
            evaluation.explanation = explanation or (
                f'主管按维度复核后的得分为 {evaluation.manager_score:.2f}，'
                f'与 AI 初评分 {evaluation.ai_overall_score:.2f} 相差 {evaluation.score_gap:.2f}，已提交 HR 审核。'
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
            next_score = self._clamp_score(final_score if final_score is not None else evaluation.manager_score)
            evaluation.overall_score = next_score
            evaluation.ai_level = self.engine.map_level(next_score)
            evaluation.status = 'confirmed'
            evaluation.explanation = comment or (
                f'HR 已通过复核，最终得分 {next_score:.2f}，'
                f'AI 初评分为 {evaluation.ai_overall_score:.2f}，主管复核分为 {evaluation.manager_score:.2f}。'
            )
        else:
            evaluation.status = 'returned'
            evaluation.explanation = comment or 'HR 已退回本次复核，请主管补充更充分的客观说明后重新提交。'

        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)

    def confirm_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            return None
        if evaluation.status == 'pending_hr' and evaluation.manager_score is not None:
            final_score = self._clamp_score(evaluation.manager_score)
            evaluation.overall_score = final_score
            evaluation.ai_level = self.engine.map_level(final_score)
            evaluation.hr_decision = 'approved'
            evaluation.hr_comment = evaluation.hr_comment or 'HR 快速确认了主管复核结果。'
        evaluation.status = 'confirmed'
        self.db.add(evaluation)
        self.db.commit()
        return self.get_evaluation(evaluation.id)
