"""Phase 32-03 Task 2b: confirm_import + cancel_import + AuditLog 真实字段。

关键安全断言：
- AuditLog 用真实字段 operator_id / target_type / target_id
  （**不是** D-13 文档假设的 actor_id / resource_type / resource_id）
- T-32-14: confirm 阶段文件 hash 校验（防外部篡改）
- T-32-15: replace 模式必须 confirm_replace=True 才接受
- 双 confirm 拒绝（status 已是 completed/failed/...）
- cancel 后删暂存文件
- cancel 对终态 job 幂等（不抛异常）
"""
from __future__ import annotations

import pytest


def test_confirm_import_writes_audit_log_with_real_fields(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """T-32-06：AuditLog 用真实字段 operator_id / target_type / target_id。"""
    from sqlalchemy import select
    from backend.app.services.import_service import ImportService
    from backend.app.models.audit_log import AuditLog
    employee_factory(employee_no='E00001')
    actor = user_factory(role='hrbp')
    svc = ImportService(db_session)
    # preview
    data = xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]])
    prev = svc.build_preview(
        import_type='hire_info', file_name='t.xlsx',
        raw_bytes=data, actor_id=str(actor.id),
    )
    # confirm
    resp = svc.confirm_import(
        job_id=prev.job_id, overwrite_mode='merge',
        actor_id=str(actor.id), actor_role='hrbp',
    )
    assert resp.status in ('completed', 'partial')
    # AuditLog 用真实字段名
    log = db_session.execute(
        select(AuditLog).where(
            AuditLog.target_id == prev.job_id,
            AuditLog.action == 'import_confirmed',
        )
    ).scalar_one()
    assert log.operator_id == str(actor.id)  # 真实字段：operator_id
    assert log.target_type == 'import_job'   # 真实字段：target_type
    assert log.target_id == prev.job_id      # 真实字段：target_id
    assert log.detail['overwrite_mode'] == 'merge'
    assert log.detail['import_type'] == 'hire_info'


def test_confirm_replace_requires_confirm_replace_flag(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """T-32-15：replace 模式必须 confirm_replace=True 才接受。"""
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001')
    actor = user_factory(role='hrbp')
    svc = ImportService(db_session)
    prev = svc.build_preview(
        import_type='hire_info', file_name='t.xlsx',
        raw_bytes=xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]]),
        actor_id=str(actor.id),
    )
    with pytest.raises(ValueError, match='替换模式'):
        svc.confirm_import(
            job_id=prev.job_id, overwrite_mode='replace', confirm_replace=False,
        )


def test_confirm_double_confirm_rejected(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """同 job_id 第二次调用 confirm（status 已是 completed/failed/partial）→ 拒绝。"""
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001')
    actor = user_factory(role='hrbp')
    svc = ImportService(db_session)
    prev = svc.build_preview(
        import_type='hire_info', file_name='t.xlsx',
        raw_bytes=xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]]),
        actor_id=str(actor.id),
    )
    svc.confirm_import(
        job_id=prev.job_id, overwrite_mode='merge', actor_id=str(actor.id),
    )
    with pytest.raises(ValueError, match='已确认或已取消'):
        svc.confirm_import(
            job_id=prev.job_id, overwrite_mode='merge', actor_id=str(actor.id),
        )


def test_confirm_hash_mismatch_raises(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir,
):
    """T-32-14：暂存文件被外部篡改 → confirm 应拒绝。"""
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    prev = svc.build_preview(
        import_type='hire_info', file_name='t.xlsx',
        raw_bytes=xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]]),
    )
    # 篡改暂存文件
    path = svc._staged_file_path(prev.job_id)
    path.write_bytes(b'tampered content')
    with pytest.raises(ValueError, match='hash mismatch'):
        svc.confirm_import(job_id=prev.job_id, overwrite_mode='merge')


def test_cancel_import_deletes_staged_file(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir,
):
    """cancel_import → status='cancelled' + 暂存文件被删除。"""
    from sqlalchemy import select
    from backend.app.services.import_service import ImportService
    from backend.app.models.import_job import ImportJob
    employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    prev = svc.build_preview(
        import_type='hire_info', file_name='t.xlsx',
        raw_bytes=xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]]),
    )
    assert svc._staged_file_path(prev.job_id).exists()
    svc.cancel_import(prev.job_id)
    job = db_session.execute(
        select(ImportJob).where(ImportJob.id == prev.job_id)
    ).scalar_one()
    assert job.status == 'cancelled'
    assert not svc._staged_file_path(prev.job_id).exists()


def test_cancel_idempotent_for_completed(
    db_session, import_job_factory, tmp_uploads_dir,
):
    """cancel 对终态 job 幂等（不抛异常，不改状态）。"""
    from backend.app.services.import_service import ImportService
    job = import_job_factory(import_type='hire_info', status='completed')
    svc = ImportService(db_session)
    svc.cancel_import(job.id)  # 不抛异常
    db_session.refresh(job)
    assert job.status == 'completed'  # 终态保持
