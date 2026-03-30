from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.employee import Employee
from backend.app.models.feishu_sync_log import FeishuSyncLog

logger = logging.getLogger(__name__)


class AttendanceService:
    """考勤数据查询服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_employee_attendance(
        self, employee_id: str, period: str | None = None,
    ) -> AttendanceRecord | None:
        """获取单员工考勤记录。

        若 period 指定，查询 employee_id + period；
        若 period 为 None，返回该员工最新 period 的记录。
        """
        query = select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
        )
        if period:
            query = query.where(AttendanceRecord.period == period)
        else:
            query = query.order_by(AttendanceRecord.period.desc())

        query = query.limit(1)
        return self.db.execute(query).scalar_one_or_none()

    def list_attendance(
        self,
        search: str | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AttendanceRecord], int]:
        """分页查询考勤列表（每个员工最新 period），支持搜索和部门筛选。"""
        # Subquery: latest period per employee
        latest_period_sub = (
            select(
                AttendanceRecord.employee_id,
                func.max(AttendanceRecord.period).label('max_period'),
            )
            .group_by(AttendanceRecord.employee_id)
            .subquery()
        )

        # Main query joining latest period
        query = (
            select(AttendanceRecord)
            .join(
                latest_period_sub,
                (AttendanceRecord.employee_id == latest_period_sub.c.employee_id)
                & (AttendanceRecord.period == latest_period_sub.c.max_period),
            )
        )

        # Apply filters (require Employee join)
        if search or department:
            query = query.join(Employee, AttendanceRecord.employee_id == Employee.id)

            if search:
                like_pattern = f'%{search}%'
                query = query.where(
                    (Employee.employee_no.ilike(like_pattern))
                    | (Employee.name.ilike(like_pattern))
                )

            if department:
                query = query.where(Employee.department == department)

        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(AttendanceRecord.employee_no).offset(offset).limit(page_size)

        items = list(self.db.execute(query).scalars().all())
        return items, total

    def get_latest_sync_status(self) -> FeishuSyncLog | None:
        """返回最近一条同步日志。"""
        return self.db.execute(
            select(FeishuSyncLog)
            .order_by(FeishuSyncLog.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
