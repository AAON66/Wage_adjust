---
phase: 33-performance-tier-engine
plan: 01
subsystem: engines
tags: [performance-tier, ties, distribution, percent-rank, tdd, pure-computation]

# Dependency graph
requires:
  - phase: v1.1-eligibility
    provides: GRADE_ORDER constant in eligibility_engine.py (single source of truth for A/B/C/D/E rank)
provides:
  - PerformanceTierEngine pure-computation engine (D-09: no I/O, no exceptions)
  - PerformanceTierConfig frozen dataclass for runtime injection (min_sample_size, tier_targets, distribution_tolerance)
  - TierAssignmentResult dataclass with 6 fields (tiers / insufficient_sample / distribution_warning / actual_distribution / sample_size / skipped_invalid_grades)
  - 4-branch ties algorithm: D-01 (first expansion) + D-02 (median assignment) + cross-tier handling + tail tier rule
  - Settings.performance_tier_min_sample_size = 50 (configurable via PERFORMANCE_TIER_MIN_SAMPLE_SIZE env var)
affects: [phase-34-performance-management-service, phase-35-employee-self-service]

tech-stack:
  added: []
  patterns:
    - "engine-purity: from __future__ import annotations / no I/O / no raise / dataclass config + dataclass result (matches eligibility_engine + salary_engine)"
    - "GRADE_ORDER single source of truth via cross-engine import (no duplication)"
    - "4-decimal float rounding for boundary comparison to defeat IEEE 754 drift on 含等 semantics"

key-files:
  created:
    - backend/app/engines/performance_tier_engine.py (162 LOC)
    - backend/tests/test_engines/test_performance_tier_engine.py (343 LOC, 30 cases)
  modified:
    - backend/app/core/config.py (Settings.performance_tier_min_sample_size: int = 50)
    - backend/app/engines/__init__.py (export PerformanceTierEngine + PerformanceTierConfig + TierAssignmentResult)
    - .env.example (new ELIGIBILITY / PERFORMANCE THRESHOLDS section)

key-decisions:
  - "_check_distribution_warning rounds bounds to 4 decimals to fix IEEE 754 drift (0.20 - 0.05 == 0.15000000000000002)"
  - "E1/E2/E3/E4/F2 use white-box tests of _check_distribution_warning because canonical D-01 algorithm makes most natural distributions tier-1 == 20% minimum"

patterns-established:
  - "Pure engine boundary contract: input is plain list[tuple], output is single dataclass result, all configuration via constructor injection"
  - "Float-precision-safe boundary comparison: round(target ± tol, 4) before <, > checks"
  - "TDD RED→GREEN flow with test count > acceptance threshold (30 cases vs 20 minimum)"

requirements-completed: [PERF-03, PERF-04, PERF-06]

# Metrics
duration: 6min
completed: 2026-04-22
---

# Phase 33 Plan 01: 绩效档次纯引擎 Summary

**4-branch ties algorithm 实现的纯计算 PerformanceTierEngine — 输入 `(employee_id, grade)` list 切 20/70/10 三档，ties 同档（D-01 首位扩张 + D-02 中位数归档），样本不足/异常 grade 通过返回结构优雅降级，30 个单测全绿。**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-22T06:08:07Z
- **Completed:** 2026-04-22T06:14:41Z
- **Tasks:** 3
- **Files modified:** 5（新建 2 + 修改 3）

## Accomplishments

