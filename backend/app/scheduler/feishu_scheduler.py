from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler(
    sync_hour: int = 6,
    sync_minute: int = 0,
    sync_timezone: str = 'Asia/Shanghai',
) -> None:
    """启动定时同步调度器，显式使用配置的时区。"""
    scheduler.add_job(
        run_incremental_sync,
        trigger=CronTrigger(hour=sync_hour, minute=sync_minute, timezone=sync_timezone),
        id='feishu_attendance_sync',
        replace_existing=True,
    )
    scheduler.start()
    logger.info('Feishu scheduler started: %02d:%02d %s', sync_hour, sync_minute, sync_timezone)


def stop_scheduler() -> None:
    """停止调度器。"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info('Feishu scheduler stopped')


def reload_scheduler(sync_hour: int, sync_minute: int, sync_timezone: str) -> None:
    """配置更新后重新加载调度器。"""
    if scheduler.running:
        try:
            scheduler.remove_job('feishu_attendance_sync')
        except Exception:
            pass
    scheduler.add_job(
        run_incremental_sync,
        trigger=CronTrigger(hour=sync_hour, minute=sync_minute, timezone=sync_timezone),
        id='feishu_attendance_sync',
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()
    logger.info('Feishu scheduler reloaded: %02d:%02d %s', sync_hour, sync_minute, sync_timezone)


def run_incremental_sync() -> None:
    """定时增量同步 job，在独立 Session 中执行。"""
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        from backend.app.services.feishu_service import FeishuService
        service = FeishuService(db)
        service.sync_with_retry(mode='incremental', triggered_by='scheduler')
    except Exception:
        logger.exception('定时考勤同步失败')
    finally:
        db.close()
