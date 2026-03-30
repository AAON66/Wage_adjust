from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.api_key import ApiKey


class ApiKeyService:
    """API Key CRUD + SHA-256 validation + expiry check (per D-01, D-02, D-04)."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_key(
        self,
        *,
        name: str,
        rate_limit: int = 1000,
        expires_at: datetime | None = None,
        created_by: str,
    ) -> tuple[ApiKey, str]:
        """Create a new API Key. Returns (ORM model, plain key). Plain key shown only once (per D-02)."""
        plain_key = secrets.token_urlsafe(32)  # 43-char base64url string
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:8]

        api_key = ApiKey(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            is_active=True,
            rate_limit=rate_limit,
            expires_at=expires_at,
            created_by=created_by,
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key, plain_key

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate_key(self, plain_key: str, *, client_ip: str | None = None) -> ApiKey | None:
        """Validate a plain key against DB. Updates last_used fields on success.
        Returns None for invalid / revoked / expired keys (per D-01, API-04)."""
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        api_key = self.db.scalar(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        )
        if api_key is None:
            return None

        # Expiry check
        if api_key.expires_at is not None:
            now = datetime.now(timezone.utc)
            expires = api_key.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                return None

        # Update last_used tracking
        api_key.last_used_at = datetime.now(timezone.utc)
        if client_ip:
            api_key.last_used_ip = client_ip
        self.db.commit()
        return api_key

    # ------------------------------------------------------------------
    # Rotate
    # ------------------------------------------------------------------

    def rotate_key(self, key_id: str, *, created_by: str) -> tuple[ApiKey, str]:
        """Rotate: revoke old key, create new key with same config (per D-01)."""
        old_key = self.db.get(ApiKey, key_id)
        if old_key is None:
            raise ValueError(f'API Key not found: {key_id}')
        old_key.is_active = False

        new_key, plain_key = self.create_key(
            name=old_key.name,
            rate_limit=old_key.rate_limit,
            expires_at=old_key.expires_at,
            created_by=created_by,
        )
        return new_key, plain_key

    # ------------------------------------------------------------------
    # Revoke
    # ------------------------------------------------------------------

    def revoke_key(self, key_id: str) -> ApiKey:
        """Revoke key: set is_active = False (per API-04, immediate invalidation)."""
        api_key = self.db.get(ApiKey, key_id)
        if api_key is None:
            raise ValueError(f'API Key not found: {key_id}')
        api_key.is_active = False
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    def list_keys(self) -> list[ApiKey]:
        """List all API Keys (including revoked)."""
        return list(self.db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())))

    def get_key(self, key_id: str) -> ApiKey | None:
        """Get single key by ID."""
        return self.db.get(ApiKey, key_id)
