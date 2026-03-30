from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.attendance import AttendanceRecordRead, AttendanceSummaryRead
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.attendance_service import AttendanceService

router = APIRouter(prefix='/attendance', tags=['attendance'])


@router.get('/', response_model=dict)
def list_attendance(
    search: str | None = None,
    department: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> dict:
    """考勤列表（admin + hrbp），支持搜索和部门筛选。"""
    service = AttendanceService(db)
    items, total = service.list_attendance(
        search=search, department=department, page=page, page_size=page_size,
    )
    return {
        'items': [AttendanceRecordRead.model_validate(item) for item in items],
        'total': total,
    }


@router.get('/{employee_id}')
def get_employee_attendance(
    employee_id: str,
    period: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> dict:
    """单员工考勤概览（admin + hrbp + manager）。

    manager 仅可查看自己部门员工。若无数据返回 200 + null（不阻断调薪流程）。
    """
    # Access control: manager limited to own department
    if current_user.role == 'manager':
        scope_service = AccessScopeService(db)
        employee = scope_service.ensure_employee_access(current_user, employee_id)
        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Employee not found',
            )

    service = AttendanceService(db)
    record = service.get_employee_attendance(employee_id, period)

    if record is None:
        return {'data': None, 'message': '暂无考勤数据'}

    return {
        'data': AttendanceSummaryRead(
            employee_id=record.employee_id,
            employee_no=record.employee_no,
            period=record.period,
            attendance_rate=record.attendance_rate,
            absence_days=record.absence_days,
            overtime_hours=record.overtime_hours,
            late_count=record.late_count,
            early_leave_count=record.early_leave_count,
            data_as_of=record.data_as_of,
        ),
    }
