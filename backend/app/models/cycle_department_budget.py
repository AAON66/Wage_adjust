from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class CycleDepartmentBudget(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'cycle_department_budgets'
    __table_args__ = (UniqueConstraint('cycle_id', 'department_id'),)

    cycle_id: Mapped[str] = mapped_column(ForeignKey('evaluation_cycles.id', ondelete='CASCADE'), nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(ForeignKey('departments.id', ondelete='CASCADE'), nullable=False, index=True)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal('0.00'))

    cycle = relationship('EvaluationCycle', back_populates='department_budgets')
    department = relationship('Department', back_populates='cycle_budgets')

    @property
    def department_name(self) -> str:
        return self.department.name if self.department is not None else ''
