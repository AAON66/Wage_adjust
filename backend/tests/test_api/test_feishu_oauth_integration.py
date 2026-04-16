"""Integration tests for Feishu OAuth API endpoints.

Covers: FAUTH-01..05 end-to-end flow via FastAPI TestClient.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.core.database import Base
from backend.app.main import create_app
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.user import User

load_model_modules()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """In-memory SQLite session shared across threads via StaticPool."""
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


@pytest.fixture()
def settings():
    """Test settings with feishu config populated."""
    return Settings(
        feishu_app_id='cli_test_app_id',
        feishu_app_secret='test_secret',
        feishu_redirect_uri='https://example.com/callback',
        redis_url='redis://localhost:6379/0',
        jwt_secret_key='test-secret-key-12345',
        database_url='sqlite://',
        feishu_encryption_key='test-enc-key-1234567890123456',
    )


@pytest.fixture()
def mock_redis():
    """Mock Redis client with dict-backed storage."""
    store: dict[str, str] = {}

    client = MagicMock()
    client.ping.return_value = True

    def setex(key, ttl, value):
        store[key] = value

    def get(key):
        return store.get(key)

    def delete(key):
        store.pop(key, None)

    def exists(key):
        return 1 if key in store else 0

    client.setex = MagicMock(side_effect=setex)
    client.get = MagicMock(side_effect=get)
    client.delete = MagicMock(side_effect=delete)
    client.exists = MagicMock(side_effect=exists)
    client._store = store
    return client


@pytest.fixture()
def seed_employee_and_user(db):
    """Create an Employee and a User linked to it (no feishu_open_id yet)."""
    emp = Employee(
        id=str(uuid.uuid4()),
        employee_no='E1001',
        name='Test Employee',
        department='Engineering',
        job_family='Software',
        job_level='P6',
    )
    db.add(emp)
    db.flush()

    user = User(
        id=str(uuid.uuid4()),
        email='test@example.com',
        hashed_password='hashed',
        role='employee',
        employee_id=emp.id,
    )
    db.add(user)
    db.commit()
    return emp, user


@pytest.fixture()
def client(db, settings):
    """FastAPI TestClient with overridden dependencies."""
    app = create_app()

    # Override dependencies
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

    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFeishuAuthorizeEndpoint:
    @patch('backend.app.services.feishu_oauth_service.redis_lib')
    def test_authorize_returns_url_and_state(self, mock_redis_lib, client, mock_redis):
        """GET /api/v1/auth/feishu/authorize 返回 authorize_url 和 state。"""
        mock_redis_lib.from_url.return_value = mock_redis

        resp = client.get('/api/v1/auth/feishu/authorize')
        assert resp.status_code == 200
        data = resp.json()
        assert 'authorize_url' in data
        assert 'state' in data
        assert 'cli_test_app_id' in data['authorize_url']
        assert 'redirect_uri' in data['authorize_url']


class TestFeishuCallbackEndpoint:
    @patch('backend.app.services.feishu_oauth_service.redis_lib')
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_callback_success_returns_tokens(
        self, mock_httpx, mock_redis_lib, client, mock_redis, seed_employee_and_user
    ):
        """POST /api/v1/auth/feishu/callback 成功返回 JWT tokens 和 user 信息。"""
        emp, user = seed_employee_and_user
        mock_redis_lib.from_url.return_value = mock_redis

        # Prepare state
        state = 'valid-state-token'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        # Mock token exchange
        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {
                'access_token': 'user_access_token_123',
                'token_type': 'Bearer',
                'expires_in': 7200,
            },
        }

        # Mock user info
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {
                'open_id': 'ou_test_open_id_123',
                'employee_no': emp.employee_no,
                'name': 'Test User',
            },
        }

        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        resp = client.post(
            '/api/v1/auth/feishu/callback',
            json={'code': 'valid-code', 'state': state},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'user' in data
        assert 'tokens' in data
        assert data['user']['id'] == user.id
        assert data['user']['feishu_open_id'] == 'ou_test_open_id_123'
        assert 'access_token' in data['tokens']
        assert 'refresh_token' in data['tokens']

    @patch('backend.app.services.feishu_oauth_service.redis_lib')
    def test_callback_invalid_state_returns_400(self, mock_redis_lib, client, mock_redis):
        """POST /api/v1/auth/feishu/callback 无效 state 返回 400。"""
        mock_redis_lib.from_url.return_value = mock_redis

        resp = client.post(
            '/api/v1/auth/feishu/callback',
            json={'code': 'some-code', 'state': 'invalid-state'},
        )
        assert resp.status_code == 400
        assert '无效的 state 参数' in resp.json()['message']

    @patch('backend.app.services.feishu_oauth_service.redis_lib')
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_callback_unmatched_employee_returns_400(
        self, mock_httpx, mock_redis_lib, db, settings, mock_redis
    ):
        """POST /api/v1/auth/feishu/callback 工号未匹配返回 400。"""
        from fastapi.testclient import TestClient
        from backend.app.dependencies import get_app_settings, get_db

        app = create_app()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_app_settings] = lambda: settings

        mock_redis_lib.from_url.return_value = mock_redis

        state = 'valid-state'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {'access_token': 'token', 'token_type': 'Bearer', 'expires_in': 7200},
        }
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {'open_id': 'ou_unmatched', 'employee_no': 'E9999', 'name': 'Unknown'},
        }
        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        with TestClient(app) as c:
            resp = c.post(
                '/api/v1/auth/feishu/callback',
                json={'code': 'valid-code', 'state': state},
            )
        assert resp.status_code == 400
        assert '工号未匹配' in resp.json()['message']
