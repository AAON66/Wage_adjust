"""Phase 31 Plan 03 Task 2: GET /api/v1/feishu/sync-logs/{id}/unmatched.csv + trigger_sync 409 tests.

Covers CSV endpoint (D-08):
- admin/hrbp get text/csv + correct filename header + header-only for empty unmatched
- employee/manager/unauthenticated blocked
- non-existent log_id → 404
- >20 unmatched → only first 20 in CSV
- special chars (comma, newline, quote) escaped by csv.writer

Covers trigger_sync upgrade (D-15 / D-16):
- Per-sync_type lock: is_sync_running(sync_type='attendance')
- 409 detail contains {error, sync_type, message}
- 409 does NOT write a new FeishuSyncLog (D-16)
- Different sync_type running does not block trigger
- SC4: two sequential triggers produce two independent logs
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.core.database import Base
from backend.app.core.security import create_access_token
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.feishu_sync_log import FeishuSyncLog
from backend.app.models.user import User

load_model_modules()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


@pytest.fixture()
def settings():
    return Settings(
        feishu_app_id='cli_test',
        feishu_app_secret='test',
        redis_url='redis://localhost:6379/0',
        jwt_secret_key='test-secret-key-12345',
        database_url='sqlite://',
        feishu_encryption_key='test-enc-key-1234567890123456',
    )


def _make_user(db: Session, role: str) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=f'{role}-{uuid.uuid4().hex[:6]}@test.com',
        hashed_password='x',
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _client_for(db: Session, settings: Settings, user: User | None) -> TestClient:
    app = create_app()
    from backend.app.dependencies import get_app_settings, get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_settings():
        return settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_app_settings] = override_get_settings

    client = TestClient(app)
    if user is not None:
        jwt = create_access_token(
            user.id,
            role=user.role,
            settings=settings,
            token_version=user.token_version,
        )
        client.headers.update({'Authorization': f'Bearer {jwt}'})
    return client


def _seed_log(
    db: Session,
    sync_type: str = 'performance',
    *,
    status: str = 'success',
    unmatched_employee_nos: list[str] | None = None,
) -> FeishuSyncLog:
    log = FeishuSyncLog(
        sync_type=sync_type,
        mode='full',
        status=status,
        total_fetched=10,
        synced_count=10,
        updated_count=0,
        skipped_count=0,
        unmatched_count=len(unmatched_employee_nos) if unmatched_employee_nos else 0,
        mapping_failed_count=0,
        failed_count=0,
        leading_zero_fallback_count=0,
        unmatched_employee_nos=(
            json.dumps(unmatched_employee_nos) if unmatched_employee_nos else None
        ),
        started_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# CSV endpoint: content + headers
# ---------------------------------------------------------------------------

def test_csv_download_content_and_headers(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=['E001', 'E002', 'E003'])
    client = _client_for(db_session, settings, admin)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 200
    # Content-Type
    assert resp.headers.get('content-type', '').startswith('text/csv')
    assert 'charset=utf-8' in resp.headers.get('content-type', '')
    # Content-Disposition
    disposition = resp.headers.get('content-disposition', '')
    assert 'attachment' in disposition
    assert f'filename=sync-log-{log.id}-unmatched.csv' in disposition
    # Body: header + 3 rows
    body = resp.text
    lines = [line for line in body.splitlines() if line]
    assert lines[0] == 'employee_no'
    assert 'E001' in body
    assert 'E002' in body
    assert 'E003' in body


def test_csv_header_only_when_unmatched_empty(db_session: Session, settings: Settings) -> None:
    """Empty / NULL unmatched_employee_nos → CSV only contains header row."""
    admin = _make_user(db_session, 'admin')
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=None)
    client = _client_for(db_session, settings, admin)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 200
    lines = [line for line in resp.text.splitlines() if line]
    assert len(lines) == 1
    assert lines[0] == 'employee_no'


def test_csv_caps_at_20_rows(db_session: Session, settings: Settings) -> None:
    """Log with 30 unmatched → CSV contains only first 20 + header."""
    admin = _make_user(db_session, 'admin')
    nos = [f'E{i:04d}' for i in range(30)]
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=nos)
    client = _client_for(db_session, settings, admin)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 200
    lines = [line for line in resp.text.splitlines() if line]
    # header + 20 data rows
    assert len(lines) == 21
    assert lines[0] == 'employee_no'
    # First 20 rows are E0000..E0019
    assert lines[1] == 'E0000'
    assert lines[20] == 'E0019'


def test_csv_escapes_special_chars(db_session: Session, settings: Settings) -> None:
    """csv.writer should auto-quote/escape employee_no with commas/newlines/quotes."""
    admin = _make_user(db_session, 'admin')
    nos = ['E,001', 'E"002', 'E\n003']
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=nos)
    client = _client_for(db_session, settings, admin)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 200
    body = resp.text
    # csv.writer quotes fields with special chars
    assert '"E,001"' in body
    # Double-quote inside field is escaped as ""
    assert '"E""002"' in body


# ---------------------------------------------------------------------------
# CSV endpoint: error / role gate
# ---------------------------------------------------------------------------

def test_csv_404_when_log_missing(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs/nonexistent-id/unmatched.csv')
    assert resp.status_code == 404


def test_csv_employee_forbidden(db_session: Session, settings: Settings) -> None:
    emp = _make_user(db_session, 'employee')
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=['E001'])
    client = _client_for(db_session, settings, emp)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 403


def test_csv_manager_forbidden(db_session: Session, settings: Settings) -> None:
    mgr = _make_user(db_session, 'manager')
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=['E001'])
    client = _client_for(db_session, settings, mgr)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 403


def test_csv_unauthenticated_returns_401(db_session: Session, settings: Settings) -> None:
    log = _seed_log(db_session, 'performance', unmatched_employee_nos=['E001'])
    client = _client_for(db_session, settings, None)
    resp = client.get(f'/api/v1/feishu/sync-logs/{log.id}/unmatched.csv')
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# trigger_sync 409 per-sync_type lock (D-15 / D-16)
# ---------------------------------------------------------------------------

def test_trigger_sync_success_when_no_running(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    client = _client_for(db_session, settings, admin)
    # Patch background thread launch to avoid real sync side-effects
    with patch('backend.app.api.v1.feishu.threading.Thread') as mock_thread:
        instance = mock_thread.return_value
        instance.start.return_value = None
        resp = client.post('/api/v1/feishu/sync', json={'mode': 'full'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['status'] == 'running'


def test_trigger_sync_409_when_attendance_running(db_session: Session, settings: Settings) -> None:
    """D-15/D-16: 409 per sync_type='attendance' + detail includes sync_type + no new log written."""
    admin = _make_user(db_session, 'admin')
    # Seed a running attendance log
    log = FeishuSyncLog(
        sync_type='attendance',
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
        started_at=datetime.now(timezone.utc),  # fresh — not expired
    )
    db_session.add(log)
    db_session.commit()
    count_before = db_session.query(FeishuSyncLog).count()

    client = _client_for(db_session, settings, admin)
    resp = client.post('/api/v1/feishu/sync', json={'mode': 'full'})
    assert resp.status_code == 409
    body = resp.json()
    detail = body.get('detail') if isinstance(body.get('detail'), dict) else body
    assert detail.get('error') == 'sync_in_progress'
    assert detail.get('sync_type') == 'attendance'
    assert 'message' in detail

    # D-16: 409 must NOT write a new FeishuSyncLog
    db_session.expire_all()
    count_after = db_session.query(FeishuSyncLog).count()
    assert count_after == count_before


def test_trigger_sync_not_blocked_by_other_sync_type(db_session: Session, settings: Settings) -> None:
    """Different sync_type running ('performance') does not block attendance trigger."""
    admin = _make_user(db_session, 'admin')
    # Seed a running performance log — should NOT block attendance trigger
    db_session.add(FeishuSyncLog(
        sync_type='performance',
        mode='full',
        status='running',
        total_fetched=0, synced_count=0, updated_count=0, skipped_count=0,
        unmatched_count=0, mapping_failed_count=0, failed_count=0,
        leading_zero_fallback_count=0,
        started_at=datetime.now(timezone.utc),
    ))
    db_session.commit()

    client = _client_for(db_session, settings, admin)
    with patch('backend.app.api.v1.feishu.threading.Thread') as mock_thread:
        instance = mock_thread.return_value
        instance.start.return_value = None
        resp = client.post('/api/v1/feishu/sync', json={'mode': 'full'})
    # performance-running doesn't block attendance trigger
    assert resp.status_code == 200


def test_trigger_sync_sequential_triggers_produce_independent_logs(
    db_session: Session, settings: Settings
) -> None:
    """SC4: First trigger completes → second trigger creates new log (not 409)."""
    admin = _make_user(db_session, 'admin')
    # Seed a completed attendance log
    db_session.add(FeishuSyncLog(
        sync_type='attendance',
        mode='full',
        status='success',   # completed
        total_fetched=10, synced_count=10, updated_count=0, skipped_count=0,
        unmatched_count=0, mapping_failed_count=0, failed_count=0,
        leading_zero_fallback_count=0,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        finished_at=datetime.now(timezone.utc) - timedelta(minutes=4),
    ))
    db_session.commit()

    client = _client_for(db_session, settings, admin)
    with patch('backend.app.api.v1.feishu.threading.Thread') as mock_thread:
        instance = mock_thread.return_value
        instance.start.return_value = None
        resp = client.post('/api/v1/feishu/sync', json={'mode': 'full'})
    # After success, new trigger is allowed (no per-sync_type running lock active)
    assert resp.status_code == 200
