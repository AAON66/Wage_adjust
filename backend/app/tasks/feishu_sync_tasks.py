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
    """Phase 31 / D-01 / Pitfall C / H: sync_methods dict 统一 canonical key 名 'performance'，
    保留 'performance_grades' alias 过渡一个 release；canonical_sync_type 规范化用于
    Celery update_state meta 与返回 payload（FeishuSyncLog.sync_type 由 service 层写入）。
    """
    # Phase 31 / Pitfall H: normalize legacy alias to canonical key for state/meta/payload.
    canonical_sync_type = 'performance' if sync_type == 'performance_grades' else sync_type

    self.update_state(
        state='PROGRESS',
        meta={
            'sync_type': canonical_sync_type,
            'processed': 0,
            'total': 0,
            'errors': 0,
            'user_id': operator_id,
        },
    )
    db = SessionLocal()
    try:
        from backend.app.services.feishu_service import FeishuService

        service = FeishuService(db)

        # Phase 31 / Pitfall C / H: 'performance' is canonical; 'performance_grades'
        # is retained as alias for in-flight Celery tasks still enqueued with the
        # legacy key. TODO(phase-32): remove performance_grades alias after Redis
        # broker drain window closes.
        sync_methods = {
            'performance': service.sync_performance_records,
            'performance_grades': service.sync_performance_records,
            'salary_adjustments': service.sync_salary_adjustments,
            'hire_info': service.sync_hire_info,
            'non_statutory_leave': service.sync_non_statutory_leave,
        }

        method = sync_methods.get(sync_type)
        if method is None:
            return {'status': 'failed', 'error': f'Unsupported sync_type: {sync_type}'}

        # Phase 31 / D-10: method now returns FeishuSyncLog (not dict). Forward
        # triggered_by=operator_id so the service writes audit trail.
        result_log = method(
            app_token=app_token,
            table_id=table_id,
            field_mapping=field_mapping,
            triggered_by=operator_id,
        )

        # Serialize counters from FeishuSyncLog for Celery state + return payload.
        # Celery JSON result backend cannot pickle SQLAlchemy ORM instances.
        result = {
            'sync_log_id': result_log.id,
            'sync_type': canonical_sync_type,
            'status': result_log.status,
            'synced': result_log.synced_count,
            'updated': result_log.updated_count,
            'unmatched': result_log.unmatched_count,
            'mapping_failed': result_log.mapping_failed_count,
            'failed': result_log.failed_count,
            'total': result_log.total_fetched,
            'leading_zero_fallback_count': result_log.leading_zero_fallback_count,
        }

        self.update_state(
            state='PROGRESS',
            meta={
                'sync_type': canonical_sync_type,
                'processed': (
                    result['synced']
                    + result['updated']
                    + result['unmatched']
                    + result['mapping_failed']
                    + result['failed']
                ),
                'total': result['total'],
                'errors': result['failed'] + result['mapping_failed'],
                'user_id': operator_id,
            },
        )

        return {'status': 'completed', 'result': result}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.exception(
                'feishu_sync_eligibility_task failed after max retries: %s', exc
            )
            return {'status': 'failed', 'error': str(exc)}
        raise
    finally:
        db.close()
