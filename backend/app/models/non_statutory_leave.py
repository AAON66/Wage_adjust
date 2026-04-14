from __future__ import annotations

from typing import Optional

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class NonStatutoryLeave(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """非法定假期记录 -- 存储员工年度非法定假期天数（事假/病假/其他）。"""

    __tablename__ = 'non_statutory_leaves'
    __table_args__ = (
        UniqueConstraint('employee_id', 'year', name='uq_leave_employee_year'),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('employees.id'), nullable=False, index=True,
    )
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_days: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    leave_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment='事假/病假/其他',
    )
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default='manual', comment='manual/excel/feishu',
    )
