from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-01: startup guard not yet implemented")
def test_production_refuses_change_me_jwt_secret() -> None:
    """When environment='production' and jwt_secret_key='change_me', app must raise RuntimeError on startup."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-01: startup guard not yet implemented")
def test_production_refuses_default_public_api_key() -> None:
    """When environment='production' and public_api_key='your_public_api_key', app must raise RuntimeError on startup."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-01: startup guard not yet implemented")
def test_development_allows_placeholder_secrets() -> None:
    """When environment='development', placeholder secrets do NOT raise — they log a warning only."""
    raise NotImplementedError
