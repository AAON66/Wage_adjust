from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_user, get_db, require_roles
from backend.app.models.audit_log import AuditLog
from backend.app.models.user import User
from backend.app.schemas.eligibility import (
    EligibilityBatchResponse,
    EligibilityBatchItemSchema,
    EligibilityResultSchema,
    OverrideDecisionPayload,
    OverrideListResponse,
    OverrideRequestCreate,
    OverrideRequestRead,
    PerformanceRecordCreate,
    PerformanceRecordRead,
    SalaryAdjustmentRecordCreate,
    SalaryAdjustmentRecordRead,
)
from backend.app.models.employee import Employee
from backend.app.models.eligibility_override import EligibilityOverride
from backend.app.services.access_scope_service import AccessScopeService
from backend.app.services.eligibility_service import EligibilityService

router = APIRouter(prefix='/eligibility', tags=['eligibility'])


def _enrich_override(override: EligibilityOverride, db: Session) -> OverrideRequestRead:
    """Enrich override with employee and requester names for display."""
    data = OverrideRequestRead.model_validate(override)
    employee = db.get(Employee, override.employee_id)
    if employee:
        data.employee_no = employee.employee_no
        data.employee_name = employee.name
    requester = db.get(User, override.requester_id)
    if requester:
        data.requester_name = requester.email
    return data


# ------------------------------------------------------------------
# Batch endpoints (before /{employee_id} to avoid path capture)
# ------------------------------------------------------------------

