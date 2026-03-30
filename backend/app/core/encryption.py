from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AES-256-GCM passphrase-based helpers (used by feishu_config encryption)
# ---------------------------------------------------------------------------


def _derive_key(passphrase: str) -> bytes:
    """Derive a 256-bit key from a passphrase using SHA-256."""
    return hashlib.sha256(passphrase.encode('utf-8')).digest()


def encrypt_value(plaintext: str, key: str) -> str:
    """Encrypt a string value using AES-256-GCM and return base64-encoded ciphertext.

    Format: base64(nonce + ciphertext + tag)
    """
    key_bytes = _derive_key(key)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key_bytes)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return base64.b64encode(nonce + ciphertext).decode('ascii')


def decrypt_value(token: str, key: str) -> str:
    """Decrypt a base64-encoded AES-256-GCM token back to plaintext."""
    key_bytes = _derive_key(key)
    raw = base64.b64decode(token)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key_bytes)
    return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')


# ---------------------------------------------------------------------------
# National ID encryption (raw-key based, used by EncryptedString TypeDecorator)
# ---------------------------------------------------------------------------

_KEY_CACHE: bytes | None = None


def _get_encryption_key() -> bytes | None:
    """Return the 32-byte AES key decoded from settings. Returns None if key is empty."""
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE
    settings = get_settings()
    raw_key = settings.national_id_encryption_key.strip()
    if not raw_key:
        logger.warning(
            'NATIONAL_ID_ENCRYPTION_KEY is not set. '
            'National ID values will be stored as plaintext. '
            'Set a 32-byte base64-encoded key in .env before production deployment.'
        )
        return None
    decoded = base64.b64decode(raw_key)
    if len(decoded) != 32:
        raise ValueError(
            f'NATIONAL_ID_ENCRYPTION_KEY must decode to exactly 32 bytes (got {len(decoded)}). '
            'Generate with: python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"'
        )
    _KEY_CACHE = decoded
    return _KEY_CACHE


def encrypt_national_id(plaintext: str, key: bytes) -> str:
    """Encrypt a national ID string using AES-256-GCM."""
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return base64.b64encode(nonce + ct).decode('ascii')


def decrypt_national_id(token: str, key: bytes) -> str:
    """Decrypt an AES-256-GCM ciphertext token."""
    try:
        raw = base64.b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode('utf-8')
    except Exception as exc:
        raise ValueError('Failed to decrypt national ID value.') from exc


def mask_national_id(plaintext: str) -> str:
    """Return a masked version of a national ID."""
    if len(plaintext) < 10:
        return '****'
    return plaintext[:6] + '********' + plaintext[-4:]


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator that transparently encrypts/decrypts string values using AES-256-GCM."""

    impl = String(256)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        key = _get_encryption_key()
        if key is None:
            return value
        return encrypt_national_id(value, key)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        key = _get_encryption_key()
        if key is None:
            return value
        try:
            return decrypt_national_id(value, key)
        except ValueError:
            logger.error('Failed to decrypt national ID -- returning None to prevent data exposure.')
            return None
