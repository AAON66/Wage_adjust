from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.app.schemas.user import UserCreate


def _make_user(password: str) -> UserCreate:
    return UserCreate(email='test@example.com', password=password, role='employee')


def test_mixed_case_and_digit_passes() -> None:
    user = _make_user('SecurePass1')
    assert user.password == 'SecurePass1'


def test_mixed_case_and_symbol_passes() -> None:
    user = _make_user('SecurePass!')
    assert user.password == 'SecurePass!'


def test_all_lowercase_rejected() -> None:
    with pytest.raises(ValidationError, match='uppercase'):
        _make_user('password1')


def test_no_digit_or_symbol_rejected() -> None:
    with pytest.raises(ValidationError, match='digit or special'):
        _make_user('SecurePassword')


def test_no_lowercase_rejected() -> None:
    with pytest.raises(ValidationError, match='lowercase'):
        _make_user('SECUREPASSWORD1')
