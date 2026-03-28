from __future__ import annotations

import json
from unittest.mock import MagicMock

from backend.app.services.cache_service import CacheService


def _make_mock_redis() -> MagicMock:
    """Create a dict-backed mock that behaves like redis.Redis."""
    store: dict[str, str] = {}
    mock = MagicMock()

    def mock_get(key: str):
        return store.get(key)

    def mock_setex(key: str, ttl: int, value: str):
        store[key] = value

    def mock_keys(pattern: str):
        import fnmatch
        return [k for k in store if fnmatch.fnmatch(k, pattern)]

    def mock_delete(*keys: str):
        count = 0
        for k in keys:
            if k in store:
                del store[k]
                count += 1
        return count

    mock.get = MagicMock(side_effect=mock_get)
    mock.setex = MagicMock(side_effect=mock_setex)
    mock.keys = MagicMock(side_effect=mock_keys)
    mock.delete = MagicMock(side_effect=mock_delete)
    mock._store = store
    return mock


def test_build_key_format() -> None:
    key = CacheService._build_key('ai_level', 'cycle-123', 'user-abc')
    assert key == 'dashboard:cycle-123:user-abc:ai_level'


def test_build_key_no_cycle() -> None:
    key = CacheService._build_key('salary_dist', None, 'user-xyz')
    assert key == 'dashboard:all:user-xyz:salary_dist'


def test_get_set_roundtrip() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    data = [{'label': 'Level 1', 'value': 5}]
    cache.set('ai_level', 'c1', 'u1', data, ttl_seconds=60)
    result = cache.get('ai_level', 'c1', 'u1')
    assert result == data


def test_get_miss_returns_none() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    assert cache.get('ai_level', 'c1', 'u1') is None


def test_user_isolation() -> None:
    """Different user_id keys should not collide (manager A vs manager B)."""
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    cache.set('ai_level', 'c1', 'manager-a', [{'v': 1}], 60)
    cache.set('ai_level', 'c1', 'manager-b', [{'v': 2}], 60)
    assert cache.get('ai_level', 'c1', 'manager-a') == [{'v': 1}]
    assert cache.get('ai_level', 'c1', 'manager-b') == [{'v': 2}]


def test_invalidate_cycle() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    cache.set('ai_level', 'c1', 'u1', [1], 60)
    cache.set('salary_dist', 'c1', 'u2', [2], 60)
    cache.set('ai_level', 'c2', 'u1', [3], 60)
    deleted = cache.invalidate_cycle('c1')
    assert deleted == 2
    assert cache.get('ai_level', 'c1', 'u1') is None
    assert cache.get('ai_level', 'c2', 'u1') == [3]


def test_invalidate_for_event_approval() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    cache.set('approval_pipeline', 'c1', 'u1', [1], 60)
    cache.set('ai_level', 'c1', 'u1', [2], 60)
    deleted = cache.invalidate_for_event('approval', cycle_id='c1')
    assert deleted == 1
    assert cache.get('approval_pipeline', 'c1', 'u1') is None
    assert cache.get('ai_level', 'c1', 'u1') == [2]


def test_invalidate_for_event_all() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    cache.set('ai_level', 'c1', 'u1', [1], 60)
    cache.set('salary_dist', 'c2', 'u2', [2], 60)
    deleted = cache.invalidate_for_event('all')
    assert deleted == 2
    assert cache.get('ai_level', 'c1', 'u1') is None
    assert cache.get('salary_dist', 'c2', 'u2') is None


def test_invalidate_for_event_evaluation() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    cache.set('ai_level', 'c1', 'u1', [1], 60)
    cache.set('salary_dist', 'c1', 'u1', [2], 60)
    cache.set('approval_pipeline', 'c1', 'u1', [3], 60)
    deleted = cache.invalidate_for_event('evaluation', cycle_id='c1')
    assert deleted == 3


def test_invalidate_for_event_import() -> None:
    mock_redis = _make_mock_redis()
    cache = CacheService(mock_redis)
    cache.set('ai_level', 'c1', 'u1', [1], 60)
    cache.set('salary_dist', 'c2', 'u2', [2], 60)
    deleted = cache.invalidate_for_event('import')
    assert deleted == 2