- `PerformanceTierEngine.assign()` 纯计算引擎落地 — 4-branch 算法清晰处理首位扩张 / 末档 / 横跨多档 / 单档边界 4 种 ties 场景
- 配置化阈值 `PerformanceTierConfig(min_sample_size=50, tier_targets=(0.20, 0.70, 0.10), distribution_tolerance=0.05)`，构造函数注入便于单测覆盖
- `TierAssignmentResult` 6 字段全部可观测：tier 映射 / 样本不足标志 / 分布偏离告警 / 实际分布 / 有效样本数 / 跳过的非法 grade 数
- D-08 异常 grade 处理统一通过 `(grade or '').strip().upper() in GRADE_ORDER` 过滤，None / '' / 'F' / '优' 全部 tier=None
- D-09 引擎不抛异常约束严格执行（`grep -c "^[[:space:]]*raise " == 0`）
- GRADE_ORDER 复用 `eligibility_engine` 单一事实源，避免双源
- 30 个 pytest 用例覆盖 7 大类边界（基础 / ties / 边界样本 / 异常 grade / distribution warning / 配置覆盖 / 不变量），超出 ROADMAP SC-5 最低线 50%

## Task Commits

Each task was committed atomically:

1. **Task 1: Settings 字段 + .env.example 段落** — `4068647` (feat)
2. **Task 2 (RED): 添加失败测试套件** — `79b134d` (test)
3. **Task 2 (GREEN): PerformanceTierEngine 实现 + 测试修正** — `aab6d5f` (feat)
4. **Task 3: engines/__init__.py 包顶层导出** — `a50f380` (chore)

## Files Created/Modified

- `backend/app/engines/performance_tier_engine.py`（新建，162 LOC）— Engine + Config + Result
- `backend/tests/test_engines/test_performance_tier_engine.py`（新建，343 LOC）— 30 个 pytest 用例
- `backend/app/core/config.py`（追加 1 字段）— `performance_tier_min_sample_size: int = 50`
- `backend/app/engines/__init__.py`（追加导出）— 新引擎/配置/结果类入 `__all__`
- `.env.example`（追加段落）— 新增「ELIGIBILITY / PERFORMANCE THRESHOLDS」分组 + 默认值注释

## D-XX 决策落地映射

| 决策 ID | 算法/字段位置 | 测试覆盖 |
|---------|---------------|---------|
| D-01 Ties 首位扩张 | `_assign_tiers` 分支 (b) `first_pct < t1_cut` 整组归 1 档 | B1 (20 A in 100), B2 (25 A in 100, last 已 24% 仍归 1 档) |
| D-02 横跨多档 / 中位数归档 | `_assign_tiers` 分支 (a) 横跨 + 分支 (d) 单档边界 | A2/A3 (全员同 grade → median 49% → 2 档), B3 (5 人 B 在 21-25 位 → median 22% → 2 档), B4 (全员 B → median 49.5% → 2 档) |
| D-03 ±5% 绝对百分点偏差 | `_check_distribution_warning` round 4 位小数比较 | E1 (15% 含等 → false), E2 (14.99% → true), E3 (25% 含等 → false), E4 (25.01% → true) |
| D-04 actual_distribution 三档占比 | `_compute_distribution` 分母 = sample_size | E5 (20/70/10 全在范围), G1 (字段存在性) |
| D-05 insufficient_sample → warning=false | `assign()` 早返回分支强制 `distribution_warning=False` | E6 (2 人 sample → warning=false) |
| D-06 内部降序排序 + GRADE_ORDER 复用 | `sorted(valid, key=lambda x: -GRADE_ORDER[x[1]])` + `from eligibility_engine import GRADE_ORDER` | G2 (`is` identity check) |
| D-07 TierAssignmentResult 6 字段 | `@dataclass` 定义 | G1 (字段集合断言) |
| D-08 异常 grade 跳过 | `assign()` 入口 `if normalized in GRADE_ORDER` 过滤 | D1 (None), D2 (''), D3 ('F'), D4 (None + '' + '优') |
| D-09 不抛异常 | 全方法零 `raise` 语句（`grep -c "raise " == 0`） | C1 (空 list), C2-C4 (1/2/3 人), 全 D 组（异常 grade 不崩） |
| D-10 Settings.performance_tier_min_sample_size = 50 | `backend/app/core/config.py` line 86 | F1 (自定义 min_sample_size=10) + Task 1 自动化验证 |
| D-11 tier_targets / distribution_tolerance 默认值硬编码 | `PerformanceTierConfig` frozen 默认 `(0.20, 0.70, 0.10)` + `0.05` | F2 (自定义 tolerance=0.10) |

