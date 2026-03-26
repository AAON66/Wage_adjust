from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-07: path traversal guard not yet implemented")
def test_valid_storage_key_resolves_within_base_dir() -> None:
    """A normal UUID-prefixed key resolves to a path inside base_dir."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-07: path traversal guard not yet implemented")
def test_traversal_key_raises_value_error() -> None:
    """'../../etc/passwd' raises ValueError (not resolved outside base_dir)."""
    raise NotImplementedError
