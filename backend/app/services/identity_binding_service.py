from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.employee import Employee
from backend.app.models.user import User


class IdentityBindingService:
    def __init__(self, db: Session):
        self.db = db

    def normalize_id_card_no(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = ''.join(value.strip().split()).upper()
        return normalized or None

    def ensure_employee_id_card_available(self, id_card_no: str | None, *, employee_id: str | None = None) -> str | None:
        normalized = self.normalize_id_card_no(id_card_no)
        if not normalized:
            return None
        query = select(Employee).where(Employee.id_card_no == normalized)
        if employee_id is not None:
            query = query.where(Employee.id != employee_id)
        existing = self.db.scalar(query)
        if existing is not None:
            raise ValueError('This ID card number is already used by another employee profile.')
        return normalized

    def ensure_user_id_card_available(self, id_card_no: str | None, *, user_id: str | None = None) -> str | None:
        normalized = self.normalize_id_card_no(id_card_no)
        if not normalized:
            return None
        query = select(User).where(User.id_card_no == normalized)
        if user_id is not None:
            query = query.where(User.id != user_id)
        existing = self.db.scalar(query)
        if existing is not None:
            raise ValueError('This ID card number is already used by another account.')
        return normalized

    def auto_bind_user_and_employee(self, *, user: User | None = None, employee: Employee | None = None) -> bool:
        target_user = user
        target_employee = employee
        id_card_no = self.normalize_id_card_no(target_user.id_card_no if target_user is not None else target_employee.id_card_no if target_employee is not None else None)
        if not id_card_no:
            return False

        if target_user is None:
            target_user = self.db.scalar(select(User).where(User.id_card_no == id_card_no))
        if target_employee is None:
            target_employee = self.db.scalar(select(Employee).where(Employee.id_card_no == id_card_no))

        if target_user is None or target_employee is None:
            return False

        if target_user.employee_id and target_user.employee_id != target_employee.id:
            raise ValueError('This ID card number is already bound to another employee profile.')
        bound_user = self.db.scalar(
            select(User).where(
                User.employee_id == target_employee.id,
                User.id != target_user.id,
            )
        )
        if bound_user is not None:
            raise ValueError('This employee profile is already bound to another account.')

        target_user.employee_id = target_employee.id
        self.db.add(target_user)
        self.db.add(target_employee)
        return True

    def search_employee_for_user_by_identity(self, *, user: User) -> Employee | None:
        id_card_no = self.normalize_id_card_no(user.id_card_no)
        if not id_card_no:
            return None
        return self.db.scalar(select(Employee).where(Employee.id_card_no == id_card_no))

    def search_user_for_employee_by_identity(self, *, employee: Employee) -> User | None:
        id_card_no = self.normalize_id_card_no(employee.id_card_no)
        if not id_card_no:
            return None
        return self.db.scalar(select(User).where(User.id_card_no == id_card_no))
