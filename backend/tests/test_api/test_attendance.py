"""RED test stubs for attendance API endpoints — implementation in Plan 02.

Covers: ATT-02 (manual sync endpoint), ATT-05 (attendance query endpoint).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_trigger_sync_requires_admin_or_hrbp() -> None:
    """ATT-02: 同步触发端点需要 admin 或 hrbp 角色。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_trigger_sync_returns_sync_log_id() -> None:
    """ATT-02: 同步触发返回 sync_log_id。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_get_employee_attendance_returns_200() -> None:
    """ATT-05: 查询员工考勤端点返回 200。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_attendance_endpoint_requires_auth() -> None:
    """考勤端点需要认证。"""
    pytest.fail('Not implemented')
