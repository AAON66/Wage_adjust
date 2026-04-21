from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.feishu_sync_log import FeishuSyncLog

load_model_modules()


# ---------------------------------------------------------------------------
# Fixture: in-memory SQLite with StaticPool, patched SessionLocal pointing to
# the same engine so helper's independent sessions share the DB.
# ---------------------------------------------------------------------------


@pytest.fixture()
def patched_service(monkeypatch):
    """Yield (engine, service, session) with SessionLocal patched to the test engine."""
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    # Patch SessionLocal in the module where helper imports it
    from backend.app.services import feishu_service as fs_module
    monkeypatch.setattr(fs_module, 'SessionLocal', session_factory)

    session = session_factory()
    from backend.app.services.feishu_service import FeishuService
    service = FeishuService(session)
    try:
        yield engine, service, session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_helper_happy_path_writes_success_log(patched_service) -> None:
    """Test 14 happy path: fn 返回 _SyncCounters(success=5) → status='success'。"""
    from backend.app.services.feishu_service import _SyncCounters

    engine, service, session = patched_service

    def fake_body(*, sync_log_id: str) -> _SyncCounters:
        return _SyncCounters(success=5, updated=3, total_fetched=8)

    log_id = service._with_sync_log('performance', fake_body, triggered_by='tester')
    assert log_id

    # Use a fresh session to verify the persisted row
    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        log = fresh.get(FeishuSyncLog, log_id)
        assert log is not None
        assert log.sync_type == 'performance'
        assert log.status == 'success'
        assert log.synced_count == 5
        assert log.updated_count == 3
        assert log.total_fetched == 8
        assert log.triggered_by == 'tester'
        assert log.finished_at is not None
    finally:
        fresh.close()


def test_helper_partial_status_derived_from_unmatched(patched_service) -> None:
    """Test 15 partial path: unmatched=2 → status='partial'。"""
    from backend.app.services.feishu_service import _SyncCounters

    engine, service, session = patched_service

    def body(*, sync_log_id: str) -> _SyncCounters:
        return _SyncCounters(success=5, unmatched=2, total_fetched=7)

    log_id = service._with_sync_log('hire_info', body)

    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        log = fresh.get(FeishuSyncLog, log_id)
        assert log.status == 'partial'
        assert log.unmatched_count == 2
    finally:
        fresh.close()


def test_helper_business_exception_writes_failed_log_and_reraises(patched_service) -> None:
    """Test 16: fn 抛 RuntimeError → helper 重抛 + log.status='failed'。"""
    engine, service, session = patched_service

    def failing_body(*, sync_log_id: str):
        raise RuntimeError('upstream exploded')

    with pytest.raises(RuntimeError, match='upstream exploded'):
        service._with_sync_log('hire_info', failing_body)

    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        log = fresh.scalar(
            select(FeishuSyncLog).where(FeishuSyncLog.sync_type == 'hire_info')
        )
        assert log is not None
        assert log.status == 'failed'
        assert log.error_message == 'upstream exploded'
        assert log.finished_at is not None
    finally:
        fresh.close()


def test_helper_rollback_isolation_from_business_session(patched_service) -> None:
    """Test 17 rollback isolation (D-13): 业务 rollback 不影响 log。

    即使业务 fn 在 self.db.add(...) 后抛异常，helper 用独立 session 写的 running log
    和 failed log 都应该可见（独立事务）。
    """
    from backend.app.models.employee import Employee
    from backend.app.services.feishu_service import _SyncCounters

    engine, service, session = patched_service

    def buggy_body(*, sync_log_id: str) -> _SyncCounters:
        # 往业务 session 写东西但不 commit
        emp = Employee(
            id='will-not-commit',
            employee_no='X999',
            name='Ghost',
            department='X',
            job_family='X',
            job_level='X',
        )
        service.db.add(emp)
        # 抛业务异常 → helper 会 rollback business session
        raise RuntimeError('fail after add')

    with pytest.raises(RuntimeError, match='fail after add'):
        service._with_sync_log('salary_adjustments', buggy_body)

    # Verify the log was still written (independent session)
    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        log = fresh.scalar(
            select(FeishuSyncLog).where(
                FeishuSyncLog.sync_type == 'salary_adjustments'
            )
        )
        assert log is not None
        assert log.status == 'failed'
        # Ghost employee should NOT exist (business rollback worked)
        emp_row = fresh.get(Employee, 'will-not-commit')
        assert emp_row is None
    finally:
        fresh.close()


def test_helper_finalize_exception_does_not_overwrite_business_exception(
    patched_service, monkeypatch
) -> None:
    """Test 18 log finalize exception swallow (Pitfall A):
    finalize 抛异常时，business exception 仍被重抛。
    """
    engine, service, session = patched_service

    def failing_body(*, sync_log_id: str):
        raise RuntimeError('real business error')

    # Patch SessionLocal in the feishu_service module so the SECOND call
    # (finalize stage) throws. First call (running-log stage) must succeed.
    from backend.app.services import feishu_service as fs_module
    original_SessionLocal = fs_module.SessionLocal
    call_count = {'n': 0}

    def flaky_session_local():
        call_count['n'] += 1
        if call_count['n'] >= 2:
            raise RuntimeError('finalize session broken')
        return original_SessionLocal()

    monkeypatch.setattr(fs_module, 'SessionLocal', flaky_session_local)

    # Business exception must be re-raised (not overwritten by finalize failure)
    with pytest.raises(RuntimeError, match='real business error'):
        service._with_sync_log('performance', failing_body)


def test_helper_rejects_invalid_sync_type(patched_service) -> None:
    """Test 19: helper 接收 sync_type='invalid_type' 抛 ValueError。"""
    from backend.app.services.feishu_service import _SyncCounters

    engine, service, session = patched_service
    with pytest.raises(ValueError, match='Unknown sync_type'):
        service._with_sync_log('bogus', lambda **kw: _SyncCounters())


def test_helper_running_log_visible_before_fn_completes(patched_service) -> None:
    """Test 20: running log 在独立 session 中创建后，另一个 session 能立即查到。"""
    from backend.app.services.feishu_service import _SyncCounters

    engine, service, session = patched_service

    captured: dict = {}

    def observing_body(*, sync_log_id: str) -> _SyncCounters:
        # In the middle of the body, spin up another session to verify running log exists
        from backend.app.services import feishu_service as fs_module
        peek = fs_module.SessionLocal()
        try:
            log = peek.get(FeishuSyncLog, sync_log_id)
            captured['status'] = log.status if log else None
            captured['sync_type'] = log.sync_type if log else None
        finally:
            peek.close()
        return _SyncCounters(success=1, total_fetched=1)

    service._with_sync_log('attendance', observing_body)
    assert captured['status'] == 'running'
    assert captured['sync_type'] == 'attendance'


def test_helper_returns_type_error_when_fn_returns_non_counters(patched_service) -> None:
    """Body 返回非 _SyncCounters 时 helper 走 business-error 路径写 failed log."""
    engine, service, session = patched_service

    def bad_return_body(*, sync_log_id: str):
        return {'synced': 1}  # dict, not _SyncCounters

    with pytest.raises(TypeError):
        service._with_sync_log('performance', bad_return_body)

    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        log = fresh.scalar(
            select(FeishuSyncLog).where(FeishuSyncLog.sync_type == 'performance')
        )
        assert log is not None
        assert log.status == 'failed'
    finally:
        fresh.close()
