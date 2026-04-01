from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import Settings, get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenValidationError(Exception):
    """Raised when a JWT cannot be decoded or does not match the expected type."""



def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)



def _build_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    settings: Settings,
    role: str | None = None,
    token_version: int | None = None,
) -> str:
    expire_at = datetime.now(UTC) + expires_delta
    payload: dict[str, object] = {
        "sub": subject,
        "type": token_type,
        "exp": expire_at,
    }
    if role is not None:
        payload["role"] = role
    if token_version is not None:
        payload["tv"] = token_version
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)



def create_access_token(subject: str, role: str | None = None, settings: Settings | None = None, token_version: int | None = None) -> str:
    resolved_settings = settings or get_settings()
    return _build_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=resolved_settings.jwt_access_token_expire_minutes),
        settings=resolved_settings,
        role=role,
        token_version=token_version,
    )



def create_refresh_token(subject: str, role: str | None = None, settings: Settings | None = None, token_version: int | None = None) -> str:
    resolved_settings = settings or get_settings()
    return _build_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=resolved_settings.jwt_refresh_token_expire_days),
        settings=resolved_settings,
        role=role,
        token_version=token_version,
    )



def decode_token(token: str, settings: Settings | None = None, expected_type: str | None = None) -> dict[str, object]:
    resolved_settings = settings or get_settings()
    try:
        payload = jwt.decode(token, resolved_settings.jwt_secret_key, algorithms=[resolved_settings.jwt_algorithm])
    except JWTError as exc:
        raise TokenValidationError("Invalid token.") from exc

    token_type = payload.get("type")
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise TokenValidationError("Token subject is missing.")
    if expected_type and token_type != expected_type:
        raise TokenValidationError(f"Expected a {expected_type} token.")
    return payload
