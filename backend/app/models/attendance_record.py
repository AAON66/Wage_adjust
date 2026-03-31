from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin


class AttendanceRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """考勤记录模型 — 存储从飞书多维表格同步的员工考勤数据。"""

    __tablename__ = 'attendance_records'
    __table_args__ = (
        UniqueConstraint('employee_id', 'period', name='uq_attendance_employee_period'),
        UniqueConstraint('feishu_record_id', name='uq_attendance_feishu_record_id'),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('employees.id'), nullable=False, index=True,
    )
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attendance_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    absence_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    overtime_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    late_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    early_leave_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leave_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    feishu_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_modified_at: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    data_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
