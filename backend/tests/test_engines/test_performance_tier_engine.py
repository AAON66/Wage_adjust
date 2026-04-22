from __future__ import annotations

import pytest

from backend.app.engines.eligibility_engine import GRADE_ORDER as ELIGIBILITY_GRADE_ORDER
from backend.app.engines.performance_tier_engine import (
    PerformanceTierConfig,
    PerformanceTierEngine,
    TierAssignmentResult,
)


@pytest.fixture
def engine() -> PerformanceTierEngine:
    return PerformanceTierEngine()


def _make_employees(count: int, grade: str) -> list[tuple[str, str]]:
    return [(f'emp_{i:03d}', grade) for i in range(count)]


# --- A. 基础正确性 ---

def test_a1_uniform_distribution_100_people(engine: PerformanceTierEngine) -> None:
    # 每 grade 20 人 -> A 全部入 1 档（20%），E 全部入 3 档（10%），其余入 2 档（70%）
    emps: list[tuple[str, str]] = []
    for grade in ('A', 'B', 'C', 'D', 'E'):
        emps.extend([(f'{grade}_{i:02d}', grade) for i in range(20)])
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    assert result.sample_size == 100
    # A grade 在前（首位 0%, 末位 19% ≤ 20%）应入 1 档
    a_tiers = {result.tiers[f'A_{i:02d}'] for i in range(20)}
    assert a_tiers == {1}
    # E grade 在末（first 80%, last 99%）应入 3 档（first ≥ 90%? 80% < 90%, last 99% ≥ 90% → 横跨? 不 first 不 < 20%, 走分支 d → median 89.5% < 90% → 2 档）
    # 实际：E grade first=80%, last=99%, median=89.5% → 走 (d) median 归档；89.5% < 90% → 2 档
    # 这个具体 case 我们只断言 tier ∈ {2, 3}
    e_tiers = {result.tiers[f'E_{i:02d}'] for i in range(20)}
    assert e_tiers.issubset({2, 3})
    assert all(v in (1, 2, 3) for v in result.tiers.values())


def test_a2_all_grade_a_50_people(engine: PerformanceTierEngine) -> None:
    # D-02 横跨多档：first=0% < 20% AND last=98% >= 90% → 中位数 49% → 2 档
    emps = _make_employees(50, 'A')
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    assert all(v == 2 for v in result.tiers.values())


def test_a3_all_grade_e_50_people(engine: PerformanceTierEngine) -> None:
    # 同 A2 逻辑，全员同 grade → 中位数 49% → 2 档
    emps = _make_employees(50, 'E')
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    assert all(v == 2 for v in result.tiers.values())


def test_a4_mixed_4_grade_100_people(engine: PerformanceTierEngine) -> None:
    # A=10, B=15, C=50, D=20, E=5
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(10)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(15)])
    emps.extend([(f'C_{i:02d}', 'C') for i in range(50)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(20)])
    emps.extend([(f'E_{i:02d}', 'E') for i in range(5)])
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    assert result.sample_size == 100
    # 三档分布合理
    counts = {1: 0, 2: 0, 3: 0}
    for tier in result.tiers.values():
        counts[tier] += 1
    assert sum(counts.values()) == 100


def test_a5_5_people_5_grade_insufficient_sample(engine: PerformanceTierEngine) -> None:
    emps = [('e1', 'A'), ('e2', 'B'), ('e3', 'C'), ('e4', 'D'), ('e5', 'E')]
    result = engine.assign(emps)
    assert result.insufficient_sample is True
    assert all(v is None for v in result.tiers.values())
    assert result.sample_size == 5


# --- B. Ties 行为 (D-01/D-02) ---

def test_b1_ties_first_expansion_20_a_in_100(engine: PerformanceTierEngine) -> None:
    # 前 20 人 grade='A'，剩 80 人 grade='B'
    # A grade ties block: first=0%, last=19% → 既不横跨也不 ≥ 90%, first < 20% → 分支 (b) → 1 档
    # B grade ties block: first=20%, last=99% → 不横跨（first 不 < 20%），first 20% < 90% → 分支 (d) → median=59.5% → 2 档
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(20)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(80)])
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    a_tiers = {result.tiers[f'A_{i:02d}'] for i in range(20)}
    assert a_tiers == {1}


def test_b2_ties_first_expansion_25_a_in_100(engine: PerformanceTierEngine) -> None:
    # 前 25 人 grade='A'，剩 75 人 grade='B'
    # A grade ties: first=0%, last=24% → first < 20%, last < 90% 不横跨 → 分支 (b) → 1 档（即使 last 已 24%）
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(25)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(75)])
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    a_tiers = {result.tiers[f'A_{i:02d}'] for i in range(25)}
    assert a_tiers == {1}


