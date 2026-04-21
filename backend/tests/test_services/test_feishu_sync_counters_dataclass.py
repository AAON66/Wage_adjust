from __future__ import annotations

import dataclasses

import pytest


def test_sync_counters_default_construction_zero_fields() -> None:
    """Test 1: _SyncCounters() 无参构造，所有字段默认 0（或空 tuple）。"""
    from backend.app.services.feishu_service import _SyncCounters

    c = _SyncCounters()
    assert c.success == 0
    assert c.updated == 0
    assert c.unmatched == 0
    assert c.mapping_failed == 0
    assert c.failed == 0
    assert c.leading_zero_fallback == 0
    assert c.total_fetched == 0
    assert c.unmatched_nos == ()


def test_sync_counters_partial_construction_works() -> None:
    """Test 2: _SyncCounters(success=5, updated=3) 可构造。"""
    from backend.app.services.feishu_service import _SyncCounters

    c = _SyncCounters(success=5, updated=3)
    assert c.success == 5
    assert c.updated == 3
    assert c.unmatched == 0
    assert c.total_fetched == 0


def test_sync_counters_is_frozen_immutable() -> None:
    """Test 3: _SyncCounters 是 frozen — 尝试 c.success = 10 抛 FrozenInstanceError。"""
    from backend.app.services.feishu_service import _SyncCounters

    c = _SyncCounters(success=5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.success = 10  # type: ignore[misc]


def test_sync_counters_has_all_eight_fields() -> None:
    """Test 4: _SyncCounters 含全部 8 字段 — 用 dataclasses.fields 验证。"""
    from backend.app.services.feishu_service import _SyncCounters

    field_names = {f.name for f in dataclasses.fields(_SyncCounters)}
    assert field_names == {
        'success',
        'updated',
        'unmatched',
        'mapping_failed',
        'failed',
        'leading_zero_fallback',
        'total_fetched',
        'unmatched_nos',
    }


def test_sync_counters_unmatched_nos_is_tuple() -> None:
    """Test: unmatched_nos 必须是 tuple (满足 frozen)."""
    from backend.app.services.feishu_service import _SyncCounters

    c = _SyncCounters(unmatched_nos=('E001', 'E002'))
    assert c.unmatched_nos == ('E001', 'E002')
    assert isinstance(c.unmatched_nos, tuple)
