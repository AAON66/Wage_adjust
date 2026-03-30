from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.approval import ApprovalRecord
from backend.app.models.audit_log import AuditLog
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.evaluation_cycle import EvaluationCycle
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.services.dashboard_service import DashboardService


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db
        self.dashboard_service = DashboardService(db)

    def _submission_query(self):
        return (
            select(EmployeeSubmission)
            .options(
                selectinload(EmployeeSubmission.employee),
                selectinload(EmployeeSubmission.cycle),
                selectinload(EmployeeSubmission.ai_evaluation).selectinload(AIEvaluation.dimension_scores),
                selectinload(EmployeeSubmission.ai_evaluation)
                .selectinload(AIEvaluation.salary_recommendation)
                .selectinload(SalaryRecommendation.approval_records),
            )
        )

    def log_public_access(self, *, action: str, target_type: str, target_id: str, detail: dict[str, object]) -> None:
        self.db.add(
            AuditLog(
                operator_id=None,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
            )
        )
        self.db.commit()

    def get_latest_employee_evaluation(self, employee_no: str) -> EmployeeSubmission | None:
        query = (
            self._submission_query()
            .join(EmployeeSubmission.employee)
            .where(Employee.employee_no == employee_no)
            .order_by(EmployeeSubmission.created_at.desc())
        )
        submissions = list(self.db.scalars(query))
        for submission in submissions:
            if submission.ai_evaluation is not None:
                return submission
        return None

    def get_cycle_salary_results(self, cycle_id: str) -> tuple[EvaluationCycle | None, list[EmployeeSubmission]]:
        cycle = self.db.get(EvaluationCycle, cycle_id)
        if cycle is None:
            return None, []
        query = (
            self._submission_query()
            .join(EmployeeSubmission.ai_evaluation)
            .join(AIEvaluation.salary_recommendation)
            .where(SalaryRecommendation.status == 'approved')
            .where(EmployeeSubmission.cycle_id == cycle_id)
            .order_by(EmployeeSubmission.created_at.asc())
        )
        submissions = [item for item in self.db.scalars(query) if item.ai_evaluation is not None]
        return cycle, submissions

    def get_approved_salary_results_paginated(
        self,
        *,
        cycle_id: str | None = None,
        department: str | None = None,
        cursor: str | None = None,
        page_size: int = 20,
    ) -> tuple[list[EmployeeSubmission], str | None, bool]:
        """Cursor-paginated query for approved salary results (per D-07, D-08).

        Returns (items, next_cursor, has_more).
        """
        from backend.app.utils.cursor_pagination import apply_cursor_pagination, encode_cursor

        query = (
            self._submission_query()
            .join(EmployeeSubmission.ai_evaluation)
            .join(AIEvaluation.salary_recommendation)
            .where(SalaryRecommendation.status == 'approved')
        )
        if cycle_id:
            query = query.where(EmployeeSubmission.cycle_id == cycle_id)
        if department:
            query = query.join(EmployeeSubmission.employee).where(Employee.department == department)

        query, page_size = apply_cursor_pagination(
            query,
            cursor=cursor,
            page_size=page_size,
            id_column=EmployeeSubmission.id,
        )
        results = list(self.db.scalars(query))
        has_more = len(results) > page_size
        if has_more:
            results = results[:page_size]
        next_cursor = encode_cursor(results[-1].id) if has_more else None
        return results, next_cursor, has_more

    def get_cycle_approval_status(self, cycle_id: str) -> tuple[EvaluationCycle | None, list[EmployeeSubmission]]:
        return self.get_cycle_salary_results(cycle_id)

    def get_dashboard_summary(self) -> dict[str, object]:
        return {
            'generated_at': datetime.now(timezone.utc),
            'overview': self.dashboard_service.get_overview(),
            'ai_level_distribution': self.dashboard_service.get_ai_level_distribution(),
            'roi_distribution': self.dashboard_service.get_roi_distribution(),
            'heatmap': self.dashboard_service.get_heatmap(),
        }
