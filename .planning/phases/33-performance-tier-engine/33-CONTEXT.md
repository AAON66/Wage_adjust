# Phase 33: 绩效档次纯引擎 - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

提供 `PerformanceTierEngine.assign()` 纯计算引擎：输入 `(employee_id, grade)` 列表，输出 `{employee_id: 1|2|3|None}` 映射 + meta 信息（样本不足标志、分布偏离告警、实际分布）。按 `PERCENT_RANK` 口径切 20/70/10，ties 同档，样本 < `Settings.performance_tier_min_sample_size`（默认 50）时全员返回 null。

**纯引擎边界 — 严格不在范围：**
- 不读 DB、不调外部服务、不做 I/O（与 `eligibility_engine.py` / `salary_engine.py` 同样的纯计算职责）
- 不消费 Service 层 / API 层 / UI 层（这些由 Phase 34/35/36 承接）
- 不读取 `PerformanceRecord` 表 — 输入 list 由调用方组装好传入
- 不持久化档次结果 — 调用方决定是否落 `PerformanceTierSnapshot`（Phase 34 范围）

</domain>

<decisions>
## Implementation Decisions

### Ties 边界处理算法

- **D-01:** Ties 向上扩张 — 按 ties 中**首位**员工的累计百分位判断归档；首位位次 ≤ 20% → 整组 grade 全部入 1 档（即使该 grade 末位 > 20%）。理由：HR 友好，宁可让边界处的多人享 1 档而非牺牲临界员工。
- **D-02:** 横跨多档的 ties（极端：某 grade 横跨 2 档边界，例如 25%-95% 百分位）按 ties 组**中位数位次**归档 — 即归入该 grade 多数员工本应所在的档。这避免「全员 grade=B 时全部入 1 档」的极端情况。

### Distribution warning 触发口径

- **D-03:** 「偏离 ±5%」是**绝对百分点偏差**：1 档实际占比 ∈ [15%, 25%]、2 档 ∈ [65%, 75%]、3 档 ∈ [5%, 15%]，任一档超出区间即触发 `distribution_warning=true`。
- **D-04:** Meta 同时返回 `actual_distribution: dict[int, float] = {1: 0.22, 2: 0.68, 3: 0.10}` 三档实际占比（保留 4 位小数），分母为「成功分档的人数」（即 `sample_size - sum(tier=None 个数)`）。**None 档不计入分母**，便于 HR 排查具体偏离哪档。
- **D-05:** Distribution warning 仅在 `insufficient_sample=false`（样本充足）时计算并可能为 true；样本不足时强制 `distribution_warning=false` 并跳过分布计算（小样本下偏离指标无意义）。

### 输入预排序责任

- **D-06:** Engine **内部**用 `eligibility_engine.GRADE_ORDER`（A=5/B=4/C=3/D=2/E=1）做**降序排序**（高分在前）。调用方传入的 list 不要求预排序。理由：合法 sort key 在引擎里集中维护，Phase 34 Service 不必关心 SQL ORDER BY 细节，且与已有 `EligibilityEngine.check_performance` 共用 GRADE_ORDER 表，单一事实源。

### Result 数据结构形态

- **D-07:** 输出 `@dataclass TierAssignmentResult`（与 `EligibilityResult` 风格一致），字段：
  - `tiers: dict[str, int | None]` — `{employee_id: 1|2|3|None}` 主映射
  - `insufficient_sample: bool` — 样本量 < min_sample_size 时 true
  - `distribution_warning: bool` — 分布偏离 ±5% 时 true（仅 insufficient_sample=false 时可能 true）
  - `actual_distribution: dict[int, float]` — `{1, 2, 3}` 三档实际占比，insufficient_sample=true 时为空 dict `{}`
  - `sample_size: int` — 参与分档的有效样本数（已扣除 skipped_invalid_grades）
  - `skipped_invalid_grades: int` — 跳过的非法 grade 计数

### 异常 grade 处理

- **D-08:** 输入 list 中 grade 为 `None`、空字符串、或不在 GRADE_ORDER（A/B/C/D/E）内的字符串（如 'F'、'A+'、'优'）的员工：
  - **从分档计算中跳过**（不进入排序、不计入 sample_size）
  - 该员工 `tier=None` 写入 `tiers` dict
  - `skipped_invalid_grades` 计数器 +1
- **D-09:** Engine 不抛异常 — 所有边界条件（空 list / 全员 grade=None / sample_size=0/1/2/3）通过返回结构表达，方便上层无感知降级。

### 阈值配置

- **D-10:** `Settings.performance_tier_min_sample_size: int = 50` 新增到 `backend/app/core/config.py`（位于现有 `eligibility_min_*` 阈值之后）。Engine 通过 `@dataclass(frozen=True) PerformanceTierConfig(min_sample_size: int = 50)` 接受（构造函数注入，便于单测覆盖不同样本阈值）。
- **D-11:** 「20/70/10」目标分布与「±5%」偏离阈值**硬编码在 `PerformanceTierConfig` 默认值**（`tier_targets: tuple[float,...] = (0.20, 0.70, 0.10)`、`distribution_tolerance: float = 0.05`），允许构造时覆盖以便单测。运行环境暂不开放 env 配置（Phase 33 范围内不需要）。

### Claude's Discretion

- 单元测试用例的具体命名 / 组织方式（按 D-01..D-11 各自的边界测就好，不限定文件分割）
- 内部 helper 方法命名（`_assign_tiers`、`_compute_distribution` 等纯计算辅助）
- `actual_distribution` 浮点保留位数（推荐 4 位但不强制）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine 风格与模式
- `backend/app/engines/eligibility_engine.py` — 引擎风格参考（@dataclass(frozen=True) 阈值 + @dataclass 结果 + 纯计算无 I/O + GRADE_ORDER 共享）
- `backend/app/engines/salary_engine.py` — 引擎风格参考（构造函数注入配置、所有规则配置化）

