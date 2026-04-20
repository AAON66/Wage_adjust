"""Tests for FeishuOAuthService — OAuth2 authorization code login flow.

Covers: FAUTH-01..05 (飞书 OAuth 登录全流程)
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings
from backend.app.core.database import Base
from backend.app.models import load_model_modules
from backend.app.models.employee import Employee
from backend.app.models.user import User

load_model_modules()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    """In-memory SQLite session for testing."""
    engine = create_engine('sqlite://', echo=False)
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
    client._store = store  # expose for assertions
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
    db.flush()
    return emp, user


def _make_service(db, settings):
    from backend.app.services.feishu_oauth_service import FeishuOAuthService
    return FeishuOAuthService(db, settings=settings)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateAuthorizeUrl:
    def test_generate_authorize_url(self, db, settings, mock_redis):
        """返回 dict 含 authorize_url 和 state，URL 包含 client_id 和 redirect_uri 参数，state 已存入 Redis（TTL 300s）。"""
        service = _make_service(db, settings)
        result = service.generate_authorize_url(mock_redis)

        assert 'authorize_url' in result
        assert 'state' in result
        assert settings.feishu_app_id in result['authorize_url']
        assert 'redirect_uri' in result['authorize_url']
        # state stored in Redis
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f'feishu_oauth_state:{result["state"]}'
        assert call_args[0][1] == 300


class TestHandleCallbackSuccess:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_handle_callback_success(self, mock_httpx, db, settings, mock_redis, seed_employee_and_user):
        """mock httpx 返回有效 token 和 user_info，mock DB 有匹配 Employee 和 User，返回 User 且 feishu_open_id 已绑定。"""
        emp, user = seed_employee_and_user

        # Prepare state in Redis
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

        service = _make_service(db, settings)
        result = service.handle_callback('valid-code', state, mock_redis)

        assert result.id == user.id
        assert result.feishu_open_id == 'ou_test_open_id_123'


class TestBoundUserFastPath:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_bound_user_fast_path(self, mock_httpx, db, settings, mock_redis, seed_employee_and_user):
        """User.feishu_open_id 已绑定时，跳过 employee_no 匹配直接返回 User。"""
        emp, user = seed_employee_and_user
        user.feishu_open_id = 'ou_already_bound'
        db.flush()

        state = 'valid-state'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        # Mock token exchange
        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {'access_token': 'tok', 'token_type': 'Bearer', 'expires_in': 7200},
        }

        # Mock user info — returns open_id matching bound user
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {'open_id': 'ou_already_bound', 'employee_no': 'IGNORED', 'name': 'Bound'},
        }

        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        service = _make_service(db, settings)
        result = service.handle_callback('code-123', state, mock_redis)

        assert result.id == user.id
        assert result.feishu_open_id == 'ou_already_bound'


class TestStateCsrfValidation:
    def test_state_csrf_validation(self, db, settings, mock_redis):
        """state 不在 Redis 中时抛出 HTTPException(400)。"""
        service = _make_service(db, settings)
        with pytest.raises(HTTPException) as exc_info:
            service.handle_callback('code', 'invalid-state', mock_redis)
        assert exc_info.value.status_code == 400


class TestStateConsumedAfterUse:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_state_consumed_after_use(self, mock_httpx, db, settings, mock_redis, seed_employee_and_user):
        """成功回调后 state key 从 Redis 删除。"""
        emp, user = seed_employee_and_user
        state = 'consume-state'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {'access_token': 'tok', 'token_type': 'Bearer', 'expires_in': 7200},
        }
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {'open_id': 'ou_consume', 'employee_no': emp.employee_no, 'name': 'X'},
        }
        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        service = _make_service(db, settings)
        service.handle_callback('code-x', state, mock_redis)

        # state should be consumed (deleted)
        assert mock_redis._store.get(f'feishu_oauth_state:{state}') is None


class TestCodeReplayPrevention:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_code_replay_prevention(self, mock_httpx, db, settings, mock_redis, seed_employee_and_user):
        """同一 code 第二次使用时抛出 HTTPException(400, '授权码已使用')。"""
        emp, user = seed_employee_and_user

        # First call succeeds
        state1 = 'state-1'
        mock_redis._store[f'feishu_oauth_state:{state1}'] = '1'

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {'access_token': 'tok', 'token_type': 'Bearer', 'expires_in': 7200},
        }
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {'open_id': 'ou_replay', 'employee_no': emp.employee_no, 'name': 'X'},
        }
        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        service = _make_service(db, settings)
        service.handle_callback('reused-code', state1, mock_redis)

        # Second call with same code should fail
        state2 = 'state-2'
        mock_redis._store[f'feishu_oauth_state:{state2}'] = '1'

        with pytest.raises(HTTPException) as exc_info:
            service.handle_callback('reused-code', state2, mock_redis)
        assert exc_info.value.status_code == 400
        assert '授权码已使用' in str(exc_info.value.detail)


class TestUnmatchedEmployeeError:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_unmatched_employee_error(self, mock_httpx, db, settings, mock_redis):
        """employee_no 在系统中无匹配时抛出 HTTPException(400, '工号未匹配，请联系管理员开通')。"""
        state = 'state-unmatched'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {'access_token': 'tok', 'token_type': 'Bearer', 'expires_in': 7200},
        }
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {'open_id': 'ou_no_match', 'employee_no': 'NONEXISTENT', 'name': 'X'},
        }
        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        service = _make_service(db, settings)
        with pytest.raises(HTTPException) as exc_info:
            service.handle_callback('code-no-match', state, mock_redis)
        assert exc_info.value.status_code == 400
        assert '工号未匹配，请联系管理员开通' in str(exc_info.value.detail)


class TestNoUserForEmployeeError:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_no_user_for_employee_error(self, mock_httpx, db, settings, mock_redis):
        """Employee 存在但无绑定 User 时抛出 HTTPException(400, '工号未匹配，请联系管理员开通')。"""
        # Create employee without a user
        emp = Employee(
            id=str(uuid.uuid4()),
            employee_no='E9999',
            name='Orphan Employee',
            department='HR',
            job_family='Admin',
            job_level='P3',
        )
        db.add(emp)
        db.flush()

        state = 'state-no-user'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 0,
            'data': {'access_token': 'tok', 'token_type': 'Bearer', 'expires_in': 7200},
        }
        user_info_resp = MagicMock()
        user_info_resp.status_code = 200
        user_info_resp.json.return_value = {
            'code': 0,
            'data': {'open_id': 'ou_orphan', 'employee_no': 'E9999', 'name': 'X'},
        }
        mock_httpx.post.return_value = token_resp
        mock_httpx.get.return_value = user_info_resp

        service = _make_service(db, settings)
        with pytest.raises(HTTPException) as exc_info:
            service.handle_callback('code-orphan', state, mock_redis)
        assert exc_info.value.status_code == 400
        assert '工号未匹配，请联系管理员开通' in str(exc_info.value.detail)


class TestFeishuApiErrorMapping:
    @patch('backend.app.services.feishu_oauth_service.httpx')
    def test_feishu_api_error_mapping(self, mock_httpx, db, settings, mock_redis):
        """飞书 API 返回错误码 20003 时映射为 '授权码已使用或已过期'。"""
        state = 'state-api-err'
        mock_redis._store[f'feishu_oauth_state:{state}'] = '1'

        token_resp = MagicMock()
        token_resp.status_code = 200
        token_resp.json.return_value = {
            'code': 20003,
            'msg': 'authorization code has been used',
        }
        mock_httpx.post.return_value = token_resp

        service = _make_service(db, settings)
        with pytest.raises(HTTPException) as exc_info:
            service.handle_callback('code-err', state, mock_redis)
        assert exc_info.value.status_code == 400
        assert '授权码已使用或已过期' in str(exc_info.value.detail)


class TestRedisUnavailable:
    def test_redis_unavailable_returns_503(self, db, settings):
        """Redis 不可用时 OAuth 操作返回 503。"""
        # Use a port that is guaranteed unreachable
        bad_settings = Settings(
            **{**settings.model_dump(), 'redis_url': 'redis://127.0.0.1:19999/0'},
        )
        service = _make_service(db, bad_settings)
        with pytest.raises(HTTPException) as exc_info:
            service.require_redis()
        assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# Phase 27.1 bind / unbind tests
# ---------------------------------------------------------------------------


def _make_user_with_employee(db, *, employee_no='E0001', open_id=None, email=None):
    """Helper: create an Employee + a User linked to it, with optional feishu_open_id."""
    emp = Employee(
        id=str(uuid.uuid4()),
        employee_no=employee_no,
        name=f'User-{employee_no}',
        department='R&D',
        job_family='Eng',
        job_level='P5',
    )
    db.add(emp)
    db.flush()
    user = User(
        id=str(uuid.uuid4()),
        email=email or f'{uuid.uuid4().hex[:8]}@ex.com',
        hashed_password='x',
        role='employee',
        employee_id=emp.id,
        feishu_open_id=open_id,
    )
    db.add(user)
    db.flush()
    return user


class TestGenerateAuthorizeUrlPurpose:
    def test_generate_authorize_url_login_vs_bind_isolation(self, db, settings, mock_redis):
        """purpose='login' / 'bind' 使用不同 state key 前缀 + 不同 redirect_uri。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        svc = _make_service(db, settings)
        login_res = svc.generate_authorize_url(mock_redis, purpose='login')
        bind_res = svc.generate_authorize_url(mock_redis, purpose='bind')
        assert f'feishu_oauth_state:{login_res["state"]}' in mock_redis._store
        assert f'feishu_oauth_state:bind:{bind_res["state"]}' in mock_redis._store
        # bind URL must use bind redirect
        assert 'settings%2Ffeishu-bind-callback' in bind_res['authorize_url']
        # login URL must NOT use bind redirect
        assert 'feishu-bind-callback' not in login_res['authorize_url']

    def test_generate_authorize_url_bind_503_when_unset(self, db, settings, mock_redis):
        """bind purpose + empty feishu_bind_redirect_uri → 503。"""
        settings.feishu_bind_redirect_uri = ''
        svc = _make_service(db, settings)
        with pytest.raises(HTTPException) as exc:
            svc.generate_authorize_url(mock_redis, purpose='bind')
        assert exc.value.status_code == 503
        assert '绑定服务暂不可用' in str(exc.value.detail)

    def test_generate_authorize_url_default_purpose_is_login(self, db, settings, mock_redis):
        """未传 purpose 时默认 login，state key 前缀为非-bind。"""
        svc = _make_service(db, settings)
        result = svc.generate_authorize_url(mock_redis)
        assert f'feishu_oauth_state:{result["state"]}' in mock_redis._store
        # must NOT have bind prefix
        assert f'feishu_oauth_state:bind:{result["state"]}' not in mock_redis._store


