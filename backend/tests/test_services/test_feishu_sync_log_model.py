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
        "(id, mode, status, total_fetched, synced_count, updated_count, "
        "skipped_count, unmatched_count, failed_count, started_at, created_at) "
        "VALUES "
        "(:id, 'full', 'success', 0, 0, 0, 0, 0, 0, :ts, :ts)"
    ), {'id': 'test-server-default-row', 'ts': ts})
    db_session.commit()
    result = db_session.execute(text(
        "SELECT leading_zero_fallback_count FROM feishu_sync_logs WHERE id=:id"
    ), {'id': 'test-server-default-row'}).scalar_one()
    # The server_default on the leading_zero_fallback_count column must populate 0 for rows
    # that did not explicitly include it in the INSERT statement.
    assert result == 0, "leading_zero_fallback_count server_default must be 0"
