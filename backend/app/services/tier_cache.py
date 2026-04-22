from __future__ import annotations

import json
import logging
from typing import Any

import redis as redis_lib

from backend.app.core.config import Settings

logger = logging.getLogger(__name__)


class TierCache:
    """Phase 34 D-02：tier-summary Redis 缓存层（写穿透 + 24h TTL）。

    构造函数注入 redis.Redis 与 Settings，便于单测 mock；
    Redis 不可达时优雅降级（get 返回 None / set/invalidate 静默 noop + warn log），
    不向上层抛 ConnectionError —— 让上层永远走表层 fallback。
    """

    def __init__(
        self,
        redis_client: redis_lib.Redis | None,
        settings: Settings,
    ) -> None:
        self._redis = redis_client
        self._settings = settings

    def cache_key(self, year: int) -> str:
        return f'{self._settings.performance_tier_redis_prefix}:{year}'

    def get_cached(self, year: int) -> dict[str, Any] | None:
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(self.cache_key(year))
        except redis_lib.RedisError as exc:
            logger.warning('Tier cache get failed for year %s: %s', year, exc)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning('Tier cache decode failed for year %s: %s', year, exc)
            return None

    def set_cached(self, year: int, payload: dict[str, Any]) -> None:
        if self._redis is None:
            return
        try:
            self._redis.set(
                self.cache_key(year),
                json.dumps(payload, default=str),
                ex=self._settings.performance_tier_redis_ttl_seconds,
            )
        except redis_lib.RedisError as exc:
            logger.warning('Tier cache set failed for year %s: %s', year, exc)

    def invalidate(self, year: int) -> None:
        if self._redis is None:
            return
        try:
            self._redis.delete(self.cache_key(year))
        except redis_lib.RedisError as exc:
            logger.warning('Tier cache invalidate failed for year %s: %s', year, exc)
