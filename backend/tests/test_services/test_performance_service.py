"""Phase 34 Plan 03 Task 3：PerformanceService 层单测（≥ 13 cases）。

覆盖：
- create_record / list_records / list_available_years / invalidate_tier_cache
- get_tier_summary（cache hit / miss table hit / full miss）
- recompute_tiers（首次 INSERT / 更新 / Engine 集成 / B-2 锁竞争 mock /
  Engine 失败 → TierRecomputeFailedError）
- B-3：list_available_years 返回 distinct desc + 空表 → 当前年
"""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from backend.app.engines import PerformanceTierConfig, PerformanceTierEngine
from backend.app.models.performance_record import PerformanceRecord
from backend.app.models.performance_tier_snapshot import PerformanceTierSnapshot
from backend.app.schemas.performance import (
    MyTierResponse,
    PerformanceHistoryResponse,
    PerformanceRecordCreateRequest,
    PerformanceRecordRead,
)
from backend.app.services.exceptions import (
    TierRecomputeBusyError,
    TierRecomputeFailedError,
)
from backend.app.services.performance_service import PerformanceService
from backend.app.services.tier_cache import TierCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_record_counter = {'n': 0}


def _make_records(db, employee_factory, *, year: int, count: int, grade: str = 'B'):
    """构造 count 个 employees + 对应 perf records；返回 list[PerformanceRecord]。

    使用进程级递增计数器避免 employee_no 冲突（多次调用同 year 不重复）。
    """
    records = []
    for _ in range(count):
        _record_counter['n'] += 1
        n = _record_counter['n']
        emp = employee_factory(employee_no=f'TEST{n:08d}')
        rec = PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=year,
            grade=grade,
            source='manual',
            department_snapshot=emp.department,
        )
        db.add(rec)
        records.append(rec)
    db.commit()
    return records


def _make_mock_cache() -> MagicMock:
    """构造 mock TierCache：默认 get 返回 None、其他无副作用。"""
    cache = MagicMock(spec=TierCache)
    cache.get_cached.return_value = None
    cache.set_cached.return_value = None
    cache.invalidate.return_value = None
    return cache


# ---------------------------------------------------------------------------
# create_record
# ---------------------------------------------------------------------------

def test_create_record_writes_department_snapshot(db_session, employee_factory):
    emp = employee_factory(employee_no='E00100', department='Engineering')
    service = PerformanceService(db_session)
    record = service.create_record(
        employee_id=emp.id, year=2026, grade='A', source='manual',
    )
    assert record.department_snapshot == 'Engineering'
    assert record.grade == 'A'


def test_create_record_handles_null_department(
    db_session, employee_factory, monkeypatch,
):
    """D-08：employee.department 为 None 时快照也写 None（不抛异常）。

    Employee.department 列本身 NOT NULL（不能直接持久化 None），通过 mock
    db.get 返回一个 department=None 的 stub 实例，覆盖 service 防御行为。
    """
    real_emp = employee_factory(employee_no='E00101', department='Eng')

    class _StubEmp:
        def __init__(self, real):
            self.id = real.id
            self.employee_no = real.employee_no
            self.department = None  # 关键点

    stub = _StubEmp(real_emp)

    service = PerformanceService(db_session)
    original_get = service.db.get

    def _fake_get(model, pk):
        from backend.app.models.employee import Employee as _Emp
        if model is _Emp and pk == stub.id:
            return stub
        return original_get(model, pk)
    monkeypatch.setattr(service.db, 'get', _fake_get)

    record = service.create_record(
        employee_id=stub.id, year=2026, grade='B',
    )
    assert record.department_snapshot is None


def test_create_record_invalid_grade_raises(db_session, employee_factory):
    emp = employee_factory(employee_no='E00102')
    service = PerformanceService(db_session)
    with pytest.raises(ValueError, match='不合法'):
        service.create_record(employee_id=emp.id, year=2026, grade='F')


def test_create_record_unknown_employee_raises(db_session):
    service = PerformanceService(db_session)
    with pytest.raises(ValueError, match='不存在'):
        service.create_record(
            employee_id='no-such-employee', year=2026, grade='A',
        )


