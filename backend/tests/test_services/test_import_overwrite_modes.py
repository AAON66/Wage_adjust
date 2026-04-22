"""Phase 32 Plan 02 Task 2: merge / replace 模式矩阵测试。

D-12：4 类资格 import_type × 字段类型矩阵：
- merge：空字段保留旧值
- replace：空必填字段 → row failed；空可选字段 → 清空（时间戳除外）
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import select


pytestmark = pytest.mark.usefixtures('tmp_uploads_dir')


def _normalize_and_import(svc, import_type: str, xlsx_bytes: bytes, *, overwrite_mode: str = 'merge'):
    df = pd.read_excel(io.BytesIO(xlsx_bytes), dtype=str).fillna('')
    df = svc._normalize_columns(import_type, df)
    return svc._dispatch_import(import_type, df, overwrite_mode=overwrite_mode)


# ============ performance_grades ============

def test_perf_grades_replace_required_empty_fails(
    db_session, employee_factory, xlsx_factory
):
    """D-12：replace 模式下必填 grade 空 → row failed。"""
    from backend.app.services.import_service import ImportService

    employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    data = xlsx_factory['performance_grades'](rows=[['E00001', 2026, '']])
    results = _normalize_and_import(svc, 'performance_grades', data, overwrite_mode='replace')

    assert results[0]['status'] == 'failed'
    msg = results[0].get('message', results[0].get('error', ''))
    assert '绩效等级' in msg


def test_perf_grades_merge_empty_no_change(
    db_session, employee_factory, xlsx_factory
):
    """merge 模式下空 grade → no_change（保留旧值/不更新）。"""
    from backend.app.services.import_service import ImportService

    employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    data = xlsx_factory['performance_grades'](rows=[['E00001', 2026, '']])
    results = _normalize_and_import(svc, 'performance_grades', data, overwrite_mode='merge')

    assert results[0]['status'] == 'success'
    # 空 grade merge 模式应跳过更新（no_change），不报错也不写入
    assert results[0].get('action') == 'no_change'


# ============ non_statutory_leave ============

def test_non_statutory_leave_replace_clears_optional(
    db_session, employee_factory, xlsx_factory
):
    """D-12：replace 模式下可选字段 leave_type 空 → 清空旧值。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.non_statutory_leave import NonStatutoryLeave

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)

    # 先 insert 含 leave_type
    _normalize_and_import(
        svc, 'non_statutory_leave',
        xlsx_factory['non_statutory_leave'](rows=[['E00001', 2026, 5.0, '事假']]),
    )
    db_session.commit()

    # replace + leave_type 空 → 应清空
    _normalize_and_import(
        svc, 'non_statutory_leave',
        xlsx_factory['non_statutory_leave'](rows=[['E00001', 2026, 5.0, None]]),
        overwrite_mode='replace',
    )
    db_session.commit()

    rec = db_session.execute(
        select(NonStatutoryLeave).where(NonStatutoryLeave.employee_id == emp.id)
    ).scalar_one()
    assert rec.leave_type is None


def test_non_statutory_leave_merge_keeps_optional(
    db_session, employee_factory, xlsx_factory
):
    """merge 模式下空可选字段 → 保留旧值。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.non_statutory_leave import NonStatutoryLeave

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)

    _normalize_and_import(
        svc, 'non_statutory_leave',
        xlsx_factory['non_statutory_leave'](rows=[['E00001', 2026, 5.0, '事假']]),
    )
    db_session.commit()

    _normalize_and_import(
        svc, 'non_statutory_leave',
        xlsx_factory['non_statutory_leave'](rows=[['E00001', 2026, 5.0, None]]),
        overwrite_mode='merge',
    )
    db_session.commit()

    rec = db_session.execute(
        select(NonStatutoryLeave).where(NonStatutoryLeave.employee_id == emp.id)
    ).scalar_one()
    assert rec.leave_type == '事假'


# ============ hire_info ============

def test_hire_info_replace_keeps_timestamp_field(
    db_session, employee_factory, xlsx_factory
):
    """CONTEXT D-子提示：时间戳类字段 last_salary_adjustment_date
    在 replace 模式下也保留旧值（无 NULL 清空语义）。"""
    from backend.app.services.import_service import ImportService

    emp = employee_factory(
        employee_no='E00001',
        hire_date=date(2020, 1, 1),
        last_salary_adjustment_date=date(2024, 6, 1),
    )
    svc = ImportService(db_session)

    # replace + last_salary_adjustment_date 空 → 应保留 2024-06-01
    data = xlsx_factory['hire_info'](rows=[['E00001', '2020-01-01', None]])
    _normalize_and_import(svc, 'hire_info', data, overwrite_mode='replace')
    db_session.commit()
    db_session.refresh(emp)
    assert emp.last_salary_adjustment_date == date(2024, 6, 1)


# ============ salary_adjustments ============

def test_salary_adjustments_replace_clears_amount(
    db_session, employee_factory, xlsx_factory
):
    """salary_adjustments amount 是可选字段：replace 空 → 清空。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)

    # 第一次：插入带 amount
    _normalize_and_import(
        svc, 'salary_adjustments',
        xlsx_factory['salary_adjustments'](
            rows=[['E00001', '2026-01-01', 'annual', 1000.0]]
        ),
    )
    db_session.commit()

    # 第二次：replace + amount 空 → 应清空
    _normalize_and_import(
        svc, 'salary_adjustments',
        xlsx_factory['salary_adjustments'](
            rows=[['E00001', '2026-01-01', 'annual', None]]
        ),
        overwrite_mode='replace',
    )
    db_session.commit()

    rec = db_session.execute(
        select(SalaryAdjustmentRecord).where(
            SalaryAdjustmentRecord.employee_id == emp.id,
        )
    ).scalar_one()
    assert rec.amount is None


def test_salary_adjustments_merge_keeps_amount(
    db_session, employee_factory, xlsx_factory
):
    """merge 模式下空 amount → 保留旧值。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord
    from decimal import Decimal

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)

    _normalize_and_import(
        svc, 'salary_adjustments',
        xlsx_factory['salary_adjustments'](
            rows=[['E00001', '2026-01-01', 'annual', 1000.0]]
        ),
    )
    db_session.commit()

    _normalize_and_import(
        svc, 'salary_adjustments',
        xlsx_factory['salary_adjustments'](
            rows=[['E00001', '2026-01-01', 'annual', None]]
        ),
        overwrite_mode='merge',
    )
    db_session.commit()

    rec = db_session.execute(
        select(SalaryAdjustmentRecord).where(
            SalaryAdjustmentRecord.employee_id == emp.id,
        )
    ).scalar_one()
    assert rec.amount == Decimal('1000.0')
