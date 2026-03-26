from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-02: login rate limiter not yet implemented")
def test_eleven_failed_logins_return_429() -> None:
    """11 failed POST /api/v1/auth/login requests from same IP within 15 min returns HTTP 429."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-02: login rate limiter not yet implemented")
def test_successful_login_does_not_count_against_limit() -> None:
    """A successful login does not increment the failed-attempt counter."""
    raise NotImplementedError
