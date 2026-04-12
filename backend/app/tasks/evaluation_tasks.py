from __future__ import annotations

import logging

from backend.app.celery_app import celery_app
from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    name='tasks.generate_evaluation',
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    soft_time_limit=300,
    time_limit=360,
)
def generate_evaluation_task(
    self,
    submission_id: str,
    force: bool = False,
    user_id: str | None = None,
) -> dict:
    self.update_state(
        state='STARTED',
        meta={'status': 'running', 'user_id': user_id},
    )
    db = SessionLocal()
    try:
        settings = get_settings()
        from backend.app.services.evaluation_service import EvaluationService
        from backend.app.api.v1.evaluations import serialize_evaluation

        service = EvaluationService(db, settings)
        evaluation = service.generate_evaluation(submission_id, force=force)
        serialized = serialize_evaluation(evaluation).model_dump(mode='json')
        return {'status': 'completed', 'result': serialized}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.exception('generate_evaluation_task failed after max retries: %s', exc)
            return {'status': 'failed', 'error': str(exc)}
        raise
    finally:
        db.close()
