"""Phase 32 D-17: APScheduler 定时清理 import 僵尸 job。

选 APScheduler 而非 Celery Beat 的理由（决议 RESEARCH Open Question 2）：
  1. 复用既有 feishu_scheduler.py 模式（v1.4 已确立）
  2. 不增加新部署进程（无需 celery beat worker）
  3. 单元测试友好（直接调用 run_expire_stale_jobs 不依赖 broker）

调度内容：
  每 interval_minutes 分钟（默认 15）调用 ImportService.expire_stale_import_jobs
  双时限清理：
    - processing 超 30min → status='failed' + result_summary.error='timeout'
    - previewing 超 60min → status='cancelled' + 删除暂存文件
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_import_scheduler(*, interval_minutes: int = 15) -> None:
    """启动 import 僵尸清理调度器，每 interval_minutes 分钟执行一次。"""
    scheduler.add_job(
        run_expire_stale_jobs,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id='import_expire_stale',
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
    logger.info('Import scheduler started: every %d minutes', interval_minutes)


def stop_import_scheduler() -> None:
    """停止调度器（lifespan shutdown 调用）。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info('Import scheduler stopped')


def run_expire_stale_jobs() -> None:
    """定时清理 — 用独立 SessionLocal 避免与请求 session 冲突。

    异常被 logger.exception 捕获后吞掉，避免单次失败影响下次调度（T-32-20 mitigate）。
    """
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from backend.app.services.import_service import ImportService
        service = ImportService(db)
        result = service.expire_stale_import_jobs()
        if result.get('processing') or result.get('previewing'):
            logger.info('Expired stale import jobs: %s', result)
    except Exception:
        logger.exception('Failed to expire stale import jobs')
    finally:
        db.close()
