from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.engines.eligibility_engine import EligibilityEngine, EligibilityResult, EligibilityThresholds
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord


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

        # Look up employee
        employee = self.db.get(Employee, employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail='员工未找到')

        # hire_date
        hire_date: date | None = employee.hire_date

        # last_adjustment_date: MAX(SalaryAdjustmentRecord.adjustment_date), fallback to Employee field
        last_adj_from_records = self.db.scalar(
            select(func.max(SalaryAdjustmentRecord.adjustment_date))
            .where(SalaryAdjustmentRecord.employee_id == employee_id)
        )
        last_adjustment_date: date | None = last_adj_from_records or employee.last_salary_adjustment_date

        # performance_grade: from PerformanceRecord for the given year
        performance_grade: str | None = self.db.scalar(
            select(PerformanceRecord.grade)
            .where(
                PerformanceRecord.employee_id == employee_id,
                PerformanceRecord.year == year,
            )
        )

        # non_statutory_leave_days: SUM across all AttendanceRecord periods for the year
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

        # Upsert on (employee_id, year)
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
