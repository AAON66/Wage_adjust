"""API-level tests for eligibility visibility and role-based access control."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings
from backend.app.core.database import Base
from backend.app.core.security import create_access_token
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.attendance_record import AttendanceRecord
from backend.app.models.department import Department
from backend.app.models.employee import Employee
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.user import User


# ---------------------------------------------------------------------------
# Lightweight credential holder (avoids detached ORM state)
# ---------------------------------------------------------------------------

@dataclass
class UserCreds:
    id: str
    role: str
    token_version: int


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

class _TestContext:
    """Set up an isolated SQLite DB + FastAPI TestClient."""

    def __init__(self) -> None:
        temp_root = Path('.tmp').resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = (temp_root / f'elig-api-{uuid4().hex}.db').as_posix()
        self.settings = Settings(
            database_url=f'sqlite+pysqlite:///{db_path}',
            allow_self_registration=True,
        )
        self.engine = create_engine(
            self.settings.database_url,
            connect_args={'check_same_thread': False},
            echo=False,
        )
        load_model_modules()
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False,
        )
        self.app = create_app(self.settings)
        self.app.dependency_overrides[get_db] = self._override_get_db

    def _override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    def db(self) -> Session:
        return self.session_factory()

    def auth_header(self, creds: UserCreds) -> dict[str, str]:
        token = create_access_token(
            subject=creds.id,
            role=creds.role,
            settings=self.settings,
            token_version=creds.token_version,
        )
        return {'Authorization': f'Bearer {token}'}


def _make_employee(db: Session, *, employee_no: str, name: str, department: str,
                   hire_date: date = date(2020, 1, 1)) -> Employee:
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
               employee_id: str | None = None) -> UserCreds:
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
    return UserCreds(id=user.id, role=user.role, token_version=user.token_version)


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEligibilityVisibility:
    """Test role-based access on all eligibility endpoints."""

    def setup_method(self) -> None:
        self.ctx = _TestContext()
        db = self.ctx.db()

        # Employees
        self.emp_eng = _make_employee(db, employee_no='E001', name='Alice', department='Engineering')
        self.emp_sales = _make_employee(db, employee_no='E002', name='Bob', department='Sales')

        # Store IDs before session closes
        self.emp_eng_id = self.emp_eng.id
        self.emp_sales_id = self.emp_sales.id

        _make_perf(db, self.emp_eng, 2025, 'D')  # ineligible
        _make_attendance(db, self.emp_eng, '2025-Q4', 5.0)
        _make_perf(db, self.emp_sales, 2025, 'A')
        _make_attendance(db, self.emp_sales, '2025-Q4', 5.0)

        # Users (returns UserCreds, not ORM objects)
        self.admin = _make_user(db, role='admin')
        self.hrbp = _make_user(db, role='hrbp', department_names=['Engineering'])
        self.manager_eng = _make_user(db, role='manager', department_names=['Engineering'])
        self.manager_sales = _make_user(db, role='manager', department_names=['Sales'])
        self.employee_user = _make_user(
            db, role='employee', employee_id=self.emp_eng_id,
        )

        db.commit()
        db.close()

        self.client = TestClient(self.ctx.app)

    # -- Employee role gets 403 on batch --
    def test_employee_role_403_on_batch(self) -> None:
        resp = self.client.get(
            '/api/v1/eligibility/batch',
            headers=self.ctx.auth_header(self.employee_user),
        )
        assert resp.status_code == 403

    # -- Employee role gets 403 on single employee --
    def test_employee_role_403_on_single_employee(self) -> None:
        resp = self.client.get(
            f'/api/v1/eligibility/{self.emp_eng_id}',
            headers=self.ctx.auth_header(self.employee_user),
        )
        assert resp.status_code == 403

    # -- Employee role gets 403 on override create --
    def test_employee_role_403_on_override_create(self) -> None:
        resp = self.client.post(
            '/api/v1/eligibility/overrides',
            json={
                'employee_id': self.emp_eng_id,
                'override_rules': ['PERFORMANCE'],
                'reason': 'test',
            },
            headers=self.ctx.auth_header(self.employee_user),
        )
        assert resp.status_code == 403

    # -- Employee role gets 403 on performance-records sub-resource --
    def test_employee_role_403_on_performance_records(self) -> None:
        resp = self.client.get(
            f'/api/v1/eligibility/{self.emp_eng_id}/performance-records',
            headers=self.ctx.auth_header(self.employee_user),
        )
        assert resp.status_code == 403

    # -- Admin gets 200 on batch --
    def test_admin_200_on_batch(self) -> None:
        resp = self.client.get(
            '/api/v1/eligibility/batch',
            headers=self.ctx.auth_header(self.admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 2

    # -- HRBP gets 200 on batch (department-scoped) --
    def test_hrbp_200_on_batch_scoped(self) -> None:
        resp = self.client.get(
            '/api/v1/eligibility/batch',
            headers=self.ctx.auth_header(self.hrbp),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1  # Only Engineering

    # -- Manager gets 200 on batch (department-scoped) --
    def test_manager_200_on_batch_scoped(self) -> None:
        resp = self.client.get(
            '/api/v1/eligibility/batch',
            headers=self.ctx.auth_header(self.manager_eng),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1  # Only Engineering

    # -- Manager gets 403 on single employee outside department --
    def test_manager_403_on_other_department_employee(self) -> None:
        resp = self.client.get(
            f'/api/v1/eligibility/{self.emp_sales_id}',
            headers=self.ctx.auth_header(self.manager_eng),
        )
        assert resp.status_code == 403

    # -- Admin gets 403 on override create (per D-03) --
    def test_admin_403_on_override_create(self) -> None:
        resp = self.client.post(
            '/api/v1/eligibility/overrides',
            json={
                'employee_id': self.emp_eng_id,
                'override_rules': ['PERFORMANCE'],
                'reason': 'test',
            },
            headers=self.ctx.auth_header(self.admin),
        )
        assert resp.status_code == 403

    # -- Manager can create override for department employee --
    def test_manager_creates_override_201(self) -> None:
        resp = self.client.post(
            '/api/v1/eligibility/overrides',
            json={
                'employee_id': self.emp_eng_id,
                'override_rules': ['PERFORMANCE'],
                'reason': 'Exceptional project delivery',
                'year': 2025,
                'reference_date': '2026-04-01',
            },
            headers=self.ctx.auth_header(self.manager_eng),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['status'] == 'pending_hrbp'
        assert data['override_rules'] == ['PERFORMANCE']
        assert data['employee_id'] == self.emp_eng_id

    # -- Override decide enforces role-step binding --
    def test_override_decide_role_step_binding(self) -> None:
        # Create override
        create_resp = self.client.post(
            '/api/v1/eligibility/overrides',
            json={
                'employee_id': self.emp_eng_id,
                'override_rules': ['PERFORMANCE'],
                'reason': 'test',
                'year': 2025,
                'reference_date': '2026-04-01',
            },
            headers=self.ctx.auth_header(self.manager_eng),
        )
        assert create_resp.status_code == 201
        override_id = create_resp.json()['id']

        # Admin tries to decide on pending_hrbp -> 403
        resp = self.client.post(
            f'/api/v1/eligibility/overrides/{override_id}/decide',
            json={'decision': 'approve'},
            headers=self.ctx.auth_header(self.admin),
        )
        assert resp.status_code == 403

        # HRBP approves -> pending_admin
        resp = self.client.post(
            f'/api/v1/eligibility/overrides/{override_id}/decide',
            json={'decision': 'approve', 'comment': 'HRBP ok'},
            headers=self.ctx.auth_header(self.hrbp),
        )
        assert resp.status_code == 200
        assert resp.json()['status'] == 'pending_admin'

        # HRBP tries to decide on pending_admin -> 403
        resp = self.client.post(
            f'/api/v1/eligibility/overrides/{override_id}/decide',
            json={'decision': 'approve'},
            headers=self.ctx.auth_header(self.hrbp),
        )
        assert resp.status_code == 403

        # Admin approves -> approved
        resp = self.client.post(
            f'/api/v1/eligibility/overrides/{override_id}/decide',
            json={'decision': 'approve', 'comment': 'Admin ok'},
            headers=self.ctx.auth_header(self.admin),
        )
        assert resp.status_code == 200
        assert resp.json()['status'] == 'approved'
