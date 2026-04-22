from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.engines.eligibility_engine import GRADE_ORDER


@dataclass(frozen=True)
class PerformanceTierConfig:
    """Configurable tier engine parameters (D-10/D-11)."""

    min_sample_size: int = 50
    tier_targets: tuple[float, float, float] = (0.20, 0.70, 0.10)
    distribution_tolerance: float = 0.05


@dataclass
class TierAssignmentResult:
    """Tier assignment output (D-07)."""

    tiers: dict[str, int | None] = field(default_factory=dict)
    insufficient_sample: bool = False
    distribution_warning: bool = False
    actual_distribution: dict[int, float] = field(default_factory=dict)
    sample_size: int = 0
    skipped_invalid_grades: int = 0


class PerformanceTierEngine:
    """Pure-computation performance tier engine (D-09: no exceptions, no I/O)."""

    def __init__(self, config: PerformanceTierConfig | None = None) -> None:
        self.config = config or PerformanceTierConfig()

    def assign(self, employees: list[tuple[str, str | None]]) -> TierAssignmentResult:
        # 1. 分离有效/无效 grade（D-08）
        valid: list[tuple[str, str]] = []
        invalid_ids: list[str] = []
        for emp_id, grade in employees:
            normalized = (grade or '').strip().upper() if grade else ''
            if normalized and normalized in GRADE_ORDER:
                valid.append((emp_id, normalized))
            else:
                invalid_ids.append(emp_id)

        sample_size = len(valid)
        tiers: dict[str, int | None] = {emp_id: None for emp_id in invalid_ids}

        # 2. 样本不足分支（D-09）
        if sample_size < self.config.min_sample_size:
            for emp_id, _ in valid:
                tiers[emp_id] = None
            return TierAssignmentResult(
                tiers=tiers,
                insufficient_sample=True,
                distribution_warning=False,
                actual_distribution={},
                sample_size=sample_size,
                skipped_invalid_grades=len(invalid_ids),
            )

        # 3. 降序排序（D-06：高 grade 在前）
        sorted_emps = sorted(valid, key=lambda x: -GRADE_ORDER[x[1]])

        # 4. Ties 分档（D-01 首位扩张 + D-02 中位数归档）
        assigned = self._assign_tiers(sorted_emps)
        tiers.update(assigned)

        # 5. 实际分布（D-04：分母为成功分档人数）
        distribution = self._compute_distribution(assigned, sample_size)

        # 6. 偏离告警（D-03/D-05）
        warning = self._check_distribution_warning(distribution)

        return TierAssignmentResult(
            tiers=tiers,
            insufficient_sample=False,
            distribution_warning=warning,
            actual_distribution=distribution,
            sample_size=sample_size,
            skipped_invalid_grades=len(invalid_ids),
        )

    def _assign_tiers(self, sorted_emps: list[tuple[str, str]]) -> dict[str, int]:
        """按 D-01 首位扩张 + D-02 中位数归档 切档（4-branch canonical 算法）。

        算法：
        1. 按 grade 分组（已排序，相同 grade 必相邻）
        2. 对每组 ties 计算 first_pct / last_pct / median_pct（基于位次 / n）
        3. 4 个分支：
           (a) ties 横跨多档（first<20% AND last>=90%，如「全员同 grade」）→ 按 D-02 中位数归档
           (b) first<20% 且非横跨多档 → D-01 首位扩张，整组归 1 档
           (c) first>=90% → 整组归 3 档
           (d) 其他（跨 1↔2 或 2↔3 单档边界）→ D-02 中位数归档
        """
        n = len(sorted_emps)
        result: dict[str, int] = {}
        t1_cut = self.config.tier_targets[0]                                   # 0.20
        t2_cut = self.config.tier_targets[0] + self.config.tier_targets[1]     # 0.90

        def _by_median(median_pct: float) -> int:
            if median_pct < t1_cut:
                return 1
            if median_pct < t2_cut:
                return 2
            return 3

        i = 0
        while i < n:
            grade = sorted_emps[i][1]
            j = i
            while j < n and sorted_emps[j][1] == grade:
                j += 1
            # ties block: indices [i, j)
            first_pct = i / n
            last_pct = (j - 1) / n
            median_pct = ((i + j - 1) / 2) / n

            if first_pct < t1_cut and last_pct >= t2_cut:
                # (a) 横跨多档（含「全员同 grade」极端 case）— D-02 中位数归档
                tier = _by_median(median_pct)
            elif first_pct < t1_cut:
                # (b) D-01 首位扩张到 1 档
                tier = 1
            elif first_pct >= t2_cut:
                # (c) 末档
                tier = 3
            else:
                # (d) 跨 1↔2 或 2↔3 单档边界 — D-02 中位数归档
                tier = _by_median(median_pct)

            for k in range(i, j):
                result[sorted_emps[k][0]] = tier
            i = j

        return result

    def _compute_distribution(
        self, assigned: dict[str, int], sample_size: int,
    ) -> dict[int, float]:
        """三档实际占比（D-04，4 位小数，分母为已分档人数）。"""
        counts = {1: 0, 2: 0, 3: 0}
        for tier in assigned.values():
            counts[tier] += 1
        return {t: round(counts[t] / sample_size, 4) for t in (1, 2, 3)}

    def _check_distribution_warning(self, distribution: dict[int, float]) -> bool:
        """任一档超出 ±tolerance 区间即触发（D-03/D-05）。

        边界比较使用 4 位小数（与 `_compute_distribution` 同口径）以避免浮点误差，
        例如 `0.20 - 0.05 == 0.15000000000000002` 在 IEEE 754 下的精度漂移。
        """
        tol = self.config.distribution_tolerance
        targets = self.config.tier_targets
        for idx, tier in enumerate((1, 2, 3)):
            target = targets[idx]
            actual = distribution[tier]
            lower = round(target - tol, 4)
            upper = round(target + tol, 4)
            if actual < lower or actual > upper:
                return True
        return False
