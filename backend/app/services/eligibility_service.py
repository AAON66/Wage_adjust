from __future__ import annotations

import io
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.engines.eligibility_engine import (
    EligibilityEngine,
    EligibilityResult,
    EligibilityThresholds,
    RuleResult,
)
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.eligibility_override import EligibilityOverride
from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord
from backend.app.models.user import User
from backend.app.services.access_scope_service import AccessScopeService

VALID_RULE_CODES = {'TENURE', 'ADJUSTMENT_INTERVAL', 'PERFORMANCE', 'LEAVE'}
MAX_EXPORT_ROWS = 5000


class EligibilityService:
    """Orchestrates DB queries and delegates to EligibilityEngine for eligibility evaluation."""

    def __init__(self, db: Session, *, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def _build_thresholds(self) -> EligibilityThresholds:
        fail_grades = tuple(
            s.strip() for s in self.settings.eligibility_performance_fail_grades.split(',')
        )
        return EligibilityThresholds(
            min_tenure_months=self.settings.eligibility_min_tenure_months,
            min_adjustment_interval_months=self.settings.eligibility_min_adjustment_interval_months,
            performance_fail_grades=fail_grades,
            max_non_statutory_leave_days=self.settings.eligibility_max_non_statutory_leave_days,
        )

    # ------------------------------------------------------------------
    # Single-employee check (existing)
    # ------------------------------------------------------------------

    def check_employee(
        self,
        employee_id: str,
        *,
        reference_date: date | None = None,
        year: int | None = None,
    ) -> EligibilityResult:
        if reference_date is None:
            reference_date = date.today()
        if year is None:
            year = reference_date.year - 1

        employee = self.db.get(Employee, employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail='员工未找到')

        hire_date: date | None = employee.hire_date

        # Prioritize employee.last_salary_adjustment_date (synced from Feishu "历史调薪日期")
        # Fall back to max date from salary_adjustment_records if not set
        last_adj_from_records = self.db.scalar(
            select(func.max(SalaryAdjustmentRecord.adjustment_date))
            .where(SalaryAdjustmentRecord.employee_id == employee_id)
        )
        last_adjustment_date: date | None = employee.last_salary_adjustment_date or last_adj_from_records

        performance_grade: str | None = self.db.scalar(
            select(PerformanceRecord.grade)
            .where(
                PerformanceRecord.employee_id == employee_id,
                PerformanceRecord.year == year,
            )
        )

        non_statutory_leave_days: float | None = self.db.scalar(
            select(func.sum(AttendanceRecord.non_statutory_leave_days))
            .where(
                AttendanceRecord.employee_id == employee_id,
                AttendanceRecord.period.like(f'{year}%'),
            )
        )

        engine = EligibilityEngine(thresholds=self._build_thresholds())
        return engine.evaluate(
            hire_date=hire_date,
            last_adjustment_date=last_adjustment_date,
            performance_grade=performance_grade,
            non_statutory_leave_days=non_statutory_leave_days,
            reference_date=reference_date,
        )

    # ------------------------------------------------------------------
    # Bulk data loading (avoid N+1)
    # ------------------------------------------------------------------

    def _bulk_load_eligibility_data(
        self, employee_ids: list[str], year: int,
    ) -> tuple[dict[str, str | None], dict[str, date | None], dict[str, float | None]]:
        """Bulk-load performance grades, max adjustment dates, and leave totals."""
        # Performance grades for the year
        perf_rows = self.db.execute(
            select(PerformanceRecord.employee_id, PerformanceRecord.grade)
            .where(
                PerformanceRecord.employee_id.in_(employee_ids),
                PerformanceRecord.year == year,
            )
        ).all()
        perf_map: dict[str, str | None] = {row[0]: row[1] for row in perf_rows}

        # Max adjustment dates
        adj_rows = self.db.execute(
            select(
                SalaryAdjustmentRecord.employee_id,
                func.max(SalaryAdjustmentRecord.adjustment_date),
            )
            .where(SalaryAdjustmentRecord.employee_id.in_(employee_ids))
            .group_by(SalaryAdjustmentRecord.employee_id)
        ).all()
        adj_map: dict[str, date | None] = {row[0]: row[1] for row in adj_rows}

        # Leave totals
        leave_rows = self.db.execute(
            select(
                AttendanceRecord.employee_id,
                func.sum(AttendanceRecord.non_statutory_leave_days),
            )
            .where(
                AttendanceRecord.employee_id.in_(employee_ids),
                AttendanceRecord.period.like(f'{year}%'),
            )
            .group_by(AttendanceRecord.employee_id)
        ).all()
        leave_map: dict[str, float | None] = {row[0]: row[1] for row in leave_rows}

        return perf_map, adj_map, leave_map

    # ------------------------------------------------------------------
    # Batch query with filter-before-paginate
    # ------------------------------------------------------------------

    def check_employees_batch(
        self,
        *,
        department: str | None,
        status_filter: str | None,
        rule_filter: str | None,
        job_family: str | None,
        job_level: str | None,
        page: int,
        page_size: int,
        current_user: User,
        reference_date: date | None,
        year: int | None,
    ) -> tuple[list[dict], int]:
        if reference_date is None:
            reference_date = date.today()
        if year is None:
            year = reference_date.year - 1

        # Step (a): DB-level filters
        query = select(Employee).where(Employee.status == 'active')
        if department:
            query = query.where(Employee.department == department)
        if job_family:
            query = query.where(Employee.job_family == job_family)
        if job_level:
            query = query.where(Employee.job_level == job_level)

        # AccessScopeService department scope for manager/hrbp
        if current_user.role in ('manager', 'hrbp'):
            scope_svc = AccessScopeService(self.db)
            dept_names = scope_svc._department_names(current_user)
            if dept_names:
                query = query.where(Employee.department.in_(dept_names))
            else:
                return [], 0

        employees = list(self.db.scalars(query).all())
        if not employees:
            return [], 0

        employee_ids = [e.id for e in employees]
        emp_map = {e.id: e for e in employees}

        # Step (b): Bulk load data
        perf_map, adj_map, leave_map = self._bulk_load_eligibility_data(employee_ids, year)

        # Step (c): Run engine per employee and apply overrides
        engine = EligibilityEngine(thresholds=self._build_thresholds())
        results: list[dict] = []
        for emp_id in employee_ids:
            emp = emp_map[emp_id]
            last_adj = emp.last_salary_adjustment_date or adj_map.get(emp_id)
            result = engine.evaluate(
                hire_date=emp.hire_date,
                last_adjustment_date=last_adj,
                performance_grade=perf_map.get(emp_id),
                non_statutory_leave_days=leave_map.get(emp_id),
                reference_date=reference_date,
            )
            result = self._apply_overrides(emp_id, result, year)
            results.append({
                'employee_id': emp_id,
                'employee_no': emp.employee_no,
                'name': emp.name,
                'department': emp.department,
                'job_family': emp.job_family,
                'job_level': emp.job_level,
                'overall_status': result.overall_status,
                'rules': [
                    {
                        'rule_code': r.rule_code,
                        'rule_label': r.rule_label,
                        'status': r.status,
                        'detail': r.detail,
                    }
                    for r in result.rules
                ],
            })

        # Step (d): Apply status_filter and rule_filter BEFORE pagination
        if status_filter and status_filter != 'all':
            results = [r for r in results if r['overall_status'] == status_filter]
        if rule_filter:
            results = [
                r for r in results
                if any(
                    rule['rule_code'] == rule_filter and rule['status'] == 'ineligible'
                    for rule in r['rules']
                )
            ]

        # Step (e): Total from filtered list
        total = len(results)

        # Step (f): Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = results[start:end]

        return paginated, total

    # ------------------------------------------------------------------
    # Override: apply approved overrides to eligibility results
    # ------------------------------------------------------------------

    def _apply_overrides(
        self, employee_id: str, result: EligibilityResult, year: int,
    ) -> EligibilityResult:
        override = self.db.scalar(
            select(EligibilityOverride).where(
                EligibilityOverride.employee_id == employee_id,
                EligibilityOverride.year == year,
                EligibilityOverride.status == 'approved',
            )
        )
        if override is None:
            return result

        overridden_codes = set(override.override_rules)
        new_rules: list[RuleResult] = []
        for r in result.rules:
            if r.rule_code in overridden_codes:
                new_rules.append(RuleResult(
                    rule_code=r.rule_code,
                    rule_label=r.rule_label,
                    status='overridden',
                    detail=r.detail + '（已通过特殊审批覆盖）',
                ))
            else:
                new_rules.append(r)

        # Recalculate overall: treat 'overridden' as 'eligible'
        effective_statuses = {
            'eligible' if r.status == 'overridden' else r.status
            for r in new_rules
        }
        if 'ineligible' in effective_statuses:
            overall = 'ineligible'
        elif effective_statuses == {'eligible'}:
            overall = 'eligible'
        else:
            overall = 'pending'

        return EligibilityResult(overall_status=overall, rules=new_rules)

    # ------------------------------------------------------------------
    # Override: create request
    # ------------------------------------------------------------------

    def create_override_request(
        self,
        *,
        employee_id: str,
        requester: User,
        override_rules: list[str],
        reason: str,
        year: int | None,
        reference_date: date | None,
    ) -> EligibilityOverride:
        if reference_date is None:
            reference_date = date.today()
        if year is None:
            year = reference_date.year - 1

        # (b) Validate requester role: only manager or hrbp (NOT admin, per D-03)
        if requester.role not in ('manager', 'hrbp'):
            raise HTTPException(
                status_code=403,
                detail='Only manager or HRBP can create override requests.',
            )

        # (a) Validate rule codes
        invalid_codes = set(override_rules) - VALID_RULE_CODES
        if invalid_codes:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid rule codes: {", ".join(sorted(invalid_codes))}',
            )

        # (c) Validate requester has AccessScope access to employee
        scope_svc = AccessScopeService(self.db)
        employee = scope_svc.ensure_employee_access(requester, employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail='员工未找到')

        # (d) Validate employee is currently ineligible
        current_result = self.check_employee(employee_id, reference_date=reference_date, year=year)
        if current_result.overall_status == 'eligible':
            raise HTTPException(
                status_code=400,
                detail='Employee is currently eligible -- no override needed.',
            )

        # (e) Validate each rule is actually 'ineligible'
        rule_status_map = {r.rule_code: r.status for r in current_result.rules}
        for code in override_rules:
            actual_status = rule_status_map.get(code)
            if actual_status != 'ineligible':
                raise HTTPException(
                    status_code=400,
                    detail=f'Rule {code} is not currently failing (status: {actual_status}).',
                )

        # (f) Check no active (non-rejected) override exists for same employee+year
        existing = self.db.scalar(
            select(EligibilityOverride).where(
                EligibilityOverride.employee_id == employee_id,
                EligibilityOverride.year == year,
                EligibilityOverride.status.notin_(['rejected']),
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail='An active override request already exists for this employee and year.',
            )

        # (g) Create the override record
        override = EligibilityOverride(
            employee_id=employee_id,
            requester_id=requester.id,
            override_rules=override_rules,
            reason=reason,
            status='pending_hrbp',
            year=year,
            reference_date=reference_date,
        )
        self.db.add(override)
        self.db.flush()
        return override

    # ------------------------------------------------------------------
    # Override: decide (approve/reject)
    # ------------------------------------------------------------------

    def decide_override(
        self,
        *,
        override_id: str,
        approver: User,
        decision: str,
        comment: str | None,
    ) -> EligibilityOverride:
        override = self.db.get(EligibilityOverride, override_id)
        if override is None:
            raise HTTPException(status_code=404, detail='Override not found.')

        now = datetime.now(tz=timezone.utc)

        if override.status == 'pending_hrbp':
            if approver.role != 'hrbp':
                raise HTTPException(
                    status_code=403,
                    detail='Only HRBP can approve/reject at this step.',
                )
            override.hrbp_approver_id = approver.id
            override.hrbp_decision = decision
            override.hrbp_comment = comment
            override.hrbp_decided_at = now
            if decision == 'approve':
                override.status = 'pending_admin'
            else:
                override.status = 'rejected'

        elif override.status == 'pending_admin':
            if approver.role != 'admin':
                raise HTTPException(
                    status_code=403,
                    detail='Only admin can approve/reject at this step.',
                )
            override.admin_approver_id = approver.id
            override.admin_decision = decision
            override.admin_comment = comment
            override.admin_decided_at = now
            if decision == 'approve':
                override.status = 'approved'
            else:
                override.status = 'rejected'

        elif override.status in ('approved', 'rejected'):
            raise HTTPException(
                status_code=400,
                detail='Override already finalized.',
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f'Unexpected override status: {override.status}',
            )

        self.db.add(override)
        self.db.flush()
        return override

    # ------------------------------------------------------------------
    # Override: list
    # ------------------------------------------------------------------

    def list_overrides(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: str | None,
        current_user: User,
    ) -> tuple[list[EligibilityOverride], int]:
        query = select(EligibilityOverride)

        if status_filter:
            query = query.where(EligibilityOverride.status == status_filter)

        # AccessScopeService scope for manager (join to Employee)
        if current_user.role in ('manager', 'hrbp'):
            scope_svc = AccessScopeService(self.db)
            dept_names = scope_svc._department_names(current_user)
            query = query.join(
                Employee, EligibilityOverride.employee_id == Employee.id,
            ).where(Employee.department.in_(dept_names))

        total_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(total_query) or 0

        query = query.order_by(EligibilityOverride.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.scalars(query).all())
        return items, total

    # ------------------------------------------------------------------
    # Export to Excel
    # ------------------------------------------------------------------

    def export_eligibility_excel(self, items: list[dict]) -> io.BytesIO:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '调薪资格'

        headers = ['工号', '姓名', '部门', '岗位族', '职级', '资格状态',
                   '入职时长', '调薪间隔', '绩效等级', '假期天数']
        ws.append(headers)

        rule_code_to_col = {
            'TENURE': '入职时长',
            'ADJUSTMENT_INTERVAL': '调薪间隔',
            'PERFORMANCE': '绩效等级',
            'LEAVE': '假期天数',
        }

        capped_items = items[:MAX_EXPORT_ROWS]
        for item in capped_items:
            rule_details: dict[str, str] = {}
            for rule in item.get('rules', []):
                col_name = rule_code_to_col.get(rule['rule_code'])
                if col_name:
                    rule_details[col_name] = f"{rule['status']}: {rule['detail']}"

            row = [
                item.get('employee_no', ''),
                item.get('name', ''),
                item.get('department', ''),
                item.get('job_family', ''),
                item.get('job_level', ''),
                item.get('overall_status', ''),
                rule_details.get('入职时长', ''),
                rule_details.get('调薪间隔', ''),
                rule_details.get('绩效等级', ''),
                rule_details.get('假期天数', ''),
            ]
            ws.append(row)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    # ------------------------------------------------------------------
    # Existing record CRUD methods
    # ------------------------------------------------------------------

    def create_performance_record(
        self,
        *,
        employee_no: str,
        year: int,
        grade: str,
        source: str = 'manual',
    ) -> PerformanceRecord:
        grade = grade.strip().upper()
        if grade not in ('A', 'B', 'C', 'D', 'E'):
            raise HTTPException(
                status_code=400,
                detail=f'绩效等级 "{grade}" 不合法，请填写 A/B/C/D/E',
            )

        employee = self.db.scalar(
            select(Employee).where(Employee.employee_no == employee_no)
        )
        if employee is None:
            raise HTTPException(
                status_code=404,
                detail=f'未找到员工工号 "{employee_no}"',
            )

        existing = self.db.scalar(
            select(PerformanceRecord).where(
                PerformanceRecord.employee_id == employee.id,
                PerformanceRecord.year == year,
            )
        )
        if existing is not None:
            existing.grade = grade
            existing.source = source
            self.db.add(existing)
            self.db.flush()
            return existing

        record = PerformanceRecord(
            employee_id=employee.id,
            employee_no=employee_no,
            year=year,
            grade=grade,
            source=source,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def create_salary_adjustment_record(
        self,
        *,
        employee_no: str,
        adjustment_date: date,
        adjustment_type: str,
        amount: Decimal | None = None,
        source: str = 'manual',
    ) -> SalaryAdjustmentRecord:
        if adjustment_type not in ('probation', 'annual', 'special'):
            raise HTTPException(
                status_code=400,
                detail=f'调薪类型 "{adjustment_type}" 不合法，请填写 probation/annual/special',
            )

        employee = self.db.scalar(
            select(Employee).where(Employee.employee_no == employee_no)
        )
        if employee is None:
            raise HTTPException(
                status_code=404,
                detail=f'未找到员工工号 "{employee_no}"',
            )

        record = SalaryAdjustmentRecord(
            employee_id=employee.id,
            employee_no=employee_no,
            adjustment_date=adjustment_date,
            adjustment_type=adjustment_type,
            amount=amount,
            source=source,
        )
        self.db.add(record)
        self.db.flush()
        return record

    def list_performance_records(self, employee_id: str) -> list[PerformanceRecord]:
        return list(
            self.db.scalars(
                select(PerformanceRecord)
                .where(PerformanceRecord.employee_id == employee_id)
                .order_by(PerformanceRecord.year.desc())
            )
        )

    def list_salary_adjustment_records(self, employee_id: str) -> list[SalaryAdjustmentRecord]:
        return list(
            self.db.scalars(
                select(SalaryAdjustmentRecord)
                .where(SalaryAdjustmentRecord.employee_id == employee_id)
                .order_by(SalaryAdjustmentRecord.adjustment_date.desc())
            )
        )
