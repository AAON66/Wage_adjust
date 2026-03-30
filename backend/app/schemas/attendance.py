from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttendanceRecordRead(BaseModel):
    """考勤记录完整响应。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    employee_no: str
    period: str
    attendance_rate: float | None
    absence_days: float | None
    overtime_hours: float | None
    late_count: int | None
    early_leave_count: int | None
    data_as_of: datetime
    synced_at: datetime


class AttendanceSummaryRead(BaseModel):
    """单员工考勤概览，用于调薪页面内嵌（ATT-05）。"""
    employee_id: str
    employee_no: str
    period: str
    attendance_rate: float | None
    absence_days: float | None
    overtime_hours: float | None
    late_count: int | None
    early_leave_count: int | None
    data_as_of: datetime
