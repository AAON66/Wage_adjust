from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal, engine

settings = get_settings()

celery_app = Celery(
    'wage_adjust',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'backend.app.tasks.test_tasks',
        'backend.app.tasks.evaluation_tasks',
        'backend.app.tasks.import_tasks',
        'backend.app.tasks.feishu_sync_tasks',
    ],
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
    # Celery prefork workers must drop the actual task DB bind after fork.
    session_bind = SessionLocal.kw.get('bind') or engine
    session_bind.dispose()
    if session_bind is not engine:
        engine.dispose()

    # 注册全部 ORM 模型，避免 relationship() 字符串引用无法解析
    from backend.app.models import load_model_modules
    load_model_modules()


from backend.app.tasks import test_tasks as _test_tasks  # noqa: F401,E402
from backend.app.tasks import evaluation_tasks as _evaluation_tasks  # noqa: F401,E402
from backend.app.tasks import import_tasks as _import_tasks  # noqa: F401,E402
from backend.app.tasks import feishu_sync_tasks as _feishu_sync_tasks  # noqa: F401,E402