def test_create_record_upserts_existing(db_session, employee_factory):
    emp = employee_factory(employee_no='E00103', department='Sales')
    service = PerformanceService(db_session)
    first = service.create_record(employee_id=emp.id, year=2026, grade='A')
    first_id = first.id
    second = service.create_record(employee_id=emp.id, year=2026, grade='B')
    # 同 (employee, year) 二次：UPSERT 而非 insert（id 不变）
    assert second.id == first_id
    assert second.grade == 'B'
    # 表中只有 1 行
    rows = db_session.execute(
        select(PerformanceRecord).where(
            PerformanceRecord.employee_id == emp.id,
            PerformanceRecord.year == 2026,
        )
    ).scalars().all()
    assert len(rows) == 1


def test_create_record_persists_comment(db_session, employee_factory):
    emp = employee_factory(employee_no='E00104', department='Engineering')
    service = PerformanceService(db_session)

    record = service.create_record(
        employee_id=emp.id,
        year=2025,
        grade='A',
        source='manual',
        comment='Q4 超额完成',
    )

    assert record.comment == 'Q4 超额完成'
    serialized = PerformanceRecordRead.model_validate(record)
    assert serialized.comment == 'Q4 超额完成'


def test_create_record_defaults_comment_to_none(db_session, employee_factory):
    emp = employee_factory(employee_no='E00105', department='Engineering')
    service = PerformanceService(db_session)

    record = service.create_record(
        employee_id=emp.id,
        year=2025,
        grade='B',
        source='manual',
    )

    assert record.comment is None
    response = PerformanceHistoryResponse(
        items=[PerformanceRecordRead.model_validate(record)],
    )
    assert response.items[0].comment is None


def test_create_record_upsert_refreshes_comment_and_department_snapshot(
    db_session, employee_factory,
):
    emp = employee_factory(employee_no='E00106', department='Sales')
    service = PerformanceService(db_session)

    first = service.create_record(
        employee_id=emp.id,
        year=2025,
        grade='A',
        source='manual',
    )
    emp.department = 'Operations'
    db_session.add(emp)
    db_session.commit()

    second = service.create_record(
        employee_id=emp.id,
        year=2025,
        grade='B',
        source='manual',
        comment='改评',
    )

    assert second.id == first.id
    assert second.grade == 'B'
    assert second.comment == '改评'
    assert second.department_snapshot == 'Operations'


def test_performance_record_create_request_rejects_comment_over_2000_chars():
    with pytest.raises(ValidationError):
        PerformanceRecordCreateRequest(
            employee_id='employee-id',
            year=2025,
            grade='A',
            source='manual',
            comment='评' * 3000,
        )


# ---------------------------------------------------------------------------
# list_records
# ---------------------------------------------------------------------------

def test_list_records_pagination(db_session, employee_factory):
    _make_records(db_session, employee_factory, year=2026, count=10)
    service = PerformanceService(db_session)
    items, total = service.list_records(year=2026, page=1, page_size=4)
    assert total == 10
    assert len(items) == 4
    items2, total2 = service.list_records(year=2026, page=3, page_size=4)
    assert total2 == 10
    assert len(items2) == 2  # 第三页只剩 2 条


def test_list_records_year_filter(db_session, employee_factory):
    _make_records(db_session, employee_factory, year=2024, count=3)
    _make_records(db_session, employee_factory, year=2026, count=5)
    service = PerformanceService(db_session)
    items, total = service.list_records(year=2026)
    assert total == 5
    assert all(it.year == 2026 for it in items)


def test_list_records_department_filter(db_session, employee_factory):
    # 不同部门
    e1 = employee_factory(employee_no='E10001', department='Eng')
    e2 = employee_factory(employee_no='E10002', department='Sales')
    db_session.add(PerformanceRecord(
        employee_id=e1.id, employee_no=e1.employee_no,
        year=2026, grade='A', source='manual', department_snapshot='Eng',
    ))
    db_session.add(PerformanceRecord(
        employee_id=e2.id, employee_no=e2.employee_no,
        year=2026, grade='B', source='manual', department_snapshot='Sales',
    ))
    db_session.commit()
    service = PerformanceService(db_session)
    items, total = service.list_records(year=2026, department='Eng')
    assert total == 1
    assert items[0].employee_no == 'E10001'


