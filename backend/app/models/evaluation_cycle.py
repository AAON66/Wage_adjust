from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class EvaluationCycle(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "evaluation_cycles"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    review_period: Mapped[str] = mapped_column(String(128), nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)

    submissions = relationship("EmployeeSubmission", back_populates="cycle")
    department_budgets = relationship("CycleDepartmentBudget", back_populates="cycle", cascade="all, delete-orphan")
