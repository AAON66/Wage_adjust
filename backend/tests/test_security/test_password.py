from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-08: password complexity validator not yet implemented")
def test_password_with_mixed_case_and_digit_passes() -> None:
    """'SecurePass1' passes the complexity validator."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-08: password complexity validator not yet implemented")
def test_password_with_mixed_case_and_symbol_passes() -> None:
    """'SecurePass!' passes the complexity validator."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-08: password complexity validator not yet implemented")
def test_all_lowercase_digits_rejected() -> None:
    """'password1' is rejected — no uppercase letter."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-08: password complexity validator not yet implemented")
def test_no_digit_or_symbol_rejected() -> None:
    """'SecurePassword' is rejected — no digit or symbol."""
    raise NotImplementedError
