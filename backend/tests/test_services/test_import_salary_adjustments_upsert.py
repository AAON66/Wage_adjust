"""Phase 32 Plan 02 Task 2: salary_adjustments upsert 测试。

D-14 + Pitfall 4：将 _import_salary_adjustments 从 append 改 upsert，
业务键 = (employee_id, adjustment_date, adjustment_type)，对齐飞书同步
_sync_salary_adjustments_body line 947-952。
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from sqlalchemy import select


pytestmark = pytest.mark.usefixtures('tmp_uploads_dir')


def _normalize_and_import(svc, xlsx_bytes: bytes, *, overwrite_mode: str = 'merge'):
    df = pd.read_excel(io.BytesIO(xlsx_bytes), dtype=str).fillna('')
    df = svc._normalize_columns('salary_adjustments', df)
    return svc._import_salary_adjustments(df, overwrite_mode=overwrite_mode)


def test_salary_adjustments_upsert_idempotent(
    db_session, employee_factory, xlsx_factory
):
    """Pitfall 4：相同 (employee_id, adjustment_date, adjustment_type) 重复导入
    第二次只更新不新增，DB 中只有 1 条记录。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    rows = [['E00001', '2026-01-01', 'annual', 1000.0]]
    data = xlsx_factory['salary_adjustments'](rows=rows)

    r1 = _normalize_and_import(svc, data)
    db_session.commit()
    assert r1[0]['status'] == 'success'
    assert r1[0]['action'] == 'insert'

    # 第二次导入完全相同的记录
    r2 = _normalize_and_import(svc, data)
    db_session.commit()
    assert r2[0]['status'] == 'success'
    # 金额未变 → no_change
    assert r2[0]['action'] in ('no_change', 'update')

    # 业务键唯一约束保证只有一条
    recs = db_session.execute(
        select(SalaryAdjustmentRecord).where(
            SalaryAdjustmentRecord.employee_id == emp.id,
        )
    ).scalars().all()
    assert len(recs) == 1


def test_salary_adjustments_update_amount(
    db_session, employee_factory, xlsx_factory
):
    """同业务键不同金额 → update。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)

    _normalize_and_import(
        svc,
        xlsx_factory['salary_adjustments'](
            rows=[['E00001', '2026-01-01', 'annual', 1000.0]]
        ),
    )
    db_session.commit()

    r2 = _normalize_and_import(
        svc,
        xlsx_factory['salary_adjustments'](
            rows=[['E00001', '2026-01-01', 'annual', 1500.0]]
        ),
    )
    db_session.commit()
    assert r2[0]['action'] == 'update'

    rec = db_session.execute(
        select(SalaryAdjustmentRecord).where(
            SalaryAdjustmentRecord.employee_id == emp.id,
        )
    ).scalar_one()
    assert rec.amount == Decimal('1500.0')


def test_salary_adjustments_same_date_different_type(
    db_session, employee_factory, xlsx_factory
):
    """业务键三元组：同员工同日 annual + special 应保留两条。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    rows = [
        ['E00001', '2026-01-01', 'annual', 1000.0],
        ['E00001', '2026-01-01', 'special', 500.0],
    ]
    _normalize_and_import(svc, xlsx_factory['salary_adjustments'](rows=rows))
    db_session.commit()

    recs = db_session.execute(
        select(SalaryAdjustmentRecord).where(
            SalaryAdjustmentRecord.employee_id == emp.id,
        ).order_by(SalaryAdjustmentRecord.adjustment_type)
    ).scalars().all()
    assert len(recs) == 2
    assert {r.adjustment_type for r in recs} == {'annual', 'special'}


def test_salary_adjustments_employee_not_found(db_session, xlsx_factory):
    from backend.app.services.import_service import ImportService

    svc = ImportService(db_session)
    rows = [['E99999', '2026-01-01', 'annual', 1000.0]]
    results = _normalize_and_import(svc, xlsx_factory['salary_adjustments'](rows=rows))
    assert results[0]['status'] == 'failed'
    assert '未找到员工工号' in results[0].get('message', results[0].get('error', ''))


def test_salary_adjustments_chinese_type_label_still_works(
    db_session, employee_factory, xlsx_factory
):
    """向后兼容：'年度调薪' 中文标签 → 'annual' 代码。"""
    from backend.app.services.import_service import ImportService
    from backend.app.models.salary_adjustment_record import SalaryAdjustmentRecord

    emp = employee_factory(employee_no='E00001')
    svc = ImportService(db_session)
    rows = [['E00001', '2026-01-01', '年度调薪', 1000.0]]
    r = _normalize_and_import(svc, xlsx_factory['salary_adjustments'](rows=rows))
    db_session.commit()
    assert r[0]['status'] == 'success'

    rec = db_session.execute(
        select(SalaryAdjustmentRecord).where(
            SalaryAdjustmentRecord.employee_id == emp.id,
        )
    ).scalar_one()
    assert rec.adjustment_type == 'annual'
    assert rec.adjustment_date == date(2026, 1, 1)
