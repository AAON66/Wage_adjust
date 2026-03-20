from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class Employee(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "employees"

    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_family: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_level: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)

    manager = relationship(
        "Employee",
        remote_side="Employee.id",
        back_populates="subordinates",
        foreign_keys="Employee.manager_id",
    )
    subordinates = relationship("Employee", back_populates="manager")
    submissions = relationship("EmployeeSubmission", back_populates="employee")
    certifications = relationship("Certification", back_populates="employee")
