"""RED test stubs for Feishu scheduler — implementation in Plan 02.

Covers: ATT-03 (cron job registration), Review #2 (timezone).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_scheduler_registers_cron_job() -> None:
    """ATT-03: 调度器注册 cron 定时任务。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_scheduler_uses_configured_timezone() -> None:
    """Review #2: 调度器使用配置的时区。"""
    pytest.fail('Not implemented')
