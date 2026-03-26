from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def create_limiter(settings) -> Limiter:
    """Create a rate limiter backed by Redis when available.

    Production: hard-fail path — caller must ensure Redis is reachable (validated in validate_startup_config).
    Development: falls back to in-memory limiter if Redis is unavailable, with a warning log.
    """
    import redis as redis_lib

    if settings.environment == 'production':
        # Production: always use Redis. startup config validation ensures Redis is reachable.
        return Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    try:
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        logger.info('Rate limiter using Redis backend at %s', settings.redis_url)
        return Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    except Exception:
        logger.warning(
            'Redis unavailable at %s — rate limiter using in-memory backend (dev only). '
            'Start Redis before deploying to production.',
            settings.redis_url,
        )
        return Limiter(key_func=get_remote_address)


# Module-level limiter instance used as a decorator source in public.py.
# This instance is created with in-memory storage by default; create_app() calls
# create_limiter(settings) and assigns the real instance to app.state.limiter.
# public.py imports THIS object for @limiter.limit() decorator binding only —
# slowapi resolves the actual backend from app.state.limiter at request time.
limiter: Limiter = Limiter(key_func=get_remote_address)
