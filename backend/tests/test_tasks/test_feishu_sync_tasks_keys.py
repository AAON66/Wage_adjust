"""Phase 31 Plan 03 Task 2: feishu_sync_eligibility_task sync_methods key migration tests.

Covers (Pitfall C + H, D-01):
- 'performance' (canonical) → service.sync_performance_records
- 'performance_grades' (legacy alias) → service.sync_performance_records; canonical_sync_type='performance'
- 'salary_adjustments' / 'hire_info' / 'non_statutory_leave' → correct service methods
- 'bogus' unknown sync_type → {'status': 'failed', ...}, no exception
- triggered_by=operator_id is forwarded to service methods
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_mock_log(sync_type: str = 'performance', status: str = 'success'):
    log = MagicMock()
    log.id = f'log-{sync_type}'
    log.status = status
    log.synced_count = 5
    log.updated_count = 1
    log.unmatched_count = 0
    log.mapping_failed_count = 0
    log.failed_count = 0
    log.total_fetched = 6
    log.leading_zero_fallback_count = 0
    return log


def test_sync_type_performance_calls_sync_performance_records() -> None:
    """Test 15: sync_type='performance' (canonical) routes to sync_performance_records."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    mock_service = MagicMock()
    mock_service.sync_performance_records.return_value = _make_mock_log('performance')

    with patch(
        'backend.app.services.feishu_service.FeishuService',
        return_value=mock_service,
    ):
        result = feishu_sync_eligibility_task.apply(
            args=['performance', 'app_token', 'table_id', {'f': 's'}, 'user-1']
        ).result

    assert result['status'] == 'completed'
    assert result['result']['sync_type'] == 'performance'
    mock_service.sync_performance_records.assert_called_once()
    kwargs = mock_service.sync_performance_records.call_args.kwargs
    assert kwargs['triggered_by'] == 'user-1'
    assert kwargs['app_token'] == 'app_token'
    assert kwargs['table_id'] == 'table_id'
    assert kwargs['field_mapping'] == {'f': 's'}


def test_legacy_alias_performance_grades_routes_to_performance_records() -> None:
    """Test 16: legacy alias 'performance_grades' still works; canonical normalized to 'performance'."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    mock_service = MagicMock()
    mock_service.sync_performance_records.return_value = _make_mock_log('performance')

    with patch(
        'backend.app.services.feishu_service.FeishuService',
        return_value=mock_service,
    ):
        result = feishu_sync_eligibility_task.apply(
            args=['performance_grades', 'app_token', 'table_id', {'f': 's'}, 'user-2']
        ).result

    assert result['status'] == 'completed'
    # Canonical form: alias normalized to 'performance' in returned payload
    assert result['result']['sync_type'] == 'performance'
    mock_service.sync_performance_records.assert_called_once()


def test_sync_type_salary_adjustments() -> None:
    """Test 17a: sync_type='salary_adjustments' routes to sync_salary_adjustments."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    mock_service = MagicMock()
    mock_service.sync_salary_adjustments.return_value = _make_mock_log('salary_adjustments')

    with patch(
        'backend.app.services.feishu_service.FeishuService',
        return_value=mock_service,
    ):
        result = feishu_sync_eligibility_task.apply(
            args=['salary_adjustments', 'app', 'tbl', {}, 'u-3']
        ).result

    assert result['status'] == 'completed'
    mock_service.sync_salary_adjustments.assert_called_once()
    assert mock_service.sync_salary_adjustments.call_args.kwargs['triggered_by'] == 'u-3'


def test_sync_type_hire_info() -> None:
    """Test 17b: sync_type='hire_info' routes to sync_hire_info."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    mock_service = MagicMock()
    mock_service.sync_hire_info.return_value = _make_mock_log('hire_info')

    with patch(
        'backend.app.services.feishu_service.FeishuService',
        return_value=mock_service,
    ):
        result = feishu_sync_eligibility_task.apply(
            args=['hire_info', 'app', 'tbl', {}, 'u-4']
        ).result

    assert result['status'] == 'completed'
    mock_service.sync_hire_info.assert_called_once()


def test_sync_type_non_statutory_leave() -> None:
    """Test 17c: sync_type='non_statutory_leave' routes to sync_non_statutory_leave."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    mock_service = MagicMock()
    mock_service.sync_non_statutory_leave.return_value = _make_mock_log('non_statutory_leave')

    with patch(
        'backend.app.services.feishu_service.FeishuService',
        return_value=mock_service,
    ):
        result = feishu_sync_eligibility_task.apply(
            args=['non_statutory_leave', 'app', 'tbl', {}, 'u-5']
        ).result

    assert result['status'] == 'completed'
    mock_service.sync_non_statutory_leave.assert_called_once()


def test_unknown_sync_type_returns_failed() -> None:
    """Test 18: unsupported sync_type returns {'status': 'failed', 'error': '...'} without exception."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    result = feishu_sync_eligibility_task.apply(
        args=['bogus', 'app', 'tbl', {}, None]
    ).result

    assert result['status'] == 'failed'
    assert 'bogus' in result['error']


def test_triggered_by_passed_as_operator_id() -> None:
    """Test 19: triggered_by kwarg receives operator_id verbatim."""
    from backend.app.tasks.feishu_sync_tasks import feishu_sync_eligibility_task

    mock_service = MagicMock()
    mock_service.sync_performance_records.return_value = _make_mock_log('performance')

    with patch(
        'backend.app.services.feishu_service.FeishuService',
        return_value=mock_service,
    ):
        feishu_sync_eligibility_task.apply(
            args=['performance', 'app', 'tbl', {}, 'operator-abc-123']
        )

    kwargs = mock_service.sync_performance_records.call_args.kwargs
    assert kwargs['triggered_by'] == 'operator-abc-123'