# ---------------------------------------------------------------------------
# list_records_by_employee
# ---------------------------------------------------------------------------

def test_list_records_by_employee_orders_by_year_desc(db_session, employee_factory):
    emp = employee_factory(
        employee_no='E20001',
        name='张三',
        department='Engineering',
    )
    db_session.add_all([
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2024,
            grade='C',
            source='manual',
            department_snapshot='Engineering',
        ),
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2026,
            grade='A',
            source='manual',
            department_snapshot='Engineering',
        ),
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2025,
            grade='B',
            source='manual',
            department_snapshot='Engineering',
        ),
    ])
    db_session.commit()

    service = PerformanceService(db_session)

    items = service.list_records_by_employee(emp.id)

    assert [item.year for item in items] == [2026, 2025, 2024]
    assert all(item.employee_id == emp.id for item in items)


def test_list_records_by_employee_returns_empty_list_when_no_records(
    db_session, employee_factory,
):
    emp = employee_factory(employee_no='E20002', name='李四')
    service = PerformanceService(db_session)

    items = service.list_records_by_employee(emp.id)

    assert items == []


def test_list_records_by_employee_handles_null_department_snapshot_and_comment(
    db_session, employee_factory,
):
    emp = employee_factory(employee_no='E20003', name='王五', department='Ops')
    db_session.add_all([
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2026,
            grade='A',
            source='manual',
            department_snapshot=None,
            comment='年度表现突出',
        ),
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2025,
            grade='B',
            source='manual',
            department_snapshot='Ops',
            comment=None,
        ),
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2024,
            grade='C',
            source='manual',
            department_snapshot='Ops',
            comment='稳定达标',
        ),
    ])
    db_session.commit()

    service = PerformanceService(db_session)

    items = service.list_records_by_employee(emp.id)
    by_year = {item.year: item for item in items}

    assert by_year[2026].department_snapshot is None
    assert by_year[2026].comment == '年度表现突出'
    assert by_year[2025].department_snapshot == 'Ops'
    assert by_year[2025].comment is None


def test_list_records_by_employee_isolates_between_employees(
    db_session, employee_factory,
):
    emp_a = employee_factory(employee_no='E20004', name='员工A', department='Dept-A')
    emp_b = employee_factory(employee_no='E20005', name='员工B', department='Dept-B')
    db_session.add_all([
        PerformanceRecord(
            employee_id=emp_a.id,
            employee_no=emp_a.employee_no,
            year=2026,
            grade='A',
            source='manual',
            department_snapshot='Dept-A',
        ),
        PerformanceRecord(
            employee_id=emp_a.id,
            employee_no=emp_a.employee_no,
            year=2025,
            grade='B',
            source='manual',
            department_snapshot='Dept-A',
        ),
        PerformanceRecord(
            employee_id=emp_b.id,
            employee_no=emp_b.employee_no,
            year=2026,
            grade='C',
            source='manual',
            department_snapshot='Dept-B',
        ),
    ])
    db_session.commit()

    service = PerformanceService(db_session)

    items = service.list_records_by_employee(emp_a.id)

    assert len(items) == 2
    assert {item.employee_id for item in items} == {emp_a.id}
    assert {item.employee_no for item in items} == {emp_a.employee_no}


def test_list_records_by_employee_returns_empty_list_for_nonexistent_employee_id(
    db_session,
):
    service = PerformanceService(db_session)

    items = service.list_records_by_employee('6df2307a-2637-4f07-a90e-7f4724451e42')

    assert items == []


