from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-03: EncryptedString TypeDecorator not yet implemented")
def test_encrypt_decrypt_round_trip() -> None:
    """encrypt_national_id followed by decrypt_national_id returns original plaintext."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-03: EncryptedString TypeDecorator not yet implemented")
def test_encrypt_produces_different_ciphertext_each_call() -> None:
    """Two calls with the same plaintext produce different ciphertext (fresh nonce per call)."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-03: mask helper not yet implemented")
def test_mask_national_id_shows_first_6_and_last_4() -> None:
    """mask_national_id('330104199001010123') == '330104********0123'."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-03: EncryptedString TypeDecorator not yet implemented")
def test_encrypted_string_typedecorator_stores_ciphertext_in_db() -> None:
    """Employee.id_card_no round-trips through SQLite without data loss."""
    raise NotImplementedError