@router.get('/batch', response_model=EligibilityBatchResponse)
def batch_list_eligibility(
    department: str | None = Query(None),
    status_param: str | None = Query(None, alias='status'),
    rule: str | None = Query(None),
    job_family: str | None = Query(None),
    job_level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    reference_date: date | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> EligibilityBatchResponse:
    service = EligibilityService(db)
    items, total = service.check_employees_batch(
        department=department,
        status_filter=status_param,
        rule_filter=rule,
        job_family=job_family,
        job_level=job_level,
        page=page,
        page_size=page_size,
        current_user=current_user,
        reference_date=reference_date,
        year=year,
    )
    return EligibilityBatchResponse(
        items=[EligibilityBatchItemSchema(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get('/batch/export')
def batch_export_eligibility(
    department: str | None = Query(None),
    status_param: str | None = Query(None, alias='status'),
    rule: str | None = Query(None),
    job_family: str | None = Query(None),
    job_level: str | None = Query(None),
    reference_date: date | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> StreamingResponse:
    service = EligibilityService(db)
    items, _ = service.check_employees_batch(
        department=department,
        status_filter=status_param,
        rule_filter=rule,
        job_family=job_family,
        job_level=job_level,
        page=1,
        page_size=5000,
        current_user=current_user,
        reference_date=reference_date,
        year=year,
    )
    buf = service.export_eligibility_excel(items)
    today = date.today().isoformat()
    return StreamingResponse(
        buf,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename=eligibility_export_{today}.xlsx',
        },
    )


# ------------------------------------------------------------------
# Override endpoints (before /{employee_id} to avoid path capture)
# ------------------------------------------------------------------

@router.post(
    '/overrides',
    response_model=OverrideRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_override(
    body: OverrideRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('manager', 'hrbp')),
) -> OverrideRequestRead:
    service = EligibilityService(db)
    override = service.create_override_request(
        employee_id=body.employee_id,
        requester=current_user,
        override_rules=body.override_rules,
        reason=body.reason,
        year=body.year,
        reference_date=body.reference_date,
    )
    audit = AuditLog(
        operator_id=current_user.id,
        action='create_eligibility_override',
        target_type='EligibilityOverride',
        target_id=override.id,
        detail={
            'employee_id': body.employee_id,
            'override_rules': body.override_rules,
            'reason': body.reason,
        },
        operator_role=current_user.role,
    )
    db.add(audit)
    db.commit()
    db.refresh(override)
    return _enrich_override(override, db)


@router.get('/overrides', response_model=OverrideListResponse)
def list_overrides(
    status_param: str | None = Query(None, alias='status'),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> OverrideListResponse:
    service = EligibilityService(db)
    items, total = service.list_overrides(
        page=page,
        page_size=page_size,
        status_filter=status_param,
        current_user=current_user,
    )
    return OverrideListResponse(
        items=[_enrich_override(item, db) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get('/overrides/{override_id}', response_model=OverrideRequestRead)
def get_override_detail(
    override_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> OverrideRequestRead:
    override = db.get(EligibilityOverride, override_id)
    if override is None:
        raise HTTPException(status_code=404, detail='Override not found.')
    return _enrich_override(override, db)


@router.post(
    '/overrides/{override_id}/decide',
    response_model=OverrideRequestRead,
)
def decide_override(
    override_id: str,
    body: OverrideDecisionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> OverrideRequestRead:
    service = EligibilityService(db)
    override = service.decide_override(
        override_id=override_id,
        approver=current_user,
        decision=body.decision,
        comment=body.comment,
    )
    audit = AuditLog(
        operator_id=current_user.id,
        action='decide_eligibility_override',
        target_type='EligibilityOverride',
        target_id=override.id,
        detail={
            'decision': body.decision,
            'comment': body.comment,
            'new_status': override.status,
        },
        operator_role=current_user.role,
    )
    db.add(audit)
    db.commit()
    db.refresh(override)
    return _enrich_override(override, db)


# ------------------------------------------------------------------
# Record creation endpoints
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# Phase 32.1 ESELF-01/02/04/05: Employee self-service eligibility endpoint
# 必须注册在 /{employee_id} 系列之前，FastAPI 按声明顺序匹配，
# 否则 'me' 会被 /{employee_id} 当作 employee_id 参数捕获（T-32.1-04）。
#
# Employee-facing endpoint — RuleResult.detail must remain desensitized (D-09).
# 当前 4 条规则的 detail 已为月数/等级字符/天数（无 YYYY-MM-DD / 无薪资数字）；
# 任何后续修改 RuleResult.detail 的 phase 必须保留这一脱敏属性。
# ------------------------------------------------------------------

@router.get('/me', response_model=EligibilityResultSchema)
def get_my_eligibility(
    reference_date: date | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EligibilityResultSchema:
    """员工自助查询本人调薪资格（ESELF-01/02/04/05）。

    - 无参数路由 → ESELF-04 横向越权天然不可达（T-32.1-01 mitigation）
    - 复用 EligibilityService.check_employee（D-06，不新增引擎逻辑）
    - 返回 EligibilityResultSchema，含 data_updated_at（D-15/D-16）
    """
    if current_user.employee_id is None:
        # T-32.1-02 mitigation: 显式 422 + 中文 detail，避免 200+empty payload 让前端误判合格
        raise HTTPException(
            status_code=422,
            detail='您尚未绑定员工信息，请前往「账号设置」完成绑定',
        )

    service = EligibilityService(db)
    # check_employee 在 employee 不存在时抛 HTTPException(404, '员工未找到')
    result = service.check_employee(
        current_user.employee_id,
        reference_date=reference_date,
        year=year,
    )
    data_updated_at = service.compute_data_updated_at(current_user.employee_id)

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
        data_updated_at=data_updated_at,
    )


# ------------------------------------------------------------------
# Sub-resource endpoints (hardened with require_roles + AccessScopeService)
# ------------------------------------------------------------------

@router.get(
    '/{employee_id}/performance-records',
    response_model=list[PerformanceRecordRead],
)
def list_performance_records(
    employee_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> list[PerformanceRecordRead]:
    scope = AccessScopeService(db)
    employee = scope.ensure_employee_access(current_user, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found.')
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
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> list[SalaryAdjustmentRecordRead]:
    scope = AccessScopeService(db)
    employee = scope.ensure_employee_access(current_user, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found.')
    service = EligibilityService(db)
    records = service.list_salary_adjustment_records(employee_id)
    return [SalaryAdjustmentRecordRead.model_validate(r) for r in records]


# ------------------------------------------------------------------
# Single-employee eligibility check (MUST be last to avoid path capture)
# ------------------------------------------------------------------

@router.get('/{employee_id}', response_model=EligibilityResultSchema)
def check_eligibility(
    employee_id: str,
    reference_date: date | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
) -> EligibilityResultSchema:
    # AccessScopeService check (HIGH concern #1)
    scope = AccessScopeService(db)
    try:
        employee = scope.ensure_employee_access(current_user, employee_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail='Access denied to this employee.')
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found.')

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
