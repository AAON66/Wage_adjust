"""RED test stubs for FeishuService — implementation in Plan 02.

Covers: ATT-01 (API field mapping), ATT-07 (retry), D-02 (token refresh),
        Review #9 (unmatched employee tracking).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_fetch_records_maps_fields_correctly() -> None:
    """ATT-01: 飞书字段映射正确转换为系统字段。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_fetch_records_handles_pagination() -> None:
    """ATT-01: 分页请求正确处理 has_more + page_token。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_sync_incremental_uses_last_sync_time() -> None:
    """增量同步仅拉取上次同步之后的记录。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_sync_full_fetches_all() -> None:
    """全量同步拉取全部记录。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_sync_retry_on_failure() -> None:
    """ATT-07: 同步失败后自动重试。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_unmatched_employee_no_tracked() -> None:
    """Review #9: 未匹配的工号被记录到 sync_log.unmatched_employee_nos。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_token_auto_refresh() -> None:
    """D-02: tenant_access_token 过期后自动刷新。"""
    pytest.fail('Not implemented')
