from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from backend.app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    'wage_adjust',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['backend.app.tasks.test_tasks'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_expires=3600,
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
)


@worker_process_init.connect
def dispose_db_engine_on_worker_init(**_: object) -> None:
    from backend.app.core.database import engine

    engine.dispose()


from backend.app.tasks import test_tasks as _test_tasks  # noqa: F401,E402
