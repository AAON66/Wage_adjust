from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class SalaryAdjustmentRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """调薪记录 -- 存储员工历次调薪信息。"""

    __tablename__ = 'salary_adjustment_records'
    __table_args__ = (
        Index('ix_salary_adj_employee_date', 'employee_id', 'adjustment_date'),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('employees.id'), nullable=False, index=True,
    )
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    adjustment_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment='probation/annual/special',
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default='manual',
    )
