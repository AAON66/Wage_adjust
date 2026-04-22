"""Phase 32-04 Task 1: POST /eligibility-import/excel/preview + GET .../active 端到端测试。

覆盖：
  - 成功 200 + PreviewResponse 结构
  - 同 import_type 第二次 → 409
  - 不同 import_type 不冲突
  - 文件类型校验 (.exe → 422)
  - 文件大小上限 (>10MB → 413)
  - 鉴权 (无 JWT → 401, employee → 403)
  - 未知 import_type → 400
  - GET /active 无活跃 / 有 previewing 两态

注意：API 测试通过 `_api_context.session_factory()` 直接在与 API 共享的 DB 中 seed
数据（`import_job_factory` / `employee_factory` 用的是独立的 in-memory DB，与 API
的 file-based DB 不共享）。
"""
from __future__ import annotations

import io


def _upload_file(xlsx_bytes: bytes, filename: str = 'test.xlsx') -> dict:
    return {'file': (filename, io.BytesIO(xlsx_bytes),
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}


def _seed_employee(api_ctx, *, employee_no: str = 'E00001') -> str:
    """直接在 API DB 中创建 Employee；返回 employee_id。"""
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
    """直接在 API DB 中创建 ImportJob；返回 job_id。"""
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


# --------- 成功路径 ---------

def test_preview_endpoint_returns_preview_response(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """POST /excel/preview?import_type=hire_info → 200 + PreviewResponse 结构完整。"""
    _seed_employee(_api_context, employee_no='E00001')
    data = xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]])
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files=_upload_file(data),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body['import_type'] == 'hire_info'
    assert 'job_id' in body
    assert 'counters' in body
    assert 'file_sha256' in body
    assert isinstance(body['counters'], dict)
    assert {'insert', 'update', 'no_change', 'conflict'} <= set(body['counters'].keys())


# --------- 并发锁 ---------

def test_preview_409_when_running(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """同 import_type 已有 previewing job → 409 + body.error='import_in_progress'。

    注意 main.py http_exception_handler：HTTPException(detail=dict) 时 body 就是
    detail dict 本身（不再嵌套 'detail' key）。
    """
    _seed_import_job(_api_context, import_type='hire_info', status='previewing')
    data = xlsx_factory['hire_info']()
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files=_upload_file(data),
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body['error'] == 'import_in_progress'
    assert body['import_type'] == 'hire_info'


def test_preview_different_type_not_blocked(
    client_hrbp, _api_context, xlsx_factory, tmp_uploads_dir,
):
    """hire_info 活跃时，performance_grades 仍可上传（per-import_type 锁）。"""
    _seed_import_job(_api_context, import_type='hire_info', status='previewing')
    _seed_employee(_api_context, employee_no='E00001')
    data = xlsx_factory['performance_grades'](rows=[['E00001', 2026, 'A']])
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=performance_grades',
        files=_upload_file(data),
    )
    assert resp.status_code == 200, resp.text


# --------- 文件安全 ---------

def test_preview_rejects_exe_file(client_hrbp, tmp_uploads_dir):
    """.exe 文件 → 422 拒绝（T-32-02）。"""
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files={'file': ('malware.exe', io.BytesIO(b'MZ\x00fake'),
                        'application/x-msdownload')},
    )
    assert resp.status_code == 422


def test_preview_rejects_html_file(client_hrbp, tmp_uploads_dir):
    """.html 文件 → 422 拒绝（T-32-02）。"""
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files={'file': ('xss.html', io.BytesIO(b'<html><script>alert(1)</script>'),
                        'text/html')},
    )
    assert resp.status_code == 422


def test_preview_rejects_oversized_file(client_hrbp, tmp_uploads_dir):
    """>10MB 文件 → 413 拒绝（T-32-03 防 DoS）。"""
    big = b'X' * (11 * 1024 * 1024)  # 11 MB
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files={'file': ('big.xlsx', io.BytesIO(big),
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
    )
    assert resp.status_code == 413


# --------- 鉴权 ---------

def test_preview_requires_jwt(client_anon, xlsx_factory, tmp_uploads_dir):
    """无 JWT → 401。"""
    data = xlsx_factory['hire_info']()
    resp = client_anon.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files=_upload_file(data),
    )
    assert resp.status_code == 401


def test_preview_employee_role_forbidden(
    client_employee, xlsx_factory, tmp_uploads_dir,
):
    """employee 角色 → 403（T-32-04）。"""
    data = xlsx_factory['hire_info']()
    resp = client_employee.post(
        '/api/v1/eligibility-import/excel/preview?import_type=hire_info',
        files=_upload_file(data),
    )
    assert resp.status_code == 403


# --------- 校验 ---------

def test_preview_unknown_import_type(client_hrbp, xlsx_factory, tmp_uploads_dir):
    """未知 import_type → 400。"""
    data = xlsx_factory['hire_info']()
    resp = client_hrbp.post(
        '/api/v1/eligibility-import/excel/preview?import_type=unknown_type',
        files=_upload_file(data),
    )
    assert resp.status_code == 400


# --------- GET /active ---------

def test_active_endpoint_no_active(client_hrbp):
    """无活跃 job → {active: false}。"""
    resp = client_hrbp.get(
        '/api/v1/eligibility-import/excel/active?import_type=hire_info'
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['active'] is False
    assert body['job_id'] is None


def test_active_endpoint_with_previewing(client_hrbp, _api_context):
    """有 previewing job → {active: true, status: 'previewing', job_id: ...}。"""
    job_id = _seed_import_job(_api_context, import_type='hire_info', status='previewing')
    resp = client_hrbp.get(
        '/api/v1/eligibility-import/excel/active?import_type=hire_info'
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['active'] is True
    assert body['job_id'] == job_id
    assert body['status'] == 'previewing'