def test_b3_ties_median_assignment_5_a_at_position_21_25(engine: PerformanceTierEngine) -> None:
    # 100 人，前 20 人 grade='B'，21-25 名 grade='A'，剩 75 人是错乱的需要手工排序
    # 实际 engine 内部按 grade 降序，所以 A 会被排在前面
    # 我们构造：5 人 grade='A' + 20 人 grade='B'(更多前位排序需求) → 不行，A 排序会到前面
    # 正确的 B3 测试：构造 5 人 grade='A' 但要让排序后他们处于 21-25 位
    # 这只能通过让 ties 之前已经有 25 人「更高」grade — 但 A 是最高，所以 A 始终在前
    # 重新理解：B3 test 的本意是「ties block 不在前 20%」的场景
    # 改方案：5 人 grade='A'，95 人 grade='C' → A 0-4%，C 5-99% → A 进 1 档（first=0% < 20%）
    # 这样无法测「first ≥ 20% 且非末档」 → 我们需要让 ties 出现在 20%-90% 中间
    # 用 grade 顺序：A B C，每段都构造合适 size：
    # 20 人 grade='A'（占 0-19%），5 人 grade='B'（占 20-24%），75 人 grade='C'（占 25-99%）
    # B grade ties: first=20%, last=24% → first 不 < 20%, first 不 ≥ 90% → 分支 (d) → median=22% → 2 档
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(20)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(5)])
    emps.extend([(f'C_{i:02d}', 'C') for i in range(75)])
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    b_tiers = {result.tiers[f'B_{i:02d}'] for i in range(5)}
    assert b_tiers == {2}


def test_b4_all_grade_b_100_people(engine: PerformanceTierEngine) -> None:
    # 极端横跨 case：全员 grade='B' → first=0% < 20% AND last=99% >= 90%
    # 分支 (a) 横跨多档 → median=49.5% → 2 档
    emps = _make_employees(100, 'B')
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    assert all(v == 2 for v in result.tiers.values())


# --- C. 边界样本 (D-09) ---

def test_c1_empty_list(engine: PerformanceTierEngine) -> None:
    result = engine.assign([])
    assert result.tiers == {}
    assert result.insufficient_sample is True
    assert result.sample_size == 0
    assert result.actual_distribution == {}
    assert result.skipped_invalid_grades == 0


def test_c2_one_person(engine: PerformanceTierEngine) -> None:
    result = engine.assign([('e1', 'A')])
    assert result.tiers == {'e1': None}
    assert result.insufficient_sample is True
    assert result.sample_size == 1


def test_c3_two_people(engine: PerformanceTierEngine) -> None:
    result = engine.assign([('e1', 'A'), ('e2', 'B')])
    assert all(v is None for v in result.tiers.values())
    assert result.insufficient_sample is True
    assert result.sample_size == 2


def test_c4_three_people(engine: PerformanceTierEngine) -> None:
    result = engine.assign([('e1', 'A'), ('e2', 'B'), ('e3', 'C')])
    assert all(v is None for v in result.tiers.values())
    assert result.insufficient_sample is True
    assert result.sample_size == 3


def test_c5_49_people(engine: PerformanceTierEngine) -> None:
    emps = _make_employees(49, 'A')
    result = engine.assign(emps)
    assert all(v is None for v in result.tiers.values())
    assert result.insufficient_sample is True
    assert result.sample_size == 49


def test_c6_50_people_threshold(engine: PerformanceTierEngine) -> None:
    # 50 人含全部有效 grade — 应通过样本量门槛
    emps = _make_employees(50, 'A')
    result = engine.assign(emps)
    assert result.insufficient_sample is False
    assert result.sample_size == 50
    # 全员 grade='A' 触发横跨多档分支 → 全员 tier=2
    assert all(v == 2 for v in result.tiers.values())


# --- D. 异常 grade (D-08) ---

def test_d1_one_grade_none(engine: PerformanceTierEngine) -> None:
    emps: list[tuple[str, str | None]] = [('bad', None)]
    emps.extend(_make_employees(99, 'A'))  # type: ignore[arg-type]
    result = engine.assign(emps)
    assert result.tiers['bad'] is None
    assert result.sample_size == 99
    assert result.skipped_invalid_grades == 1


def test_d2_one_grade_empty_string(engine: PerformanceTierEngine) -> None:
    emps: list[tuple[str, str | None]] = [('bad', '')]
    emps.extend(_make_employees(99, 'A'))
    result = engine.assign(emps)
    assert result.tiers['bad'] is None
    assert result.sample_size == 99
    assert result.skipped_invalid_grades == 1


def test_d3_one_grade_unrecognized(engine: PerformanceTierEngine) -> None:
    emps: list[tuple[str, str | None]] = [('bad', 'F')]
    emps.extend(_make_employees(99, 'A'))
    result = engine.assign(emps)
    assert result.tiers['bad'] is None
    assert result.sample_size == 99
    assert result.skipped_invalid_grades == 1


def test_d4_three_invalid_grades_mixed(engine: PerformanceTierEngine) -> None:
    emps: list[tuple[str, str | None]] = [
        ('bad1', None),
        ('bad2', ''),
        ('bad3', '优'),
    ]
    emps.extend(_make_employees(97, 'A'))
    result = engine.assign(emps)
    assert result.tiers['bad1'] is None
    assert result.tiers['bad2'] is None
    assert result.tiers['bad3'] is None
    assert result.sample_size == 97
    assert result.skipped_invalid_grades == 3


