from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Grade rank map for comparison -- uses numeric ranking, NOT string comparison.
# Addresses review concern about fragile string ordering.
GRADE_ORDER: dict[str, int] = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}


@dataclass(frozen=True)
class EligibilityThresholds:
    """Configurable thresholds for eligibility rules (D-04)."""

    min_tenure_months: int = 6
    min_adjustment_interval_months: int = 6
    performance_fail_grades: tuple[str, ...] = ('C', 'D', 'E')
    max_non_statutory_leave_days: float = 30.0


@dataclass(frozen=True)
class RuleResult:
    """Result of a single eligibility rule evaluation.

    rule_code: one of TENURE, ADJUSTMENT_INTERVAL, PERFORMANCE, LEAVE
    status: one of 'eligible', 'ineligible', 'data_missing'
    """

    rule_code: str
    rule_label: str
    status: str
    detail: str


@dataclass
class EligibilityResult:
    """Aggregated eligibility evaluation result.

    Terminology mapping (ELIG-08/D-10):
    - per-rule 'data_missing' maps to overall 'pending' when no rule is 'ineligible'
    - overall_status: 'eligible' | 'ineligible' | 'pending'
    """

    overall_status: str
    rules: list[RuleResult] = field(default_factory=list)


class EligibilityEngine:
    """Pure-computation eligibility engine -- no DB access, no I/O (per D-06).

    Evaluates 4 salary adjustment eligibility rules with three-state results:
    eligible / ineligible / data_missing per rule;
    eligible / ineligible / pending overall.
    """

    def __init__(self, thresholds: EligibilityThresholds | None = None) -> None:
        self.thresholds = thresholds or EligibilityThresholds()

    def _month_diff(self, earlier: date, later: date) -> int:
        """Calculate month difference using year*12+month arithmetic.

        Day-of-month is ignored. Examples:
        - 2026-01-15 to 2026-07-15 = 6 months
        - 2026-01-31 to 2026-07-01 = 6 months
        """
        return (later.year - earlier.year) * 12 + (later.month - earlier.month)

    def check_tenure(self, hire_date: date | None, reference_date: date) -> RuleResult:
        """Check minimum tenure requirement."""
        if hire_date is None:
            return RuleResult(
                rule_code='TENURE',
                rule_label='入职时长',
                status='data_missing',
                detail='入职日期未录入',
            )
        months = self._month_diff(hire_date, reference_date)
        if months >= self.thresholds.min_tenure_months:
            return RuleResult(
                rule_code='TENURE',
                rule_label='入职时长',
                status='eligible',
                detail=f'已入职 {months} 个月',
            )
        return RuleResult(
            rule_code='TENURE',
            rule_label='入职时长',
            status='ineligible',
            detail=f'入职仅 {months} 个月，需满 {self.thresholds.min_tenure_months} 个月',
        )

    def check_adjustment_interval(
        self, last_adjustment_date: date | None, reference_date: date,
    ) -> RuleResult:
        """Check minimum interval since last salary adjustment.

        No-history (None) returns data_missing, NOT ineligible.
        """
        if last_adjustment_date is None:
            return RuleResult(
                rule_code='ADJUSTMENT_INTERVAL',
                rule_label='调薪间隔',
                status='data_missing',
                detail='无调薪记录',
            )
        months = self._month_diff(last_adjustment_date, reference_date)
        if months >= self.thresholds.min_adjustment_interval_months:
            return RuleResult(
                rule_code='ADJUSTMENT_INTERVAL',
                rule_label='调薪间隔',
                status='eligible',
                detail=f'距上次调薪已 {months} 个月',
            )
        return RuleResult(
            rule_code='ADJUSTMENT_INTERVAL',
            rule_label='调薪间隔',
            status='ineligible',
            detail=f'距上次调薪仅 {months} 个月，需满 {self.thresholds.min_adjustment_interval_months} 个月',
        )

    def check_performance(self, grade: str | None) -> RuleResult:
        """Check performance grade against fail threshold.

        Uses GRADE_ORDER rank map for comparison, not string comparison.
        """
        if grade is None:
            return RuleResult(
                rule_code='PERFORMANCE',
                rule_label='绩效等级',
                status='data_missing',
                detail='绩效数据未导入',
            )
        grade_upper = grade.strip().upper()
        if grade_upper not in GRADE_ORDER:
            return RuleResult(
                rule_code='PERFORMANCE',
                rule_label='绩效等级',
                status='data_missing',
                detail=f'绩效等级 "{grade}" 无法识别',
            )
        if grade_upper in self.thresholds.performance_fail_grades:
            return RuleResult(
                rule_code='PERFORMANCE',
                rule_label='绩效等级',
                status='ineligible',
                detail=f'绩效等级为 {grade_upper}，低于合格线',
            )
        return RuleResult(
            rule_code='PERFORMANCE',
            rule_label='绩效等级',
            status='eligible',
            detail=f'绩效等级为 {grade_upper}',
        )

    def check_leave(self, non_statutory_leave_days: float | None) -> RuleResult:
        """Check non-statutory leave days against threshold.

        Exactly at threshold (e.g. 30.0) = eligible; strictly greater = ineligible.
        """
        if non_statutory_leave_days is None:
            return RuleResult(
                rule_code='LEAVE',
                rule_label='非法定假期',
                status='data_missing',
                detail='非法定假期数据未导入',
            )
        if non_statutory_leave_days > self.thresholds.max_non_statutory_leave_days:
            return RuleResult(
                rule_code='LEAVE',
                rule_label='非法定假期',
                status='ineligible',
                detail=f'非法定假期 {non_statutory_leave_days} 天，超过上限 {self.thresholds.max_non_statutory_leave_days} 天',
            )
        return RuleResult(
            rule_code='LEAVE',
            rule_label='非法定假期',
            status='eligible',
            detail=f'非法定假期 {non_statutory_leave_days} 天，符合要求',
        )

    def evaluate(
        self,
        *,
        hire_date: date | None,
        last_adjustment_date: date | None,
        performance_grade: str | None,
        non_statutory_leave_days: float | None,
        reference_date: date,
    ) -> EligibilityResult:
        """Evaluate all 4 eligibility rules and compute overall status.

        Overall status logic (per D-10, addresses ELIG-08):
        - ANY rule 'ineligible' -> overall 'ineligible'
        - ALL rules 'eligible' -> overall 'eligible'
        - otherwise (no ineligible but some data_missing) -> overall 'pending'
        """
        rules = [
            self.check_tenure(hire_date, reference_date),
            self.check_adjustment_interval(last_adjustment_date, reference_date),
            self.check_performance(performance_grade),
            self.check_leave(non_statutory_leave_days),
        ]

        statuses = {r.status for r in rules}

        if 'ineligible' in statuses:
            overall = 'ineligible'
        elif statuses == {'eligible'}:
            overall = 'eligible'
        else:
            overall = 'pending'

        return EligibilityResult(overall_status=overall, rules=rules)
