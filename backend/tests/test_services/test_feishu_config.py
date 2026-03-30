"""RED test stubs for FeishuConfig CRUD — implementation in Plan 02.

Covers: ATT-04 (config CRUD + encryption), Review #10 (blank secret keeps current).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_create_config_encrypts_secret() -> None:
    """ATT-04: 创建配置时 app_secret 被加密存储。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_read_config_masks_secret() -> None:
    """ATT-04: 读取配置时 app_secret 仅返回掩码。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_update_config_blank_secret_keeps_current() -> None:
    """Review #10: 更新时 app_secret 为 None/空字符串则保留原值。"""
    pytest.fail('Not implemented')


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_field_mapping_persists_correctly() -> None:
    """ATT-04: field_mapping JSON 正确持久化和读取。"""
    pytest.fail('Not implemented')
