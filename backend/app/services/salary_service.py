from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.engines.salary_engine import SalaryEngine
from backend.app.models.approval import ApprovalRecord
from backend.app.models.certification import Certification
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User


class SalaryService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = SalaryEngine()

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

    def get_recommendation_by_evaluation(self, evaluation_id: str) -> SalaryRecommendation | None:
        query = (
            select(SalaryRecommendation)
            .options(selectinload(SalaryRecommendation.evaluation).selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(SalaryRecommendation.evaluation_id == evaluation_id)
        )
        return self.db.scalar(query)

    def get_recommendation(self, recommendation_id: str) -> SalaryRecommendation | None:
        return self._query_recommendation(recommendation_id)

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

    def recommend_salary(self, evaluation_id: str) -> SalaryRecommendation:
        evaluation = self.db.get(AIEvaluation, evaluation_id)
        if evaluation is None:
            raise ValueError('Evaluation not found.')
        if evaluation.status not in {'confirmed', 'reviewed', 'generated', 'needs_review'}:
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
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        setattr(recommendation, 'explanation', result.explanation)
        return recommendation

    def update_recommendation(self, recommendation_id: str, *, final_adjustment_ratio: float, status: str | None) -> SalaryRecommendation | None:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            return None
        recommendation.final_adjustment_ratio = round(final_adjustment_ratio, 4)
        recommendation.recommended_salary = (recommendation.current_salary * Decimal(str(1 + recommendation.final_adjustment_ratio))).quantize(Decimal('0.01'))
        if status is not None:
            recommendation.status = status
        else:
            recommendation.status = 'adjusted'
        self.db.add(recommendation)
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
        cycle_id: str,
        department: str | None,
        job_family: str | None,
        budget_amount: Decimal | None,
    ) -> tuple[list[dict[str, object]], Decimal, Decimal, bool]:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(EmployeeSubmission.cycle_id == cycle_id)
            .join(AIEvaluation.submission)
        )
        evaluations = list(self.db.scalars(query))
        items: list[dict[str, object]] = []
        total = Decimal('0.00')
        effective_budget = budget_amount or Decimal('0.00')

        for evaluation in evaluations:
            employee = evaluation.submission.employee
            if department and employee.department != department:
                continue
            if job_family and employee.job_family != job_family:
                continue
            recommendation = self.get_recommendation_by_evaluation(evaluation.id) or self.recommend_salary(evaluation.id)
            total += recommendation.recommended_salary - recommendation.current_salary
            if budget_amount is None:
                effective_budget += recommendation.recommended_salary - recommendation.current_salary
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
        return items, effective_budget, total.quantize(Decimal('0.01')), self.engine.is_over_budget(total_increase=total, budget_amount=effective_budget)


