from __future__ import annotations

from collections.abc import Callable, Generator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import get_db_session
from backend.app.core.security import TokenValidationError, decode_token, oauth2_scheme
from backend.app.models.department import Department
from backend.app.models.user import User


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    yield from get_db_session()



def get_app_settings() -> Settings:
    """FastAPI dependency that returns cached application settings."""
    return get_settings()



def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token, settings=settings, expected_type="access")
    except TokenValidationError as exc:
        raise credentials_error from exc

    user = db.scalar(select(User).options(selectinload(User.departments)).where(User.id == payload["sub"]))
    if user is None:
        raise credentials_error
    return user



def get_public_api_key(
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    settings: Settings = Depends(get_app_settings),
) -> str:
    """Deprecated: use require_public_api_key instead (multi-key DB validation)."""
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='X-API-Key header is required.')
    if x_api_key != settings.public_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid public API key.')
    return x_api_key


def require_public_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    db: Session = Depends(get_db),
):
    """Validate X-API-Key header with multi-key DB lookup (per D-01).

    Revoked or expired keys return 401 immediately (per API-04).
    Returns the ApiKey ORM model on success.
    """
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='X-API-Key header is required.')
    from backend.app.services.api_key_service import ApiKeyService
    service = ApiKeyService(db)
    client_ip = request.client.host if request.client else None
    api_key = service.validate_key(x_api_key, client_ip=client_ip)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid, revoked, or expired API key.')
    return api_key



def require_roles(*roles: str) -> Callable[[User], User]:
    allowed_roles = set(roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return current_user

    return dependency
