from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class PerformanceRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """绩效记录 -- 存储员工年度绩效等级 (A/B/C/D/E)。"""

    __tablename__ = 'performance_records'
    __table_args__ = (
        UniqueConstraint('employee_id', 'year', name='uq_performance_employee_year'),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('employees.id'), nullable=False, index=True,
    )
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(8), nullable=False, comment='A/B/C/D/E')
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default='manual', comment='manual/excel/feishu',
    )
    department_snapshot: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment='Phase 34 D-07：录入时员工所属部门快照；存量行 NULL 不回填',
    )
