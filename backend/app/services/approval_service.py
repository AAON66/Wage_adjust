from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.approval import ApprovalRecord
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db

    def _approval_query(self):
        return (
            select(ApprovalRecord)
            .options(
                selectinload(ApprovalRecord.approver),
                selectinload(ApprovalRecord.recommendation)
                .selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.employee),
                selectinload(ApprovalRecord.recommendation)
                .selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.cycle),
            )
        )

    def _recommendation_query(self, recommendation_id: str):
        return (
            select(SalaryRecommendation)
            .options(
                selectinload(SalaryRecommendation.approval_records).selectinload(ApprovalRecord.approver),
                selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.employee),
                selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.cycle),
            )
            .where(SalaryRecommendation.id == recommendation_id)
        )

    def get_recommendation(self, recommendation_id: str) -> SalaryRecommendation | None:
        return self.db.scalar(self._recommendation_query(recommendation_id))

    def submit_for_approval(
        self,
        *,
        recommendation_id: str,
        steps: list[dict[str, str | None]],
    ) -> SalaryRecommendation:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise ValueError('Salary recommendation not found.')
        if not steps:
            raise ValueError('At least one approval step is required.')

        step_names = [str(step['step_name']).strip() for step in steps]
        if len(step_names) != len(set(step_names)):
            raise ValueError('Approval step names must be unique per recommendation.')

        approver_ids = [str(step['approver_id']).strip() for step in steps]
        approvers = list(self.db.scalars(select(User).where(User.id.in_(approver_ids))))
        if len(approvers) != len(set(approver_ids)):
            raise ValueError('One or more approvers were not found.')

        existing_by_step = {record.step_name: record for record in recommendation.approval_records}
        for step in steps:
            step_name = str(step['step_name']).strip()
            approver_id = str(step['approver_id']).strip()
            comment = str(step['comment']).strip() if step.get('comment') else None
            record = existing_by_step.get(step_name)
            if record is None:
                record = ApprovalRecord(
                    recommendation_id=recommendation_id,
                    approver_id=approver_id,
                    step_name=step_name,
                    decision='pending',
                    comment=comment,
                )
            else:
                record.approver_id = approver_id
                record.decision = 'pending'
                record.comment = comment
                record.decided_at = None
            self.db.add(record)

        recommendation.status = 'pending_approval'
        self.db.add(recommendation)
        self.db.commit()
        refreshed = self.get_recommendation(recommendation_id)
        if refreshed is None:
            raise ValueError('Recommendation refresh failed.')
        return refreshed

    def list_approvals(
        self,
        *,
        current_user: User,
        include_all: bool = False,
        decision: str | None = None,
    ) -> list[ApprovalRecord]:
        query = self._approval_query().order_by(ApprovalRecord.created_at.desc())
        if decision:
            query = query.where(ApprovalRecord.decision == decision)
        if not include_all or current_user.role not in {'admin', 'hrbp'}:
            query = query.where(ApprovalRecord.approver_id == current_user.id)
        return list(self.db.scalars(query))

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        query = self._approval_query().where(ApprovalRecord.id == approval_id)
        return self.db.scalar(query)

    def decide_approval(
        self,
        approval_id: str,
        *,
        current_user: User,
        decision: str,
        comment: str | None,
    ) -> ApprovalRecord | None:
        approval = self.get_approval(approval_id)
        if approval is None:
            return None
        if current_user.role not in {'admin', 'hrbp'} and approval.approver_id != current_user.id:
            raise PermissionError("You cannot act on another approver's task.")

        normalized_decision = decision.strip().lower()
        if normalized_decision not in {'approved', 'rejected'}:
            raise ValueError('Decision must be approved or rejected.')

        approval.decision = normalized_decision
        approval.comment = comment
        approval.decided_at = datetime.now(timezone.utc)
        self.db.add(approval)
        self.db.flush()

        recommendation = self.get_recommendation(approval.recommendation_id)
        if recommendation is None:
            raise ValueError('Related recommendation not found.')

        decisions = [record.decision for record in recommendation.approval_records]
        if any(item == 'rejected' for item in decisions):
            recommendation.status = 'rejected'
        elif decisions and all(item == 'approved' for item in decisions):
            recommendation.status = 'approved'
        else:
            recommendation.status = 'pending_approval'

        self.db.add(recommendation)
        self.db.commit()
        return self.get_approval(approval_id)

    def list_history(self, recommendation_id: str) -> list[ApprovalRecord]:
        query = self._approval_query().where(ApprovalRecord.recommendation_id == recommendation_id).order_by(ApprovalRecord.created_at.asc())
        return list(self.db.scalars(query))

    def list_calibration_queue(self, *, include_completed: bool = False) -> list[AIEvaluation]:
        statuses = ['needs_review', 'reviewed'] if not include_completed else ['needs_review', 'reviewed', 'confirmed']
        query = (
            select(AIEvaluation)
            .options(
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee),
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.cycle),
            )
            .where(AIEvaluation.status.in_(statuses))
            .order_by(AIEvaluation.updated_at.desc())
        )
        return list(self.db.scalars(query))

