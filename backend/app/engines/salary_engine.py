from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


LEVEL_RULES = {
    'Level 1': {'multiplier': 1.00, 'base_ratio': 0.00, 'floor': 0.00, 'ceiling': 0.04},
    'Level 2': {'multiplier': 1.04, 'base_ratio': 0.03, 'floor': 0.02, 'ceiling': 0.08},
    'Level 3': {'multiplier': 1.08, 'base_ratio': 0.06, 'floor': 0.04, 'ceiling': 0.12},
    'Level 4': {'multiplier': 1.13, 'base_ratio': 0.10, 'floor': 0.07, 'ceiling': 0.18},
    'Level 5': {'multiplier': 1.18, 'base_ratio': 0.14, 'floor': 0.10, 'ceiling': 0.22},
}

JOB_LEVEL_ADJUSTMENTS = {
    'P4': 0.00,
    'P5': 0.01,
    'P6': 0.02,
    'P7': 0.03,
}

DEPARTMENT_ADJUSTMENTS = {
    'Engineering': 0.01,
    '研发': 0.01,
    '研发中心': 0.01,
    'Product': 0.008,
    '产品': 0.008,
    '产品中心': 0.008,
    'Design': 0.005,
    '设计': 0.005,
    '设计中心': 0.005,
}

JOB_FAMILY_ADJUSTMENTS = {
    'Platform': 0.01,
    '平台研发': 0.01,
    '平台': 0.01,
    'Product': 0.008,
    '产品': 0.008,
    'Design': 0.005,
    '设计': 0.005,
    'Operations': 0.003,
    '运营': 0.003,
}


@dataclass
class SalaryResult:
    current_salary: Decimal
    recommended_ratio: float
    recommended_salary: Decimal
    ai_multiplier: float
    certification_bonus: float
    final_adjustment_ratio: float
    explanation: str


class SalaryEngine:
    def _resolve_adjustment(self, source: dict[str, float], key: str | None) -> float:
        if not key:
            return 0.0
        normalized = key.strip()
        if normalized in source:
            return source[normalized]
        lowered = normalized.casefold()
        for candidate, value in source.items():
            if candidate.casefold() == lowered:
                return value
        return 0.0

    def calculate(
        self,
        *,
        ai_level: str,
        overall_score: float,
        current_salary: Decimal,
        certification_bonus: float = 0.0,
        job_level: str | None = None,
        department: str | None = None,
        job_family: str | None = None,
    ) -> SalaryResult:
        level_rule = LEVEL_RULES.get(ai_level, LEVEL_RULES['Level 1'])
        ai_multiplier = level_rule['multiplier']
        base_ratio = level_rule['base_ratio']
        score_bonus = max(0.0, min((overall_score - 60) / 450, 0.06))
        job_level_bonus = JOB_LEVEL_ADJUSTMENTS.get(job_level or '', 0.0)
        department_bonus = self._resolve_adjustment(DEPARTMENT_ADJUSTMENTS, department)
        job_family_bonus = self._resolve_adjustment(JOB_FAMILY_ADJUSTMENTS, job_family)
        clamped_certification_bonus = round(max(0.0, min(certification_bonus, 0.12)), 4)

        raw_ratio = base_ratio + score_bonus + clamped_certification_bonus + job_level_bonus + department_bonus + job_family_bonus
        final_ratio = round(max(level_rule['floor'], min(raw_ratio, level_rule['ceiling'])), 4)
        recommended_salary = (current_salary * Decimal(str(1 + final_ratio))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        explanation = (
            f'建议基于 {ai_level}、综合评分 {overall_score:.2f}、AI 系数 {ai_multiplier:.2f} 以及'
            f'基础比例 {base_ratio:.2%}、评分加成 {score_bonus:.2%}、认证加成 {clamped_certification_bonus:.2%}、'
            f'职级加成 {job_level_bonus:.2%}、部门加成 {department_bonus:.2%}、序列加成 {job_family_bonus:.2%} 综合计算。'
            f'最终调薪比例会被约束在当前等级对应的区间 {level_rule["floor"]:.2%} - {level_rule["ceiling"]:.2%} 内。'
        )
        return SalaryResult(
            current_salary=current_salary,
            recommended_ratio=round(base_ratio + score_bonus, 4),
            recommended_salary=recommended_salary,
            ai_multiplier=ai_multiplier,
            certification_bonus=clamped_certification_bonus,
            final_adjustment_ratio=final_ratio,
            explanation=explanation,
        )

    def is_over_budget(self, *, total_increase: Decimal, budget_amount: Decimal) -> bool:
        return total_increase > budget_amount
