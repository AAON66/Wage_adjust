from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="DB-03: certification upsert not yet implemented")
def test_importing_same_certification_twice_creates_one_row() -> None:
    """Importing a certification CSV twice results in exactly 1 Certification row, not 2."""
    raise NotImplementedError


@pytest.mark.xfail(reason="DB-03: certification upsert not yet implemented")
def test_certification_import_returns_success_on_second_import() -> None:
    """Second import of the same certification returns status='success' (not error)."""
    raise NotImplementedError