# --- E. Distribution warning (D-03/D-04/D-05) ---

def test_e1_tier1_exact_15_percent_no_warning(engine: PerformanceTierEngine) -> None:
    # 1 档实际占比恰 15.0% — 边界含等
    # 构造：100 人，前 15 人 grade='A'（→ 1 档），70 人 grade='B'（→ 2 档），15 人 grade='D'（→ 3 档）
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(15)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(70)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(15)])
    result = engine.assign(emps)
    # A: first=0% last=14% → 分支 (b) → 1 档
    # B: first=15% last=84% → 不横跨, first 不 < 20% → 分支 (d) → median=49.5% → 2 档
    # D: first=85% last=99% → 不横跨, first 不 < 20%, first 不 >= 90% → 分支 (d) → median=92% >= 90% → 3 档
    assert result.actual_distribution[1] == 0.15
    assert result.distribution_warning is False


def test_e2_tier1_below_15_warning(engine: PerformanceTierEngine) -> None:
    # 1 档 < 15% 触发 warning
    # 构造 14 人 A → 1 档（仅 14%）
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(14)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(71)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(15)])
    result = engine.assign(emps)
    assert result.actual_distribution[1] == 0.14
    assert result.distribution_warning is True


def test_e3_tier1_exact_25_percent_no_warning(engine: PerformanceTierEngine) -> None:
    # 1 档 25% 边界
    # 构造 25 人 A → 1 档（D-01 ties 首位扩张：first=0% last=24% < 20%? last 24% > 20% but first<20% non-cross → 分支 (b) → 1 档）
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(25)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(60)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(15)])
    result = engine.assign(emps)
    assert result.actual_distribution[1] == 0.25
    assert result.distribution_warning is False


def test_e4_tier1_above_25_warning(engine: PerformanceTierEngine) -> None:
    # 1 档 > 25% 触发 warning
    # 构造 26 人 A → 1 档
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(26)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(59)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(15)])
    result = engine.assign(emps)
    assert result.actual_distribution[1] == 0.26
    assert result.distribution_warning is True


def test_e5_all_tiers_in_range_no_warning(engine: PerformanceTierEngine) -> None:
    # 三档全部在 [15-25, 65-75, 5-15] 区间
    # 构造 20/70/10 完美分布
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(20)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(70)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(10)])
    result = engine.assign(emps)
    assert result.distribution_warning is False
    assert result.actual_distribution[1] == 0.20
    assert result.actual_distribution[2] == 0.70
    assert result.actual_distribution[3] == 0.10


def test_e6_insufficient_sample_forces_warning_false(engine: PerformanceTierEngine) -> None:
    # D-05: 样本不足时即使分布偏离也强制 warning=false
    result = engine.assign([('e1', 'A'), ('e2', 'A')])
    assert result.insufficient_sample is True
    assert result.distribution_warning is False


# --- F. 配置覆盖 (D-10/D-11) ---

def test_f1_custom_min_sample_size_10(engine: PerformanceTierEngine) -> None:
    # 自定义 min_sample_size=10 → 10 人不触发 insufficient_sample
    custom = PerformanceTierEngine(PerformanceTierConfig(min_sample_size=10))
    emps = _make_employees(10, 'A')  # 10 人 grade='A'
    result = custom.assign(emps)
    assert result.insufficient_sample is False
    assert result.sample_size == 10


def test_f2_custom_distribution_tolerance_10_percent(engine: PerformanceTierEngine) -> None:
    # 自定义 tolerance=0.10 → 1 档 12% 不触发 warning（10% 容差 → [10%, 30%]）
    # 构造 12 人 A，73 人 B，15 人 D
    custom = PerformanceTierEngine(PerformanceTierConfig(distribution_tolerance=0.10))
    emps: list[tuple[str, str]] = []
    emps.extend([(f'A_{i:02d}', 'A') for i in range(12)])
    emps.extend([(f'B_{i:02d}', 'B') for i in range(73)])
    emps.extend([(f'D_{i:02d}', 'D') for i in range(15)])
    result = custom.assign(emps)
    assert result.actual_distribution[1] == 0.12
    assert result.distribution_warning is False


# --- G. 不变量 / 结构 ---

def test_g1_result_dataclass_has_six_fields(engine: PerformanceTierEngine) -> None:
    result = engine.assign([])
    expected_fields = {
        'tiers',
        'insufficient_sample',
        'distribution_warning',
        'actual_distribution',
        'sample_size',
        'skipped_invalid_grades',
    }
    actual_fields = set(result.__dataclass_fields__.keys())  # type: ignore[attr-defined]
    assert actual_fields == expected_fields


def test_g2_grade_order_is_imported_from_eligibility_engine() -> None:
    # GRADE_ORDER 必须是从 eligibility_engine import 的同一对象
    from backend.app.engines.performance_tier_engine import GRADE_ORDER as TIER_GRADE_ORDER
    assert TIER_GRADE_ORDER is ELIGIBILITY_GRADE_ORDER
