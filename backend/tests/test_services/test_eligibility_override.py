"""Tests for EligibilityService override lifecycle (create, decide, apply)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.eligibility_override import EligibilityOverride
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord
from backend.app.models.user import User
from backend.app.models.department import Department
from backend.app.services.eligibility_service import EligibilityService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> tuple[Session, sessionmaker]:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    db_path = (temp_root / f'elig-override-{uuid4().hex}.db').as_posix()
    engine = create_engine(
        f'sqlite+pysqlite:///{db_path}',
        connect_args={'check_same_thread': False},
        echo=False,
    )
    load_model_modules()
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return factory(), factory


def _make_employee(db: Session, *, employee_no: str, name: str, department: str,
                   hire_date: date | None = date(2020, 1, 1)) -> Employee:
    emp = Employee(
        id=uuid4().hex[:36],
        employee_no=employee_no,
        name=name,
        department=department,
        job_family='tech',
        job_level='P5',
        hire_date=hire_date,
    )
    db.add(emp)
    db.flush()
    return emp


def _make_user(db: Session, *, role: str, department_names: list[str] | None = None,
               employee_id: str | None = None) -> User:
    user = User(
        id=uuid4().hex[:36],
        email=f'{uuid4().hex[:8]}@test.com',
        hashed_password='x',
        role=role,
        employee_id=employee_id,
    )
    db.add(user)
    db.flush()
    if department_names:
        for dept_name in department_names:
            dept = db.query(Department).filter(Department.name == dept_name).first()
            if dept is None:
                dept = Department(id=uuid4().hex[:36], name=dept_name)
                db.add(dept)
                db.flush()
            user.departments.append(dept)
        db.flush()
    return user


def _make_perf(db: Session, emp: Employee, year: int, grade: str) -> None:
    rec = PerformanceRecord(
        employee_id=emp.id,
        employee_no=emp.employee_no,
        year=year,
        grade=grade,
    )
    db.add(rec)
    db.flush()


def _make_attendance(db: Session, emp: Employee, period: str, leave_days: float) -> None:
    now = datetime.now(tz=timezone.utc)
    rec = AttendanceRecord(
        employee_id=emp.id,
        employee_no=emp.employee_no,
        period=period,
        non_statutory_leave_days=leave_days,
        data_as_of=now,
        synced_at=now,
    )
    db.add(rec)
    db.flush()


class TestCreateOverrideRequest:
    def setup_method(self) -> None:
        self.db, _ = _make_db()
        self.year = 2025
        self.ref_date = date(2026, 4, 1)

        # Create ineligible employee (bad perf grade D)
        self.emp = _make_employee(self.db, employee_no='E001', name='Alice', department='Engineering')
        _make_perf(self.db, self.emp, self.year, 'D')
        _make_attendance(self.db, self.emp, f'{self.year}-Q4', 5.0)

        # Create eligible employee
        self.eligible_emp = _make_employee(self.db, employee_no='E002', name='Bob', department='Engineering')
        _make_perf(self.db, self.eligible_emp, self.year, 'A')
        _make_attendance(self.db, self.eligible_emp, f'{self.year}-Q4', 5.0)

        # Requester: manager with Engineering access
        self.manager = _make_user(self.db, role='manager', department_names=['Engineering'])
        # HRBP with Engineering access
        self.hrbp = _make_user(self.db, role='hrbp', department_names=['Engineering'])
        # Admin user
        self.admin = _make_user(self.db, role='admin')
        # Manager without Engineering access
        self.other_manager = _make_user(self.db, role='manager', department_names=['Sales'])

        self.db.commit()

    def teardown_method(self) -> None:
        self.db.close()

    def _service(self) -> EligibilityService:
        return EligibilityService(self.db)

    def test_create_override_with_pending_hrbp_status(self) -> None:
        svc = self._service()
        override = svc.create_override_request(
            employee_id=self.emp.id,
            requester=self.manager,
            override_rules=['PERFORMANCE'],
            reason='Special circumstances',
            year=self.year,
            reference_date=self.ref_date,
        )
        assert override.status == 'pending_hrbp'
        assert override.employee_id == self.emp.id
        assert override.requester_id == self.manager.id
        assert override.override_rules == ['PERFORMANCE']

    def test_create_override_rejects_invalid_rule_codes(self) -> None:
        svc = self._service()
        with pytest.raises(HTTPException) as exc_info:
            svc.create_override_request(
                employee_id=self.emp.id,
                requester=self.manager,
                override_rules=['INVALID_RULE'],
                reason='test',
                year=self.year,
                reference_date=self.ref_date,
            )
        assert exc_info.value.status_code == 400

    def test_create_override_validates_access_scope(self) -> None:
        """HIGH concern #4a: requester must have AccessScope access to employee."""
        svc = self._service()
        with pytest.raises((HTTPException, PermissionError)):
            svc.create_override_request(
                employee_id=self.emp.id,
                requester=self.other_manager,
                override_rules=['PERFORMANCE'],
                reason='test',
                year=self.year,
                reference_date=self.ref_date,
            )

    def test_create_override_validates_employee_ineligible(self) -> None:
        """HIGH concern #4b: employee must be currently ineligible."""
        svc = self._service()
        with pytest.raises(HTTPException) as exc_info:
            svc.create_override_request(
                employee_id=self.eligible_emp.id,
                requester=self.manager,
                override_rules=['PERFORMANCE'],
                reason='test',
                year=self.year,
                reference_date=self.ref_date,
            )
        assert exc_info.value.status_code == 400

    def test_create_override_validates_rules_actually_failing(self) -> None:
        """HIGH concern #4c: selected rules must actually be failing."""
        svc = self._service()
        with pytest.raises(HTTPException) as exc_info:
            svc.create_override_request(
                employee_id=self.emp.id,
                requester=self.manager,
                override_rules=['TENURE'],  # TENURE is eligible for this employee
                reason='test',
                year=self.year,
                reference_date=self.ref_date,
            )
        assert exc_info.value.status_code == 400

    def test_create_override_rejects_duplicate_active(self) -> None:
        svc = self._service()
        svc.create_override_request(
            employee_id=self.emp.id,
            requester=self.manager,
            override_rules=['PERFORMANCE'],
            reason='First request',
            year=self.year,
            reference_date=self.ref_date,
        )
        self.db.commit()
        with pytest.raises(HTTPException) as exc_info:
            svc.create_override_request(
                employee_id=self.emp.id,
                requester=self.manager,
                override_rules=['PERFORMANCE'],
                reason='Second request',
                year=self.year,
                reference_date=self.ref_date,
            )
        assert exc_info.value.status_code == 409

    def test_create_override_admin_forbidden(self) -> None:
        """MEDIUM concern #5: admin cannot create override (per D-03)."""
        svc = self._service()
        with pytest.raises(HTTPException) as exc_info:
            svc.create_override_request(
                employee_id=self.emp.id,
                requester=self.admin,
                override_rules=['PERFORMANCE'],
                reason='test',
                year=self.year,
                reference_date=self.ref_date,
            )
        assert exc_info.value.status_code == 403


