from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.access_scope_service import AccessScopeService


class DashboardService:
    AI_LEVEL_ORDER = ['Level 1', 'Level 2', 'Level 3', 'Level 4', 'Level 5']
    ACTIVE_RECOMMENDATION_STATUSES = {'recommended', 'adjusted', 'pending_approval', 'approved', 'locked'}
    REVIEW_BACKLOG_STATUSES = {'needs_review', 'reviewed', 'pending_manager', 'pending_hr', 'returned'}

    def __init__(self, db: Session):
        self.db = db

    def _is_accessible(self, current_user: User | None, submission: EmployeeSubmission) -> bool:
        if current_user is None:
            return True
        return AccessScopeService(self.db).can_access_employee(current_user, submission.employee)

    def _submissions(self, current_user: User | None = None, cycle_id: str | None = None) -> list[EmployeeSubmission]:
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
        return [submission for submission in self.db.scalars(query) if self._is_accessible(current_user, submission)]

    def _evaluations(self, current_user: User | None = None, cycle_id: str | None = None) -> list[AIEvaluation]:
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
        return [evaluation for evaluation in self.db.scalars(query) if self._is_accessible(current_user, evaluation.submission)]

    def _cycles(self, current_user: User | None = None, cycle_id: str | None = None) -> list[EvaluationCycle]:
        query = select(EvaluationCycle)
        if cycle_id:
            query = query.where(EvaluationCycle.id == cycle_id)
            return list(self.db.scalars(query))

        visible_cycle_ids = {submission.cycle_id for submission in self._submissions(current_user)}
        if not visible_cycle_ids:
            return []
        return list(self.db.scalars(query.where(EvaluationCycle.id.in_(visible_cycle_ids))))

    def _format_percent(self, value: Decimal) -> str:
        return f'{int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))}%'

    def _level_rank(self, ai_level: str) -> int:
        try:
            return self.AI_LEVEL_ORDER.index(ai_level)
        except ValueError:
            return -1

    def get_cycle_summary(self, current_user: User | None = None, cycle_id: str | None = None) -> dict[str, object] | None:
        cycles = self._cycles(current_user, cycle_id)
        if not cycles:
            return None
        if cycle_id:
            cycle = cycles[0]
        else:
            cycle = sorted(cycles, key=lambda item: item.created_at, reverse=True)[0]
        return {
            'cycle_id': cycle.id,
            'cycle_name': cycle.name,
            'review_period': cycle.review_period,
            'status': cycle.status,
            'budget_amount': cycle.budget_amount,
        }

    def _estimate_roi_multiple(self, evaluation: AIEvaluation, recommendation: SalaryRecommendation) -> Decimal:
        adjustment_factor = max(Decimal(str(recommendation.final_adjustment_ratio)) * Decimal('10'), Decimal('0.50'))
        impact_factor = Decimal(str(evaluation.overall_score)) / Decimal('50')
        multiplier_factor = Decimal(str(recommendation.ai_multiplier + recommendation.certification_bonus))
        roi = (impact_factor * multiplier_factor) / adjustment_factor
        return roi.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def get_overview(self, current_user: User | None = None, cycle_id: str | None = None) -> list[dict[str, str]]:
        submissions = self._submissions(current_user, cycle_id)
        evaluations = [submission.ai_evaluation for submission in submissions if submission.ai_evaluation is not None]
        cycles = self._cycles(current_user, cycle_id)

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
        review_backlog = sum(1 for evaluation in evaluations if evaluation.status in self.REVIEW_BACKLOG_STATUSES)
        approved_count = sum(
            1
            for evaluation in evaluations
            if evaluation.salary_recommendation is not None and evaluation.salary_recommendation.status in {'approved', 'locked'}
        )
        pending_approval_count = sum(
            1
            for evaluation in evaluations
            if evaluation.salary_recommendation is not None and evaluation.salary_recommendation.status == 'pending_approval'
        )
        average_increase = Decimal('0.00')
        active_recommendations = [
            evaluation.salary_recommendation
            for evaluation in evaluations
            if evaluation.salary_recommendation is not None and evaluation.salary_recommendation.status in self.ACTIVE_RECOMMENDATION_STATUSES
        ]
        if active_recommendations:
            average_increase = (
                sum((Decimal(str(item.final_adjustment_ratio)) for item in active_recommendations), Decimal('0.00'))
                / Decimal(len(active_recommendations))
            ).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

        return [
            {
                'label': '覆盖员工数' if cycle_id else '纳入范围员工数',
                'value': str(len(employee_ids)),
                'note': '当前提交范围内去重后的员工总数。',
            },
            {
                'label': '已用预算',
                'value': self._format_percent(budget_percent),
                'note': f'已使用 {budget_used.quantize(Decimal("0.01"))} / 总预算 {budget_total.quantize(Decimal("0.01"))} 的调薪额度。',
            },
            {
                'label': '平均涨幅',
                'value': self._format_percent(average_increase * Decimal('100')),
                'note': '当前已生成调薪建议中的平均最终调薪比例。',
            },
            {
                'label': '高潜人才',
                'value': str(high_potential),
                'note': 'AI 四级及以上，或综合得分达到 85 分及以上的员工数。',
            },
            {
                'label': '待复核项',
                'value': str(review_backlog),
                'note': '仍待人工复核确认或校准处理的评估数量。',
            },
            {
                'label': '审批中建议',
                'value': str(pending_approval_count),
                'note': '已经进入审批流、但尚未完成审批的调薪建议数量。',
            },
            {
                'label': '已审批建议',
                'value': str(approved_count),
                'note': '已经完成审批或锁定的调薪建议数量。',
            },
        ]

    def get_ai_level_distribution(self, current_user: User | None = None, cycle_id: str | None = None) -> list[dict[str, int | str]]:
        evaluations = self._evaluations(current_user, cycle_id)
        counts = Counter(evaluation.ai_level for evaluation in evaluations)
        return [{'label': label, 'value': counts.get(label, 0)} for label in self.AI_LEVEL_ORDER]

    def get_heatmap(self, current_user: User | None = None, cycle_id: str | None = None) -> list[dict[str, int | str]]:
        evaluations = self._evaluations(current_user, cycle_id)
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

    def get_roi_distribution(self, current_user: User | None = None, cycle_id: str | None = None) -> list[dict[str, int | str]]:
        evaluations = self._evaluations(current_user, cycle_id)
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

    def get_department_insights(self, current_user: User | None = None, cycle_id: str | None = None) -> list[dict[str, object]]:
        evaluations = self._evaluations(current_user, cycle_id)
        grouped: dict[str, list[AIEvaluation]] = defaultdict(list)
        for evaluation in evaluations:
            grouped[evaluation.submission.employee.department].append(evaluation)

        insights: list[dict[str, object]] = []
        for department, items in grouped.items():
            recommendation_items = [item.salary_recommendation for item in items if item.salary_recommendation is not None]
            budget_used = sum(
                (
                    recommendation.recommended_salary - recommendation.current_salary
                    for recommendation in recommendation_items
                    if recommendation.status in self.ACTIVE_RECOMMENDATION_STATUSES
                ),
                Decimal('0.00'),
            ).quantize(Decimal('0.01'))
            avg_increase_ratio = 0.0
            active_recommendations = [item for item in recommendation_items if item.status in self.ACTIVE_RECOMMENDATION_STATUSES]
            if active_recommendations:
                avg_increase_ratio = round(
                    sum(item.final_adjustment_ratio for item in active_recommendations) / len(active_recommendations),
                    4,
                )
            insights.append(
                {
                    'department': department,
                    'employee_count': len({item.submission.employee_id for item in items}),
                    'avg_score': round(sum(item.overall_score for item in items) / len(items), 1),
                    'high_potential_count': sum(1 for item in items if item.ai_level in {'Level 4', 'Level 5'} or item.overall_score >= 85),
                    'pending_review_count': sum(1 for item in items if item.status in self.REVIEW_BACKLOG_STATUSES),
                    'approved_count': sum(
                        1
                        for recommendation in recommendation_items
                        if recommendation.status in {'approved', 'locked'}
                    ),
                    'budget_used': budget_used,
                    'avg_increase_ratio': avg_increase_ratio,
                }
            )
        insights.sort(key=lambda item: (-float(item['avg_score']), -int(item['employee_count']), str(item['department'])))
        return insights

    def get_top_talents(self, current_user: User | None = None, cycle_id: str | None = None, limit: int = 6) -> list[dict[str, object]]:
        evaluations = self._evaluations(current_user, cycle_id)
        ranked = sorted(
            evaluations,
            key=lambda item: (
                -item.overall_score,
                -self._level_rank(item.ai_level),
                item.submission.employee.name,
            ),
        )
        talents: list[dict[str, object]] = []
        for evaluation in ranked[:limit]:
            employee = evaluation.submission.employee
            recommendation = evaluation.salary_recommendation
            talents.append(
                {
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'department': employee.department,
                    'ai_level': evaluation.ai_level,
                    'overall_score': evaluation.overall_score,
                    'recommendation_status': recommendation.status if recommendation is not None else None,
                    'final_adjustment_ratio': recommendation.final_adjustment_ratio if recommendation is not None else None,
                }
            )
        return talents

    def get_action_items(self, current_user: User | None = None, cycle_id: str | None = None) -> list[dict[str, str]]:
        evaluations = self._evaluations(current_user, cycle_id)
        cycles = self._cycles(current_user, cycle_id)
        recommendations = [item.salary_recommendation for item in evaluations if item.salary_recommendation is not None]

        review_backlog = sum(1 for item in evaluations if item.status in self.REVIEW_BACKLOG_STATUSES)
        waiting_submission = sum(1 for item in recommendations if item.status in {'recommended', 'adjusted', 'rejected'})
        waiting_approval = sum(1 for item in recommendations if item.status == 'pending_approval')
        budget_total = sum((cycle.budget_amount for cycle in cycles), Decimal('0.00'))
        budget_used = sum(
            (
                recommendation.recommended_salary - recommendation.current_salary
                for recommendation in recommendations
                if recommendation.status in self.ACTIVE_RECOMMENDATION_STATUSES
            ),
            Decimal('0.00'),
        )
        over_budget = budget_total > 0 and budget_used > budget_total

        items = [
            {
                'title': '待人工复核',
                'value': str(review_backlog),
                'note': '这些评估还没有完成复核或校准，建议优先处理。',
                'severity': 'high' if review_backlog else 'low',
            },
            {
                'title': '待发起审批',
                'value': str(waiting_submission),
                'note': '调薪建议已经生成，但还没有进入审批流。',
                'severity': 'medium' if waiting_submission else 'low',
            },
            {
                'title': '审批流处理中',
                'value': str(waiting_approval),
                'note': '这些调薪建议已经进入审批流，建议跟进节点处理进度。',
                'severity': 'medium' if waiting_approval else 'low',
            },
            {
                'title': '预算风险',
                'value': '超预算' if over_budget else '正常',
                'note': f'当前已使用 {budget_used.quantize(Decimal("0.01"))}，总预算 {budget_total.quantize(Decimal("0.01"))}。',
                'severity': 'high' if over_budget else 'low',
            },
        ]
        return items
