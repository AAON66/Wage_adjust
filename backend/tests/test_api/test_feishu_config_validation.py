"""EMPNO-03 / EMPNO-04 API integration tests.

Covers POST/PUT /api/v1/feishu/config 422 + GET /api/v1/feishu/sync-logs
field passthrough for leading_zero_fallback_count.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
from backend.app.services.feishu_service import FeishuConfigValidationError

load_model_modules()


# ---------------------------------------------------------------------------
# Local fixtures (no conftest.py exists for this test tree — inline by design)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """In-memory SQLite session shared via StaticPool."""
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


@pytest.fixture()
def admin_user(db_session: Session):
    """Seed an admin user for dependency override / JWT generation."""
    user = User(
        id=str(uuid.uuid4()),
        email='admin@test.com',
        hashed_password='x',
        role='admin',
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_client(db_session: Session, settings, admin_user):
    """FastAPI TestClient with admin JWT + get_db override."""
    app = create_app()
    from backend.app.dependencies import get_app_settings, get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_settings():
        return settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_app_settings] = override_get_settings

    jwt = create_access_token(
        admin_user.id,
        role=admin_user.role,
        settings=settings,
        token_version=admin_user.token_version,
    )
    client = TestClient(app)
    client.headers.update({'Authorization': f'Bearer {jwt}'})
    return client


def _config_create_payload() -> dict:
    return {
        'app_id': 'cli_test',
        'app_secret': 'secret_test',
        'bitable_app_token': 'token_test',
        'bitable_table_id': 'tbl_test',
        'field_mapping': [
            {'feishu_field': '工号', 'system_field': 'employee_no'},
        ],
        'sync_hour': 6,
        'sync_minute': 0,
        'sync_timezone': 'Asia/Shanghai',
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_config_rejects_invalid_field_type_with_422(
    admin_client: TestClient,
) -> None:
    with patch(
        'backend.app.api.v1.feishu.FeishuService.create_config',
        side_effect=FeishuConfigValidationError({
            'error': 'invalid_field_type',
            'field': 'employee_no',
            'expected': 'text',
            'actual': 'number',
        }),
    ):
        resp = admin_client.post('/api/v1/feishu/config', json=_config_create_payload())
    assert resp.status_code == 422
    body = resp.json()
    payload = body.get('detail') if isinstance(body.get('detail'), dict) else body
    assert payload.get('error') == 'invalid_field_type'
    assert payload.get('field') == 'employee_no'
    assert payload.get('expected') == 'text'
    assert payload.get('actual') == 'number'


def test_update_config_rejects_invalid_field_type_with_422(
    admin_client: TestClient,
) -> None:
    with patch(
        'backend.app.api.v1.feishu.FeishuService.update_config',
        side_effect=FeishuConfigValidationError({
            'error': 'invalid_field_type',
            'field': 'employee_no',
            'expected': 'text',
            'actual': 'number',
        }),
    ):
        resp = admin_client.put(
            '/api/v1/feishu/config/test-config-id',
            json={
                'field_mapping': [{'feishu_field': '工号', 'system_field': 'employee_no'}],
            },
        )
    assert resp.status_code == 422
    body = resp.json()
    payload = body.get('detail') if isinstance(body.get('detail'), dict) else body
    assert payload.get('error') == 'invalid_field_type'
    assert payload.get('field') == 'employee_no'


def test_create_config_succeeds_when_validator_passes(
    admin_client: TestClient,
) -> None:
    """Validator 通过时路由正常返回非 422。"""
    with patch(
        'backend.app.services.feishu_service.FeishuService._validate_field_mapping_with_credentials',
        return_value=None,
    ), patch(
        'backend.app.api.v1.feishu.reload_scheduler',
        return_value=None,
    ), patch(
        'backend.app.services.feishu_service.FeishuService._ensure_token',
        return_value='mock-token',
    ):
        resp = admin_client.post('/api/v1/feishu/config', json=_config_create_payload())
    # Validator 不是错误源；期望非 422
    assert resp.status_code != 422


def test_sync_logs_response_includes_leading_zero_fallback_count(
    admin_client: TestClient, db_session: Session,
) -> None:
    log = FeishuSyncLog(
        sync_type='attendance',  # Phase 31 / D-01
        mode='full',
        status='success',
        total_fetched=100,
        synced_count=100,
        updated_count=0,
        skipped_count=0,
        unmatched_count=0,
        failed_count=0,
        leading_zero_fallback_count=7,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db_session.add(log)
    db_session.commit()

    resp = admin_client.get('/api/v1/feishu/sync-logs?limit=10')
    assert resp.status_code == 200
    logs = resp.json()
    matched = [entry for entry in logs if entry.get('id') == log.id]
    assert len(matched) == 1
    assert matched[0]['leading_zero_fallback_count'] == 7
