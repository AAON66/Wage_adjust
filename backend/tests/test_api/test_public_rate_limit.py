from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-05: public API rate limiter not yet wired")
def test_public_api_rate_limit_config_is_enforced() -> None:
    """The public_api_rate_limit config value is applied to /api/v1/public/ routes via slowapi."""
    raise NotImplementedError
