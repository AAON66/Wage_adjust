from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings, get_settings
from backend.app.engines.salary_engine import LEVEL_RULES, SalaryEngine
from backend.app.models.approval import ApprovalRecord
from backend.app.models.audit_log import AuditLog
from backend.app.models.certification import Certification
from backend.app.models.cycle_department_budget import CycleDepartmentBudget
from backend.app.models.department import Department
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.llm_service import DeepSeekService


CHINESE_TEXT_PATTERN = re.compile(r'[\u4e00-\u9fff]')


class SalaryService:
    RECOMMENDABLE_EVALUATION_STATUSES = {'confirmed', 'reviewed', 'generated', 'needs_review'}

    def __init__(self, db: Session, settings: Settings | None = None, *, llm_service: DeepSeekService | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.engine = SalaryEngine()
        self.llm_service = llm_service or DeepSeekService(self.settings)

    def _query_recommendation(self, recommendation_id: str) -> SalaryRecommendation | None:
        query = (
            select(SalaryRecommendation)
            .options(
                selectinload(SalaryRecommendation.evaluation).selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee),
                selectinload(SalaryRecommendation.approval_records),
            )
            .where(SalaryRecommendation.id == recommendation_id)
        )
        return self.db.scalar(query)

    def _query_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(AIEvaluation.id == evaluation_id)
        )
        return self.db.scalar(query)

    def get_recommendation_by_evaluation(self, evaluation_id: str) -> SalaryRecommendation | None:
        query = (
            select(SalaryRecommendation)
            .options(selectinload(SalaryRecommendation.evaluation).selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(SalaryRecommendation.evaluation_id == evaluation_id)
        )
        return self._synchronize_explanation(self.db.scalar(query))

    def get_recommendation(self, recommendation_id: str) -> SalaryRecommendation | None:
        return self._synchronize_explanation(self._query_recommendation(recommendation_id))

    def _get_cycle(self, cycle_id: str) -> EvaluationCycle | None:
        query = (
            select(EvaluationCycle)
            .options(selectinload(EvaluationCycle.department_budgets).selectinload(CycleDepartmentBudget.department))
            .where(EvaluationCycle.id == cycle_id)
        )
        return self.db.scalar(query)

    def _derive_department_budget(self, cycle: EvaluationCycle, department_name: str | None) -> Decimal:
        if not department_name:
            return cycle.budget_amount.quantize(Decimal('0.01'))

        active_departments = [
            department.name
            for department in self.db.scalars(select(Department).where(Department.status == 'active').order_by(Department.name.asc()))
        ]
        if department_name not in active_departments:
            return Decimal('0.00')

        explicit_budget_map = {
            item.department.name: item.budget_amount.quantize(Decimal('0.01'))
            for item in cycle.department_budgets
            if item.department is not None
        }
        if department_name in explicit_budget_map:
            return explicit_budget_map[department_name]

        remaining_departments = [name for name in active_departments if name not in explicit_budget_map]
        if not remaining_departments:
            return Decimal('0.00')

        if explicit_budget_map:
            explicit_total = sum(explicit_budget_map.values(), Decimal('0.00')).quantize(Decimal('0.01'))
            remaining_budget = max(Decimal('0.00'), (cycle.budget_amount - explicit_total).quantize(Decimal('0.01')))
        else:
            remaining_budget = cycle.budget_amount.quantize(Decimal('0.01'))

        return (remaining_budget / Decimal(len(remaining_departments))).quantize(Decimal('0.01'))

    def get_salary_history_by_employee(self, employee_id: str) -> list[dict[str, object]]:
        query = (
            select(SalaryRecommendation)
            .join(SalaryRecommendation.evaluation)
            .join(AIEvaluation.submission)
            .join(EmployeeSubmission.cycle)
            .options(
                selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.cycle)
            )
            .where(EmployeeSubmission.employee_id == employee_id)
            .order_by(EvaluationCycle.created_at.asc(), SalaryRecommendation.created_at.asc())
        )
        recommendations = list(self.db.scalars(query))
        history_items: list[dict[str, object]] = []
        for recommendation in recommendations:
            evaluation = recommendation.evaluation
            submission = evaluation.submission
            cycle = submission.cycle
            adjustment_amount = (recommendation.recommended_salary - recommendation.current_salary).quantize(Decimal('0.01'))
            history_items.append(
                {
                    'recommendation_id': recommendation.id,
                    'evaluation_id': evaluation.id,
                    'submission_id': submission.id,
                    'cycle_id': cycle.id,
                    'cycle_name': cycle.name,
                    'review_period': cycle.review_period,
                    'current_salary': recommendation.current_salary,
                    'recommended_salary': recommendation.recommended_salary,
                    'recommended_ratio': recommendation.recommended_ratio,
                    'final_adjustment_ratio': recommendation.final_adjustment_ratio,
                    'adjustment_amount': adjustment_amount,
                    'ai_level': evaluation.ai_level,
                    'overall_score': evaluation.overall_score,
                    'status': recommendation.status,
                    'created_at': recommendation.created_at,
                }
            )
        return history_items

    def _estimate_current_salary(self, job_level: str) -> Decimal:
        salary_map = {
            'P4': Decimal('35000.00'),
            'P5': Decimal('45000.00'),
            'P6': Decimal('60000.00'),
            'P7': Decimal('80000.00'),
        }
        return salary_map.get(job_level, Decimal('30000.00'))

    def _certification_bonus(self, employee_id: str) -> float:
        now = datetime.now(timezone.utc)
        query = select(Certification).where(Certification.employee_id == employee_id)
        certifications = list(self.db.scalars(query))
        bonus = 0.0
        for cert in certifications:
            if cert.expires_at is None or cert.expires_at >= now:
                bonus += cert.bonus_rate
        return round(min(bonus, 0.12), 4)

    def _has_chinese_text(self, text: str | None) -> bool:
        return bool(text and CHINESE_TEXT_PATTERN.search(text))

    def _needs_explanation_refresh(self, explanation: str | None) -> bool:
        if not explanation or not explanation.strip():
            return True
        normalized = explanation.strip()
        if normalized.startswith('Recommendation built from'):
            return True
        return not self._has_chinese_text(normalized)

    def _score_assessment(self, overall_score: float) -> str:
        if overall_score >= 90:
            return '表现非常突出'
        if overall_score >= 80:
            return '整体表现良好'
        if overall_score >= 70:
            return '已基本达到岗位要求'
        if overall_score >= 60:
            return '接近岗位要求'
        return '当前表现仍未稳定达到岗位要求'

    def _build_fallback_salary_payload(
        self,
        *,
        evaluation: AIEvaluation,
        recommendation: SalaryRecommendation,
    ) -> dict[str, Any]:
        employee = evaluation.submission.employee
        level_rule = LEVEL_RULES.get(evaluation.ai_level, LEVEL_RULES['Level 1'])
        ratio_percent = recommendation.final_adjustment_ratio * 100
        risk_flags: list[str] = []
        if evaluation.overall_score < 70:
            risk_flags.append('综合评分仍在达标边缘，建议结合后续成长节奏继续观察')
        if recommendation.final_adjustment_ratio >= level_rule['ceiling'] - 0.005:
            risk_flags.append('当前建议比例已接近该等级调薪上限，落地前需结合部门预算复核')
        if recommendation.final_adjustment_ratio <= level_rule['floor'] + 0.002 and evaluation.overall_score >= 80:
            risk_flags.append('当前比例偏保守，如部门预算允许可结合岗位稀缺度再校准')

        return {
            'explanation': (
                f'{employee.name}本次 AI 能力评估为 {evaluation.ai_level}，综合评分 {evaluation.overall_score:.1f} 分，'
                f'{self._score_assessment(evaluation.overall_score)}。结合其当前薪资 {recommendation.current_salary} 元、'
                f'建议调薪比例 {ratio_percent:.2f}% 和建议薪资 {recommendation.recommended_salary} 元来看，'
                f'该结果与当前职级 {employee.job_level}、部门 {employee.department} 以及岗位序列 {employee.job_family} 的预期基本匹配。'
            ),
            'risk_flags': risk_flags,
            'budget_commentary': (
                f'本次建议已按 {evaluation.ai_level} 对应的调薪区间 '
                f'{level_rule["floor"] * 100:.2f}% - {level_rule["ceiling"] * 100:.2f}% 进行约束，'
                '预算判断仍建议结合部门总包和同批次人员统一校准。'
            ),
            'fairness_commentary': (
                f'该建议综合参考了 AI 等级、综合评分、岗位职级、部门与岗位序列加成，'
                '可作为同层级员工横向对比时的公平性基线。'
            ),
        }

    def _build_salary_explanation_text(self, payload: dict[str, Any]) -> str:
        parts: list[str] = []

        explanation = str(payload.get('explanation') or '').strip()
        budget_commentary = str(payload.get('budget_commentary') or '').strip()
        fairness_commentary = str(payload.get('fairness_commentary') or '').strip()
        raw_risk_flags = payload.get('risk_flags') or []
        if isinstance(raw_risk_flags, str):
            raw_risk_flags = [raw_risk_flags]
        risk_flags = [str(item).strip() for item in raw_risk_flags if str(item).strip()]

        if explanation:
            parts.append(explanation.rstrip('。；; ') + '。')
        if budget_commentary:
            parts.append(f'预算视角：{budget_commentary.rstrip("。；; ")}。')
        if fairness_commentary:
            parts.append(f'公平性判断：{fairness_commentary.rstrip("。；; ")}。')
        if risk_flags:
            parts.append(f'风险提示：{"；".join(risk_flags)}。')

        combined = ' '.join(parts).strip()
        return combined if combined else '当前建议说明暂未生成，请重新计算调薪建议。'

    def _build_evaluation_context(self, evaluation: AIEvaluation) -> dict[str, Any]:
        employee = evaluation.submission.employee
        return {
            'employee_name': employee.name,
            'employee_no': employee.employee_no,
            'department': employee.department,
            'job_family': employee.job_family,
            'job_level': employee.job_level,
            'ai_level': evaluation.ai_level,
            'overall_score': evaluation.overall_score,
            'confidence_score': evaluation.confidence_score,
            'evaluation_explanation': evaluation.explanation,
        }

    def _build_salary_context(self, evaluation: AIEvaluation, recommendation: SalaryRecommendation) -> dict[str, Any]:
        employee = evaluation.submission.employee
        level_rule = LEVEL_RULES.get(evaluation.ai_level, LEVEL_RULES['Level 1'])
        return {
            'employee_name': employee.name,
            'department': employee.department,
            'job_family': employee.job_family,
            'job_level': employee.job_level,
            'current_salary': str(recommendation.current_salary),
            'recommended_salary': str(recommendation.recommended_salary),
            'recommended_ratio': recommendation.recommended_ratio,
            'ai_multiplier': recommendation.ai_multiplier,
            'certification_bonus': recommendation.certification_bonus,
            'final_adjustment_ratio': recommendation.final_adjustment_ratio,
            'status': recommendation.status,
            'ratio_floor': level_rule['floor'],
            'ratio_ceiling': level_rule['ceiling'],
        }

    def _generate_salary_explanation(self, *, evaluation: AIEvaluation, recommendation: SalaryRecommendation) -> str:
        fallback_payload = self._build_fallback_salary_payload(evaluation=evaluation, recommendation=recommendation)
        result = self.llm_service.generate_salary_explanation(
            self._build_evaluation_context(evaluation),
            self._build_salary_context(evaluation, recommendation),
            fallback_payload=fallback_payload,
        )
        payload = result.payload if isinstance(result.payload, dict) else fallback_payload
        explanation = self._build_salary_explanation_text(payload)
        if not self._has_chinese_text(explanation):
            return self._build_salary_explanation_text(fallback_payload)
        return explanation

    def _synchronize_explanation(self, recommendation: SalaryRecommendation | None) -> SalaryRecommendation | None:
        if recommendation is None or not self._needs_explanation_refresh(recommendation.explanation):
            return recommendation
        evaluation = recommendation.evaluation or self._query_evaluation(recommendation.evaluation_id)
        if evaluation is None:
            return recommendation
        recommendation.explanation = self._generate_salary_explanation(evaluation=evaluation, recommendation=recommendation)
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def recommend_salary(self, evaluation_id: str) -> SalaryRecommendation:
        evaluation = self._query_evaluation(evaluation_id)
        if evaluation is None:
            raise ValueError('Evaluation not found.')
        if evaluation.status not in self.RECOMMENDABLE_EVALUATION_STATUSES:
            raise ValueError('Evaluation is not ready for salary recommendation.')

        existing = self.get_recommendation_by_evaluation(evaluation_id)
        submission = evaluation.submission
        employee = submission.employee
        current_salary = self._estimate_current_salary(employee.job_level)
        certification_bonus = self._certification_bonus(employee.id)
        result = self.engine.calculate(
            ai_level=evaluation.ai_level,
            overall_score=evaluation.overall_score,
            current_salary=current_salary,
            certification_bonus=certification_bonus,
            job_level=employee.job_level,
            department=employee.department,
            job_family=employee.job_family,
        )

        recommendation = existing or SalaryRecommendation(evaluation_id=evaluation_id)
        recommendation.current_salary = result.current_salary
        recommendation.recommended_ratio = result.recommended_ratio
        recommendation.recommended_salary = result.recommended_salary
        recommendation.ai_multiplier = result.ai_multiplier
        recommendation.certification_bonus = result.certification_bonus
        recommendation.final_adjustment_ratio = result.final_adjustment_ratio
        recommendation.status = 'recommended'
        recommendation.explanation = self._generate_salary_explanation(evaluation=evaluation, recommendation=recommendation)
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def update_recommendation(self, recommendation_id: str, *, final_adjustment_ratio: float, status: str | None, operator: User | None = None) -> SalaryRecommendation | None:
        recommendation = self._query_recommendation(recommendation_id)
        if recommendation is None:
            return None

        # Capture old values before mutation for audit (APPR-04)
        old_ratio = float(recommendation.final_adjustment_ratio)
        old_status = recommendation.status

        recommendation.final_adjustment_ratio = round(final_adjustment_ratio, 4)
        recommendation.recommended_salary = (recommendation.current_salary * Decimal(str(1 + recommendation.final_adjustment_ratio))).quantize(Decimal('0.01'))
        if status is not None:
            recommendation.status = status
        else:
            recommendation.status = 'adjusted'
        if recommendation.evaluation is None:
            recommendation.evaluation = self._query_evaluation(recommendation.evaluation_id)
        if recommendation.evaluation is not None:
            recommendation.explanation = self._generate_salary_explanation(evaluation=recommendation.evaluation, recommendation=recommendation)
        self.db.add(recommendation)

        # Write audit log in same transaction (APPR-04)
        audit_entry = AuditLog(
            operator_id=operator.id if operator else None,
            operator_role=operator.role if operator else None,
            action='salary_updated',
            target_type='salary_recommendation',
            target_id=recommendation_id,
            detail={
                'old_final_adjustment_ratio': old_ratio,
                'new_final_adjustment_ratio': round(final_adjustment_ratio, 4),
                'old_status': old_status,
                'new_status': status if status is not None else old_status,
            },
        )
        self.db.add(audit_entry)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def lock_recommendation(self, recommendation_id: str, approver: User) -> SalaryRecommendation | None:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            return None
        recommendation.status = 'locked'
        self.db.add(recommendation)

        existing_record = self.db.scalar(
            select(ApprovalRecord).where(
                ApprovalRecord.recommendation_id == recommendation_id,
                ApprovalRecord.step_name == 'salary_lock',
            )
        )
        if existing_record is None:
            self.db.add(
                ApprovalRecord(
                    recommendation_id=recommendation_id,
                    approver_id=approver.id,
                    step_name='salary_lock',
                    decision='approved',
                    comment='Recommendation locked by salary API.',
                    decided_at=datetime.now(timezone.utc),
                )
            )
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def simulate_cycle(
        self,
        *,
        current_user: User,
        cycle_id: str,
        department: str | None,
        job_family: str | None,
        budget_amount: Decimal | None,
    ) -> tuple[list[dict[str, object]], Decimal, Decimal, bool]:
        cycle = self._get_cycle(cycle_id)
        if cycle is None:
            raise ValueError('Evaluation cycle not found.')
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(EmployeeSubmission.cycle_id == cycle_id)
            .join(AIEvaluation.submission)
        )
        evaluations = list(self.db.scalars(query))
        scope_service = AccessScopeService(self.db)
        items: list[dict[str, object]] = []
        total = Decimal('0.00')
        effective_budget = budget_amount.quantize(Decimal('0.01')) if budget_amount is not None else self._derive_department_budget(cycle, department)

        for evaluation in evaluations:
            employee = evaluation.submission.employee
            if not scope_service.can_access_employee(current_user, employee):
                continue
            if department and employee.department != department:
                continue
            if job_family and employee.job_family != job_family:
                continue
            recommendation = self.get_recommendation_by_evaluation(evaluation.id)
            if recommendation is None:
                if evaluation.status not in self.RECOMMENDABLE_EVALUATION_STATUSES:
                    continue
                recommendation = self.recommend_salary(evaluation.id)
            total += recommendation.recommended_salary - recommendation.current_salary
            items.append(
                {
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'department': employee.department,
                    'job_family': employee.job_family,
                    'evaluation_id': evaluation.id,
                    'ai_level': evaluation.ai_level,
                    'current_salary': recommendation.current_salary,
                    'recommended_salary': recommendation.recommended_salary,
                    'final_adjustment_ratio': recommendation.final_adjustment_ratio,
                }
            )
        total = total.quantize(Decimal('0.01'))
        return items, effective_budget, total, self.engine.is_over_budget(total_increase=total, budget_amount=effective_budget)



