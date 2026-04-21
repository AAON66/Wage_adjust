"""Phase 31 Plan 03 Task 1: GET /api/v1/feishu/sync-logs API integration tests.

Covers:
- admin/hrbp see all 5 sync_types (role gate pass)
- employee/manager/unauthenticated return 403/401 (role gate fail)
- sync_type filter (Pydantic Literal validation)
- page / page_size Query validation (ge=1, le=100)
- response JSON schema contains sync_type + mapping_failed_count + status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

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
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# Role gate tests
# ---------------------------------------------------------------------------

def test_list_employee_forbidden(db_session: Session, settings: Settings) -> None:
    user = _make_user(db_session, 'employee')
    client = _client_for(db_session, settings, user)
    resp = client.get('/api/v1/feishu/sync-logs')
    assert resp.status_code == 403


def test_list_manager_forbidden(db_session: Session, settings: Settings) -> None:
    user = _make_user(db_session, 'manager')
    client = _client_for(db_session, settings, user)
    resp = client.get('/api/v1/feishu/sync-logs')
    assert resp.status_code == 403


def test_list_unauthenticated_returns_401(db_session: Session, settings: Settings) -> None:
    client = _client_for(db_session, settings, None)
    resp = client.get('/api/v1/feishu/sync-logs')
    assert resp.status_code == 401


def test_list_admin_sees_all_sync_types(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    for t in ('attendance', 'performance', 'hire_info'):
        _seed_log(db_session, t)
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert {row['sync_type'] for row in data} == {'attendance', 'performance', 'hire_info'}


def test_list_hrbp_sees_all(db_session: Session, settings: Settings) -> None:
    hr = _make_user(db_session, 'hrbp')
    _seed_log(db_session, 'performance')
    client = _client_for(db_session, settings, hr)
    resp = client.get('/api/v1/feishu/sync-logs')
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# sync_type filter & validation
# ---------------------------------------------------------------------------

def test_list_filter_by_sync_type_performance(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    _seed_log(db_session, 'performance')
    _seed_log(db_session, 'performance')
    _seed_log(db_session, 'attendance')
    _seed_log(db_session, 'hire_info')
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs?sync_type=performance')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(row['sync_type'] == 'performance' for row in data)


def test_list_rejects_invalid_sync_type_with_422(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs?sync_type=bogus')
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pagination validation
# ---------------------------------------------------------------------------

def test_list_rejects_page_zero(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs?page=0')
    assert resp.status_code == 422


def test_list_rejects_oversize_page_size(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs?page_size=200')
    assert resp.status_code == 422


def test_list_pagination_page2_pagesize5(db_session: Session, settings: Settings) -> None:
    admin = _make_user(db_session, 'admin')
    for i in range(15):
        _seed_log(db_session, 'performance', minutes_ago=i)
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs?page=2&page_size=5')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

def test_list_response_has_sync_type_and_mapping_failed_count(
    db_session: Session, settings: Settings
) -> None:
    admin = _make_user(db_session, 'admin')
    _seed_log(db_session, 'performance', status='partial')
    client = _client_for(db_session, settings, admin)
    resp = client.get('/api/v1/feishu/sync-logs')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    row = data[0]
    assert 'sync_type' in row
    assert row['sync_type'] == 'performance'
    assert 'mapping_failed_count' in row
    assert row['status'] in ('running', 'success', 'partial', 'failed')