### 配置位置
- `backend/app/core/config.py` line 79-81 — `eligibility_min_*` 阈值放置示例（D-10 的 `performance_tier_min_sample_size` 应放在同一节内）

### 需求与约束
- `.planning/REQUIREMENTS.md` line 22-25 — PERF-03/04/06 三个原始需求文本
- `.planning/ROADMAP.md` line 166-176 — Phase 33 Goal + Success Criteria 1-5（5 个客观可验证条件）
- `CLAUDE.md` "AI Evaluation Standards" + "Coding Conventions" — 评分阈值/系数必须配置化、AI 结果输出结构化 JSON、引擎纯计算无 I/O 等核心约束

### Codebase 维度
- `.planning/codebase/CONVENTIONS.md` — Python 命名/类型注解/import 顺序约定
- `.planning/codebase/TESTING.md` — pytest 组织模式与测试约定（Phase 33 单测 20+ 用例需遵循）
- `.planning/codebase/STRUCTURE.md` — `backend/app/engines/` 目录归属说明

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`eligibility_engine.GRADE_ORDER`** (`backend/app/engines/eligibility_engine.py` line 8) — `dict[str,int]` 把 A/B/C/D/E 映射为 5/4/3/2/1，用于 grade 排序与比较。Phase 33 必须 import 复用，禁止重复定义（D-06 单一事实源）。
- **`@dataclass(frozen=True)` Thresholds 模式** — `EligibilityThresholds`、`SalaryEngine` 内部参数 dataclass 都是 frozen 不可变结构。Phase 33 `PerformanceTierConfig` 沿用同模式。
- **`@dataclass` Result 模式** — `EligibilityResult` 包含 status + rules list + meta 字段。Phase 33 `TierAssignmentResult` 沿用同模式（D-07）。
- **Settings 注入模式** — `Settings.eligibility_min_*` 通过 `pydantic_settings.BaseSettings` 暴露，Engine 构造函数接受可选 `Config | None = None` 参数（默认值由 dataclass 兜底）。Phase 33 `performance_tier_min_sample_size` 沿用该路径。

### Established Patterns
- **`from __future__ import annotations` 必须在所有后端模块顶部** — `CLAUDE.md` 强制约定。
- **PEP 604 union 语法**（`int | None` 而非 `Optional[int]`）— 已在 eligibility_engine 全面采用。
- **私有 helper 方法以 `_` 前缀**（如 `_month_diff`）— 用于纯计算辅助。
- **Engine 不写 docstring 或写极简单行 docstring** — 与现有 engines 保持一致；类型注解承担文档职责。
- **pytest 测试文件位于 `backend/tests/test_engines/`** — Phase 33 单测应放置于 `backend/tests/test_engines/test_performance_tier_engine.py`（参照 `test_eligibility_engine.py` 组织风格）。

### Integration Points
- **`backend/app/engines/__init__.py`** — Phase 33 需要 export `PerformanceTierEngine` 与 `TierAssignmentResult` 供 Phase 34 Service 层 import。
- **`backend/app/core/config.py` Settings 类** — D-10 新增 `performance_tier_min_sample_size: int = 50`。
- **`backend/.env.example`** — 同步加 `PERFORMANCE_TIER_MIN_SAMPLE_SIZE=50` 注释行（与现有 ELIGIBILITY_MIN_TENURE_MONTHS 同级）。
- **不接触：** `backend/app/services/`、`backend/app/api/v1/`、`backend/app/models/`、`frontend/` 任何文件 — 这些归 Phase 34/35/36。

</code_context>

<specifics>
## Specific Ideas

- 单测文件应有 1 个分组测「ties 向上扩张行为」（覆盖 D-01/D-02 的核心算法），1 个分组测「distribution_warning 边界值」（14.99% / 15% / 15.01% / 25% / 25.01% 等），1 个分组测「样本不足边界」（0/1/2/3/49/50 人），1 个分组测「异常 grade 处理」（None/'F'/空字符串/'优' 混入）。
- ROADMAP Success Criteria 5 要求 20+ 用例，建议覆盖：
  - 基础正确性（5 用例）：100 人均匀分布 / 全员 A / 全员 E / 100 人 4 grade 混合 / 5 人 5 grade
  - Ties 行为（4 用例）：D-01 首位扩张正向 / D-01 首位扩张反向（不入档）/ D-02 中位数归档 / 全员 grade=B 极端
  - 边界样本（5 用例）：sample=0 / 1 / 2 / 3 / 49（应触发 insufficient_sample）/ 50（不触发）
  - 异常 grade（4 用例）：None / 空字符串 / 'F' / 'A+' 混入正常样本
  - Distribution warning（5 用例）：1 档恰 15% / 14.99% 触发 / 25% 不触发 / 25.01% 触发 / 三档全在范围内
  - 配置覆盖（2 用例）：自定义 min_sample_size=10、自定义 distribution_tolerance=0.10

</specifics>

<deferred>
## Deferred Ideas

- **绩效档次快照持久化**（写 `PerformanceTierSnapshot` 表）→ Phase 34 范围
- **手动重算档次 API**（HR 在「绩效管理」页面点击重算）→ Phase 34 范围
- **HR 端「分布视图 + 黄色 warning 横幅」UI** → Phase 34 范围（Engine 只输出 `distribution_warning=true`，UI 由 Service+前端消费）
- **员工端档次徽章** → Phase 35 范围（消费档次结果，不产生新档次）
- **绩效历史展示** → Phase 36 范围

</deferred>

---

*Phase: 33-performance-tier-engine*
*Context gathered: 2026-04-22*