class TestHandleBindCallback:
    def test_handle_bind_callback_happy_path(self, db, settings, mock_redis):
        """正常绑定：state 验证通过 → open_id 写入 user.feishu_open_id。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        user = _make_user_with_employee(db, employee_no='E0001')
        mock_redis._store['feishu_oauth_state:bind:S1'] = '1'
        svc = _make_service(db, settings)
        with patch.object(svc, '_exchange_code_for_token_for_bind', return_value={'access_token': 'T'}), \
             patch.object(svc, '_get_user_info', return_value={'open_id': 'ou_abc', 'employee_no': 'E0001'}):
            result = svc.handle_bind_callback('C1', 'S1', user, mock_redis)
        assert result.feishu_open_id == 'ou_abc'
        # state consumed
        assert mock_redis._store.get('feishu_oauth_state:bind:S1') is None
        # code recorded for replay prevention
        assert mock_redis._store.get('feishu_oauth_code:C1') == '1'

    def test_handle_bind_callback_conflict_409(self, db, settings, mock_redis):
        """open_id 已被其他 User 占用 → 409。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        # Existing user with the open_id
        _make_user_with_employee(db, employee_no='E0002', open_id='ou_taken', email='taken@ex.com')
        me = _make_user_with_employee(db, employee_no='E0001', email='me@ex.com')
        mock_redis._store['feishu_oauth_state:bind:S2'] = '1'
        svc = _make_service(db, settings)
        with patch.object(svc, '_exchange_code_for_token_for_bind', return_value={'access_token': 'T'}), \
             patch.object(svc, '_get_user_info', return_value={'open_id': 'ou_taken', 'employee_no': 'E0001'}):
            with pytest.raises(HTTPException) as exc:
                svc.handle_bind_callback('C2', 'S2', me, mock_redis)
        assert exc.value.status_code == 409
        assert '该飞书账号已被其他系统账号绑定' in str(exc.value.detail)
        # me.feishu_open_id must remain None
        assert me.feishu_open_id is None

    def test_handle_bind_callback_employee_no_mismatch_400(self, db, settings, mock_redis):
        """飞书工号 ≠ user.employee.employee_no → 400。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        user = _make_user_with_employee(db, employee_no='E0001')
        mock_redis._store['feishu_oauth_state:bind:S3'] = '1'
        svc = _make_service(db, settings)
        with patch.object(svc, '_exchange_code_for_token_for_bind', return_value={'access_token': 'T'}), \
             patch.object(svc, '_get_user_info', return_value={'open_id': 'ou_x', 'employee_no': 'E9999'}):
            with pytest.raises(HTTPException) as exc:
                svc.handle_bind_callback('C3', 'S3', user, mock_redis)
        assert exc.value.status_code == 400
        assert '飞书工号与当前账号绑定的工号不一致' in str(exc.value.detail)

    def test_handle_bind_callback_user_without_employee_400(self, db, settings, mock_redis):
        """User.employee_id is None → 400。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        # User without Employee
        user = User(
            id=str(uuid.uuid4()),
            email='no-emp@ex.com',
            hashed_password='x',
            role='admin',
            employee_id=None,
        )
        db.add(user)
        db.flush()
        mock_redis._store['feishu_oauth_state:bind:S4'] = '1'
        svc = _make_service(db, settings)
        with patch.object(svc, '_exchange_code_for_token_for_bind', return_value={'access_token': 'T'}), \
             patch.object(svc, '_get_user_info', return_value={'open_id': 'ou_z', 'employee_no': 'E0001'}):
            with pytest.raises(HTTPException) as exc:
                svc.handle_bind_callback('C4', 'S4', user, mock_redis)
        assert exc.value.status_code == 400
        assert '当前账号未关联员工信息' in str(exc.value.detail)

    def test_handle_bind_callback_invalid_state_400(self, db, settings, mock_redis):
        """bind state key 不存在 → 400（login state 不能被 bind 消费）。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        user = _make_user_with_employee(db, employee_no='E0001')
        # Pre-seed login-prefix state (no bind-prefix)
        mock_redis._store['feishu_oauth_state:LOGIN_ONLY'] = '1'
        svc = _make_service(db, settings)
        with pytest.raises(HTTPException) as exc:
            svc.handle_bind_callback('C5', 'LOGIN_ONLY', user, mock_redis)
        assert exc.value.status_code == 400
        assert '无效的 state 参数' in str(exc.value.detail)

    def test_handle_bind_callback_leading_zero_tolerant(self, db, settings, mock_redis):
        """leading-zero 容差：E00001 vs 1 可匹配。"""
        settings.feishu_bind_redirect_uri = 'https://ex.com/settings/feishu-bind-callback'
        user = _make_user_with_employee(db, employee_no='00001')
        mock_redis._store['feishu_oauth_state:bind:S6'] = '1'
        svc = _make_service(db, settings)
        # Feishu returns '1' (leading zeros stripped); system stored '00001'
        with patch.object(svc, '_exchange_code_for_token_for_bind', return_value={'access_token': 'T'}), \
             patch.object(svc, '_get_user_info', return_value={'open_id': 'ou_lz', 'employee_no': '1'}):
            result = svc.handle_bind_callback('C6', 'S6', user, mock_redis)
        assert result.feishu_open_id == 'ou_lz'


class TestHandleUnbind:
    def test_handle_unbind_clears_open_id(self, db, settings, mock_redis):
        """handle_unbind 清空 feishu_open_id。"""
        user = _make_user_with_employee(db, open_id='ou_present')
        svc = _make_service(db, settings)
        result = svc.handle_unbind(user)
        assert result.feishu_open_id is None

    def test_handle_unbind_idempotent(self, db, settings, mock_redis):
        """handle_unbind 对已为 None 的用户幂等。"""
        user = _make_user_with_employee(db, open_id=None)
        svc = _make_service(db, settings)
        result = svc.handle_unbind(user)
        assert result.feishu_open_id is None
        # Second call — still idempotent, no error
        result2 = svc.handle_unbind(result)
        assert result2.feishu_open_id is None

    def test_handle_unbind_does_not_touch_token_version(self, db, settings, mock_redis):
        """handle_unbind 不改动 token_version（D-10：保留当前 session）。"""
        user = _make_user_with_employee(db, open_id='ou_keep_session')
        initial_version = user.token_version
        svc = _make_service(db, settings)
        svc.handle_unbind(user)
        assert user.token_version == initial_version
