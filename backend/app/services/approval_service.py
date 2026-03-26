from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.approval import ApprovalRecord
from backend.app.models.audit_log import AuditLog
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.user import User
from backend.app.services.access_scope_service import AccessScopeService


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

    def _ordered_records(self, recommendation: SalaryRecommendation) -> list[ApprovalRecord]:
        return sorted(
            recommendation.approval_records,
            key=lambda item: (item.step_order, item.created_at),
        )

    def _is_current_step(self, record: ApprovalRecord, *, current_user: User | None = None) -> bool:
        recommendation = record.recommendation
        if recommendation is None or recommendation.status != 'pending_approval' or record.decision != 'pending':
            return False
        if current_user is not None and current_user.role != 'admin' and record.approver_id != current_user.id:
            return False
        # Only consider the current generation
        all_records = recommendation.approval_records
        if not all_records:
            return False
        current_gen = max(r.generation for r in all_records)
        current_gen_records = sorted(
            [r for r in all_records if r.generation == current_gen],
            key=lambda item: (item.step_order, item.created_at),
        )
        for item in current_gen_records:
            if item.id == record.id:
                return True
            if item.decision != 'approved':
                return False
        return False

    def _find_department_approvers(self, *, role: str, department_name: str, exclude_ids: set[str] | None = None) -> list[User]:
        excluded = exclude_ids or set()
        query = (
            select(User)
            .options(selectinload(User.departments))
            .where(User.role == role)
            .order_by(User.created_at.asc())
        )
        candidates = list(self.db.scalars(query))
        return [
            user
            for user in candidates
            if user.id not in excluded and any(department.name == department_name for department in user.departments)
        ]

    def _find_admin_approvers(self, *, exclude_ids: set[str] | None = None) -> list[User]:
        excluded = exclude_ids or set()
        query = (
            select(User)
            .where(User.role == 'admin')
            .order_by(User.created_at.asc())
        )
        return [user for user in self.db.scalars(query) if user.id not in excluded]

    def build_default_steps(self, *, recommendation: SalaryRecommendation, initiator: User) -> list[dict[str, str]]:
        department_name = recommendation.evaluation.submission.employee.department
        excluded_ids = {initiator.id}
        steps: list[dict[str, str]] = []

        if initiator.role == 'manager':
            hrbp_candidates = self._find_department_approvers(role='hrbp', department_name=department_name, exclude_ids=excluded_ids)
            if hrbp_candidates:
                steps.append(
                    {
                        'step_name': 'hrbp_review',
                        'approver_id': hrbp_candidates[0].id,
                        'comment': f'由经理发起，等待 {hrbp_candidates[0].email} 进行 HRBP 复核。',
                    }
                )
                excluded_ids.add(hrbp_candidates[0].id)

            admin_candidates = self._find_admin_approvers(exclude_ids=excluded_ids)
            if admin_candidates:
                steps.append(
                    {
                        'step_name': 'admin_final_review',
                        'approver_id': admin_candidates[0].id,
                        'comment': f'等待 {admin_candidates[0].email} 完成最终审批。',
                    }
                )
        elif initiator.role == 'hrbp':
            admin_candidates = self._find_admin_approvers(exclude_ids=excluded_ids)
            if admin_candidates:
                steps.append(
                    {
                        'step_name': 'admin_final_review',
                        'approver_id': admin_candidates[0].id,
                        'comment': f'由 HRBP 发起，等待 {admin_candidates[0].email} 完成最终审批。',
                    }
                )
        elif initiator.role == 'admin':
            steps.append(
                {
                    'step_name': 'admin_final_review',
                    'approver_id': initiator.id,
                    'comment': '管理员直接进入最终审批。',
                }
            )
        else:
            raise ValueError('Current role cannot initiate salary approval.')

        if not steps:
            raise ValueError('No eligible approvers were found for this recommendation.')
        return steps

    def can_edit_route(self, recommendation: SalaryRecommendation) -> tuple[bool, str | None]:
        if recommendation.status in {'approved', 'locked'}:
            return False, '当前审批已完成或已锁定，不能再修改审批路线。'
        if recommendation.status == 'pending_approval' and any(record.decision != 'pending' for record in recommendation.approval_records):
            return False, '审批已经开始处理，不能再直接修改审批路线。'
        return True, None

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
        if recommendation.status == 'locked':
            raise ValueError('Locked recommendations cannot be submitted for approval again.')
        if not steps:
            raise ValueError('At least one approval step is required.')

        step_names = [str(step['step_name']).strip() for step in steps]
        if len(step_names) != len(set(step_names)):
            raise ValueError('Approval step names must be unique per recommendation.')

        approver_ids = [str(step['approver_id']).strip() for step in steps]
        approvers = list(self.db.scalars(select(User).where(User.id.in_(approver_ids)).order_by(User.created_at.asc())))
        if len(approvers) != len(set(approver_ids)):
            raise ValueError('One or more approvers were not found.')
        approver_by_id = {approver.id: approver for approver in approvers}
        for approver_id in approver_ids:
            approver = approver_by_id[approver_id]
            if approver.role not in {'admin', 'hrbp', 'manager'}:
                raise ValueError('Approvers must be admin, HRBP, or manager accounts.')

        # Determine current generation and whether this is a resubmission after a decision
        existing_records = list(recommendation.approval_records)
        if existing_records:
            current_generation = max(r.generation for r in existing_records)
            any_decided = any(
                r.generation == current_generation and r.decision != 'pending'
                for r in existing_records
            )
            new_generation = current_generation + 1 if any_decided else current_generation
        else:
            current_generation = 0
            new_generation = 0

        if new_generation == current_generation:
            # Route update on an un-decided submission — safe to delete current-gen pending records
            # whose step_name is not in the new steps list
            incoming_step_names = {str(step['step_name']).strip() for step in steps}
            for record in existing_records:
                if record.generation == current_generation and record.step_name not in incoming_step_names:
                    self.db.delete(record)
            existing_by_step_current = {
                r.step_name: r
                for r in existing_records
                if r.generation == current_generation
            }
        else:
            # Resubmission — preserve ALL existing records, start fresh with new generation
            existing_by_step_current = {}

        for index, step in enumerate(steps, start=1):
            step_name = str(step['step_name']).strip()
            approver_id = str(step['approver_id']).strip()
            comment = str(step['comment']).strip() if step.get('comment') else None
            record = existing_by_step_current.get(step_name)
            if record is None:
                record = ApprovalRecord(
                    recommendation_id=recommendation_id,
                    approver_id=approver_id,
                    step_name=step_name,
                    step_order=index,
                    decision='pending',
                    comment=comment,
                    generation=new_generation,
                )
            else:
                record.approver_id = approver_id
                record.step_order = index
                record.decision = 'pending'
                record.comment = comment
                record.decided_at = None
            self.db.add(record)

        recommendation.status = 'pending_approval'
        recommendation.defer_until = None
        recommendation.defer_target_score = None
        recommendation.defer_reason = None
        self.db.add(recommendation)
        self.db.commit()
        refreshed = self.get_recommendation(recommendation_id)
        if refreshed is None:
            raise ValueError('Recommendation refresh failed.')
        return refreshed

    def submit_default_approval(self, *, recommendation_id: str, current_user: User) -> SalaryRecommendation:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise ValueError('Salary recommendation not found.')
        steps = self.build_default_steps(recommendation=recommendation, initiator=current_user)
        return self.submit_for_approval(recommendation_id=recommendation_id, steps=steps)

    def update_approval_route(
        self,
        *,
        recommendation_id: str,
        steps: list[dict[str, str | None]],
    ) -> SalaryRecommendation:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            raise ValueError('Salary recommendation not found.')
        can_edit, reason = self.can_edit_route(recommendation)
        if not can_edit:
            raise ValueError(reason or 'Approval route cannot be modified.')
        return self.submit_for_approval(recommendation_id=recommendation_id, steps=steps)

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
        scope_service = AccessScopeService(self.db)
        return [
            record
            for record in self.db.scalars(query)
            if scope_service.can_access_employee(current_user, record.recommendation.evaluation.submission.employee)
        ]

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
        defer_until: datetime | None = None,
        defer_target_score: float | None = None,
    ) -> ApprovalRecord | None:
        # SQLite silently ignores FOR UPDATE; the decision != 'pending' guard below
        # provides application-level idempotency. On PostgreSQL this lock is effective.
        stmt = (
            select(ApprovalRecord)
            .options(
                selectinload(ApprovalRecord.approver),
                selectinload(ApprovalRecord.recommendation)
                .selectinload(SalaryRecommendation.approval_records),
            )
            .where(ApprovalRecord.id == approval_id)
            .with_for_update()
        )
        approval = self.db.scalar(stmt)
        if approval is None:
            return None
        if current_user.role != 'admin' and approval.approver_id != current_user.id:
            raise PermissionError("You cannot act on another approver's task.")
        if not self._is_current_step(approval, current_user=current_user):
            raise ValueError('This approval step is not actionable yet.')

        normalized_decision = decision.strip().lower()
        if normalized_decision not in {'approved', 'rejected', 'deferred'}:
            raise ValueError('Decision must be approved, rejected, or deferred.')
        if normalized_decision == 'rejected' and not (comment or '').strip():
            raise ValueError('A rejection reason is required.')
        if normalized_decision == 'deferred':
            if not (comment or '').strip():
                raise ValueError('A defer reason is required.')
            if defer_until is None and defer_target_score is None:
                raise ValueError('A defer until date or target score is required.')
            if defer_until is not None and defer_until <= datetime.now(timezone.utc):
                raise ValueError('Defer until must be a future time.')
            if defer_target_score is not None and not 0 <= defer_target_score <= 100:
                raise ValueError('Target score must be between 0 and 100.')
        if approval.decision != 'pending':
            raise ValueError('This approval step has already been processed.')

        approval.decision = normalized_decision
        approval.comment = comment.strip() if comment and comment.strip() else None
        approval.decided_at = datetime.now(timezone.utc)
        self.db.add(approval)
        self.db.flush()

        recommendation = self.get_recommendation(approval.recommendation_id)
        if recommendation is None:
            raise ValueError('Related recommendation not found.')

        decisions = [record.decision for record in recommendation.approval_records]
        if any(item == 'rejected' for item in decisions):
            recommendation.status = 'rejected'
            recommendation.defer_until = None
            recommendation.defer_target_score = None
            recommendation.defer_reason = None
        elif any(item == 'deferred' for item in decisions):
            recommendation.status = 'deferred'
            recommendation.defer_until = defer_until
            recommendation.defer_target_score = defer_target_score
            recommendation.defer_reason = approval.comment
        elif decisions and all(item == 'approved' for item in decisions):
            recommendation.status = 'approved'
            recommendation.defer_until = None
            recommendation.defer_target_score = None
            recommendation.defer_reason = None
        else:
            recommendation.status = 'pending_approval'
            recommendation.defer_until = None
            recommendation.defer_target_score = None
            recommendation.defer_reason = None

        self.db.add(recommendation)

        audit_entry = AuditLog(
            operator_id=current_user.id,
            action='approval_decided',
            target_type='approval_record',
            target_id=approval.id,
            detail={
                'decision': normalized_decision,
                'recommendation_id': str(approval.recommendation_id),
                'step_name': approval.step_name,
                'step_order': approval.step_order,
                'comment': approval.comment,
                'operator_role': current_user.role,
            },
        )
        self.db.add(audit_entry)
        self.db.commit()
        return self.get_approval(approval_id)

    def list_history(self, recommendation_id: str, *, current_user: User | None = None) -> list[ApprovalRecord]:
        query = (
            self._approval_query()
            .where(ApprovalRecord.recommendation_id == recommendation_id)
            .order_by(ApprovalRecord.generation.asc(), ApprovalRecord.step_order.asc(), ApprovalRecord.created_at.asc())
        )
        records = list(self.db.scalars(query))
        if current_user is None:
            return records
        scope_service = AccessScopeService(self.db)
        return [
            record
            for record in records
            if scope_service.can_access_employee(current_user, record.recommendation.evaluation.submission.employee)
        ]

    def list_calibration_queue(self, *, current_user: User, include_completed: bool = False) -> list[AIEvaluation]:
        statuses = ['pending_hr', 'returned'] if not include_completed else ['pending_hr', 'returned', 'confirmed']
        query = (
            select(AIEvaluation)
            .options(
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee),
                selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.cycle),
            )
            .where(AIEvaluation.status.in_(statuses))
            .order_by(AIEvaluation.updated_at.desc())
        )
        scope_service = AccessScopeService(self.db)
        return [
            evaluation
            for evaluation in self.db.scalars(query)
            if scope_service.can_access_employee(current_user, evaluation.submission.employee)
        ]

    def list_submission_candidates(self, *, current_user: User) -> list[SalaryRecommendation]:
        query = (
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
            .where(SalaryRecommendation.status.in_(['recommended', 'adjusted', 'rejected', 'deferred', 'pending_approval']))
            .order_by(SalaryRecommendation.created_at.desc())
        )
        scope_service = AccessScopeService(self.db)
        return [
            recommendation
            for recommendation in self.db.scalars(query)
            if scope_service.can_access_employee(current_user, recommendation.evaluation.submission.employee)
        ]