def test_list_records_by_employee_populates_employee_name_via_join(
    db_session, employee_factory,
):
    emp = employee_factory(
        employee_no='E20006',
        name='赵六',
        department='Finance',
    )
    db_session.add(
        PerformanceRecord(
            employee_id=emp.id,
            employee_no=emp.employee_no,
            year=2026,
            grade='A',
            source='manual',
            department_snapshot='Finance',
            comment='达成关键目标',
        )
    )
    db_session.commit()

    service = PerformanceService(db_session)

    items = service.list_records_by_employee(emp.id)

    assert len(items) == 1
    assert items[0].employee_name == '赵六'
    assert items[0].comment == '达成关键目标'


# ---------------------------------------------------------------------------
# get_tier_summary
# ---------------------------------------------------------------------------

def test_get_tier_summary_cache_hit(db_session):
    cache = _make_mock_cache()
    cache.get_cached.return_value = {
        'year': 2026,
        'computed_at': '2026-04-22T10:00:00+00:00',
        'sample_size': 100,
        'insufficient_sample': False,
        'distribution_warning': False,
        'tiers_count': {'1': 20, '2': 70, '3': 10, 'none': 0},
        'actual_distribution': {'1': 0.20, '2': 0.70, '3': 0.10},
        'skipped_invalid_grades': 0,
    }
    service = PerformanceService(db_session, cache=cache)
    summary = service.get_tier_summary(2026)
    assert summary is not None
    assert summary.sample_size == 100
    cache.get_cached.assert_called_once_with(2026)
    cache.set_cached.assert_not_called()  # cache hit 时不写回


def test_get_tier_summary_cache_miss_table_hit(db_session):
    cache = _make_mock_cache()
    snap = PerformanceTierSnapshot(
        year=2026,
        tiers_json={'emp1': 1, 'emp2': 2, 'emp3': 3},
        sample_size=3,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.33, '2': 0.34, '3': 0.33},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session, cache=cache)
    summary = service.get_tier_summary(2026)
    assert summary is not None
    assert summary.sample_size == 3
    assert summary.tiers_count == {'1': 1, '2': 1, '3': 1, 'none': 0}
    cache.set_cached.assert_called_once()  # miss → 写回 cache


def test_get_tier_summary_full_miss_returns_none(db_session):
    cache = _make_mock_cache()
    service = PerformanceService(db_session, cache=cache)
    assert service.get_tier_summary(2030) is None


# ---------------------------------------------------------------------------
# recompute_tiers
# ---------------------------------------------------------------------------

def test_recompute_tiers_creates_snapshot_first_time(db_session, employee_factory):
    cache = _make_mock_cache()
    _make_records(db_session, employee_factory, year=2026, count=60, grade='A')
    # min_sample_size 默认 50，60 行可达
    service = PerformanceService(db_session, cache=cache)
    summary = service.recompute_tiers(2026)
    assert summary.sample_size == 60
    cache.set_cached.assert_called_once()
    snap = db_session.scalar(
        select(PerformanceTierSnapshot).where(
            PerformanceTierSnapshot.year == 2026,
        )
    )
    assert snap is not None


def test_recompute_tiers_updates_existing_snapshot(db_session, employee_factory):
    """重算复用同 year 的 snapshot 行（不重新插入），且业务数据被刷新。"""
    cache = _make_mock_cache()
    _make_records(db_session, employee_factory, year=2026, count=60, grade='B')
    service = PerformanceService(db_session, cache=cache)
    service.recompute_tiers(2026)
    snap = db_session.scalar(
        select(PerformanceTierSnapshot).where(
            PerformanceTierSnapshot.year == 2026,
        )
    )
    first_id = snap.id
    first_sample_size = snap.sample_size
    assert first_sample_size == 60

    # 加 30 条 grade='A' 记录 → 业务数据必变；snapshot 行 id 不变
    extra = _make_records(
        db_session, employee_factory, year=2026, count=30, grade='A',
    )
    assert len(extra) == 30
    db_session.expire_all()

    service.recompute_tiers(2026)
    snap2 = db_session.scalar(
        select(PerformanceTierSnapshot).where(
            PerformanceTierSnapshot.year == 2026,
        )
    )
    assert snap2.id == first_id  # 同一行被 UPSERT
    assert snap2.sample_size == 90  # 业务数据已更新
    # 表中只有 1 行（不是新插入）
    rows = db_session.execute(
        select(PerformanceTierSnapshot).where(
            PerformanceTierSnapshot.year == 2026,
        )
    ).scalars().all()
    assert len(rows) == 1


