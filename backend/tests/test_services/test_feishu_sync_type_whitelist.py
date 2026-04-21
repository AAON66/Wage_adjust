from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.feishu_sync_log import FeishuSyncLog

load_model_modules()


@pytest.fixture()
def patched_service(monkeypatch):
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    from backend.app.services import feishu_service as fs_module
    monkeypatch.setattr(fs_module, 'SessionLocal', session_factory)

    session = session_factory()
    from backend.app.services.feishu_service import FeishuService
    service = FeishuService(session)
    try:
        yield service, session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_helper_rejects_non_whitelist_sync_type(patched_service) -> None:
    """Test 25: _with_sync_log 非白名单值立即 ValueError，不写任何 log。"""
    from backend.app.services.feishu_service import _SyncCounters

    service, session = patched_service
    with pytest.raises(ValueError, match='Unknown sync_type'):
        service._with_sync_log('bogus', lambda **kw: _SyncCounters())

    # No log written
    from backend.app.services import feishu_service as fs_module
    fresh = fs_module.SessionLocal()
    try:
        rows = fresh.execute(select(FeishuSyncLog)).scalars().all()
        assert rows == []
    finally:
        fresh.close()


def test_helper_accepts_all_five_whitelisted_sync_types(patched_service) -> None:
    """Test 26: 五个合法 sync_type 都不抛。"""
    from backend.app.services.feishu_service import _SyncCounters

    service, session = patched_service

    def noop_body(*, sync_log_id: str) -> _SyncCounters:
        return _SyncCounters(success=1)

    for sync_type in (
        'attendance',
        'performance',
        'salary_adjustments',
        'hire_info',
        'non_statutory_leave',
    ):
        log_id = service._with_sync_log(sync_type, noop_body)
        assert log_id


def test_valid_sync_types_constant_is_frozenset() -> None:
    """_VALID_SYNC_TYPES 是 frozenset，包含五个白名单值。"""
    from backend.app.services.feishu_service import _VALID_SYNC_TYPES

    assert isinstance(_VALID_SYNC_TYPES, frozenset)
    assert _VALID_SYNC_TYPES == frozenset({
        'attendance',
        'performance',
        'salary_adjustments',
        'hire_info',
        'non_statutory_leave',
    })
