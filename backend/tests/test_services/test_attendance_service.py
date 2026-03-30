"""RED test stubs for AttendanceService — implementation in Plan 02.

Covers: ATT-05 (single employee query), ATT-06 (data_as_of timestamp).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_get_employee_attendance_returns_latest_period() -> None:
    """ATT-05: 查询单员工考勤返回最新周期记录。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_attendance_includes_data_as_of() -> None:
    """ATT-06: 考勤记录包含面向用户的 data_as_of 时间戳。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_list_attendance_with_search_filter() -> None:
    """考勤列表支持按工号或姓名搜索过滤。"""
    pytest.fail('Not implemented')
