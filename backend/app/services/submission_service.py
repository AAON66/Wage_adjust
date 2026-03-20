from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.submission import EmployeeSubmission


class SubmissionService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_submission(self, *, employee_id: str, cycle_id: str) -> EmployeeSubmission:
        existing = self.db.scalar(
            select(EmployeeSubmission).where(
                EmployeeSubmission.employee_id == employee_id,
                EmployeeSubmission.cycle_id == cycle_id,
            )
        )
        if existing is not None:
            return existing

        submission = EmployeeSubmission(employee_id=employee_id, cycle_id=cycle_id, status='collecting')
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def list_employee_submissions(self, employee_id: str) -> list[EmployeeSubmission]:
        query = (
            select(EmployeeSubmission)
            .where(EmployeeSubmission.employee_id == employee_id)
            .order_by(EmployeeSubmission.created_at.desc())
        )
        return list(self.db.scalars(query))