from __future__ import annotations

import logging
import secrets
import time
import urllib.parse
from collections.abc import Callable
from typing import TypeVar

import httpx
import redis as redis_lib
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.models.employee import Employee
from backend.app.models.user import User
from backend.app.services.feishu_service import FeishuService

logger = logging.getLogger(__name__)

_TRANSIENT_HTTPX_ERRORS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
)

T = TypeVar('T')


def _call_feishu_with_retry(
    fn: Callable[[], T],
    *,
    endpoint_label: str,
    max_attempts: int = 3,
    backoff_base: float = 0.5,
) -> T:
    """Call a httpx function with exponential backoff on transient transport errors.

    Retries only on ConnectError / TimeoutException / ReadError / WriteError /
    RemoteProtocolError — Feishu's endpoints occasionally drop connections from
    oversea networks. Business errors (HTTP 4xx with a JSON body) still propagate
    immediately since httpx does not raise on them.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except _TRANSIENT_HTTPX_ERRORS as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            delay = backoff_base * (2 ** (attempt - 1))
            logger.warning(
                'Feishu %s transient error (attempt %d/%d): %s — retrying in %.2fs',
                endpoint_label, attempt, max_attempts, exc, delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc

# Error code mapping from Feishu OAuth token endpoint
_FEISHU_ERROR_MAP: dict[int, tuple[int, str]] = {
    20002: (500, '飞书应用配置错误，请联系管理员'),
    20003: (400, '授权码已使用或已过期'),
    20004: (400, '授权码已过期，请重新授权'),
    20010: (403, '应用未获得用户授权，请联系管理员'),
}


class FeishuOAuthService:
    """飞书 OAuth2 授权码登录服务。"""

    FEISHU_AUTHORIZE_URL = 'https://accounts.feishu.cn/open-apis/authen/v1/authorize'
    FEISHU_TOKEN_URL = 'https://open.feishu.cn/open-apis/authen/v2/oauth/token'
    FEISHU_USER_INFO_URL = 'https://open.feishu.cn/open-apis/authen/v1/user_info'
    # Required OAuth scope — flash authorize returns 4401 without this in real Feishu env.
    FEISHU_AUTHORIZE_SCOPE = 'contact:user.employee_id:readonly'

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_authorize_url(
        self,
        redis_client: redis_lib.Redis,
        *,
        purpose: str = 'login',
    ) -> dict[str, str]:
        """Generate a Feishu OAuth authorize URL with CSRF state token.

        purpose='login' → state key 'feishu_oauth_state:{state}', redirect_uri=feishu_redirect_uri
        purpose='bind'  → state key 'feishu_oauth_state:bind:{state}', redirect_uri=feishu_bind_redirect_uri
        """
        if purpose not in ('login', 'bind'):
            raise HTTPException(status_code=400, detail='无效的 purpose 参数')

        if purpose == 'bind':
            redirect_uri = self._settings.feishu_bind_redirect_uri
            if not redirect_uri:
                raise HTTPException(status_code=503, detail='绑定服务暂不可用，请联系管理员')
            state_key_prefix = 'feishu_oauth_state:bind:'
        else:
            redirect_uri = self._settings.feishu_redirect_uri
            state_key_prefix = 'feishu_oauth_state:'

        state = secrets.token_urlsafe(32)
        redis_client.setex(f'{state_key_prefix}{state}', 300, '1')

        params = urllib.parse.urlencode({
            'client_id': self._settings.feishu_app_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': self.FEISHU_AUTHORIZE_SCOPE,
        })
        authorize_url = f'{self.FEISHU_AUTHORIZE_URL}?{params}'
        return {'authorize_url': authorize_url, 'state': state}

    def handle_callback(self, code: str, state: str, redis_client: redis_lib.Redis) -> User:
        """Handle the OAuth callback: validate state, exchange code, find/bind user."""
        self._validate_state(state, redis_client)
        self._check_code_replay(code, redis_client)
        redis_client.setex(f'feishu_oauth_code:{code}', 600, '1')

        token_data = self._exchange_code_for_token(code)
        # v2 /oauth/token returns access_token at top-level (standard OAuth 2.0).
        # Fallback to data.access_token for v1-style compatibility.
        access_token = (
            token_data.get('access_token')
            or token_data.get('data', {}).get('access_token')
            or ''
        )
        if not access_token:
            logger.error('Feishu token exchange returned no access_token: %s', token_data)
            raise HTTPException(status_code=502, detail='飞书认证服务异常，请稍后重试')

        user_info = self._get_user_info(access_token)
        open_id = user_info.get('open_id', '')
        employee_no = user_info.get('employee_no', '')

        return self._find_or_bind_user(open_id, employee_no)

    def handle_bind_callback(
        self,
        code: str,
        state: str,
        user: User,
        redis_client: redis_lib.Redis,
    ) -> User:
        """Handle the bind callback: validate bind-prefix state, exchange code, verify employee_no, bind open_id to the current user.

        Raises:
            HTTPException 400 — invalid state / user without employee / employee_no mismatch / code already used
            HTTPException 409 — open_id already bound to another user
            HTTPException 502/503 — Feishu or Redis unreachable
        """
        self._validate_state_bind(state, redis_client)
        self._check_code_replay(code, redis_client)
        redis_client.setex(f'feishu_oauth_code:{code}', 600, '1')

        token_data = self._exchange_code_for_token_for_bind(code)
        access_token = (
            token_data.get('access_token')
            or token_data.get('data', {}).get('access_token')
            or ''
        )
        if not access_token:
            logger.error('Feishu bind token exchange returned no access_token: %s', token_data)
            raise HTTPException(status_code=502, detail='飞书认证服务异常，请稍后重试')

        user_info = self._get_user_info(access_token)
        open_id = user_info.get('open_id', '')
        feishu_employee_no = user_info.get('employee_no', '')

        # D-07: user must have Employee bound
        if user.employee_id is None or user.employee is None:
            raise HTTPException(status_code=400, detail='当前账号未关联员工信息，请联系管理员')

        # D-06 AMENDMENT (D-18): Feishu employee_no check is OPTIONAL — only enforced when
        # Feishu actually returns a non-empty employee_no. Feishu's /authen/v1/user_info omits
        # this field when the Feishu admin hasn't filled it on the user's profile, so requiring
        # a match would block most real-world binds. When Feishu does return it, we still verify
        # consistency (leading-zero tolerant).
        if feishu_employee_no:
            current_emp_no = user.employee.employee_no or ''
            emp_map: dict[str, str] = {current_emp_no: user.employee_id}
            stripped = current_emp_no.lstrip('0') or '0'
            if stripped not in emp_map:
                emp_map[stripped] = user.employee_id
            if FeishuService._lookup_employee(emp_map, feishu_employee_no) is None:
                raise HTTPException(
                    status_code=400,
                    detail='飞书工号与当前账号绑定的工号不一致，无法绑定',
                )

        # D-05: open_id must not be occupied by another user
        if not open_id:
            raise HTTPException(status_code=502, detail='获取飞书用户信息失败')
        other = self.db.scalar(
            select(User).where(
                User.feishu_open_id == open_id,
                User.id != user.id,
            )
        )
        if other is not None:
            raise HTTPException(
                status_code=409,
                detail='该飞书账号已被其他系统账号绑定，请先在原账号解绑',
            )

        user.feishu_open_id = open_id
        self.db.flush()
        return user

    def handle_unbind(self, user: User) -> User:
        """Clear user.feishu_open_id; idempotent when already None. Does not touch token_version (D-10)."""
        if user.feishu_open_id is not None:
            user.feishu_open_id = None
            self.db.flush()
        return user

    def require_redis(self) -> redis_lib.Redis:
        """Obtain a Redis client; raise 503 if unavailable."""
        try:
            client = redis_lib.from_url(self._settings.redis_url)
            client.ping()
            return client
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail='认证服务暂不可用，请稍后重试',
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_state(self, state: str, redis_client: redis_lib.Redis) -> None:
        """Validate CSRF state token from Redis; consume it immediately."""
        key = f'feishu_oauth_state:{state}'
        val = redis_client.get(key)
        if val is None:
            raise HTTPException(status_code=400, detail='无效的 state 参数，请重新发起授权')
        redis_client.delete(key)

    def _validate_state_bind(self, state: str, redis_client: redis_lib.Redis) -> None:
        """Validate CSRF state for bind flow (feishu_oauth_state:bind: prefix); consume on use."""
        key = f'feishu_oauth_state:bind:{state}'
        val = redis_client.get(key)
        if val is None:
            raise HTTPException(status_code=400, detail='无效的 state 参数，请重新发起授权')
        redis_client.delete(key)

    def _check_code_replay(self, code: str, redis_client: redis_lib.Redis) -> None:
        """Reject reused authorization codes."""
        key = f'feishu_oauth_code:{code}'
        val = redis_client.get(key)
        if val is not None:
            raise HTTPException(status_code=400, detail='授权码已使用')

    def _exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for user access token via Feishu API."""
        try:
            resp = _call_feishu_with_retry(
                lambda: httpx.post(
                    self.FEISHU_TOKEN_URL,
                    json={
                        'grant_type': 'authorization_code',
                        'client_id': self._settings.feishu_app_id,
                        'client_secret': self._settings.feishu_app_secret,
                        'code': code,
                        'redirect_uri': self._settings.feishu_redirect_uri,
                    },
                    timeout=10,
                ),
                endpoint_label='token',
            )
        except _TRANSIENT_HTTPX_ERRORS as exc:
            logger.warning('Feishu token endpoint unreachable after retries: %s', exc)
            raise HTTPException(status_code=502, detail='无法连接飞书认证服务，请稍后重试') from exc

        data = resp.json()
        error_code = data.get('code', 0)

        if error_code != 0:
            status_code, message = _FEISHU_ERROR_MAP.get(error_code, (502, '飞书认证服务异常'))
            logger.warning('Feishu token exchange failed: code=%s msg=%s', error_code, data.get('msg'))
            raise HTTPException(status_code=status_code, detail=message)

        return data

    def _exchange_code_for_token_for_bind(self, code: str) -> dict:
        """Bind-flow token exchange — uses feishu_bind_redirect_uri instead of feishu_redirect_uri.

        Kept as a separate method (instead of parameterizing the existing login path)
        to preserve Phase 26 login contract untouched.
        """
        try:
            resp = _call_feishu_with_retry(
                lambda: httpx.post(
                    self.FEISHU_TOKEN_URL,
                    json={
                        'grant_type': 'authorization_code',
                        'client_id': self._settings.feishu_app_id,
                        'client_secret': self._settings.feishu_app_secret,
                        'code': code,
                        'redirect_uri': self._settings.feishu_bind_redirect_uri,
                    },
                    timeout=10,
                ),
                endpoint_label='token_bind',
            )
        except _TRANSIENT_HTTPX_ERRORS as exc:
            logger.warning('Feishu token endpoint unreachable after retries (bind): %s', exc)
            raise HTTPException(status_code=502, detail='无法连接飞书认证服务，请稍后重试') from exc

        data = resp.json()
        error_code = data.get('code', 0)
        if error_code != 0:
            status_code, message = _FEISHU_ERROR_MAP.get(error_code, (502, '飞书认证服务异常'))
            logger.warning('Feishu bind token exchange failed: code=%s msg=%s', error_code, data.get('msg'))
            raise HTTPException(status_code=status_code, detail=message)
        return data

    def _get_user_info(self, access_token: str) -> dict:
        """Fetch user info from Feishu using user access token."""
        try:
            resp = _call_feishu_with_retry(
                lambda: httpx.get(
                    self.FEISHU_USER_INFO_URL,
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10,
                ),
                endpoint_label='user_info',
            )
        except _TRANSIENT_HTTPX_ERRORS as exc:
            logger.warning('Feishu user_info endpoint unreachable after retries: %s', exc)
            raise HTTPException(status_code=502, detail='无法获取飞书用户信息，请稍后重试') from exc

        data = resp.json()
        if data.get('code', 0) != 0:
            logger.warning('Feishu user_info failed: code=%s msg=%s', data.get('code'), data.get('msg'))
            raise HTTPException(status_code=502, detail='获取飞书用户信息失败')
        return data.get('data', {})

    def _find_or_bind_user(self, open_id: str, employee_no: str) -> User:
        """Find user by feishu_open_id (fast path) or match via employee_no (slow path)."""
        # Fast path: user already bound
        existing = self.db.scalar(
            select(User).where(User.feishu_open_id == open_id)
        )
        if existing is not None:
            return existing

        # Slow path: match by employee_no
        emp_rows = self.db.execute(select(Employee.employee_no, Employee.id)).all()
        emp_map: dict[str, str] = {}
        for emp_no, emp_id in emp_rows:
            emp_map[emp_no] = emp_id
            stripped = emp_no.lstrip('0') or '0'
            if stripped not in emp_map:
                emp_map[stripped] = emp_id

        employee_id = FeishuService._lookup_employee(emp_map, employee_no)
        if employee_id is None:
            raise HTTPException(status_code=400, detail='工号未匹配，请联系管理员开通')

        user = self.db.scalar(
            select(User).where(User.employee_id == employee_id)
        )
        if user is None:
            raise HTTPException(status_code=400, detail='工号未匹配，请联系管理员开通')

        user.feishu_open_id = open_id
        self.db.flush()
        return user
