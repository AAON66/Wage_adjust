from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.feishu_sync_log import FeishuSyncLog

load_model_modules()


# ---------------------------------------------------------------------------
# Local fixtures (no conftest.py exists for this test tree — inline by design)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """In-memory SQLite session — each test gets a fresh engine + schema."""
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_log(**overrides) -> FeishuSyncLog:
    defaults = {
        'sync_type': 'attendance',
        'mode': 'full',
        'status': 'success',
        'started_at': datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return FeishuSyncLog(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_leading_zero_fallback_count_default_is_zero(db_session: Session) -> None:
    log = _make_log()
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    assert log.leading_zero_fallback_count == 0


def test_leading_zero_fallback_count_can_be_set(db_session: Session) -> None:
    log = _make_log(leading_zero_fallback_count=5)
    db_session.add(log)
    db_session.commit()
    row_id = log.id
    db_session.expire_all()
    fetched = db_session.get(FeishuSyncLog, row_id)
    assert fetched is not None
    assert fetched.leading_zero_fallback_count == 5


def test_existing_rows_have_zero_server_default(db_session: Session) -> None:
    # 通过 raw SQL 直接插入不含 leading_zero_fallback_count 列的行，验证 server_default 生效
    ts = datetime.now(timezone.utc)
    db_session.execute(text(
        "INSERT INTO feishu_sync_logs "
        "(id, sync_type, mode, status, total_fetched, synced_count, updated_count, "
        "skipped_count, unmatched_count, failed_count, started_at, created_at) "
        "VALUES "
        "(:id, 'attendance', 'full', 'success', 0, 0, 0, 0, 0, 0, :ts, :ts)"
    ), {'id': 'test-server-default-row', 'ts': ts})
    db_session.commit()
    result = db_session.execute(text(
        "SELECT leading_zero_fallback_count FROM feishu_sync_logs WHERE id=:id"
    ), {'id': 'test-server-default-row'}).scalar_one()
    # The server_default on the leading_zero_fallback_count column must populate 0 for rows
    # that did not explicitly include it in the INSERT statement.
    assert result == 0, "leading_zero_fallback_count server_default must be 0"


# ---------------------------------------------------------------------------
# Phase 31 / IMPORT-03 / IMPORT-04 — sync_type + mapping_failed_count tests
# ---------------------------------------------------------------------------

def test_create_log_with_sync_type_performance(db_session: Session) -> None:
    """D-01: FeishuSyncLog 可按 sync_type='performance' 写入并查询回来。"""
    from sqlalchemy import select
    log = FeishuSyncLog(
        sync_type='performance',
        mode='full',
        status='running',
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    db_session.commit()
    fetched = db_session.scalar(
        select(FeishuSyncLog).where(FeishuSyncLog.sync_type == 'performance')
    )
    assert fetched is not None
    assert fetched.mapping_failed_count == 0  # D-02 default


def test_mapping_failed_count_defaults_to_zero(db_session: Session) -> None:
    """D-02: 未指定 mapping_failed_count 时，ORM default=0 生效。"""
    log = FeishuSyncLog(
        sync_type='hire_info',
        mode='full',
        status='success',
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    assert log.mapping_failed_count == 0


def test_sync_type_is_required(db_session: Session) -> None:
    """D-01: sync_type NOT NULL — 未指定则 commit 抛 IntegrityError。"""
    log = FeishuSyncLog(
        mode='full',
        status='success',
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    with pytest.raises(Exception):  # IntegrityError: sync_type NOT NULL
        db_session.commit()
    db_session.rollback()


def test_mapping_failed_count_accepts_positive(db_session: Session) -> None:
    """D-02: mapping_failed_count 可接受正整数。"""
    log = FeishuSyncLog(
        sync_type='salary_adjustments',
        mode='full',
        status='partial',
        mapping_failed_count=5,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    assert log.mapping_failed_count == 5


def test_all_five_sync_type_values_are_persistable(db_session: Session) -> None:
    """D-01: 五种 sync_type 值全部可以独立写入。"""
    from sqlalchemy import select
    values = ('attendance', 'performance', 'salary_adjustments', 'hire_info', 'non_statutory_leave')
    for sync_type in values:
        log = FeishuSyncLog(
            sync_type=sync_type,
            mode='full',
            status='success',
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(log)
    db_session.commit()
    rows = db_session.scalars(
        select(FeishuSyncLog).where(FeishuSyncLog.sync_type.in_(values))
    ).all()
    assert {r.sync_type for r in rows} == set(values)


# ---------------------------------------------------------------------------
# Pydantic SyncLogRead schema tests (D-01 / D-02 / D-09)
# ---------------------------------------------------------------------------

def test_sync_log_read_accepts_partial_status() -> None:
    """D-09: SyncLogRead.status 接受 'partial'。"""
    from backend.app.schemas.feishu import SyncLogRead
    data = {
        'id': 'abc',
        'sync_type': 'performance',
        'mode': 'full',
        'status': 'partial',
        'total_fetched': 10,
        'synced_count': 5,
        'updated_count': 3,
        'skipped_count': 1,
        'unmatched_count': 1,
        'mapping_failed_count': 0,
        'failed_count': 0,
        'leading_zero_fallback_count': 0,
        'error_message': None,
        'unmatched_employee_nos': None,
        'started_at': datetime.now(timezone.utc),
        'finished_at': None,
        'triggered_by': None,
    }
    obj = SyncLogRead.model_validate(data)
    assert obj.status == 'partial'
    assert obj.sync_type == 'performance'
    assert obj.mapping_failed_count == 0


def test_sync_log_read_rejects_invalid_status() -> None:
    """D-09: SyncLogRead.status 是 Literal — 'bogus' 抛 ValidationError。"""
    from pydantic import ValidationError
    from backend.app.schemas.feishu import SyncLogRead
    data = {
        'id': 'abc',
        'sync_type': 'performance',
        'mode': 'full',
        'status': 'bogus',
        'total_fetched': 0,
        'synced_count': 0,
        'updated_count': 0,
        'skipped_count': 0,
        'unmatched_count': 0,
        'mapping_failed_count': 0,
        'failed_count': 0,
        'leading_zero_fallback_count': 0,
        'error_message': None,
        'unmatched_employee_nos': None,
        'started_at': datetime.now(timezone.utc),
        'finished_at': None,
        'triggered_by': None,
    }
    with pytest.raises(ValidationError):
        SyncLogRead.model_validate(data)


def test_sync_log_read_rejects_invalid_sync_type() -> None:
    """D-01: SyncLogRead.sync_type 是 Literal — 非白名单值抛 ValidationError。"""
    from pydantic import ValidationError
    from backend.app.schemas.feishu import SyncLogRead
    data = {
        'id': 'abc',
        'sync_type': 'unknown_type',
        'mode': 'full',
        'status': 'success',
        'total_fetched': 0,
        'synced_count': 0,
        'updated_count': 0,
        'skipped_count': 0,
        'unmatched_count': 0,
        'mapping_failed_count': 0,
        'failed_count': 0,
        'leading_zero_fallback_count': 0,
        'error_message': None,
        'unmatched_employee_nos': None,
        'started_at': datetime.now(timezone.utc),
        'finished_at': None,
        'triggered_by': None,
    }
    with pytest.raises(ValidationError):
        SyncLogRead.model_validate(data)