def test_recompute_tiers_idempotent_call_still_refreshes_updated_at(
    db_session, employee_factory,
):
    """Phase 34 UAT Item 5 gap closure: 重复调用 recompute_tiers（无数据变化）也必须刷新 updated_at。

    根因：SQLAlchemy UpdatedAtMixin.onupdate 只在字段值变化时触发。
    当业务数据不变时（idempotent recompute），updated_at 不会自动刷新，
    导致 HR UI 的「最近重算」时间戳不能反映按钮最后点击时间。
    修复：recompute_tiers 在 commit 前显式 snapshot.updated_at = datetime.now(UTC)。
    """
    import time
    cache = _make_mock_cache()
    _make_records(db_session, employee_factory, year=2026, count=60, grade='B')
    service = PerformanceService(db_session, cache=cache)

    service.recompute_tiers(2026)
    snap1 = db_session.scalar(
        select(PerformanceTierSnapshot).where(PerformanceTierSnapshot.year == 2026)
    )
    first_updated_at = snap1.updated_at
    assert first_updated_at is not None

    # Sleep ≥ 10ms 确保下一次 datetime.now() 至少差 10 微秒（防止 SQLite datetime 精度问题）
    time.sleep(0.01)
    db_session.expire_all()

    # 重新调 recompute_tiers — 业务数据完全没变（同 60 条 grade='B' records）
    service.recompute_tiers(2026)
    snap2 = db_session.scalar(
        select(PerformanceTierSnapshot).where(PerformanceTierSnapshot.year == 2026)
    )
    second_updated_at = snap2.updated_at
    assert second_updated_at is not None
    assert second_updated_at > first_updated_at, (
        f'updated_at 应在每次 recompute_tiers 调用后刷新（即使业务数据不变），'
        f'first={first_updated_at}, second={second_updated_at}'
    )
    # 业务数据仍正确
    assert snap2.sample_size == 60
    assert snap2.id == snap1.id  # 同一行


def test_recompute_tiers_calls_engine_with_grades(db_session, employee_factory):
    cache = _make_mock_cache()
    _make_records(db_session, employee_factory, year=2026, count=55, grade='A')
    fake_engine = MagicMock(spec=PerformanceTierEngine)
    from backend.app.engines.performance_tier_engine import TierAssignmentResult
    fake_engine.assign.return_value = TierAssignmentResult(
        tiers={'e1': 1}, insufficient_sample=False,
        distribution_warning=False, actual_distribution={1: 0.2, 2: 0.7, 3: 0.1},
        sample_size=55, skipped_invalid_grades=0,
    )
    service = PerformanceService(db_session, cache=cache, engine=fake_engine)
    service.recompute_tiers(2026)
    fake_engine.assign.assert_called_once()
    args, _ = fake_engine.assign.call_args
    inputs = args[0]
    assert len(inputs) == 55
    # 每个 input 是 (employee_id, grade) tuple
    assert all(isinstance(t, tuple) and len(t) == 2 for t in inputs)


