from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.department import Department


class DepartmentService:
    def __init__(self, db: Session):
        self.db = db

    def list_departments(self) -> tuple[list[Department], int]:
        query = select(Department).order_by(Department.name.asc())
        items = list(self.db.scalars(query))
        total = int(self.db.scalar(select(func.count()).select_from(Department)) or 0)
        return items, total

    def create_department(self, *, name: str, description: str | None, status: str) -> Department:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError('Department name is required.')

        existing = self.db.scalar(select(Department).where(func.lower(Department.name) == normalized_name.lower()))
        if existing is not None:
            raise ValueError('Department already exists.')

        department = Department(
            name=normalized_name,
            description=description.strip() if description else None,
            status=status.strip().lower(),
        )
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        return department

    def update_department(
        self,
        department_id: str,
        *,
        name: str | None,
        description: str | None,
        status: str | None,
    ) -> Department | None:
        department = self.db.get(Department, department_id)
        if department is None:
            return None

        if name is not None:
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError('Department name is required.')
            existing = self.db.scalar(
                select(Department).where(
                    func.lower(Department.name) == normalized_name.lower(),
                    Department.id != department_id,
                )
            )
            if existing is not None:
                raise ValueError('Department already exists.')
            department.name = normalized_name

        if description is not None:
            department.description = description.strip() or None
        if status is not None:
            department.status = status.strip().lower()

        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        return department

    def delete_department(self, department_id: str) -> str | None:
        department = self.db.get(Department, department_id)
        if department is None:
            return None

        department.users = []
        self.db.delete(department)
        self.db.commit()
        return department_id
