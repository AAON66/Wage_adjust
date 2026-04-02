from __future__ import annotations

from datetime import date

import pytest

from backend.app.engines.eligibility_engine import (
    EligibilityEngine,
    EligibilityResult,
    EligibilityThresholds,
    RuleResult,
)

REF_DATE = date(2026, 1, 15)


@pytest.fixture
def engine() -> EligibilityEngine:
    return EligibilityEngine()


# --- Tenure rule ---

def test_tenure_eligible(engine: EligibilityEngine) -> None:
    result = engine.check_tenure(date(2025, 5, 15), REF_DATE)
    assert result.status == 'eligible'
    assert result.rule_code == 'TENURE'


def test_tenure_ineligible(engine: EligibilityEngine) -> None:
    result = engine.check_tenure(date(2025, 10, 15), REF_DATE)
    assert result.status == 'ineligible'


def test_tenure_data_missing(engine: EligibilityEngine) -> None:
    result = engine.check_tenure(None, REF_DATE)
    assert result.status == 'data_missing'


def test_tenure_boundary_exact_6_months(engine: EligibilityEngine) -> None:
    # 2025-07-15 to 2026-01-15 = exactly 6 months => eligible
    result = engine.check_tenure(date(2025, 7, 15), REF_DATE)
    assert result.status == 'eligible'


def test_tenure_boundary_5_months(engine: EligibilityEngine) -> None:
    # 2025-08-15 to 2026-01-15 = 5 months => ineligible
    result = engine.check_tenure(date(2025, 8, 15), REF_DATE)
    assert result.status == 'ineligible'


# --- Adjustment interval rule ---

def test_adjustment_interval_eligible(engine: EligibilityEngine) -> None:
    result = engine.check_adjustment_interval(date(2025, 5, 15), REF_DATE)
    assert result.status == 'eligible'
    assert result.rule_code == 'ADJUSTMENT_INTERVAL'


def test_adjustment_interval_ineligible(engine: EligibilityEngine) -> None:
    result = engine.check_adjustment_interval(date(2025, 11, 15), REF_DATE)
    assert result.status == 'ineligible'


def test_adjustment_no_history_no_fallback(engine: EligibilityEngine) -> None:
    result = engine.check_adjustment_interval(None, REF_DATE)
    assert result.status == 'data_missing'


def test_adjustment_boundary_exact_6_months(engine: EligibilityEngine) -> None:
    result = engine.check_adjustment_interval(date(2025, 7, 15), REF_DATE)
    assert result.status == 'eligible'


# --- Performance rule ---

def test_performance_eligible_a(engine: EligibilityEngine) -> None:
    result = engine.check_performance('A')
    assert result.status == 'eligible'
    assert result.rule_code == 'PERFORMANCE'


def test_performance_eligible_b(engine: EligibilityEngine) -> None:
    result = engine.check_performance('B')
    assert result.status == 'eligible'


def test_performance_ineligible_c(engine: EligibilityEngine) -> None:
    result = engine.check_performance('C')
    assert result.status == 'ineligible'


def test_performance_ineligible_d(engine: EligibilityEngine) -> None:
    result = engine.check_performance('D')
    assert result.status == 'ineligible'


def test_performance_ineligible_e(engine: EligibilityEngine) -> None:
    result = engine.check_performance('E')
    assert result.status == 'ineligible'


def test_performance_data_missing(engine: EligibilityEngine) -> None:
    result = engine.check_performance(None)
    assert result.status == 'data_missing'


def test_performance_unrecognized_grade(engine: EligibilityEngine) -> None:
    result = engine.check_performance('X')
    assert result.status == 'data_missing'


# --- Leave rule ---

def test_leave_eligible(engine: EligibilityEngine) -> None:
    result = engine.check_leave(20.0)
    assert result.status == 'eligible'
    assert result.rule_code == 'LEAVE'


def test_leave_ineligible(engine: EligibilityEngine) -> None:
    result = engine.check_leave(35.0)
    assert result.status == 'ineligible'


def test_leave_data_missing(engine: EligibilityEngine) -> None:
    result = engine.check_leave(None)
    assert result.status == 'data_missing'


def test_leave_boundary_exact_30(engine: EligibilityEngine) -> None:
    result = engine.check_leave(30.0)
    assert result.status == 'eligible'


def test_leave_boundary_30_point_1(engine: EligibilityEngine) -> None:
    result = engine.check_leave(30.1)
    assert result.status == 'ineligible'


# --- Overall evaluation ---

def test_overall_all_eligible(engine: EligibilityEngine) -> None:
    result = engine.evaluate(
        hire_date=date(2025, 1, 1),
        last_adjustment_date=date(2025, 1, 1),
        performance_grade='A',
        non_statutory_leave_days=10.0,
        reference_date=REF_DATE,
    )
    assert result.overall_status == 'eligible'
    assert len(result.rules) == 4


def test_overall_one_ineligible(engine: EligibilityEngine) -> None:
    result = engine.evaluate(
        hire_date=date(2025, 1, 1),
        last_adjustment_date=date(2025, 1, 1),
        performance_grade='D',
        non_statutory_leave_days=10.0,
        reference_date=REF_DATE,
    )
    assert result.overall_status == 'ineligible'


def test_overall_some_data_missing_none_ineligible(engine: EligibilityEngine) -> None:
    result = engine.evaluate(
        hire_date=date(2025, 1, 1),
        last_adjustment_date=None,
        performance_grade='A',
        non_statutory_leave_days=10.0,
        reference_date=REF_DATE,
    )
    assert result.overall_status == 'pending'


def test_overall_ineligible_trumps_data_missing(engine: EligibilityEngine) -> None:
    result = engine.evaluate(
        hire_date=None,
        last_adjustment_date=date(2025, 12, 1),
        performance_grade='E',
        non_statutory_leave_days=None,
        reference_date=REF_DATE,
    )
    assert result.overall_status == 'ineligible'


# --- Custom thresholds ---

def test_custom_thresholds(engine: EligibilityEngine) -> None:
    custom_engine = EligibilityEngine(EligibilityThresholds(min_tenure_months=12))
    result = custom_engine.check_tenure(date(2025, 5, 15), REF_DATE)
    # 8 months tenure with 12 month threshold => ineligible
    assert result.status == 'ineligible'


# --- Rule codes ---

def test_rule_codes(engine: EligibilityEngine) -> None:
    result = engine.evaluate(
        hire_date=date(2025, 1, 1),
        last_adjustment_date=date(2025, 1, 1),
        performance_grade='A',
        non_statutory_leave_days=10.0,
        reference_date=REF_DATE,
    )
    codes = [r.rule_code for r in result.rules]
    assert 'TENURE' in codes
    assert 'ADJUSTMENT_INTERVAL' in codes
    assert 'PERFORMANCE' in codes
    assert 'LEAVE' in codes


# --- Detail contains Chinese ---

def test_detail_contains_chinese(engine: EligibilityEngine) -> None:
    result = engine.evaluate(
        hire_date=date(2025, 1, 1),
        last_adjustment_date=date(2025, 1, 1),
        performance_grade='A',
        non_statutory_leave_days=10.0,
        reference_date=REF_DATE,
    )
    for rule in result.rules:
        assert rule.detail, f'Rule {rule.rule_code} has empty detail'
        # Check at least one Chinese character exists
        assert any('\u4e00' <= c <= '\u9fff' for c in rule.detail), (
            f'Rule {rule.rule_code} detail lacks Chinese: {rule.detail}'
        )
