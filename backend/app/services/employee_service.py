from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.user import User
from backend.app.schemas.employee import EmployeeCreate, EmployeeUpdate
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.identity_binding_service import IdentityBindingService


class EmployeeService:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_department_name(self, department_name: str) -> str:
        normalized_name = department_name.strip()
        department = self.db.scalar(select(Department).where(Department.name == normalized_name))
        if department is None:
            raise ValueError('Department not found. Please create it in department management first.')
        if department.status != 'active':
            raise ValueError('Department is inactive. Please enable it before binding employees.')
        return department.name

    def _ensure_employee_no_available(self, employee_no: str, *, employee_id: str | None = None) -> str:
        normalized = employee_no.strip()
        query = select(Employee).where(Employee.employee_no == normalized)
        if employee_id is not None:
            query = query.where(Employee.id != employee_id)
        existing_employee = self.db.scalar(query)
        if existing_employee is not None:
            raise ValueError('Employee number already exists.')
        return normalized

    def create_employee(self, payload: EmployeeCreate) -> Employee:
        employee_data = payload.model_dump()
        identity_service = IdentityBindingService(self.db)
        employee_data['employee_no'] = self._ensure_employee_no_available(payload.employee_no)
        employee_data['department'] = self._resolve_department_name(payload.department)
        employee_data['sub_department'] = payload.sub_department.strip() if payload.sub_department else None
        employee_data['id_card_no'] = identity_service.ensure_employee_id_card_available(payload.id_card_no)
        employee = Employee(**employee_data)
        self.db.add(employee)
        self.db.flush()
        identity_service.auto_bind_user_and_employee(employee=employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def update_employee(self, employee_id: str, payload: EmployeeUpdate) -> Employee | None:
        employee = self.get_employee(employee_id)
        if employee is None:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        identity_service = IdentityBindingService(self.db)

        if 'employee_no' in update_data and update_data['employee_no'] is not None:
            update_data['employee_no'] = self._ensure_employee_no_available(update_data['employee_no'], employee_id=employee.id)
        if 'department' in update_data and update_data['department'] is not None:
            update_data['department'] = self._resolve_department_name(update_data['department'])
        if 'sub_department' in update_data:
            update_data['sub_department'] = update_data['sub_department'].strip() if update_data['sub_department'] else None
        if 'id_card_no' in update_data:
            update_data['id_card_no'] = identity_service.ensure_employee_id_card_available(update_data['id_card_no'], employee_id=employee.id)

        for field, value in update_data.items():
            setattr(employee, field, value)

        self.db.add(employee)
        self.db.flush()
        identity_service.auto_bind_user_and_employee(employee=employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def get_employees(
        self,
        *,
        current_user: User | None = None,
        page: int = 1,
        page_size: int = 20,
        department: str | None = None,
        job_family: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[Employee], int]:
        filters = []
        if department:
            filters.append(Employee.department == department)
        if job_family:
            filters.append(Employee.job_family == job_family)
        if status:
            filters.append(Employee.status == status)
        if keyword:
            like_pattern = f'%{keyword}%'
            filters.append(
                (Employee.name.ilike(like_pattern)) | (Employee.employee_no.ilike(like_pattern))
            )

        base_query = select(Employee)
        if filters:
            for condition in filters:
                base_query = base_query.where(condition)
        base_query = base_query.order_by(Employee.created_at.desc())
        scoped_items = [
            item
            for item in self.db.scalars(base_query)
            if current_user is None or AccessScopeService(self.db).can_access_employee(current_user, item)
        ]
        total = len(scoped_items)
        start = (page - 1) * page_size
        end = start + page_size
        return scoped_items[start:end], total

    def get_employee(self, employee_id: str) -> Employee | None:
        return self.db.get(Employee, employee_id)