def test_recompute_tiers_busy_raises_TierRecomputeBusyError_via_mock(
    db_session, employee_factory, monkeypatch,
):
    """B-2：mock OperationalError 'could not obtain lock' → TierRecomputeBusyError。"""
    cache = _make_mock_cache()
    _make_records(db_session, employee_factory, year=2026, count=55, grade='B')
    service = PerformanceService(db_session, cache=cache)

    # 强制 _acquire_year_lock 走真实 SQL 路径（绕过 SQLite skip）
    def _fake_acquire(year: int) -> None:
        raise OperationalError(
            'SELECT id FROM performance_tier_snapshots WHERE year = :year FOR UPDATE NOWAIT',
            {'year': year},
            Exception('could not obtain lock on row in relation "performance_tier_snapshots"'),
        )
    # 但我们要复现：service._acquire_year_lock 应该把 OperationalError 转 BusyError
    # 直接把 db.execute 的 lock SQL 拦截即可
    original_execute = service.db.execute

    def _fake_execute(stmt, *args, **kwargs):
        sql_str = str(stmt) if stmt is not None else ''
        if 'FOR UPDATE NOWAIT' in sql_str.upper():
            raise OperationalError(
                'SELECT', {},
                Exception('could not obtain lock on row in relation tier'),
            )
        return original_execute(stmt, *args, **kwargs)

    # 同时强制 dialect 看作 postgresql（绕过 sqlite 降级路径）
    fake_dialect = MagicMock()
    fake_dialect.name = 'postgresql'
    monkeypatch.setattr(service.db.bind, 'dialect', fake_dialect)
    monkeypatch.setattr(service.db, 'execute', _fake_execute)

    with pytest.raises(TierRecomputeBusyError) as exc_info:
        service.recompute_tiers(2026)
    assert exc_info.value.year == 2026


def test_recompute_tiers_engine_failure_raises_failed(
    db_session, employee_factory,
):
    cache = _make_mock_cache()
    _make_records(db_session, employee_factory, year=2026, count=55, grade='A')
    fake_engine = MagicMock(spec=PerformanceTierEngine)
    fake_engine.assign.side_effect = RuntimeError('engine boom')
    service = PerformanceService(db_session, cache=cache, engine=fake_engine)
    with pytest.raises(TierRecomputeFailedError) as exc_info:
        service.recompute_tiers(2026)
    assert exc_info.value.year == 2026
    assert 'engine boom' in exc_info.value.cause


# ---------------------------------------------------------------------------
# invalidate_tier_cache
# ---------------------------------------------------------------------------

def test_invalidate_tier_cache_calls_cache_invalidate(db_session):
    cache = _make_mock_cache()
    service = PerformanceService(db_session, cache=cache)
    service.invalidate_tier_cache(2026)
    cache.invalidate.assert_called_once_with(2026)
    cache.invalidate.reset_mock()
    service.invalidate_tier_cache([2024, 2025, 2026])
    assert cache.invalidate.call_count == 3


def test_invalidate_tier_cache_with_none_cache_is_noop(db_session):
    service = PerformanceService(db_session, cache=None)
    # 不抛异常即可
    service.invalidate_tier_cache(2026)
    service.invalidate_tier_cache([2024, 2025])


# ---------------------------------------------------------------------------
# list_available_years (B-3)
# ---------------------------------------------------------------------------

def test_get_available_years_returns_distinct_sorted_desc(
    db_session, employee_factory,
):
    """B-3：表有重复 year → distinct desc。"""
    _make_records(db_session, employee_factory, year=2024, count=2)
    _make_records(db_session, employee_factory, year=2026, count=2)
    _make_records(db_session, employee_factory, year=2025, count=2)
    # 重复一次 2026
    e_extra = employee_factory(employee_no='EXTRA001')
    db_session.add(PerformanceRecord(
        employee_id=e_extra.id, employee_no=e_extra.employee_no,
        year=2026, grade='C', source='manual',
        department_snapshot=e_extra.department,
    ))
    db_session.commit()
    service = PerformanceService(db_session)
    years = service.list_available_years()
    assert years == [2026, 2025, 2024]


def test_list_available_years_empty_returns_current_year(db_session):
    service = PerformanceService(db_session)
    years = service.list_available_years()
    assert years == [date.today().year]


# ==== Phase 35 ESELF-03: get_my_tier 用例 ====
# NOTE: datetime / UUID / MyTierResponse 已在文件顶部 import 区提升，section 内不再 inline import。


def test_get_my_tier_returns_no_snapshot_when_db_empty(db_session, employee_factory):
    """分支 A：全库无任何 PerformanceTierSnapshot → reason='no_snapshot'。"""
    emp = employee_factory(employee_no='E35001')
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert isinstance(result, MyTierResponse)
    assert result.year is None
    assert result.tier is None
    assert result.reason == 'no_snapshot'
    assert result.data_updated_at is None


