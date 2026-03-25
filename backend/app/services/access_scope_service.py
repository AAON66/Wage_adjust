from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.approval import ApprovalRecord
from backend.app.models.employee import Employee
from backend.app.models.evaluation import AIEvaluation
from backend.app.models.salary_recommendation import SalaryRecommendation
from backend.app.models.submission import EmployeeSubmission
from backend.app.models.uploaded_file import UploadedFile
from backend.app.models.user import User


class AccessScopeService:
    def __init__(self, db: Session):
        self.db = db

    def _department_names(self, current_user: User) -> set[str]:
        return {department.name for department in current_user.departments}

    def can_access_employee(self, current_user: User, employee: Employee | None) -> bool:
        if employee is None:
            return False
        if current_user.role == 'admin':
            return True
        if current_user.role == 'employee':
            return current_user.employee_id == employee.id
        if current_user.role in {'hrbp', 'manager'}:
            return employee.department in self._department_names(current_user)
        return False

    def ensure_employee_access(self, current_user: User, employee_id: str) -> Employee | None:
        employee = self.db.get(Employee, employee_id)
        if employee is None:
            return None
        if not self.can_access_employee(current_user, employee):
            raise PermissionError('You do not have access to this employee.')
        return employee

    def get_submission(self, submission_id: str) -> EmployeeSubmission | None:
        query = (
            select(EmployeeSubmission)
            .options(selectinload(EmployeeSubmission.employee), selectinload(EmployeeSubmission.cycle))
            .where(EmployeeSubmission.id == submission_id)
        )
        return self.db.scalar(query)

    def ensure_submission_access(self, current_user: User, submission_id: str) -> EmployeeSubmission | None:
        submission = self.get_submission(submission_id)
        if submission is None:
            return None
        if not self.can_access_employee(current_user, submission.employee):
            raise PermissionError('You do not have access to this employee submission.')
        return submission

    def get_evaluation(self, evaluation_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(AIEvaluation.id == evaluation_id)
        )
        return self.db.scalar(query)

    def ensure_evaluation_access(self, current_user: User, evaluation_id: str) -> AIEvaluation | None:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            return None
        if not self.can_access_employee(current_user, evaluation.submission.employee):
            raise PermissionError('You do not have access to this evaluation.')
        return evaluation

    def ensure_evaluation_access_by_submission(self, current_user: User, submission_id: str) -> AIEvaluation | None:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.submission).selectinload(EmployeeSubmission.employee))
            .where(AIEvaluation.submission_id == submission_id)
        )
        evaluation = self.db.scalar(query)
        if evaluation is None:
            return None
        if not self.can_access_employee(current_user, evaluation.submission.employee):
            raise PermissionError('You do not have access to this evaluation.')
        return evaluation

    def get_uploaded_file(self, file_id: str) -> UploadedFile | None:
        query = (
            select(UploadedFile)
            .options(selectinload(UploadedFile.submission).selectinload(EmployeeSubmission.employee))
            .where(UploadedFile.id == file_id)
        )
        return self.db.scalar(query)

    def ensure_uploaded_file_access(self, current_user: User, file_id: str) -> UploadedFile | None:
        file_record = self.get_uploaded_file(file_id)
        if file_record is None:
            return None
        if not self.can_access_employee(current_user, file_record.submission.employee):
            raise PermissionError('You do not have access to this file.')
        return file_record

    def get_recommendation(self, recommendation_id: str) -> SalaryRecommendation | None:
        query = (
            select(SalaryRecommendation)
            .options(
                selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.employee)
            )
            .where(SalaryRecommendation.id == recommendation_id)
        )
        return self.db.scalar(query)

    def ensure_recommendation_access(self, current_user: User, recommendation_id: str) -> SalaryRecommendation | None:
        recommendation = self.get_recommendation(recommendation_id)
        if recommendation is None:
            return None
        if not self.can_access_employee(current_user, recommendation.evaluation.submission.employee):
            raise PermissionError('You do not have access to this salary recommendation.')
        return recommendation

    def ensure_recommendation_access_by_evaluation(self, current_user: User, evaluation_id: str) -> SalaryRecommendation | None:
        query = (
            select(SalaryRecommendation)
            .options(
                selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.employee)
            )
            .where(SalaryRecommendation.evaluation_id == evaluation_id)
        )
        recommendation = self.db.scalar(query)
        if recommendation is None:
            return None
        if not self.can_access_employee(current_user, recommendation.evaluation.submission.employee):
            raise PermissionError('You do not have access to this salary recommendation.')
        return recommendation

    def ensure_approval_access(self, current_user: User, approval_id: str) -> ApprovalRecord | None:
        query = (
            select(ApprovalRecord)
            .options(
                selectinload(ApprovalRecord.recommendation)
                .selectinload(SalaryRecommendation.evaluation)
                .selectinload(AIEvaluation.submission)
                .selectinload(EmployeeSubmission.employee)
            )
            .where(ApprovalRecord.id == approval_id)
        )
        approval = self.db.scalar(query)
        if approval is None:
            return None
        if not self.can_access_employee(current_user, approval.recommendation.evaluation.submission.employee):
            raise PermissionError('You do not have access to this approval record.')
        return approval
