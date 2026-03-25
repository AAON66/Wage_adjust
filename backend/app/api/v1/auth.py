from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
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
    PasswordChangeRequest,
    TokenPair,
    TokenRefreshRequest,
    UserCreate,
    UserLogin,
    UserRead,
)
from backend.app.services.identity_binding_service import IdentityBindingService

router = APIRouter(prefix='/auth', tags=['auth'])


def _build_auth_response(user: User, settings) -> AuthResponse:
    return AuthResponse(
        user=UserRead.model_validate(user),
        tokens=TokenPair(
            access_token=create_access_token(user.id, role=user.role, settings=settings),
            refresh_token=create_refresh_token(user.id, role=user.role, settings=settings),
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
    payload: UserLogin,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password.')

    return TokenPair(
        access_token=create_access_token(user.id, role=user.role, settings=settings),
        refresh_token=create_refresh_token(user.id, role=user.role, settings=settings),
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

    return TokenPair(
        access_token=create_access_token(user.id, role=user.role, settings=settings),
        refresh_token=create_refresh_token(user.id, role=user.role, settings=settings),
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Current password is incorrect.')
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='New password must be different from the current password.')

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()
    return {'message': 'Password updated successfully.'}
