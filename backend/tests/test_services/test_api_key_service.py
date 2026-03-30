"""RED test stubs for ApiKeyService — implementation in Plan 02.

Covers: API-03 (key CRUD), API-04 (revoked/expired key validation).
"""
from __future__ import annotations

import pytest


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_create_key_stores_sha256_hash() -> None:
    """创建 Key 时存储 SHA-256 hash 而非明文"""
    assert False, 'RED: ApiKeyService.create not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_validate_key_matches_hash() -> None:
    """验证时比较 SHA-256 hash"""
    assert False, 'RED: ApiKeyService.validate not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_validate_key_updates_last_used() -> None:
    """验证成功后更新 last_used_at 和 last_used_ip"""
    assert False, 'RED: ApiKeyService.validate not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_per_key_rate_limit_uses_key_id() -> None:
    """限流使用 key_id 而非 IP"""
    assert False, 'RED: per-key rate limiting not implemented'