class TestDecideOverride:
    def setup_method(self) -> None:
        self.db, _ = _make_db()
        self.year = 2025
        self.ref_date = date(2026, 4, 1)

        self.emp = _make_employee(self.db, employee_no='E001', name='Alice', department='Engineering')
        _make_perf(self.db, self.emp, self.year, 'D')
        _make_attendance(self.db, self.emp, f'{self.year}-Q4', 5.0)

        self.manager = _make_user(self.db, role='manager', department_names=['Engineering'])
        self.hrbp = _make_user(self.db, role='hrbp', department_names=['Engineering'])
        self.admin = _make_user(self.db, role='admin')

        self.db.commit()

        # Create override via service
        svc = EligibilityService(self.db)
        self.override = svc.create_override_request(
            employee_id=self.emp.id,
            requester=self.manager,
            override_rules=['PERFORMANCE'],
            reason='Special case',
            year=self.year,
            reference_date=self.ref_date,
        )
        self.db.commit()

    def teardown_method(self) -> None:
        self.db.close()

    def _service(self) -> EligibilityService:
        return EligibilityService(self.db)

    def test_hrbp_approve_transitions_to_pending_admin(self) -> None:
        svc = self._service()
        result = svc.decide_override(
            override_id=self.override.id,
            approver=self.hrbp,
            decision='approve',
            comment='HRBP approves',
        )
        assert result.status == 'pending_admin'
        assert result.hrbp_approver_id == self.hrbp.id
        assert result.hrbp_decision == 'approve'

    def test_admin_approve_on_pending_admin_transitions_to_approved(self) -> None:
        svc = self._service()
        svc.decide_override(
            override_id=self.override.id,
            approver=self.hrbp,
            decision='approve',
            comment=None,
        )
        self.db.commit()
        result = svc.decide_override(
            override_id=self.override.id,
            approver=self.admin,
            decision='approve',
            comment='Admin final approval',
        )
        assert result.status == 'approved'
        assert result.admin_approver_id == self.admin.id

    def test_admin_on_pending_hrbp_raises_error(self) -> None:
        """HIGH concern #3: role-step binding."""
        svc = self._service()
        with pytest.raises(HTTPException) as exc_info:
            svc.decide_override(
                override_id=self.override.id,
                approver=self.admin,
                decision='approve',
                comment='Admin tries early',
            )
        assert exc_info.value.status_code == 403

    def test_hrbp_on_pending_admin_raises_error(self) -> None:
        """HIGH concern #3: role-step binding."""
        svc = self._service()
        svc.decide_override(
            override_id=self.override.id,
            approver=self.hrbp,
            decision='approve',
            comment=None,
        )
        self.db.commit()
        with pytest.raises(HTTPException) as exc_info:
            svc.decide_override(
                override_id=self.override.id,
                approver=self.hrbp,
                decision='approve',
                comment='HRBP tries again',
            )
        assert exc_info.value.status_code == 403

    def test_hrbp_reject_terminates_without_admin(self) -> None:
        svc = self._service()
        result = svc.decide_override(
            override_id=self.override.id,
            approver=self.hrbp,
            decision='reject',
            comment='Denied',
        )
        assert result.status == 'rejected'
        assert result.hrbp_decision == 'reject'
        assert result.admin_approver_id is None

    def test_admin_reject_at_pending_admin(self) -> None:
        svc = self._service()
        svc.decide_override(
            override_id=self.override.id,
            approver=self.hrbp,
            decision='approve',
            comment=None,
        )
        self.db.commit()
        result = svc.decide_override(
            override_id=self.override.id,
            approver=self.admin,
            decision='reject',
            comment='Admin rejects',
        )
        assert result.status == 'rejected'
        assert result.admin_decision == 'reject'


