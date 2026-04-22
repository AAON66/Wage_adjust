"""Phase 32-04 Task 2: per-import_type 锁的端到端并发场景集成测试。

覆盖 5 个核心并发场景（D-16）：
  1. 同 import_type 第二次 preview → 409
  2. 不同 import_type 可并行（hire_info preview vs performance_grades preview）
  3. processing 状态下同 import_type preview → 409（锁覆盖 previewing + processing）
  4. 同 job_id 第二次 confirm → 409（双 confirm 防护）
  5. preview 锁住后 GET /active 仍可用（HR 用来诊断）
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


def _upload(client, xlsx_bytes, import_type: str = 'hire_info'):
    return client.post(
        f'/api/v1/eligibility-import/excel/preview?import_type={import_type}',
        files={'file': ('t.xlsx', io.BytesIO(xlsx_bytes),
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
    )


# --------- Scenario 1: 同 type 锁 ---------

def test_preview_concurrent_same_type_returns_409(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """HR A preview hire_info（持锁 previewing） → HR B preview hire_info → 409。"""
    _seed_employee(_api_context, employee_no='E00001')
    data = xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]])
    r1 = _upload(client_hrbp, data)
    assert r1.status_code == 200, r1.text
    r2 = _upload(client_hrbp, data)
    assert r2.status_code == 409
    body = r2.json()
    # main.py http_exception_handler 对 dict detail 直返
    assert body['error'] == 'import_in_progress'
    assert body['import_type'] == 'hire_info'


# --------- Scenario 2: 不同 type 可并行 ---------

def test_preview_concurrent_different_type_not_blocked(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """hire_info 持锁时，performance_grades 仍可上传（per-import_type 锁）。"""
    _seed_employee(_api_context, employee_no='E00001')
    d1 = xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]])
    d2 = xlsx_factory['performance_grades'](rows=[['E00001', 2026, 'A']])
    r1 = _upload(client_hrbp, d1, 'hire_info')
    assert r1.status_code == 200, r1.text
    r2 = _upload(client_hrbp, d2, 'performance_grades')
    assert r2.status_code == 200, r2.text


# --------- Scenario 3: processing 状态也持锁 ---------

def test_preview_after_processing_same_type_returns_409(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """同 import_type 已有 processing job → preview 仍 409（锁覆盖 previewing + processing）。"""
    _seed_import_job(_api_context, import_type='hire_info', status='processing')
    _seed_employee(_api_context, employee_no='E00001')
    data = xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]])
    resp = _upload(client_hrbp, data)
    assert resp.status_code == 409


# --------- Scenario 4: 双 confirm 防护 ---------

def test_double_confirm_returns_409(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """同 job_id 第二次 confirm → 409（job 已不在 previewing 状态）。"""
    _seed_employee(_api_context, employee_no='E00001')
    data = xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]])
    r1 = _upload(client_hrbp, data)
    assert r1.status_code == 200, r1.text
    job_id = r1.json()['job_id']
    c1 = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'merge', 'confirm_replace': False},
    )
    assert c1.status_code == 200, c1.text
    c2 = client_hrbp.post(
        f'/api/v1/eligibility-import/excel/{job_id}/confirm',
        json={'overwrite_mode': 'merge', 'confirm_replace': False},
    )
    assert c2.status_code == 409


# --------- Scenario 5: 锁 vs active 端点诊断 ---------

def test_active_endpoint_after_lock_still_works(
    client_hrbp, _api_context,
):
    """即使锁住 preview，active 端点仍可用（HR 用来诊断当前活跃 job）。"""
    job_id = _seed_import_job(
        _api_context, import_type='hire_info', status='previewing',
    )
    resp = client_hrbp.get(
        '/api/v1/eligibility-import/excel/active?import_type=hire_info'
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['active'] is True
    assert body['job_id'] == job_id
    assert body['status'] == 'previewing'
