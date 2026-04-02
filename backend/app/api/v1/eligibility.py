from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User
from backend.app.schemas.eligibility import (
    EligibilityResultSchema,
    PerformanceRecordCreate,
    PerformanceRecordRead,
    SalaryAdjustmentRecordCreate,
    SalaryAdjustmentRecordRead,
)
from backend.app.services.eligibility_service import EligibilityService

router = APIRouter(prefix='/eligibility', tags=['eligibility'])


@router.get('/{employee_id}', response_model=EligibilityResultSchema)
def check_eligibility(
    employee_id: str,
    reference_date: date | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EligibilityResultSchema:
    service = EligibilityService(db)
    result = service.check_employee(
        employee_id, reference_date=reference_date, year=year,
    )
    return EligibilityResultSchema(
        overall_status=result.overall_status,
        rules=[
            {
                'rule_code': r.rule_code,
                'rule_label': r.rule_label,
                'status': r.status,
                'detail': r.detail,
            }
            for r in result.rules
        ],
    )


@router.post(
    '/performance-records',
    response_model=PerformanceRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_performance_record(
    body: PerformanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> PerformanceRecordRead:
    service = EligibilityService(db)
    record = service.create_performance_record(
        employee_no=body.employee_no,
        year=body.year,
        grade=body.grade,
        source='manual',
    )
    audit = AuditLog(
        operator_id=current_user.id,
        action='create_performance_record',
        target_type='PerformanceRecord',
        target_id=record.id,
        detail={
            'employee_no': body.employee_no,
            'year': body.year,
            'grade': body.grade,
        },
        operator_role=current_user.role,
    )
    db.add(audit)
    db.commit()
    db.refresh(record)
    return PerformanceRecordRead.model_validate(record)


@router.post(
    '/salary-adjustment-records',
    response_model=SalaryAdjustmentRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_salary_adjustment_record(
    body: SalaryAdjustmentRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> SalaryAdjustmentRecordRead:
    service = EligibilityService(db)
    record = service.create_salary_adjustment_record(
        employee_no=body.employee_no,
        adjustment_date=body.adjustment_date,
        adjustment_type=body.adjustment_type,
        amount=body.amount,
        source='manual',
    )
    audit = AuditLog(
        operator_id=current_user.id,
        action='create_salary_adjustment_record',
        target_type='SalaryAdjustmentRecord',
        target_id=record.id,
        detail={
            'employee_no': body.employee_no,
            'adjustment_date': str(body.adjustment_date),
            'adjustment_type': body.adjustment_type,
        },
        operator_role=current_user.role,
    )
    db.add(audit)
    db.commit()
    db.refresh(record)
    return SalaryAdjustmentRecordRead.model_validate(record)


@router.get(
    '/{employee_id}/performance-records',
    response_model=list[PerformanceRecordRead],
)
def list_performance_records(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PerformanceRecordRead]:
    service = EligibilityService(db)
    records = service.list_performance_records(employee_id)
    return [PerformanceRecordRead.model_validate(r) for r in records]


@router.get(
    '/{employee_id}/salary-adjustment-records',
    response_model=list[SalaryAdjustmentRecordRead],
)
def list_salary_adjustment_records(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SalaryAdjustmentRecordRead]:
    service = EligibilityService(db)
    records = service.list_salary_adjustment_records(employee_id)
    return [SalaryAdjustmentRecordRead.model_validate(r) for r in records]