class TestApplyOverrides:
    def setup_method(self) -> None:
        self.db, _ = _make_db()
        self.year = 2025
        self.ref_date = date(2026, 4, 1)

        self.emp = _make_employee(self.db, employee_no='E001', name='Alice', department='Engineering')
        _make_perf(self.db, self.emp, self.year, 'D')
        _make_attendance(self.db, self.emp, f'{self.year}-Q4', 5.0)

        self.manager = _make_user(self.db, role='manager', department_names=['Engineering'])
        self.hrbp = _make_user(self.db, role='hrbp', department_names=['Engineering'])
        self.admin = _make_user(self.db, role='admin')

        self.db.commit()

    def teardown_method(self) -> None:
        self.db.close()

    def test_approved_override_changes_rule_to_overridden(self) -> None:
        svc = self._service()
        # Create and fully approve override
        override = svc.create_override_request(
            employee_id=self.emp.id,
            requester=self.manager,
            override_rules=['PERFORMANCE'],
            reason='Special',
            year=self.year,
            reference_date=self.ref_date,
        )
        self.db.commit()
        svc.decide_override(override_id=override.id, approver=self.hrbp, decision='approve', comment=None)
        self.db.commit()
        svc.decide_override(override_id=override.id, approver=self.admin, decision='approve', comment=None)
        self.db.commit()

        # Now check eligibility -- PERFORMANCE rule should be 'overridden'
        result = svc.check_employee(self.emp.id, reference_date=self.ref_date, year=self.year)
        # After _apply_overrides, the PERFORMANCE rule should have status 'overridden'
        # We need to call _apply_overrides explicitly or check through batch
        result = svc._apply_overrides(self.emp.id, result, self.year)
        perf_rule = [r for r in result.rules if r.rule_code == 'PERFORMANCE'][0]
        assert perf_rule.status == 'overridden'
        # Overall should be recalculated treating 'overridden' as 'eligible'
        # Since only PERFORMANCE was ineligible and now overridden, overall should not be ineligible
        # (other rules may still be eligible/data_missing)

    def _service(self) -> EligibilityService:
        return EligibilityService(self.db)