def test_get_my_tier_returns_insufficient_sample_when_flag_true(db_session, employee_factory):
    """分支 B：当前年快照 insufficient_sample=True → reason='insufficient_sample'，tier=None。"""
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E35002')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={},
        sample_size=5,
        insufficient_sample=True,
        distribution_warning=False,
        actual_distribution_json={},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    db_session.refresh(snap)
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert result.year == current_year
    assert result.tier is None
    assert result.reason == 'insufficient_sample'
    assert result.data_updated_at is not None
    assert result.data_updated_at == snap.updated_at


def test_get_my_tier_returns_tier_when_employee_in_tiers_json(db_session, employee_factory):
    """分支 C：当前年快照命中 + tiers_json[str(uuid)] == 2 → tier=2, reason=None。"""
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E35003')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): 2},
        sample_size=100,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.2, '2': 0.7, '3': 0.1},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert result.year == current_year
    assert result.tier == 2
    assert result.reason is None


def test_get_my_tier_accepts_uuid_object_and_stringifies_key(db_session, employee_factory):
    """str(UUID) lookup：调用方传 UUID 对象时，内部 str(employee_id) 匹配 tiers_json str key。"""
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E35004')
    emp_uuid = UUID(emp.id) if isinstance(emp.id, str) else emp.id
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): 1},
        sample_size=80,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.25, '2': 0.65, '3': 0.10},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session)
    # 传 UUID 对象也应命中
    result_uuid = service.get_my_tier(emp_uuid)
    assert result_uuid.tier == 1
    # 传 str 也应命中
    result_str = service.get_my_tier(str(emp.id))
    assert result_str.tier == 1


def test_get_my_tier_returns_not_ranked_when_key_missing(db_session, employee_factory):
    """分支 D-1：key 不存在于 tiers_json → reason='not_ranked'。"""
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E35005')
    other_emp = employee_factory(employee_no='E35006')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(other_emp.id): 1},  # 仅 other，不含 emp
        sample_size=60,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.2, '2': 0.7, '3': 0.1},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert result.year == current_year
    assert result.tier is None
    assert result.reason == 'not_ranked'
    assert result.data_updated_at is not None


def test_get_my_tier_returns_not_ranked_when_value_is_none(db_session, employee_factory):
    """分支 D-2：tiers_json[str(uuid)] is None → reason='not_ranked'。"""
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E35007')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): None},
        sample_size=60,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert result.tier is None
    assert result.reason == 'not_ranked'


def test_get_my_tier_falls_back_to_latest_year_when_current_missing(db_session, employee_factory):
    """分支 E (fallback)：当前年无快照 → 使用 ORDER BY year DESC 最新年快照。"""
    current_year = datetime.now().year
    older_year = current_year - 2  # 绝对不等于 current_year
    emp = employee_factory(employee_no='E35008')
    snap = PerformanceTierSnapshot(
        year=older_year,
        tiers_json={str(emp.id): 3},
        sample_size=50,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.2, '2': 0.7, '3': 0.1},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert result.year == older_year  # ← fallback 到旧年
    assert result.tier == 3
    assert result.reason is None


def test_get_my_tier_invariant_tier_implies_reason_none(db_session, employee_factory):
    """不变式：tier in {1,2,3} → reason 必为 None（D-04 契约）。"""
    current_year = datetime.now().year
    emp = employee_factory(employee_no='E35009')
    snap = PerformanceTierSnapshot(
        year=current_year,
        tiers_json={str(emp.id): 2},
        sample_size=100,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={},
        skipped_invalid_grades=0,
    )
    db_session.add(snap)
    db_session.commit()
    service = PerformanceService(db_session)
    result = service.get_my_tier(str(emp.id))
    assert result.tier in {1, 2, 3}
    assert result.reason is None, f'tier={result.tier} 时 reason 必须为 None'