## ROADMAP Success Criteria 映射

| ROADMAP SC | 验证证据 |
|------------|----------|
| SC-1 调用 `PerformanceTierEngine.assign()` 返回 tier 映射，ties 同档 | A1, B1, B2, B3 — 全部 PASS |
| SC-2 sample < min_sample_size 时全员 tier=null + insufficient_sample=true | C5 (49 人) + Task 1 Settings 加载验证 |
| SC-3 0/1/2/3 人边界样本不抛异常 | C1, C2, C3, C4 — 全部 PASS（无 exception） |
| SC-4 实际分布偏离 20/70/10 ±5% 时 distribution_warning=true | E2, E4, E7 — 全部 PASS |
| SC-5 单元测试覆盖 20+ 用例 | 30 cases collected ✓（150% of minimum） |

## Phase 34 Service 层接口契约

```python
from backend.app.engines import PerformanceTierEngine, PerformanceTierConfig, TierAssignmentResult
from backend.app.core.config import get_settings

settings = get_settings()
engine = PerformanceTierEngine(
    config=PerformanceTierConfig(min_sample_size=settings.performance_tier_min_sample_size)
)
result: TierAssignmentResult = engine.assign(
    [('emp_001', 'A'), ('emp_002', 'B'), ('emp_003', None), ...]
)
# result.tiers                  -> dict[str, int | None]，{'emp_001': 1, 'emp_003': None}
# result.insufficient_sample    -> bool
# result.distribution_warning   -> bool
# result.actual_distribution    -> dict[int, float]，{1: 0.22, 2: 0.68, 3: 0.10}
# result.sample_size            -> int（已扣除 skipped_invalid_grades）
# result.skipped_invalid_grades -> int
```

Phase 34 Service 直接消费 `result.tiers` 写入 `PerformanceTierSnapshot`，`distribution_warning=true` 时附 HR 提示横幅。

## Decisions Made

1. **Float-precision-safe boundary check (Rule 1 — Bug fix during execution)**
   - 在 GREEN 阶段发现 E1 测试失败：`{1: 0.15, 2: 0.70, 3: 0.15}` 期待 warning=False 但实测 True
   - 根因：IEEE 754 下 `0.20 - 0.05 == 0.15000000000000002`，导致 `0.15 < 0.15000000000000002` 为 True 误触发
   - 修复：`_check_distribution_warning` 内对 `target ± tol` 取 `round(..., 4)` 后再比较
   - 与 `_compute_distribution` 4 位小数同口径，对应 threat model T-33-03 的「accept」转「mitigate」
   - 落在 `aab6d5f` 提交内（与 GREEN 实现同步）
2. **E1-E4/F2 改为白盒测试 _check_distribution_warning**
   - 原因：D-01 4-branch 算法下，自然 100 人样本的 tier 1 占比下界 = 20%（任何 first_pct < 20% 的相邻分组都会被首位扩张吸入 1 档）
   - 因此「tier 1 = 14.99%」「tier 1 = 15.0%」等下界场景**无法通过端到端构造达到**
   - 解决：E1/E2/E3/E4/F2 直接调用 `engine._check_distribution_warning(synthetic_dict)` 验证 D-03 边界含等语义；E5/E7 仍保留端到端 100 人构造覆盖自然分布路径

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `_check_distribution_warning` IEEE 754 浮点精度漂移**
- **Found during:** Task 2 GREEN（E1 测试失败）
- **Issue:** `target=0.20, tol=0.05 → target - tol = 0.15000000000000002`，导致 actual=0.15 时 `0.15 < 0.15000000000000002` 为 True，错误触发 distribution_warning（D-03 含等语义被破坏）
- **Fix:** `_check_distribution_warning` 内对 lower/upper 边界取 `round(..., 4)` 后再做 `<`/`>` 比较；与 `_compute_distribution` 同口径，确保「含等」语义在所有 4 位小数倍数边界（如 0.15、0.25、0.65、0.75 等）正确生效
- **Files modified:** `backend/app/engines/performance_tier_engine.py`（`_check_distribution_warning` 方法）
- **Verification:** 30 个测试全绿，含 E1（0.15 不告警）/ E3（0.25 不告警）/ E5（20/70/10 不告警）边界用例
- **Committed in:** `aab6d5f`（与 GREEN 实现同提交，行内修复）

