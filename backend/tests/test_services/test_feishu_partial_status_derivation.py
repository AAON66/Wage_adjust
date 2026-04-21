from __future__ import annotations


def test_derive_status_all_zero_returns_success() -> None:
    """Test 5: 全零 → 'success'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert _derive_status(_SyncCounters()) == 'success'


def test_derive_status_only_success_returns_success() -> None:
    """Test 6: success=100 others=0 → 'success'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert _derive_status(_SyncCounters(success=100)) == 'success'


def test_derive_status_unmatched_triggers_partial() -> None:
    """Test 7: success=100, unmatched=1 → 'partial'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert _derive_status(_SyncCounters(success=100, unmatched=1)) == 'partial'


def test_derive_status_mapping_failed_triggers_partial() -> None:
    """Test 8: success=100, mapping_failed=1 → 'partial'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert _derive_status(_SyncCounters(success=100, mapping_failed=1)) == 'partial'


def test_derive_status_failed_triggers_partial() -> None:
    """Test 9: success=100, failed=1 → 'partial'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert _derive_status(_SyncCounters(success=100, failed=1)) == 'partial'


def test_derive_status_all_three_non_zero_triggers_partial() -> None:
    """Test 10: unmatched=1, mapping_failed=1, failed=1 → 'partial'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert (
        _derive_status(_SyncCounters(unmatched=1, mapping_failed=1, failed=1))
        == 'partial'
    )


def test_derive_status_leading_zero_fallback_does_not_trigger_partial() -> None:
    """Test 11: success=100, leading_zero_fallback=5, others=0 → 'success'（关键：fallback 不降级）。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    c = _SyncCounters(
        success=100,
        leading_zero_fallback=5,
        unmatched=0,
        mapping_failed=0,
        failed=0,
    )
    assert _derive_status(c) == 'success'


def test_derive_status_high_leading_zero_fallback_still_success() -> None:
    """Test 12: success=100, leading_zero_fallback=100 → 'success'（fallback 即使很高也不降级）。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    c = _SyncCounters(success=100, leading_zero_fallback=100)
    assert _derive_status(c) == 'success'


def test_derive_status_all_non_fallback_counters_non_zero_is_partial() -> None:
    """Test 13: all non-fallback counters 同时非零 → 'partial'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    c = _SyncCounters(
        success=5,
        updated=3,
        unmatched=1,
        mapping_failed=2,
        failed=4,
        leading_zero_fallback=7,
        total_fetched=10,
    )
    assert _derive_status(c) == 'partial'


def test_derive_status_only_updated_non_zero_is_success() -> None:
    """updated=100 但其他为 0 → success（updated 不触发 partial）。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    c = _SyncCounters(updated=100)
    assert _derive_status(c) == 'success'


def test_derive_status_only_total_fetched_non_zero_is_success() -> None:
    """total_fetched=100 但其他为 0 → success（total_fetched 不触发 partial）。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    c = _SyncCounters(total_fetched=100)
    assert _derive_status(c) == 'success'


def test_derive_status_unmatched_alone_is_partial() -> None:
    """只 unmatched=1 其他全零 → 'partial'。"""
    from backend.app.services.feishu_service import _SyncCounters, _derive_status

    assert _derive_status(_SyncCounters(unmatched=1)) == 'partial'
