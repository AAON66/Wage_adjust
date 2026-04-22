"""Phase 32-03 Task 2a: build_preview + _detect_in_file_conflicts + _build_row_diff。

测试覆盖：
- build_preview 基本结构（job_id / counters / file_sha256 / total_rows）
- 写 ImportJob status='previewing' + 暂存文件落盘
- 同文件业务键冲突检测（D-09）→ counters.conflict
- _detect_in_file_conflicts helper 直接单元测试
- _build_row_diff（hire_info update / performance_grades insert）
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest


def test_build_preview_basic_structure(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir,
):
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001')
    employee_factory(employee_no='E00002')
    svc = ImportService(db_session)
    data = xlsx_factory['hire_info']()  # 2 行默认数据
    resp = svc.build_preview(
        import_type='hire_info', file_name='test.xlsx', raw_bytes=data,
    )
    assert resp.job_id
    assert resp.import_type == 'hire_info'
    assert resp.total_rows == 2
    assert resp.file_sha256
    counters_sum = (
        resp.counters.insert + resp.counters.update
        + resp.counters.no_change + resp.counters.conflict
    )
    assert isinstance(counters_sum, int)
    assert counters_sum == 2  # 每行落入唯一 counter


def test_build_preview_writes_job_status_previewing(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir,
):
    from sqlalchemy import select
    from backend.app.services.import_service import ImportService
    from backend.app.models.import_job import ImportJob
    employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    resp = svc.build_preview(
        import_type='hire_info',
        file_name='t.xlsx',
        raw_bytes=xlsx_factory['hire_info'](rows=[['E00001', '2026-01-01', None]]),
    )
    job = db_session.execute(
        select(ImportJob).where(ImportJob.id == resp.job_id)
    ).scalar_one()
    assert job.status == 'previewing'
    # 暂存文件存在
    assert svc._staged_file_path(resp.job_id).exists()
    # result_summary.preview.file_sha256 已写入
    assert (job.result_summary or {}).get('preview', {}).get('file_sha256') == resp.file_sha256


def test_build_preview_detects_in_file_conflicts(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir,
):
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001')
    employee_factory(employee_no='E00002')
    svc = ImportService(db_session)
    data = xlsx_factory['non_statutory_leave'](with_conflict=True)
    resp = svc.build_preview(
        import_type='non_statutory_leave', file_name='t.xlsx', raw_bytes=data,
    )
    # with_conflict 在默认 2 行上追加 1 行 (E00001, 2026, ...) 重复
    # 应有 ≥2 行被标 conflict（同 group 内所有行都标）
    assert resp.counters.conflict >= 2
    conflict_rows = [r for r in resp.rows if r.action == 'conflict']
    assert len(conflict_rows) >= 2
    # 至少一行 conflict_reason 含中文「出现」
    assert any('出现' in (r.conflict_reason or '') for r in conflict_rows)


def test_detect_in_file_conflicts_helper(db_session):
    from backend.app.services.import_service import ImportService
    svc = ImportService(db_session)
    df = pd.DataFrame([
        {'employee_no': 'E001', 'year': 2026, 'total_days': 5},
        {'employee_no': 'E001', 'year': 2026, 'total_days': 8},  # dup
        {'employee_no': 'E002', 'year': 2026, 'total_days': 3},
    ])
    conflicts = svc._detect_in_file_conflicts('non_statutory_leave', df)
    assert 0 in conflicts and 1 in conflicts
    assert 2 not in conflicts


def test_build_row_diff_hire_info_update(db_session, employee_factory):
    """_build_row_diff 单元测试：hire_info 已有员工，新值不同 → update。"""
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001', hire_date=date(2020, 1, 1))
    svc = ImportService(db_session)
    row = pd.Series({
        'employee_no': 'E00001',
        'hire_date': '2024-03-15',
        'last_salary_adjustment_date': None,
    })
    action, fields = svc._build_row_diff('hire_info', row)
    assert action == 'update'
    assert 'hire_date' in fields
    assert fields['hire_date']['new'] == '2024-03-15'


def test_build_row_diff_perf_grades_insert_for_new(db_session, employee_factory):
    """_build_row_diff 单元测试：performance_grades 新员工无历史记录 → insert。"""
    from backend.app.services.import_service import ImportService
    employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    row = pd.Series({'employee_no': 'E00001', 'year': 2026, 'grade': 'A'})
    action, fields = svc._build_row_diff('performance_grades', row)
    assert action == 'insert'
    assert fields['grade']['new'] == 'A'
    assert fields['grade']['old'] is None