---

**Total deviations:** 1 auto-fixed（Rule 1 浮点精度 bug）
**Impact on plan:** 修复属于 D-03 含等语义的强制约束（threat model T-33-03 原标 accept，本次升为 mitigate），无 scope creep。

## Issues Encountered

**1. 测试用例与 D-01 算法的可达性冲突**
- 在 GREEN 阶段第一轮发现 E1/E2/E3/F2 共 4 个测试因「测试构造数据」而非「引擎实现」错误而失败
- 分析后确认 D-01 4-branch 算法天然导致 tier 1 占比下界 = 20%（除非全员同 grade 触发分支 a），所以「tier 1 = 15%」等场景在 100 人样本下无法通过自然 grade 分布达到
- 决定：测试 `_check_distribution_warning` 的 D-03 边界语义改为白盒，端到端测试保留覆盖自然分布路径
- 同时新增 E7（端到端 26 A → tier 1 = 26% 触发 warning）确保自然分布的 warning 触发也覆盖

**2. Python 解释器路径 / venv 定位**
- 仓库根目录无独立 `python` 命令；用 `/Users/mac/PycharmProjects/Wage_adjust/.venv/bin/python` 显式指定 venv 解释器
- 不影响代码 / 测试，仅是执行命令的路径细节

## Next Phase Readiness

**Ready for Phase 34:**
- `PerformanceTierEngine` / `PerformanceTierConfig` / `TierAssignmentResult` 已通过 `backend.app.engines` 顶层导出
- `Settings.performance_tier_min_sample_size` 可通过 `get_settings()` + `Depends` 注入
- 接口契约清晰：input `list[tuple[str, str | None]]`，output `TierAssignmentResult`
- 30 个测试用例可作为 Phase 34 Service 层的回归基线

**已知遗留（按 D-11 计划范围）：**
- `tier_targets` (`(0.20, 0.70, 0.10)`) 与 `distribution_tolerance` (`0.05`) 仅通过 `PerformanceTierConfig` 构造函数覆盖，未开放 env 配置 — Phase 34 决定是否升级
- 浮点精度修复将 threat model T-33-03 从「accept」升为「mitigate」，无需新增 threat 条目

**无 blockers。**

## User Setup Required

None — engine 是纯计算模块，无需外部服务配置。新增 env 变量 `PERFORMANCE_TIER_MIN_SAMPLE_SIZE` 已在 `.env.example` 文档化，默认值 50 适用于多数场景。

## Self-Check: PASSED

- ✓ `backend/app/engines/performance_tier_engine.py` exists（162 LOC）
- ✓ `backend/tests/test_engines/test_performance_tier_engine.py` exists（343 LOC，30 cases）
- ✓ Commit `4068647` (Task 1) found in `git log --oneline`
- ✓ Commit `79b134d` (Task 2 RED) found
- ✓ Commit `aab6d5f` (Task 2 GREEN) found
- ✓ Commit `a50f380` (Task 3) found
- ✓ `pytest backend/tests/test_engines/` → 64 passed (existing 34 + new 30)
- ✓ `from backend.app.engines import PerformanceTierEngine, PerformanceTierConfig, TierAssignmentResult` succeeds
- ✓ `Settings().performance_tier_min_sample_size == 50` verified
- ✓ Engine purity: 0 `raise` / 0 I/O imports / GRADE_ORDER reused via import

---

*Phase: 33-performance-tier-engine*
*Completed: 2026-04-22*
