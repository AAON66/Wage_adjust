"""Phase 31 Plan 03 Task 2: expire_stale_running_logs covers all 5 sync_types (D-17).

Covers:
- Test 20: one running+stale log for each sync_type → all 5 marked failed
- Test 21: running logs within the timeout window are NOT cleaned
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.feishu_sync_log import FeishuSyncLog

load_model_modules()


@pytest.fixture()
def db_session():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _seed_running(session: Session, sync_type: str, *, minutes_ago: int) -> FeishuSyncLog:
    log = FeishuSyncLog(
        sync_type=sync_type,
        mode='full',
        status='running',
        total_fetched=0,
        synced_count=0,
        updated_count=0,
        skipped_count=0,
        unmatched_count=0,
        mapping_failed_count=0,
        failed_count=0,
        leading_zero_fallback_count=0,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def test_expire_stale_covers_all_five_sync_types(db_session: Session) -> None:
    """D-17: all 5 sync_types should be cleaned uniformly."""
    from backend.app.services.feishu_service import FeishuService

    sync_types = (
        'attendance',
        'performance',
        'salary_adjustments',
        'hire_info',
        'non_statutory_leave',
    )
    # Seed one stale running log (started 45 min ago) for each sync_type
    for t in sync_types:
        _seed_running(db_session, t, minutes_ago=45)

    svc = FeishuService(db_session)
    expired = svc.expire_stale_running_logs(timeout_minutes=30)
    assert expired == 5

    db_session.expire_all()
    logs = db_session.query(FeishuSyncLog).all()
    # All 5 should be status='failed' now
    statuses_by_type = {log.sync_type: log.status for log in logs}
    assert statuses_by_type == {t: 'failed' for t in sync_types}


def test_expire_stale_does_not_clean_recent_running(db_session: Session) -> None:
    """Running logs started within the timeout window remain 'running'."""
    from backend.app.services.feishu_service import FeishuService

    # Seed a fresh running log (5 min ago) — inside 30 min window
    _seed_running(db_session, 'performance', minutes_ago=5)

    svc = FeishuService(db_session)
    expired = svc.expire_stale_running_logs(timeout_minutes=30)
    assert expired == 0

    db_session.expire_all()
    log = db_session.query(FeishuSyncLog).first()
    assert log.status == 'running'
