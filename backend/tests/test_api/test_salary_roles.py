from __future__ import annotations
import pytest


@pytest.mark.xfail(reason="SEC-04: role-aware salary response not yet implemented")
def test_admin_sees_full_salary_figures() -> None:
    """Admin role receives current_salary, recommended_salary, and adjustment fields."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-04: role-aware salary response not yet implemented")
def test_employee_sees_only_adjustment_percentage() -> None:
    """Employee role receives only final_adjustment_ratio — not current_salary or recommended_salary."""
    raise NotImplementedError


@pytest.mark.xfail(reason="SEC-04: role-aware salary response not yet implemented")
def test_manager_sees_only_adjustment_percentage() -> None:
    """Manager role receives only final_adjustment_ratio."""
    raise NotImplementedError
