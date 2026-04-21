from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.feishu_sync_log import FeishuSyncLog

load_model_modules()


@pytest.fixture()
def service_ctx(monkeypatch):
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    from backend.app.services import feishu_service as fs_module
    monkeypatch.setattr(fs_module, 'SessionLocal', session_factory)

    session = session_factory()
    emp = Employee(
        id='emp-1',
        employee_no='E001',
        name='Alice',
        department='Eng',
        job_family='SW',
        job_level='P5',
    )
    session.add(emp)
    session.commit()

    from backend.app.services.feishu_service import FeishuService
    service = FeishuService(session)

    mock_config = MagicMock()
    mock_config.app_id = 'app-id'
    mock_config.get_app_secret = lambda key: 'secret'
    monkeypatch.setattr(service, 'get_config', lambda: mock_config)
    monkeypatch.setattr(service, '_ensure_token', lambda app_id, app_secret: 'tok')

    try:
        yield service, session, monkeypatch
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# Test 8-12: D-02 新语义 — year/grade/adjustment_date 解析失败归 mapping_failed
# ---------------------------------------------------------------------------


def test_performance_year_parse_failure_counts_as_mapping_failed(service_ctx) -> None:
    """Test 8: year='not-a-number' → log.mapping_failed_count=1, skipped_count=0。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {'employee_no': 'E001', 'year': 'not-a-number', 'grade': 'A'}
        ],
    )

    log = service.sync_performance_records(app_token='t', table_id='tbl')
    assert log.mapping_failed_count == 1
    assert log.skipped_count == 0
    assert log.status == 'partial'


def test_performance_invalid_grade_counts_as_mapping_failed(service_ctx) -> None:
    """Test 9: grade='Z' → log.mapping_failed_count=1。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [{'employee_no': 'E001', 'year': 2026, 'grade': 'Z'}],
    )

    log = service.sync_performance_records(app_token='t', table_id='tbl')
    assert log.mapping_failed_count == 1
    assert log.status == 'partial'


def test_performance_unmatched_employee_no_counts_as_unmatched_not_mapping_failed(
    service_ctx,
) -> None:
    """Test 10: emp_no='NONEXIST' → unmatched_count=1, mapping_failed_count=0。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [{'employee_no': 'NONEXIST', 'year': 2026, 'grade': 'A'}],
    )

    log = service.sync_performance_records(app_token='t', table_id='tbl')
    assert log.unmatched_count == 1
    assert log.mapping_failed_count == 0
    assert log.status == 'partial'


def test_salary_adjustments_date_parse_failure_counts_as_mapping_failed(
    service_ctx,
) -> None:
    """Test 11: adjustment_date='garbage' → log.mapping_failed_count=1。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {
                'employee_no': 'E001',
                'adjustment_date': 'garbage',
                'adjustment_type': '年度调薪',
            }
        ],
    )

    log = service.sync_salary_adjustments(app_token='t', table_id='tbl')
    assert log.mapping_failed_count == 1
    assert log.status == 'partial'


def test_performance_mixed_success_mapping_failed_unmatched(service_ctx) -> None:
    """Test 12: 2 条合法 + 1 条 year 错 + 1 条 emp 找不到 → synced=2, mapping_failed=1, unmatched=1。"""
    service, session, monkeypatch = service_ctx

    # Seed additional employee E002
    emp2 = Employee(
        id='emp-2',
        employee_no='E002',
        name='Bob',
        department='Eng',
        job_family='SW',
        job_level='P5',
    )
    session.add(emp2)
    session.commit()

    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {'employee_no': 'E001', 'year': 2026, 'grade': 'A'},
            {'employee_no': 'E002', 'year': 2026, 'grade': 'B'},
            {'employee_no': 'E001', 'year': 'BAD', 'grade': 'A'},  # mapping_failed
            {'employee_no': 'NONEXIST', 'year': 2026, 'grade': 'A'},  # unmatched
        ],
    )

    log = service.sync_performance_records(app_token='t', table_id='tbl')
    assert log.synced_count == 2
    assert log.mapping_failed_count == 1
    assert log.unmatched_count == 1
    assert log.status == 'partial'


# ---------------------------------------------------------------------------
# Additional: non_statutory_leave / hire_info mapping_failed for completeness
# ---------------------------------------------------------------------------


def test_non_statutory_leave_invalid_total_days_counts_as_mapping_failed(
    service_ctx,
) -> None:
    """leave total_days 非数字 → mapping_failed_count=1。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {
                'employee_no': 'E001',
                'year': 2026,
                'total_days': 'garbage',
                'leave_type': '事假',
            }
        ],
    )

    log = service.sync_non_statutory_leave(app_token='t', table_id='tbl')
    assert log.mapping_failed_count == 1
    assert log.status == 'partial'
