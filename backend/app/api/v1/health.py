from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/health', tags=['health'])


@router.get('/celery')
def celery_health() -> dict[str, object]:
    try:
        inspector = celery_app.control.inspect(timeout=3)
        ping_result = inspector.ping() if inspector else None
    except Exception:
        logger.exception('Celery health check failed')
        ping_result = None

    checked_at = datetime.now(timezone.utc).isoformat()
    if ping_result:
        return {
            'status': 'healthy',
            'workers_online': len(ping_result),
            'checked_at': checked_at,
        }

    return {
        'status': 'unhealthy',
        'workers_online': 0,
        'checked_at': checked_at,
    }
