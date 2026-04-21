from __future__ import annotations

from datetime import datetime, timezone

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


def _insert_running_log(session: Session, sync_type: str) -> None:
    session.add(
        FeishuSyncLog(
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
            started_at=datetime.now(timezone.utc),
        )
    )
    session.commit()


def test_is_sync_running_returns_false_when_no_running_logs(db_session: Session) -> None:
    """Test 21: 无 running log → is_sync_running() == False。"""
    from backend.app.services.feishu_service import FeishuService

    svc = FeishuService(db_session)
    assert svc.is_sync_running() is False
    assert svc.is_sync_running('performance') is False
    assert svc.is_sync_running('attendance') is False


def test_is_sync_running_filters_by_sync_type(db_session: Session) -> None:
    """Test 22: 有 attendance running → 分桶过滤正确。"""
    from backend.app.services.feishu_service import FeishuService

    _insert_running_log(db_session, 'attendance')

    svc = FeishuService(db_session)
    assert svc.is_sync_running() is True  # 无参兼容
    assert svc.is_sync_running('attendance') is True
    assert svc.is_sync_running('performance') is False
    assert svc.is_sync_running('hire_info') is False


def test_is_sync_running_parallel_types(db_session: Session) -> None:
    """Test 23: attendance running + performance running 同时存在，各自可检测。"""
    from backend.app.services.feishu_service import FeishuService

    _insert_running_log(db_session, 'attendance')
    _insert_running_log(db_session, 'performance')

    svc = FeishuService(db_session)
    assert svc.is_sync_running() is True
    assert svc.is_sync_running('attendance') is True
    assert svc.is_sync_running('performance') is True
    assert svc.is_sync_running('hire_info') is False


def test_is_sync_running_invalid_sync_type_returns_false_no_exception(
    db_session: Session,
) -> None:
    """Test 24: is_sync_running('invalid_type') 不抛异常，返回 False。"""
    from backend.app.services.feishu_service import FeishuService

    svc = FeishuService(db_session)
    # Non-whitelisted sync_type is allowed; no log matches → False
    assert svc.is_sync_running('invalid_type') is False


def test_is_sync_running_non_running_status_not_counted(db_session: Session) -> None:
    """status='success' 的行不应被识别为 running。"""
    from backend.app.services.feishu_service import FeishuService

    db_session.add(
        FeishuSyncLog(
            sync_type='attendance',
            mode='full',
            status='success',
            total_fetched=0,
            synced_count=0,
            updated_count=0,
            skipped_count=0,
            unmatched_count=0,
            mapping_failed_count=0,
            failed_count=0,
            leading_zero_fallback_count=0,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    svc = FeishuService(db_session)
    assert svc.is_sync_running() is False
    assert svc.is_sync_running('attendance') is False
