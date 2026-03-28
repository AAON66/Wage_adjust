from __future__ import annotations

import json
import logging

import redis as redis_lib

logger = logging.getLogger(__name__)

# TTL constants (seconds). TTL_KPI_SUMMARY = 0 means "do not cache".
TTL_KPI_SUMMARY = 0
TTL_AI_LEVEL = 600
TTL_SALARY_DIST = 600
TTL_APPROVAL_PIPELINE = 300
TTL_DEPARTMENT_INSIGHT = 900
TTL_DEPARTMENT_DRILLDOWN = 600


class CacheService:
    """Redis cache wrapper for dashboard data.

    Redis is a required dependency (per D-03). The constructor does NOT accept
    None -- callers must provide a valid redis.Redis instance.
    """

    KEY_PREFIX = 'dashboard'

    def __init__(self, redis_client: redis_lib.Redis) -> None:
        self.redis = redis_client

    @staticmethod
    def _build_key(chart_type: str, cycle_id: str | None, user_id: str) -> str:
        """Build a cache key that isolates data by cycle + user.

        Key format: dashboard:{cycle_id or 'all'}:{user_id}:{chart_type}
        Using user_id (not role) prevents manager-A from seeing manager-B's
        department data through shared cache (review fix #1).
        """
        return f'dashboard:{cycle_id or "all"}:{user_id}:{chart_type}'

    def get(self, chart_type: str, cycle_id: str | None, user_id: str) -> dict | list | None:
        """Return cached data or None on miss.

        Does NOT catch ConnectionError -- caller (API layer) handles it.
        """
        key = self._build_key(chart_type, cycle_id, user_id)
        raw = self.redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(
        self,
        chart_type: str,
        cycle_id: str | None,
        user_id: str,
        data: dict | list,
        ttl_seconds: int = 300,
    ) -> None:
        """Serialize and store data with TTL.

        Uses ``json.dumps(data, default=str)`` to handle Decimal values.
        Does NOT catch ConnectionError.
        """
        key = self._build_key(chart_type, cycle_id, user_id)
        self.redis.setex(key, ttl_seconds, json.dumps(data, default=str))

    def invalidate_cycle(self, cycle_id: str) -> int:
        """Delete all cache keys for a specific cycle."""
        pattern = f'{self.KEY_PREFIX}:{cycle_id}:*'
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0

    def invalidate_for_event(self, event_type: str, cycle_id: str | None = None) -> int:
        """Clear cache keys related to a business event.

        event_type values:
        - 'approval': clears approval_pipeline keys
        - 'evaluation': clears ai_level + salary_dist + approval_pipeline + dept keys
        - 'import': clears all dashboard keys
        - 'all': clears all dashboard keys

        Returns the number of deleted keys.
        """
        if event_type in ('all', 'import'):
            pattern = f'{self.KEY_PREFIX}:*'
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0

        if cycle_id:
            chart_types_map: dict[str, list[str]] = {
                'approval': ['approval_pipeline'],
                'evaluation': ['ai_level', 'salary_dist', 'approval_pipeline', 'dept_insight', 'dept_drilldown_*'],
            }
            chart_types = chart_types_map.get(event_type, ['*'])
            deleted = 0
            for ct in chart_types:
                pattern = f'{self.KEY_PREFIX}:{cycle_id}:*:{ct}'
                keys = self.redis.keys(pattern)
                if keys:
                    deleted += self.redis.delete(*keys)
            return deleted

        # No cycle_id -- clear all
        pattern = f'{self.KEY_PREFIX}:*'
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0
