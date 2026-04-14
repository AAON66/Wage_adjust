from __future__ import annotations

import logging

from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    name='tasks.feishu_sync_eligibility',
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=660,
)
def feishu_sync_eligibility_task(
    self,
    sync_type: str,
    app_token: str,
    table_id: str,
    field_mapping: dict[str, str],
    operator_id: str | None = None,
) -> dict:
    self.update_state(
        state='PROGRESS',
        meta={'sync_type': sync_type, 'processed': 0, 'total': 0, 'errors': 0, 'user_id': operator_id},
    )
    db = SessionLocal()
    try:
        from backend.app.services.feishu_service import FeishuService

        service = FeishuService(db)

        sync_methods = {
            'performance_grades': service.sync_performance_records,
            'salary_adjustments': service.sync_salary_adjustments,
            'hire_info': service.sync_hire_info,
            'non_statutory_leave': service.sync_non_statutory_leave,
        }

        method = sync_methods.get(sync_type)
        if method is None:
            return {'status': 'failed', 'error': f'Unsupported sync_type: {sync_type}'}

        result = method(app_token=app_token, table_id=table_id, field_mapping=field_mapping)

        self.update_state(
            state='PROGRESS',
            meta={
                'sync_type': sync_type,
                'processed': result.get('synced', 0) + result.get('skipped', 0) + result.get('failed', 0),
                'total': result.get('total', 0),
                'errors': result.get('failed', 0),
                'user_id': operator_id,
            },
        )

        return {'status': 'completed', 'result': result}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.exception('feishu_sync_eligibility_task failed after max retries: %s', exc)
            return {'status': 'failed', 'error': str(exc)}
        raise
    finally:
        db.close()
