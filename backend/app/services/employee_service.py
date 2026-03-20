from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.employee import Employee
from backend.app.schemas.employee import EmployeeCreate


class EmployeeService:
    def __init__(self, db: Session):
        self.db = db

    def create_employee(self, payload: EmployeeCreate) -> Employee:
        existing_employee = self.db.scalar(select(Employee).where(Employee.employee_no == payload.employee_no))
        if existing_employee is not None:
            raise ValueError("Employee number already exists.")

        employee = Employee(**payload.model_dump())
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get_employees(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        department: str | None = None,
        job_family: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Employee], int]:
        filters = []
        if department:
            filters.append(Employee.department == department)
        if job_family:
            filters.append(Employee.job_family == job_family)
        if status:
            filters.append(Employee.status == status)

        base_query = select(Employee)
        count_query = select(func.count()).select_from(Employee)
        if filters:
            for condition in filters:
                base_query = base_query.where(condition)
                count_query = count_query.where(condition)

        base_query = base_query.order_by(Employee.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(base_query))
        total = int(self.db.scalar(count_query) or 0)
        return items, total

    def get_employee(self, employee_id: str) -> Employee | None:
        return self.db.get(Employee, employee_id)
