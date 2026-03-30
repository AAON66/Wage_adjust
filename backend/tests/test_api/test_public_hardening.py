"""RED test stubs for public API hardening — implementation in Plan 02.

Covers: API-01 (approved-only filter), API-02 (cursor pagination),
        API-03 (multi-key management), API-04 (revoked/expired key 401).
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# API-01: 仅返回 approved 记录
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_approved_only_filter_excludes_draft() -> None:
    """salary-results 端点不返回 status=draft 的记录"""
    assert False, 'RED: approved-only filter not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_approved_only_filter_excludes_pending() -> None:
    """salary-results 端点不返回 status=pending 的记录"""
    assert False, 'RED: approved-only filter not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_approved_only_returns_approved() -> None:
    """salary-results 端点返回 status=approved 的记录"""
    assert False, 'RED: approved-only filter not implemented'


# ---------------------------------------------------------------------------
# API-02: 游标分页
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_cursor_pagination_first_page() -> None:
    """首页请求返回 items + next_cursor + has_more"""
    assert False, 'RED: cursor pagination not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_cursor_pagination_no_duplicates() -> None:
    """翻页不丢失不重复"""
    assert False, 'RED: cursor pagination not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_cursor_pagination_max_page_size() -> None:
    """page_size > 100 被截断为 100（per D-06）"""
    assert False, 'RED: cursor pagination not implemented'


# ---------------------------------------------------------------------------
# API-03: 多 Key 管理
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_create_api_key_returns_plain_key() -> None:
    """创建 Key 返回明文（仅一次）"""
    assert False, 'RED: api key management not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_rotate_api_key() -> None:
    """轮换 Key 撤销旧 Key 并返回新 Key"""
    assert False, 'RED: api key rotation not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_revoke_api_key() -> None:
    """撤销 Key 设置 is_active=False"""
    assert False, 'RED: api key revocation not implemented'


# ---------------------------------------------------------------------------
# API-04: 撤销/过期 Key 立即 401
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_revoked_key_returns_401() -> None:
    """已撤销的 Key 请求返回 401"""
    assert False, 'RED: revoked key check not implemented'


@pytest.mark.xfail(reason='RED: implementation in Plan 02')
def test_expired_key_returns_401() -> None:
    """已过期的 Key 请求返回 401"""
    assert False, 'RED: expired key check not implemented'
