"""Phase 32.1 Task 1 — Schema field + Service helper for data freshness timestamp.

Covers D-15 (EligibilityResultSchema.data_updated_at) +
D-16 (EligibilityService.compute_data_updated_at — max of 4 sources).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.non_statutory_leave import NonStatutoryLeave
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord
from backend.app.schemas.eligibility import EligibilityResultSchema
from backend.app.services.eligibility_service import EligibilityService


def _make_db() -> Session:
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    db_path = (temp_root / f'elig-fresh-{uuid4().hex}.db').as_posix()
    engine = create_engine(
        f'sqlite+pysqlite:///{db_path}',
        connect_args={'check_same_thread': False},
        echo=False,
    )
    load_model_modules()
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return factory()


def _make_employee(db: Session, *, employee_no: str = 'E001') -> Employee:
    emp = Employee(
        employee_no=employee_no,
        name='测试员工',
        department='R&D',
        job_family='tech',
        job_level='P5',
        status='active',
        hire_date=date(2020, 1, 1),
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


# ------------------------------------------------------------------
# Schema-level
# ------------------------------------------------------------------

def test_schema_default_data_updated_at_is_none() -> None:
    schema = EligibilityResultSchema(overall_status='eligible', rules=[])
    assert schema.data_updated_at is None


def test_schema_accepts_datetime_and_serializes_iso8601() -> None:
    now = datetime.now(tz=timezone.utc)
    schema = EligibilityResultSchema(
        overall_status='eligible', rules=[], data_updated_at=now,
    )
    assert schema.data_updated_at is not None
    payload = schema.model_dump(mode='json')
    assert 'data_updated_at' in payload
    # ISO 8601 form
    assert isinstance(payload['data_updated_at'], str)
    assert 'T' in payload['data_updated_at']


# ------------------------------------------------------------------
# Service-level: compute_data_updated_at
# ------------------------------------------------------------------

def test_compute_data_updated_at_returns_employee_timestamp_when_only_employee_exists() -> None:
    db = _make_db()
    emp = _make_employee(db)
    service = EligibilityService(db)

    result = service.compute_data_updated_at(emp.id)

    # employee.updated_at 自动由 UpdatedAtMixin 设置
    assert result is not None
    assert result == emp.updated_at


def test_compute_data_updated_at_picks_max_across_sources() -> None:
    db = _make_db()
    emp = _make_employee(db)

    # 写一条最新的 performance record（在 employee.updated_at 之后）
    perf = PerformanceRecord(
        employee_id=emp.id,
        employee_no=emp.employee_no,
        year=2026,
        grade='B',
        source='manual',
    )
    db.add(perf)
    db.commit()
    db.refresh(perf)

    service = EligibilityService(db)
    result = service.compute_data_updated_at(emp.id)

    assert result is not None
    # 期待 max() 返回 perf.updated_at（最新写入）
    assert result >= emp.updated_at
    assert result == max(emp.updated_at, perf.updated_at)


def test_compute_data_updated_at_includes_salary_adjustment_and_leave() -> None:
    db = _make_db()
    emp = _make_employee(db)

    db.add(SalaryAdjustmentRecord(
        employee_id=emp.id,
        employee_no=emp.employee_no,
        adjustment_date=date(2026, 1, 1),
        adjustment_type='annual',
        amount=Decimal('100.00'),
        source='manual',
    ))
    db.add(NonStatutoryLeave(
        employee_id=emp.id,
        employee_no=emp.employee_no,
        year=2026,
        total_days=Decimal('1.5'),
        leave_type='事假',
        source='manual',
    ))
    db.commit()

    service = EligibilityService(db)
    result = service.compute_data_updated_at(emp.id)

    # 应取 4 个 source 的 max
    assert result is not None


def test_compute_data_updated_at_returns_none_for_unknown_employee() -> None:
    db = _make_db()
    service = EligibilityService(db)

    result = service.compute_data_updated_at(str(uuid4()))

    # 不存在的 employee 没有任何数据源 → None
    assert result is None


def test_compute_data_updated_at_does_not_raise_on_missing_employee() -> None:
    db = _make_db()
    service = EligibilityService(db)

    # 不应抛任何异常（端点层用 check_employee 的 404 处理）
    try:
        service.compute_data_updated_at(str(uuid4()))
    except Exception as exc:
        pytest.fail(f'compute_data_updated_at raised on missing employee: {exc!r}')
