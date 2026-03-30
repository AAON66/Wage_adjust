from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


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
