"""Phase 32-04 Task 1: POST /eligibility-import/excel/{job_id}/confirm + .../cancel 端到端测试。

覆盖：
  - confirm merge 成功 + AuditLog 写入（用真实字段名 operator_id/target_type/target_id）
  - confirm replace + confirm_replace=False → 422
  - confirm replace + confirm_replace=True → 200
  - confirm 双 confirm 同 job_id → 409
  - confirm 未知 job_id → 404
  - cancel previewing → 204
  - cancel employee 角色 → 403
"""
from __future__ import annotations

import io


def _seed_employee(api_ctx, *, employee_no: str = 'E00001'):
    from backend.app.models.employee import Employee
    db = api_ctx.session_factory()
    try:
        emp = Employee(
            employee_no=employee_no,
            name='测试员工',
            department='R&D',
            job_family='engineering',
            job_level='P5',
            status='active',
        )
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return emp.id
    finally:
        db.close()


def _seed_import_job(api_ctx, *, import_type: str, status: str) -> str:
    from backend.app.models.import_job import ImportJob
    db = api_ctx.session_factory()
    try:
        job = ImportJob(
            file_name='seed.xlsx',
            import_type=import_type,
            status=status,
            total_rows=0,
            success_rows=0,
            failed_rows=0,
            result_summary={},
            overwrite_mode='merge',
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id
    finally:
        db.close()


def _do_preview(client_hrbp, api_ctx, xlsx_factory, import_type: str = 'hire_info') -> str:
    """通过 API 完整 preview 一次（确保 staged 文件 + sha256 写入），返回 job_id。"""
    _seed_employee(api_ctx, employee_no='E00001')
    if import_type == 'hire_info':
        data = xlsx_factory[import_type](rows=[['E00001', '2026-01-01', None]])
    elif import_type == 'performance_grades':
        data = xlsx_factory[import_type](rows=[['E00001', 2026, 'A']])
    else:
        data = xlsx_factory[import_type]()
    resp = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/preview?import_type={import_type}',
        files={'file': ('t.xlsx', io.BytesIO(data),
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['job_id']


# --------- confirm 成功 + AuditLog ---------

def test_confirm_endpoint_writes_audit_log(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """confirm merge 成功 → 200 + AuditLog 真实字段写入。"""
    from backend.app.models.audit_log import AuditLog
    from sqlalchemy import select
    job_id = _do_preview(client_hrbp, _api_context, xlsx_factory)
    resp = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'merge', 'confirm_replace': False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['job_id'] == job_id
    assert body['status'] in ('completed', 'partial', 'failed')

    # 验证 AuditLog 用真实字段名 operator_id / target_type / target_id
    db = _api_context.session_factory()
    try:
        log = db.execute(select(AuditLog).where(
            AuditLog.action == 'import_confirmed',
            AuditLog.target_id == job_id,
        )).scalar_one()
        assert log.target_type == 'import_job'
        assert log.detail['overwrite_mode'] == 'merge'
        assert log.detail['import_type'] == 'hire_info'
    finally:
        db.close()


# --------- replace 二次确认 ---------

def test_confirm_replace_without_flag_returns_422(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """replace 模式 + confirm_replace=False → 422（T-32-15）。"""
    job_id = _do_preview(client_hrbp, _api_context, xlsx_factory)
    resp = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'replace', 'confirm_replace': False},
    )
    assert resp.status_code == 422


def test_confirm_replace_with_flag_succeeds(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """replace 模式 + confirm_replace=True → 200。"""
    job_id = _do_preview(client_hrbp, _api_context, xlsx_factory)
    resp = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'replace', 'confirm_replace': True},
    )
    assert resp.status_code == 200, resp.text


# --------- 双 confirm 防护 ---------

def test_confirm_double_returns_409(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """同 job_id 第二次 confirm → 409（job 已不在 previewing 状态）。"""
    job_id = _do_preview(client_hrbp, _api_context, xlsx_factory)
    r1 = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'merge', 'confirm_replace': False},
    )
    assert r1.status_code == 200, r1.text
    r2 = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'merge', 'confirm_replace': False},
    )
    assert r2.status_code == 409


# --------- 错误路径 ---------

def test_confirm_unknown_job_returns_404(client_hrbp, tmp_uploads_dir):
    """未知 job_id → 404。"""
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/00000000-0000-0000-0000-000000000000/confirm',
        json={'overwrite_mode': 'merge', 'confirm_replace': False},
    )
    assert resp.status_code == 404


# --------- cancel 端点 ---------

def test_cancel_endpoint_returns_204(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """cancel previewing job → 204。"""
    job_id = _do_preview(client_hrbp, _api_context, xlsx_factory)
    resp = client_hrbp.post(f'/api/v1/eligibility-import/excel/{job_id}/cancel')
    assert resp.status_code == 204


def test_cancel_employee_role_forbidden(
    client_employee, _api_context, tmp_uploads_dir,
):
    """employee 角色 cancel → 403（T-32-04）。"""
    job_id = _seed_import_job(_api_context, import_type='hire_info', status='previewing')
    resp = client_employee.post(f'/api/v1/eligibility-import/excel/{job_id}/cancel')
    assert resp.status_code == 403
