from __future__ import annotations

import base64
import io
import logging

from fastapi import UploadFile

from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal
from backend.app.schemas.import_job import ImportJobRead

logger = logging.getLogger(__name__)


@celery_app.task(
    name='tasks.run_import',
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    soft_time_limit=600,
    time_limit=660,
)
def run_import_task(
    self,
    import_type: str,
    file_bytes_b64: str,
    file_name: str,
    operator_id: str | None = None,
    operator_role: str | None = None,
) -> dict:
    self.update_state(
        state='PROGRESS',
        meta={'processed': 0, 'total': 0, 'errors': 0, 'user_id': operator_id},
    )
    db = SessionLocal()
    try:
        raw_bytes = base64.b64decode(file_bytes_b64)
        upload_file = UploadFile(file=io.BytesIO(raw_bytes), filename=file_name)

        from backend.app.services.import_service import ImportService

        def progress_callback(processed: int, total: int, errors: int) -> None:
            self.update_state(
                state='PROGRESS',
                meta={'processed': processed, 'total': total, 'errors': errors, 'user_id': operator_id},
            )

        service = ImportService(db, operator_id=operator_id, operator_role=operator_role)
        job = service.run_import(
            import_type=import_type,
            upload=upload_file,
            progress_callback=progress_callback,
        )
        serialized = ImportJobRead.model_validate(job).model_dump(mode='json')
        return {'status': 'completed', 'result': serialized}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.exception('run_import_task failed after max retries: %s', exc)
            return {'status': 'failed', 'error': str(exc)}
        raise
    finally:
        db.close()
