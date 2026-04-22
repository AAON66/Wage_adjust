"""Phase 34 Plan 01 Task 3: PerformanceTierSnapshot ORM 模型层单测。

覆盖：
  Test 1 - JSON round-trip：所有 7 业务字段写入后查询值一致
  Test 2 - UNIQUE(year) 约束：同年插两行触发 IntegrityError
  Test 3 - 默认值生效：仅设必填，自动填充 sample_size=0 / boolean=False / skipped=0
  Test 4 - updated_at 在 UPDATE 时变化（N-1 修复：用 SQL UPDATE 强制时间差，
           避免 time.sleep 在 CI / 高负载机器上的不可靠）
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.models.performance_tier_snapshot import PerformanceTierSnapshot


def test_round_trip_persists_all_fields(db_session) -> None:  # noqa: ANN001
    snap = PerformanceTierSnapshot(
        year=2026,
        tiers_json={'emp_1': 1, 'emp_2': 2, 'emp_3': None},
        sample_size=2,
        insufficient_sample=False,
        distribution_warning=False,
        actual_distribution_json={'1': 0.5, '2': 0.5, '3': 0.0},
        skipped_invalid_grades=1,
    )
    db_session.add(snap)
    db_session.commit()
    snap_id = snap.id

    db_session.expire_all()
    loaded = db_session.get(PerformanceTierSnapshot, snap_id)
    assert loaded is not None
    assert loaded.year == 2026
    assert loaded.tiers_json == {'emp_1': 1, 'emp_2': 2, 'emp_3': None}
    assert loaded.sample_size == 2
    assert loaded.insufficient_sample is False
    assert loaded.distribution_warning is False
    assert loaded.actual_distribution_json == {'1': 0.5, '2': 0.5, '3': 0.0}
    assert loaded.skipped_invalid_grades == 1


def test_unique_year_constraint(db_session) -> None:  # noqa: ANN001
    db_session.add(PerformanceTierSnapshot(
        year=2025, tiers_json={}, actual_distribution_json={},
    ))
    db_session.commit()
    db_session.add(PerformanceTierSnapshot(
        year=2025, tiers_json={'a': 1}, actual_distribution_json={},
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_default_values_applied(db_session) -> None:  # noqa: ANN001
    snap = PerformanceTierSnapshot(
        year=2024,
        tiers_json={},
        actual_distribution_json={},
    )
    db_session.add(snap)
    db_session.commit()
    db_session.expire_all()
    loaded = db_session.get(PerformanceTierSnapshot, snap.id)
    assert loaded is not None
    assert loaded.sample_size == 0
    assert loaded.insufficient_sample is False
    assert loaded.distribution_warning is False
    assert loaded.skipped_invalid_grades == 0


def test_updated_at_changes_on_update(db_session) -> None:  # noqa: ANN001
    """N-1 修复：用 SQL UPDATE 强制把 updated_at 倒推 1 秒，避免 time.sleep 不可靠。"""
    snap = PerformanceTierSnapshot(
        year=2023, tiers_json={}, actual_distribution_json={},
    )
    db_session.add(snap)
    db_session.commit()
    initial_updated = snap.updated_at

    # 关键：用 raw SQL 把 updated_at 倒推 1 秒（避开 time.sleep 在 CI 慢机器上的不可靠）
    past = initial_updated - timedelta(seconds=1)
    db_session.execute(
        text('UPDATE performance_tier_snapshots SET updated_at = :t WHERE id = :i'),
        {'t': past, 'i': snap.id},
    )
    db_session.commit()

    # 现在做真正的 ORM UPDATE，UpdatedAtMixin 会把 updated_at 刷成「现在」
    db_session.refresh(snap)
    snap.sample_size = 99
    db_session.commit()
    db_session.refresh(snap)

    assert snap.updated_at > past
