from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from backend.app.core.security import get_password_hash
from backend.app.models.approval import ApprovalRecord
from backend.app.models.audit_log import AuditLog
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.user import User
from backend.app.schemas.user import ROLE_OPTIONS, UserAdminCreate
from backend.app.services.identity_binding_service import IdentityBindingService

ROLE_PRIORITY = {
    'employee': 1,
    'hrbp': 2,
    'manager': 2,
    'admin': 3,
}


@dataclass(slots=True)
class BulkFailure:
    identifier: str
    message: str


class UserAdminService:
    def __init__(self, db: Session):
        self.db = db

    def _normalize_department_ids(self, department_ids: list[str] | None) -> list[str]:
        return list(dict.fromkeys([department_id for department_id in (department_ids or []) if department_id]))

    def _resolve_departments(self, department_ids: list[str] | None) -> list[Department]:
        normalized_ids = self._normalize_department_ids(department_ids)
        if not normalized_ids:
            return []
        departments = list(self.db.scalars(select(Department).where(Department.id.in_(normalized_ids)).order_by(Department.name.asc())))
        if len(departments) != len(normalized_ids):
            raise ValueError('One or more departments were not found.')
        department_by_id = {department.id: department for department in departments}
        return [department_by_id[department_id] for department_id in normalized_ids]

    def _validate_department_scope(self, role: str, departments: list[Department]) -> None:
        if role in {'hrbp', 'manager'} and not departments:
            raise ValueError('HRBP and manager accounts must be bound to at least one department.')
        if role not in {'hrbp', 'manager'} and departments:
            raise ValueError('Only HRBP and manager accounts can be bound to departments.')

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def _validate_role(self, role: str) -> str:
        normalized_role = role.strip().lower()
        if normalized_role not in ROLE_OPTIONS:
            raise ValueError('Invalid role.')
        return normalized_role

    def _role_priority(self, role: str) -> int:
        normalized_role = self._validate_role(role)
        return ROLE_PRIORITY[normalized_role]

    def _can_manage_role(self, operator_role: str, target_role: str) -> bool:
        return self._role_priority(operator_role) > self._role_priority(target_role)

    def _ensure_manageable(self, operator: User, target: User) -> None:
        if target.id == operator.id:
            raise ValueError('Please use personal settings to change the current account password.')
        if not self._can_manage_role(operator.role, target.role):
            raise ValueError('You cannot manage accounts with the same or higher role level.')

    def _ensure_role_assignable(self, operator: User, role: str) -> str:
        normalized_role = self._validate_role(role)
        if not self._can_manage_role(operator.role, normalized_role):
            raise ValueError('You cannot create accounts with the same or higher role level.')
        return normalized_role

    def _log_action(self, *, operator_id: str, action: str, target_id: str, detail: dict[str, object]) -> None:
        self.db.add(
            AuditLog(
                operator_id=operator_id,
                action=action,
                target_type='user',
                target_id=target_id,
                detail=detail,
            )
        )

    def list_users(
        self,
        *,
        operator: User,
        page: int = 1,
        page_size: int = 20,
        role: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[User], int]:
        operator_priority = self._role_priority(operator.role)
        visible_roles = [name for name, priority in ROLE_PRIORITY.items() if priority < operator_priority]
        filters = [or_(User.id == operator.id, User.role.in_(visible_roles))]

        if role:
            normalized_role = self._validate_role(role)
            if normalized_role != operator.role and normalized_role not in visible_roles:
                return [], 0
            filters.append(User.role == normalized_role)
        if keyword:
            normalized_keyword = f"%{keyword.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(User.email).like(normalized_keyword),
                    func.lower(func.coalesce(User.id_card_no, '')).like(normalized_keyword),
                )
            )

        base_query = select(User).options(selectinload(User.departments))
        count_query = select(func.count()).select_from(User)
        for condition in filters:
            base_query = base_query.where(condition)
            count_query = count_query.where(condition)

        base_query = base_query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(base_query))
        total = int(self.db.scalar(count_query) or 0)
        return items, total

    def create_user(self, payload: UserAdminCreate, *, operator: User) -> User:
        normalized_email = self._normalize_email(str(payload.email))
        normalized_role = self._ensure_role_assignable(operator, payload.role)
        departments = self._resolve_departments(payload.department_ids)
        self._validate_department_scope(normalized_role, departments)
        identity_service = IdentityBindingService(self.db)

        existing_user = self.db.scalar(select(User).where(User.email == normalized_email))
        if existing_user is not None:
            raise ValueError('Email already registered.')

        user = User(
            email=normalized_email,
            hashed_password=get_password_hash(payload.password),
            role=normalized_role,
            id_card_no=identity_service.ensure_user_id_card_available(payload.id_card_no),
            must_change_password=True,
        )
        user.departments = departments
        self.db.add(user)
        self.db.flush()
        identity_service.auto_bind_user_and_employee(user=user)
        self._log_action(
            operator_id=operator.id,
            action='admin.user.create',
            target_id=user.id,
            detail={
                'email': user.email,
                'role': user.role,
                'id_card_no': user.id_card_no,
                'must_change_password': user.must_change_password,
                'department_ids': [department.id for department in departments],
            },
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def bulk_create_users(self, payloads: list[UserAdminCreate], *, operator: User) -> tuple[list[User], list[BulkFailure]]:
        created: list[User] = []
        failed: list[BulkFailure] = []

        for payload in payloads:
            try:
                user = self.create_user(payload, operator=operator)
            except ValueError as exc:
                failed.append(BulkFailure(identifier=str(payload.email), message=str(exc)))
            else:
                created.append(user)

        return created, failed

    def bind_employee(self, user_id: str, *, employee_id: str | None, operator: User) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError('User not found.')
        self._ensure_manageable(operator, user)

        if employee_id is None:
            user.employee_id = None
            self.db.add(user)
            self._log_action(
                operator_id=operator.id,
                action='admin.user.unbind_employee',
                target_id=user.id,
                detail={'email': user.email},
            )
            self.db.commit()
            self.db.refresh(user)
            return user

        employee = self.db.get(Employee, employee_id)
        if employee is None:
            raise ValueError('Employee not found.')

        existing_binding = self.db.scalar(select(User).where(User.employee_id == employee_id, User.id != user.id))
        if existing_binding is not None:
            raise ValueError('This employee profile is already bound to another account.')

        user.employee_id = employee_id
        self.db.add(user)
        self._log_action(
            operator_id=operator.id,
            action='admin.user.bind_employee',
            target_id=user.id,
            detail={'email': user.email, 'employee_id': employee.id, 'employee_no': employee.employee_no, 'employee_name': employee.name},
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_password(self, user_id: str, *, new_password: str, operator: User) -> str:
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError('User not found.')
        self._ensure_manageable(operator, user)

        user.hashed_password = get_password_hash(new_password)
        user.must_change_password = True
        self.db.add(user)
        self._log_action(
            operator_id=operator.id,
            action='admin.user.password_update',
            target_id=user.id,
            detail={'email': user.email, 'role': user.role, 'must_change_password': user.must_change_password},
        )
        self.db.commit()
        return user.id

    def update_user_departments(self, user_id: str, *, department_ids: list[str], operator: User) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError('User not found.')
        self._ensure_manageable(operator, user)

        departments = self._resolve_departments(department_ids)
        self._validate_department_scope(user.role, departments)
        user.departments = departments
        self.db.add(user)
        self._log_action(
            operator_id=operator.id,
            action='admin.user.update_departments',
            target_id=user.id,
            detail={
                'email': user.email,
                'role': user.role,
                'department_ids': [department.id for department in departments],
                'department_names': [department.name for department in departments],
            },
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: str, *, operator: User) -> str:
        user = self.db.get(User, user_id)
        if user is None:
            raise ValueError('User not found.')
        if user.id == operator.id:
            raise ValueError('You cannot delete the currently logged-in account.')
        if not self._can_manage_role(operator.role, user.role):
            raise ValueError('You cannot manage accounts with the same or higher role level.')

        linked_approvals = int(self.db.scalar(select(func.count()).select_from(ApprovalRecord).where(ApprovalRecord.approver_id == user.id)) or 0)
        if linked_approvals > 0:
            raise ValueError('This account is linked to approval records and cannot be deleted.')

        if user.role == 'admin':
            admin_count = int(self.db.scalar(select(func.count()).select_from(User).where(User.role == 'admin')) or 0)
            if admin_count <= 1:
                raise ValueError('At least one admin account must be retained.')

        self.db.execute(update(AuditLog).where(AuditLog.operator_id == user.id).values(operator_id=None))
        self._log_action(
            operator_id=operator.id,
            action='admin.user.delete',
            target_id=user.id,
            detail={'email': user.email, 'role': user.role},
        )
        self.db.delete(user)
        self.db.commit()
        return user.id

    def bulk_delete_users(self, user_ids: list[str], *, operator: User) -> tuple[list[str], list[BulkFailure]]:
        deleted_user_ids: list[str] = []
        failed: list[BulkFailure] = []

        for user_id in user_ids:
            try:
                deleted_user_ids.append(self.delete_user(user_id, operator=operator))
            except ValueError as exc:
                failed.append(BulkFailure(identifier=user_id, message=str(exc)))

        return deleted_user_ids, failed

