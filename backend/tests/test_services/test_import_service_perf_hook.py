"""Phase 34 Plan 03 Task 3：import_service hook 集成测试（≥ 4 cases）。

覆盖：
- B-1：_import_performance_grades insert/existing 两条分支均显式写
       department_snapshot=employee.department
- B-2：confirm_import 路径撞 TierRecomputeBusyError → ConfirmResponse 字段
       tier_recompute_status='busy_skipped'
- happy：confirm 'performance_grades' 触发 recompute_tiers + 字段返回 'completed'
- failure：recompute 抛 TierRecomputeFailedError → ConfirmResponse.status='completed'
          + tier_recompute_status='failed'（D-04：不阻塞 import 落库）
- 非 performance_grades：不触发 recompute；tier_recompute_status is None
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy import select

from backend.app.models.performance_record import PerformanceRecord
from backend.app.services.exceptions import (
    TierRecomputeBusyError,
    TierRecomputeFailedError,
)
from backend.app.services.import_service import ImportService


# ---------------------------------------------------------------------------
# B-1：_import_performance_grades 显式写 department_snapshot
# ---------------------------------------------------------------------------

def test_import_perf_grades_writes_department_snapshot(
    db_session, employee_factory,
):
    """B-1：HR 上传 Excel 后 PerformanceRecord.department_snapshot == employee.department。"""
    emp = employee_factory(employee_no='E11001', department='Engineering')
    svc = ImportService(db_session)
    df = pd.DataFrame([
        {'employee_no': 'E11001', 'year': 2026, 'grade': 'A'},
    ])
    results = svc._import_performance_grades(df)
    assert results[0]['status'] == 'success'
    assert results[0]['action'] == 'insert'
    record = db_session.scalar(
        select(PerformanceRecord).where(
            PerformanceRecord.employee_id == emp.id,
            PerformanceRecord.year == 2026,
        )
    )
    assert record is not None
    assert record.department_snapshot == 'Engineering'


def test_import_perf_grades_existing_record_updates_department_snapshot(
    db_session, employee_factory,
):
    """B-1：existing 更新分支也刷新 department_snapshot（旧 NULL 被覆盖为当前部门）。"""
    emp = employee_factory(employee_no='E11002', department='Sales')
    db_session.add(PerformanceRecord(
        employee_id=emp.id,
        employee_no='E11002',
        year=2026,
        grade='B',
        source='manual',
        department_snapshot=None,  # 旧 NULL
    ))
    db_session.commit()

    svc = ImportService(db_session)
    df = pd.DataFrame([
        {'employee_no': 'E11002', 'year': 2026, 'grade': 'A'},
    ])
    svc._import_performance_grades(df)
    db_session.expire_all()

    existing = db_session.scalar(
        select(PerformanceRecord).where(
            PerformanceRecord.employee_id == emp.id,
            PerformanceRecord.year == 2026,
        )
    )
    assert existing is not None
    assert existing.department_snapshot == 'Sales'  # 旧 NULL 被刷新
    assert existing.grade == 'A'  # grade 同步更新


# ---------------------------------------------------------------------------
# B-2 + happy + failure：confirm_import hook 行为
# ---------------------------------------------------------------------------

def _build_perf_grades_job_and_confirm(
    ctx_db,
    employee_factory,
    xlsx_factory,
    user_factory,
    *,
    employee_no: str = 'E22001',
    rows=None,
):
    """复用 helper：build preview + confirm 一个 performance_grades job，返回 resp。

    上层用 patch 拦截 PerformanceService.recompute_tiers 行为后再调用此 helper。
    """
    employee_factory(employee_no=employee_no)
    actor = user_factory(role='hrbp')
    svc = ImportService(ctx_db)
    if rows is None:
        rows = [[employee_no, 2026, 'A']]
    data = xlsx_factory['performance_grades'](rows=rows)
    prev = svc.build_preview(
        import_type='performance_grades',
        file_name='perf.xlsx',
        raw_bytes=data,
        actor_id=str(actor.id),
    )
    return svc.confirm_import(
        job_id=prev.job_id,
        overwrite_mode='merge',
        actor_id=str(actor.id),
        actor_role='hrbp',
    )


def test_recompute_tiers_busy_in_import_hook_returns_busy_skipped(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """B-2：mock recompute_tiers 抛 TierRecomputeBusyError → tier_recompute_status='busy_skipped'。"""
    with patch(
        'backend.app.services.performance_service.PerformanceService.recompute_tiers',
        side_effect=TierRecomputeBusyError(2026),
    ):
        resp = _build_perf_grades_job_and_confirm(
            db_session, employee_factory, xlsx_factory, user_factory,
        )
    # import 已落库（D-04：不阻塞）
    assert resp.status in ('completed', 'partial')
    # hook 写回 W-1 字段
    assert resp.tier_recompute_status == 'busy_skipped'


def test_confirm_performance_grades_triggers_recompute(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """happy 路径：confirm 后 recompute_tiers 被以正确 year 调用一次。"""
    with patch(
        'backend.app.services.performance_service.PerformanceService.recompute_tiers',
        return_value=None,
    ) as mock_recompute:
        resp = _build_perf_grades_job_and_confirm(
            db_session, employee_factory, xlsx_factory, user_factory,
        )
    assert resp.status in ('completed', 'partial')
    assert resp.tier_recompute_status == 'completed'
    # 至少调一次（rows 中只有 year=2026）
    assert mock_recompute.called
    # year 入参验证
    called_years = [c.args[0] for c in mock_recompute.call_args_list]
    assert 2026 in called_years


def test_recompute_failure_does_not_block_import_commit(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """D-04：recompute 失败不影响 import 落库；ConfirmResponse 仍正常返回。"""
    with patch(
        'backend.app.services.performance_service.PerformanceService.recompute_tiers',
        side_effect=TierRecomputeFailedError(2026, 'engine boom'),
    ):
        resp = _build_perf_grades_job_and_confirm(
            db_session, employee_factory, xlsx_factory, user_factory,
        )
    # import 仍 completed/partial（行已落库）
    assert resp.status in ('completed', 'partial')
    assert resp.tier_recompute_status == 'failed'
    # 验证行已落库
    record = db_session.scalar(
        select(PerformanceRecord).where(
            PerformanceRecord.year == 2026,
        )
    )
    assert record is not None


def test_non_performance_grades_does_not_trigger_recompute(
    db_session, employee_factory, xlsx_factory, tmp_uploads_dir, user_factory,
):
    """非 performance_grades import_type → recompute_tiers 不被调用；tier_recompute_status is None。"""
    employee_factory(employee_no='E33001')
    actor = user_factory(role='hrbp')
    svc = ImportService(db_session)
    data = xlsx_factory['hire_info'](rows=[['E33001', '2026-01-01', None]])
    prev = svc.build_preview(
        import_type='hire_info',
        file_name='hire.xlsx',
        raw_bytes=data,
        actor_id=str(actor.id),
    )
    with patch(
        'backend.app.services.performance_service.PerformanceService.recompute_tiers',
    ) as mock_recompute:
        resp = svc.confirm_import(
            job_id=prev.job_id,
            overwrite_mode='merge',
            actor_id=str(actor.id),
            actor_role='hrbp',
        )
    assert resp.status in ('completed', 'partial')
    assert resp.tier_recompute_status is None  # W-1：非 perf_grades 路径保持 None
    assert mock_recompute.call_count == 0
