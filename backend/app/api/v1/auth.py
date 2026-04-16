from __future__ import annotations

import logging

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from backend.app.dependencies import get_app_settings, get_current_user, get_db
from backend.app.models.user import User
from backend.app.schemas.user import (
    AuthResponse,
    FeishuCallbackRequest,
    PasswordChangeRequest,
    SelfBindPreview,
    SelfBindRequest,
    TokenPair,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserRead,
)
from backend.app.services.feishu_oauth_service import FeishuOAuthService
from backend.app.services.identity_binding_service import IdentityBindingService

router = APIRouter(prefix='/auth', tags=['auth'])

logger = logging.getLogger(__name__)

_FAILED_ATTEMPT_LIMIT = 10
_FAILED_ATTEMPT_WINDOW_SECONDS = 900  # 15 minutes


def _get_redis_client(settings) -> redis_lib.Redis | None:
    """Return a Redis client, or None if Redis is unavailable."""
    try:
        client = redis_lib.from_url(settings.redis_url)
        client.ping()
        return client
    except Exception:
        return None


def _check_and_increment_failed_login(ip: str, settings) -> None:
    """Check if IP is rate-limited; raise HTTP 429 if so. Increment counter on call."""
    redis_client = _get_redis_client(settings)
    if redis_client is None:
        return  # Redis unavailable — skip rate limiting (graceful degradation in dev)
    key = f'login_failed:{ip}'
    count = redis_client.get(key)
    if count is not None and int(count) >= _FAILED_ATTEMPT_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Too many failed login attempts. Try again in 15 minutes.',
        )
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.execute()
    # Only set expiry if the key has no TTL yet (compatible with Redis < 7.0)
    if redis_client.ttl(key) < 0:
        redis_client.expire(key, _FAILED_ATTEMPT_WINDOW_SECONDS)


def _reset_failed_login(ip: str, settings) -> None:
    """Clear the failed-attempt counter for an IP after successful login."""
    redis_client = _get_redis_client(settings)
    if redis_client is None:
        return
    redis_client.delete(f'login_failed:{ip}')


def _build_auth_response(user: User, settings) -> AuthResponse:
    return AuthResponse(
        user=UserRead.model_validate(user),
        tokens=TokenPair(
            access_token=create_access_token(user.id, role=user.role, settings=settings, token_version=user.token_version),
            refresh_token=create_refresh_token(user.id, role=user.role, settings=settings, token_version=user.token_version),
        ),
    )


@router.post('/register', response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> AuthResponse:
    if not settings.allow_self_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Self registration is disabled.')

    existing_user = db.scalar(select(User).where(User.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered.')

    identity_service = IdentityBindingService(db)
    try:
        normalized_id_card_no = identity_service.ensure_user_id_card_available(payload.id_card_no)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        id_card_no=normalized_id_card_no,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    try:
        identity_service.auto_bind_user_and_employee(user=user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return _build_auth_response(user, settings)


@router.post('/login', response_model=TokenPair)
def login_user(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> TokenPair:
    ip = request.client.host if request.client else '0.0.0.0'
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        _check_and_increment_failed_login(ip, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password.')
    _reset_failed_login(ip, settings)
    return TokenPair(
        access_token=create_access_token(user.id, role=user.role, settings=settings, token_version=user.token_version),
        refresh_token=create_refresh_token(user.id, role=user.role, settings=settings, token_version=user.token_version),
    )


@router.post('/refresh', response_model=TokenPair)
def refresh_tokens(
    payload: TokenRefreshRequest,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> TokenPair:
    try:
        token_payload = decode_token(payload.refresh_token, settings=settings, expected_type='refresh')
    except TokenValidationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token.') from exc

    user = db.get(User, token_payload['sub'])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token.')

    # Reject refresh tokens issued before a token_version change (e.g. after unbind)
    tv_claim = token_payload.get('tv')
    if tv_claim is not None and int(tv_claim) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token.')

    return TokenPair(
        access_token=create_access_token(user.id, role=user.role, settings=settings, token_version=user.token_version),
        refresh_token=create_refresh_token(user.id, role=user.role, settings=settings, token_version=user.token_version),
    )


@router.get('/me', response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.post('/change-password', response_model=dict[str, str])
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='当前密码输入错误，请重新输入。')
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='新密码不能与当前密码相同，请设置一个不同的密码。')

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()
    return {'message': '密码修改成功。'}


@router.get('/self-bind/preview', response_model=SelfBindPreview)
def self_bind_preview(
    id_card_no: str = Query(min_length=1, max_length=32),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SelfBindPreview:
    identity_service = IdentityBindingService(db)
    original_id_card_no = current_user.id_card_no

    try:
        normalized = identity_service.normalize_id_card_no(id_card_no)
        current_user.id_card_no = normalized
        employee = identity_service.search_employee_for_user_by_identity(user=current_user)
    finally:
        current_user.id_card_no = original_id_card_no

    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='未找到匹配的员工信息')

    # Check if employee is already bound to another user
    bound_user = db.scalar(
        select(User).where(User.employee_id == employee.id, User.id != current_user.id)
    )
    if bound_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'该员工已绑定到账号 {bound_user.email}，请联系管理员处理',
        )

    return SelfBindPreview(
        employee_id=employee.id,
        employee_no=employee.employee_no,
        name=employee.name,
        department=employee.department,
    )


@router.post('/self-bind', response_model=UserRead)
def self_bind_confirm(
    payload: SelfBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if current_user.employee_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='当前账号已绑定员工信息')

    identity_service = IdentityBindingService(db)
    normalized = identity_service.normalize_id_card_no(payload.id_card_no)
    current_user.id_card_no = normalized

    try:
        bound = identity_service.auto_bind_user_and_employee(user=current_user)
    except ValueError as exc:
        message = str(exc)
        # Enrich conflict message with bound user email per D-05
        if 'already bound to another account' in message:
            employee = identity_service.search_employee_for_user_by_identity(user=current_user)
            if employee is not None:
                bound_user = db.scalar(
                    select(User).where(User.employee_id == employee.id, User.id != current_user.id)
                )
                if bound_user is not None:
                    message = f'该员工已绑定到账号 {bound_user.email}，请联系管理员处理'
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    if not bound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='未找到匹配的员工信息')

    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)


@router.get('/feishu/authorize')
def feishu_authorize(
    db: Session = Depends(get_db),
    settings = Depends(get_app_settings),
) -> dict[str, str]:
    """生成飞书 OAuth 授权 URL，返回 authorize_url 和 state。"""
    service = FeishuOAuthService(db, settings=settings)
    redis_client = service.require_redis()
    return service.generate_authorize_url(redis_client)


@router.post('/feishu/callback', response_model=AuthResponse)
def feishu_callback(
    payload: FeishuCallbackRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings = Depends(get_app_settings),
) -> AuthResponse:
    """处理飞书 OAuth 回调，验证 state 和 code，返回 JWT token pair。"""
    service = FeishuOAuthService(db, settings=settings)
    redis_client = service.require_redis()

    user = service.handle_callback(payload.code, payload.state, redis_client)

    # Clear any failed login attempts for this IP on successful OAuth login
    client_ip = request.client.host if request.client else 'unknown'
    _reset_failed_login(client_ip, settings)

    return _build_auth_response(user, settings)
