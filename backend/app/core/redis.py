from __future__ import annotations

import logging

import redis

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return a lazily-initialized Redis client singleton.

    On first call, creates the client and verifies connectivity via ping().
    If Redis is unreachable, raises redis.ConnectionError (caller handles).
    Redis is a required dependency (per D-03) -- no in-memory fallback.
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            _redis_client.ping()
            logger.info('Redis 连接成功')
        except redis.ConnectionError:
            logger.error('Redis 服务不可用，请启动 Redis 或检查 REDIS_URL 配置')
            _redis_client = None
            raise
    return _redis_client


def reset_redis() -> None:
    """Reset the singleton (used in tests)."""
    global _redis_client
    _redis_client = None
