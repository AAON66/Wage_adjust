from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.feishu_sync_log import FeishuSyncLog

load_model_modules()


# ---------------------------------------------------------------------------
# Fixture: in-memory SQLite + patched SessionLocal + seeded employee E001,
# with FeishuService-level collaborators mocked (get_config / _ensure_token / _fetch_all_records).
# ---------------------------------------------------------------------------


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
# Test 1-4: 四个新 sync 方法写入 FeishuSyncLog + 正确 sync_type
# ---------------------------------------------------------------------------


def test_sync_performance_records_writes_log_with_sync_type_performance(service_ctx) -> None:
    """Test 1: sync_performance_records 写 sync_type='performance' + synced=1 + triggered_by。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [{'employee_no': 'E001', 'year': 2026, 'grade': 'A'}],
    )

    log = service.sync_performance_records(
        app_token='t', table_id='tbl', triggered_by='user-1'
    )
    assert isinstance(log, FeishuSyncLog)
    assert log.sync_type == 'performance'
    assert log.status == 'success'
    assert log.synced_count == 1
    assert log.triggered_by == 'user-1'


def test_sync_salary_adjustments_writes_log_with_sync_type_salary_adjustments(
    service_ctx,
) -> None:
    """Test 2: sync_salary_adjustments 写 sync_type='salary_adjustments'。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {
                'employee_no': 'E001',
                'adjustment_date': '2026-01-01',
                'adjustment_type': '年度调薪',
                'amount': '1000',
            }
        ],
    )

    log = service.sync_salary_adjustments(
        app_token='t', table_id='tbl', triggered_by='user-2'
    )
    assert log.sync_type == 'salary_adjustments'
    assert log.status == 'success'
    assert log.synced_count == 1
    assert log.triggered_by == 'user-2'


def test_sync_hire_info_writes_log_with_sync_type_hire_info(service_ctx) -> None:
    """Test 3: sync_hire_info 写 sync_type='hire_info'。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {
                'employee_no': 'E001',
                'hire_date': '2023-06-15',
                'last_salary_adjustment_date': '2025-01-01',
            }
        ],
    )

    log = service.sync_hire_info(
        app_token='t', table_id='tbl', triggered_by='user-3'
    )
    assert log.sync_type == 'hire_info'
    assert log.status == 'success'
    assert log.synced_count == 1
    assert log.triggered_by == 'user-3'


def test_sync_non_statutory_leave_writes_log_with_sync_type_non_statutory_leave(
    service_ctx,
) -> None:
    """Test 4: sync_non_statutory_leave 写 sync_type='non_statutory_leave'。"""
    service, session, monkeypatch = service_ctx
    monkeypatch.setattr(
        service,
        '_fetch_all_records',
        lambda *a, **kw: [
            {
                'employee_no': 'E001',
                'year': 2026,
                'total_days': '5.5',
                'leave_type': '事假',
            }
        ],
    )

    log = service.sync_non_statutory_leave(
        app_token='t', table_id='tbl', triggered_by='user-4'
    )
    assert log.sync_type == 'non_statutory_leave'
    assert log.status == 'success'
    assert log.synced_count == 1
    assert log.triggered_by == 'user-4'


# ---------------------------------------------------------------------------
# Test 5-6: sync_attendance 外部签名不变（Pitfall F）
# ---------------------------------------------------------------------------


def test_sync_attendance_signature_mode_triggered_by_returns_feishu_sync_log(
    service_ctx,
) -> None:
    """Test 5: sync_attendance(mode, triggered_by) 仍返回 FeishuSyncLog。"""
    import json

    service, session, monkeypatch = service_ctx

    # active config with field_mapping
    mock_config = MagicMock()
    mock_config.app_id = 'app-id'
    mock_config.get_app_secret = lambda key: 'secret'
    mock_config.bitable_app_token = 'app-tok'
    mock_config.bitable_table_id = 'tbl'
    mock_config.field_mapping = json.dumps({'工号': 'employee_no'})
    monkeypatch.setattr(service, 'get_config', lambda: mock_config)

    # no records, so synced/updated all 0
    monkeypatch.setattr(service, '_fetch_all_records', lambda *a, **kw: [])

    log = service.sync_attendance('full', triggered_by='sched-1')
    assert isinstance(log, FeishuSyncLog)
    assert log.sync_type == 'attendance'
    assert log.mode == 'full'
    assert log.triggered_by == 'sched-1'
    assert log.status == 'success'


def test_sync_attendance_mode_incremental_preserved(service_ctx) -> None:
    """Test 6: sync_attendance 的 mode='incremental' 透传到 log.mode。"""
    import json

    service, session, monkeypatch = service_ctx

    mock_config = MagicMock()
    mock_config.app_id = 'app-id'
    mock_config.get_app_secret = lambda key: 'secret'
    mock_config.bitable_app_token = 'app-tok'
    mock_config.bitable_table_id = 'tbl'
    mock_config.field_mapping = json.dumps({'工号': 'employee_no'})
    monkeypatch.setattr(service, 'get_config', lambda: mock_config)
    monkeypatch.setattr(service, '_fetch_all_records', lambda *a, **kw: [])

    log = service.sync_attendance('incremental', triggered_by='sched-2')
    assert log.sync_type == 'attendance'
    assert log.mode == 'incremental'


# ---------------------------------------------------------------------------
# Test 7: 业务 fn 抛异常 → log.status='failed'
# ---------------------------------------------------------------------------


def test_sync_performance_records_body_exception_marks_log_failed(service_ctx) -> None:
    """Test 7: 业务 body 抛异常 → log.status='failed' + error_message 非空。"""
    service, session, monkeypatch = service_ctx

    def fetch_raises(*args, **kwargs):
        raise RuntimeError('feishu api exploded')

    monkeypatch.setattr(service, '_fetch_all_records', fetch_raises)

    with pytest.raises(RuntimeError, match='feishu api exploded'):
        service.sync_performance_records(app_token='t', table_id='tbl')

    # Find the log in an independent session
    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        log = fresh.scalar(
            select(FeishuSyncLog).where(FeishuSyncLog.sync_type == 'performance')
        )
        assert log is not None
        assert log.status == 'failed'
        assert log.error_message
        assert 'feishu api exploded' in log.error_message
    finally:
        fresh.close()
