from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from backend.app.core.config import Settings
from backend.app.services.tier_cache import TierCache


@pytest.fixture()
def settings() -> Settings:
    return Settings()


def _mock_redis() -> MagicMock:
    m = MagicMock()
    m.get.return_value = None
    m.set.return_value = True
    m.delete.return_value = 1
    return m


def test_cache_key_default_prefix(settings: Settings) -> None:
    cache = TierCache(redis_client=_mock_redis(), settings=settings)
    assert cache.cache_key(2026) == 'tier_summary:2026'


def test_cache_key_custom_prefix() -> None:
    custom = Settings(performance_tier_redis_prefix='foo')
    cache = TierCache(redis_client=_mock_redis(), settings=custom)
    assert cache.cache_key(2026) == 'foo:2026'


def test_set_cached_uses_default_ttl(settings: Settings) -> None:
    redis_mock = _mock_redis()
    cache = TierCache(redis_client=redis_mock, settings=settings)
    payload = {'year': 2026, 'sample_size': 100}
    cache.set_cached(2026, payload)
    redis_mock.set.assert_called_once_with(
        'tier_summary:2026',
        json.dumps(payload, default=str),
        ex=86_400,
    )


def test_set_cached_uses_custom_ttl() -> None:
    custom = Settings(performance_tier_redis_ttl_seconds=10)
    redis_mock = _mock_redis()
    cache = TierCache(redis_client=redis_mock, settings=custom)
    cache.set_cached(2026, {'a': 1})
    _, kwargs = redis_mock.set.call_args
    assert kwargs['ex'] == 10


def test_get_cached_returns_decoded_dict(settings: Settings) -> None:
    redis_mock = _mock_redis()
    redis_mock.get.return_value = '{"year": 2026, "n": 99}'
    cache = TierCache(redis_client=redis_mock, settings=settings)
    got = cache.get_cached(2026)
    assert got == {'year': 2026, 'n': 99}


def test_get_cached_returns_none_on_miss(settings: Settings) -> None:
    redis_mock = _mock_redis()
    redis_mock.get.return_value = None
    cache = TierCache(redis_client=redis_mock, settings=settings)
    assert cache.get_cached(2026) is None


def test_invalidate_calls_redis_delete(settings: Settings) -> None:
    redis_mock = _mock_redis()
    cache = TierCache(redis_client=redis_mock, settings=settings)
    cache.invalidate(2026)
    redis_mock.delete.assert_called_once_with('tier_summary:2026')


def test_get_silent_on_redis_unavailable(settings: Settings) -> None:
    redis_mock = MagicMock()
    redis_mock.get.side_effect = RedisConnectionError('boom')
    cache = TierCache(redis_client=redis_mock, settings=settings)
    assert cache.get_cached(2026) is None  # 不抛异常


def test_set_silent_on_redis_unavailable(settings: Settings) -> None:
    redis_mock = MagicMock()
    redis_mock.set.side_effect = RedisConnectionError('boom')
    cache = TierCache(redis_client=redis_mock, settings=settings)
    cache.set_cached(2026, {'a': 1})  # 不抛异常


def test_invalidate_silent_on_redis_unavailable(settings: Settings) -> None:
    redis_mock = MagicMock()
    redis_mock.delete.side_effect = RedisConnectionError('boom')
    cache = TierCache(redis_client=redis_mock, settings=settings)
    cache.invalidate(2026)  # 不抛异常


def test_redis_client_none_returns_none_no_op(settings: Settings) -> None:
    cache = TierCache(redis_client=None, settings=settings)
    assert cache.get_cached(2026) is None
    cache.set_cached(2026, {'a': 1})  # 不抛
    cache.invalidate(2026)  # 不抛


def test_get_cached_returns_none_on_invalid_json(settings: Settings) -> None:
    redis_mock = _mock_redis()
    redis_mock.get.return_value = 'not-json{'
    cache = TierCache(redis_client=redis_mock, settings=settings)
    assert cache.get_cached(2026) is None
