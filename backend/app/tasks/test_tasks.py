from __future__ import annotations

from sqlalchemy import text

from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal


@celery_app.task(name='tasks.db_health_check')
def db_health_check() -> dict:
    db = SessionLocal()
    try:
        result = db.execute(text('SELECT 1')).scalar()
        return {'status': 'ok', 'db_check': result == 1}
    finally:
        db.close()
