from __future__ import annotations

import base64
import os

import pytest

from backend.app.core.encryption import (
    EncryptedString,
    decrypt_national_id,
    encrypt_national_id,
    mask_national_id,
)


def _make_test_key() -> bytes:
    return os.urandom(32)


def test_encrypt_decrypt_round_trip() -> None:
    key = _make_test_key()
    plaintext = '330104199001010123'
    ciphertext = encrypt_national_id(plaintext, key)
    assert decrypt_national_id(ciphertext, key) == plaintext


def test_encrypt_produces_different_ciphertext_each_call() -> None:
    key = _make_test_key()
    plaintext = '330104199001010123'
    ct1 = encrypt_national_id(plaintext, key)
    ct2 = encrypt_national_id(plaintext, key)
    assert ct1 != ct2


def test_mask_national_id_shows_first_6_and_last_4() -> None:
    assert mask_national_id('330104199001010123') == '330104********0123'


def test_mask_national_id_short_input() -> None:
    assert mask_national_id('12345') == '****'


def test_encrypted_string_typedecorator_passthrough_when_no_key(monkeypatch) -> None:
    """When encryption key is empty, values pass through unmodified."""
    import backend.app.core.encryption as enc_module
    monkeypatch.setattr(enc_module, '_KEY_CACHE', None)
    from unittest.mock import patch
    with patch('backend.app.core.encryption.get_settings') as mock_settings:
        mock_settings.return_value.national_id_encryption_key = ''
        col = EncryptedString()
        result = col.process_bind_param('330104199001010123', None)
        assert result == '330104199001010123'


def test_encrypted_string_db_round_trip() -> None:
    """DB round-trip: raw stored value is NOT plaintext; ORM read returns original plaintext.

    Uses a real in-memory SQLite DB with an encryption key set, exercising the full
    TypeDecorator path: Python value -> encrypted DB storage -> decrypted Python value.
    """
    import base64
    import os
    from unittest.mock import patch

    from sqlalchemy import Column, Integer, MetaData, Table, create_engine, text

    # Generate a real 32-byte AES key
    raw_key = base64.b64encode(os.urandom(32)).decode()

    import backend.app.core.encryption as enc_module

    # Patch settings to return the test key and reset key cache
    with patch('backend.app.core.encryption.get_settings') as mock_settings:
        mock_settings.return_value.national_id_encryption_key = raw_key
        # Reset module-level key cache so the patched settings take effect
        original_cache = enc_module._KEY_CACHE
        enc_module._KEY_CACHE = None
        try:
            engine = create_engine('sqlite+pysqlite:///:memory:')
            metadata = MetaData()
            test_table = Table(
                'test_employees',
                metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('id_card_no', EncryptedString(256), nullable=True),
            )
            metadata.create_all(bind=engine)

            plaintext = '330104199001010123'

            # Insert via Core INSERT (triggers process_bind_param -- encrypts)
            with engine.connect() as conn:
                result = conn.execute(
                    test_table.insert().values(id_card_no=plaintext)
                )
                conn.commit()
                inserted_id = result.inserted_primary_key[0]

            # Read raw value via SQL -- must NOT be the original plaintext
            with engine.connect() as conn:
                row = conn.execute(
                    text('SELECT id_card_no FROM test_employees WHERE id = :id'),
                    {'id': inserted_id},
                ).fetchone()
                raw_stored = row[0]
            assert raw_stored != plaintext, (
                f'Expected encrypted ciphertext in DB, but got plaintext: {raw_stored!r}'
            )

            # Read via ORM select -- must return the original plaintext (transparent decrypt)
            with engine.connect() as conn:
                row = conn.execute(
                    test_table.select().where(test_table.c.id == inserted_id)
                ).fetchone()
                assert row is not None
                assert row.id_card_no == plaintext, (
                    f'Expected ORM read to return plaintext, got: {row.id_card_no!r}'
                )
        finally:
            enc_module._KEY_CACHE = original_cache
