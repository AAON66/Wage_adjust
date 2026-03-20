from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission


class DashboardService:
    AI_LEVEL_ORDER = ['Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5']
    ACTIVE_RECOMMENDATION_STATUSES = {'recommended', 'adjusted', 'pending_approval', 'approved', 'locked'}

    def __init__(self, db: Session):
        self.db = db

    def _submissions(self, cycle_id: str | None = None) -> list[EmployeeSubmission]:
        query = (
            select(EmployeeSubmission)
            .options(
                selectinload(EmployeeSubmission.employee),
                selectinload(EmployeeSubmission.cycle),
                selectinload(EmployeeSubmission.ai_evaluation).selectinload(AIEvaluation.salary_recommendation),
            )
        )
        if cycle_id:
            query = query.where(EmployeeSubmission.cycle_id == cycle_id)
        return list(self.db.scalars(query))

    def _evaluations(self, cycle_id: str | None = None) -> list[AIEvaluation]:
        query = (
            select(AIEvaluation)
            .options(
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee),
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.cycle),
                selectinload(AIEvaluation.salary_recommendation),
            )
            .join(AIEvaluation.submission)
        )
        if cycle_id:
            query = query.where(EmployeeSubmission.cycle_id == cycle_id)
        return list(self.db.scalars(query))

    def _cycles(self, cycle_id: str | None = None) -> list[EvaluationCycle]:
        query = select(EvaluationCycle)
        if cycle_id:
            query = query.where(EvaluationCycle.id == cycle_id)
        return list(self.db.scalars(query))

    def _format_percent(self, value: Decimal) -> str:
        return f'{int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))}%'

    def _estimate_roi_multiple(self, evaluation: AIEvaluation, recommendation: SalaryRecommendation) -> Decimal:
        adjustment_factor = max(Decimal(str(recommendation.final_adjustment_ratio)) * Decimal('10'), Decimal('0.50'))
        impact_factor = Decimal(str(evaluation.overall_score)) / Decimal('50')
        multiplier_factor = Decimal(str(recommendation.ai_multiplier + recommendation.certification_bonus))
        roi = (impact_factor * multiplier_factor) / adjustment_factor
        return roi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_overview(self, cycle_id: str | None = None) -> list[dict[str, str]]:
        submissions = self._submissions(cycle_id)
        evaluations = [submission.ai_evaluation for submission in submissions if submission.ai_evaluation is not None]
        cycles = self._cycles(cycle_id)

        employee_ids = {submission.employee_id for submission in submissions}
        budget_total = sum((cycle.budget_amount for cycle in cycles), Decimal('0.00'))
        budget_used = Decimal('0.00')
        for evaluation in evaluations:
            recommendation = evaluation.salary_recommendation
            if recommendation and recommendation.status in self.ACTIVE_RECOMMENDATION_STATUSES:
                budget_used += recommendation.recommended_salary - recommendation.current_salary
        budget_percent = Decimal('0')
        if budget_total > 0:
            budget_percent = ((budget_used / budget_total) * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

        high_potential = sum(1 for evaluation in evaluations if evaluation.ai_level in {'Level 4', 'Level 5'} or evaluation.overall_score >= 85)
        review_backlog = sum(1 for evaluation in evaluations if evaluation.status in {'needs_review', 'reviewed'})

        return [
            {
                'label': 'Employees in cycle' if cycle_id else 'Employees in scope',
                'value': str(len(employee_ids)),
                'note': 'Distinct employees covered by current submission scope.',
            },
            {
                'label': 'Budget used',
                'value': self._format_percent(budget_percent),
                'note': f'{budget_used.quantize(Decimal("0.01"))} of {budget_total.quantize(Decimal("0.01"))} salary increase budget.',
            },
            {
                'label': 'High potential',
                'value': str(high_potential),
                'note': 'Evaluations at Level 4+, or overall score 85 and above.',
            },
            {
                'label': 'Review backlog',
                'value': str(review_backlog),
                'note': 'Evaluations still waiting for review confirmation or calibration.',
            },
        ]

    def get_ai_level_distribution(self, cycle_id: str | None = None) -> list[dict[str, int | str]]:
        evaluations = self._evaluations(cycle_id)
        counts = Counter(evaluation.ai_level for evaluation in evaluations)
        return [{'label': label, 'value': counts.get(label, 0)} for label in self.AI_LEVEL_ORDER]

    def get_heatmap(self, cycle_id: str | None = None) -> list[dict[str, int | str]]:
        evaluations = self._evaluations(cycle_id)
        grouped: dict[str, list[AIEvaluation]] = defaultdict(list)
        for evaluation in evaluations:
            grouped[evaluation.submission.employee.department].append(evaluation)

        cells: list[dict[str, int | str]] = []
        for department, items in grouped.items():
            avg_score = sum(item.overall_score for item in items) / len(items)
            dominant_level = Counter(item.ai_level for item in items).most_common(1)[0][0]
            cells.append(
                {
                    'department': department,
                    'level': dominant_level,
                    'intensity': int(round(avg_score)),
                }
            )
        cells.sort(key=lambda item: (-int(item['intensity']), str(item['department'])))
        return cells

    def get_roi_distribution(self, cycle_id: str | None = None) -> list[dict[str, int | str]]:
        evaluations = self._evaluations(cycle_id)
        buckets = {
            'Under 1.0x': 0,
            '1.0x - 1.5x': 0,
            '1.5x - 2.0x': 0,
            '2.0x+': 0,
        }
        for evaluation in evaluations:
            recommendation = evaluation.salary_recommendation
            if recommendation is None or recommendation.status not in self.ACTIVE_RECOMMENDATION_STATUSES:
                continue
            roi = self._estimate_roi_multiple(evaluation, recommendation)
            if roi < Decimal('1.0'):
                buckets['Under 1.0x'] += 1
            elif roi < Decimal('1.5'):
                buckets['1.0x - 1.5x'] += 1
            elif roi < Decimal('2.0'):
                buckets['1.5x - 2.0x'] += 1
            else:
                buckets['2.0x+'] += 1
        return [{'label': label, 'value': value} for label, value in buckets.items()]
