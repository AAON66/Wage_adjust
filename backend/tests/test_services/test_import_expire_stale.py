"""Phase 32-03 Task 1: expire_stale_import_jobs 双时限清理。

测试覆盖：
- processing 30min → failed + result_summary.error='timeout'
- previewing 60min → cancelled + 删暂存文件
- 终态保持不动
- 无 job 时安全返回
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def test_expire_stale_processing_to_failed(db_session, import_job_factory, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    job = import_job_factory(import_type='hire_info', status='processing')
    # 倒车 created_at 到 45min 前
    old_time = datetime.now(timezone.utc) - timedelta(minutes=45)
    job.created_at = old_time
    db_session.commit()
    svc = ImportService(db_session)
    result = svc.expire_stale_import_jobs(processing_timeout_minutes=30)
    assert result['processing'] == 1
    db_session.refresh(job)
    assert job.status == 'failed'
    assert job.result_summary.get('error') == 'timeout'


def test_expire_stale_previewing_to_cancelled_and_deletes_file(
    db_session, import_job_factory, tmp_uploads_dir,
):
    from backend.app.services.import_service import ImportService
    job = import_job_factory(import_type='hire_info', status='previewing')
    svc = ImportService(db_session)
    # 创建假暂存文件
    svc._save_staged_file(job.id, b'fake xlsx bytes')
    assert svc._staged_file_path(job.id).exists()
    # 倒车 created_at 到 70min 前
    job.created_at = datetime.now(timezone.utc) - timedelta(minutes=70)
    db_session.commit()
    result = svc.expire_stale_import_jobs(previewing_timeout_minutes=60)
    assert result['previewing'] == 1
    db_session.refresh(job)
    assert job.status == 'cancelled'
    assert not svc._staged_file_path(job.id).exists()  # 文件已删
    assert job.result_summary.get('cancellation_reason') == 'preview_timeout'


def test_expire_stale_does_not_touch_terminal(db_session, import_job_factory, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    job = import_job_factory(import_type='hire_info', status='completed')
    job.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
    db_session.commit()
    svc = ImportService(db_session)
    result = svc.expire_stale_import_jobs()
    assert result == {'processing': 0, 'previewing': 0}
    db_session.refresh(job)
    assert job.status == 'completed'


def test_expire_stale_no_jobs(db_session, tmp_uploads_dir):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    assert svc.expire_stale_import_jobs() == {'processing': 0, 'previewing': 0}
