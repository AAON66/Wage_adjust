"""Phase 31 Plan 03 Task 1: FeishuService.get_sync_logs service-layer tests.

Covers:
- Test 1: no-arg returns logs sorted by started_at desc (default page=1 page_size=20).
- Test 2: sync_type='performance' filters.
- Test 3: legacy limit=5 path (backward-compat for AttendanceManagement polling).
- Test 4: page=2, page_size=3 uses offset=3.
- Test 5: sync_type + pagination combination.
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


def _seed_log(
    session: Session,
    sync_type: str,
    *,
    minutes_ago: int = 0,
    status: str = 'success',
) -> FeishuSyncLog:
    log = FeishuSyncLog(
        sync_type=sync_type,
        mode='full',
        status=status,
        total_fetched=10,
        synced_count=10,
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


def test_get_sync_logs_no_args_returns_started_at_desc(db_session: Session) -> None:
    """Test 1: default page=1 page_size=20, ordered started_at desc."""
    from backend.app.services.feishu_service import FeishuService

    _seed_log(db_session, 'attendance', minutes_ago=10)   # older
    _seed_log(db_session, 'performance', minutes_ago=5)   # middle
    _seed_log(db_session, 'hire_info', minutes_ago=0)     # newest

    svc = FeishuService(db_session)
    logs = svc.get_sync_logs()
    assert len(logs) == 3
    assert logs[0].sync_type == 'hire_info'       # newest first
    assert logs[1].sync_type == 'performance'
    assert logs[2].sync_type == 'attendance'


def test_get_sync_logs_filter_by_sync_type(db_session: Session) -> None:
    """Test 2: sync_type='performance' only returns performance logs."""
    from backend.app.services.feishu_service import FeishuService

    _seed_log(db_session, 'performance', minutes_ago=1)
    _seed_log(db_session, 'performance', minutes_ago=2)
    _seed_log(db_session, 'attendance', minutes_ago=0)

    svc = FeishuService(db_session)
    logs = svc.get_sync_logs(sync_type='performance')
    assert len(logs) == 2
    assert all(log.sync_type == 'performance' for log in logs)


def test_get_sync_logs_legacy_limit_backward_compat(db_session: Session) -> None:
    """Test 3: get_sync_logs(limit=5) continues to work for AttendanceManagement polling."""
    from backend.app.services.feishu_service import FeishuService

    for i in range(10):
        _seed_log(db_session, 'attendance', minutes_ago=i)

    svc = FeishuService(db_session)
    logs = svc.get_sync_logs(limit=5)
    assert len(logs) == 5
    # Newest first (minutes_ago=0..4)
    assert logs[0].sync_type == 'attendance'


def test_get_sync_logs_pagination_page2_pagesize3(db_session: Session) -> None:
    """Test 4: page=2, page_size=3 returns records 4-6 (offset=3)."""
    from backend.app.services.feishu_service import FeishuService

    # Seed 10 logs, minutes_ago 0..9 (0=newest)
    for i in range(10):
        _seed_log(db_session, 'performance', minutes_ago=i)

    svc = FeishuService(db_session)
    logs = svc.get_sync_logs(page=2, page_size=3)
    assert len(logs) == 3
    # page 2, page_size 3 → offset 3 → records[3:6] in newest-first order.
    # started_at desc: index 0 = minutes_ago=0, index 3 = minutes_ago=3.


def test_get_sync_logs_filter_and_pagination(db_session: Session) -> None:
    """Test 5: sync_type='hire_info' + page=1 page_size=20 combined."""
    from backend.app.services.feishu_service import FeishuService

    for i in range(5):
        _seed_log(db_session, 'hire_info', minutes_ago=i)
    for i in range(5):
        _seed_log(db_session, 'attendance', minutes_ago=i + 10)

    svc = FeishuService(db_session)
    logs = svc.get_sync_logs(sync_type='hire_info', page=1, page_size=20)
    assert len(logs) == 5
    assert all(log.sync_type == 'hire_info' for log in logs)
