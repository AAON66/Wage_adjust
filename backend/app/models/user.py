from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    id_card_no: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='0')
    employee_id: Mapped[str | None] = mapped_column(ForeignKey('employees.id'), nullable=True, unique=True, index=True)

    employee = relationship('Employee', back_populates='bound_user', foreign_keys=[employee_id])
    approval_records = relationship('ApprovalRecord', back_populates='approver')
    audit_logs = relationship('AuditLog', back_populates='operator')
    uploaded_handbooks = relationship('EmployeeHandbook', back_populates='uploaded_by')
    departments = relationship('Department', secondary='user_department_links', back_populates='users')

    @property
    def employee_name(self) -> str | None:
        return self.employee.name if self.employee is not None else None

    @property
    def employee_no(self) -> str | None:
        return self.employee.employee_no if self.employee is not None else None
