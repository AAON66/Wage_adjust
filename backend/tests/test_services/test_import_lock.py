"""Phase 32-03 Task 1: ImportService.is_import_running per-import_type 锁。

测试覆盖：
- 无 job 时返回 False
- 同 type processing/previewing 持锁
- 不同 type 互不影响
- 终态（completed/failed/partial/cancelled）不持锁
- get_active_job 返回最新创建的活跃 job
"""
from __future__ import annotations

import pytest


def test_is_import_running_no_jobs(db_session):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    assert svc.is_import_running('hire_info') is False
    assert svc.is_import_running() is False


def test_is_import_running_filters_by_type(db_session, import_job_factory):
    from backend.app.services.import_service import ImportService
    import_job_factory(import_type='hire_info', status='processing')
    svc = ImportService(db_session)
    assert svc.is_import_running('hire_info') is True
    assert svc.is_import_running('performance_grades') is False
    assert svc.is_import_running() is True  # 不传 type 时全局检查


def test_is_import_running_locks_previewing(db_session, import_job_factory):
    from backend.app.services.import_service import ImportService
    import_job_factory(import_type='non_statutory_leave', status='previewing')
    svc = ImportService(db_session)
    assert svc.is_import_running('non_statutory_leave') is True


def test_is_import_running_terminal_does_not_lock(db_session, import_job_factory):
    from backend.app.services.import_service import ImportService
    for status in ['completed', 'failed', 'partial', 'cancelled']:
        import_job_factory(import_type='hire_info', status=status)
    svc = ImportService(db_session)
    assert svc.is_import_running('hire_info') is False


def test_get_active_job_returns_latest(db_session, import_job_factory):
    from backend.app.services.import_service import ImportService
    old = import_job_factory(import_type='hire_info', status='previewing')
    new = import_job_factory(import_type='hire_info', status='processing')
    svc = ImportService(db_session)
    active = svc.get_active_job('hire_info')
    assert active is not None
    assert active.id == new.id  # 最新创建优先
