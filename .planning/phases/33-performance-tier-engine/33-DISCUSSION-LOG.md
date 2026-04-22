# Phase 33: 绩效档次纯引擎 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 33-performance-tier-engine
**Areas discussed:** Ties 边界处理算法 / Distribution warning 触发口径 / 输入预排序责任 / Result 数据结构形态 / 异常 grade 处理

---

## Area 1: Ties 边界处理算法

### Q1.1 — Ties「整批入更宽档」的边界判断方式

| Option | Description | Selected |
|--------|-------------|----------|
| A | 按 ties 中**首位**员工位次判断 — 首位 ≤ 20% → 整 grade 入 1 档（ties 向上扩张） | ✓ |
| B | 按 ties 中**末位**员工位置判断 — 末位也 ≤ 20% 才入 1 档（ties 向下收缩） | |
| C | 按 ties 组**中位数位次** vs 20% 边界（接近真实但实现复杂） | |

**User's choice:** A
**Rationale:** HR 友好优先 — 宁可让边界处的多人享 1 档，而非牺牲临界员工

### Q1.2 — Ties 横跨多档（极端情况，例如某 grade 横跨 2 档边界）

| Option | Description | Selected |
|--------|-------------|----------|
| A | 归入该 grade **多数员工本应所在的档**（中位数） | ✓ |
| B | 永远归更宽档（即 1 档） | |
| C | 永远归更严档（即 3 档） | |

**User's choice:** A
**Rationale:** 避免「全员 grade=B 时全部入 1 档」的极端情况

---

## Area 2: Distribution warning 触发口径

### Q2.1 — 「±5%」偏离的判断方式

| Option | Description | Selected |
|--------|-------------|----------|
| A | **绝对百分点偏差** — 1 档 ∈ [15%, 25%]、2 档 ∈ [65%, 75%]、3 档 ∈ [5%, 15%]，任一超出触发 | ✓ |
| B | **相对偏差** `\|实际 - 理想\| / 理想 > 5%`（3 档极度敏感：5% × 5% = ±0.25% 即触发） | |
| C | 仅看 1 档与 3 档（业务最关心两端） | |

**User's choice:** A (用户后续选择「全部按推荐」)
**Rationale:** 绝对百分点最直观、阈值不被档位规模放大

### Q2.2 — `actual_distribution` 字段形态

| Option | Description | Selected |
|--------|-------------|----------|
| A | dict `{1: 0.22, 2: 0.68, 3: 0.10}`（None 档不计入分母） | ✓ |
| B | dict 含 None 档 `{1, 2, 3, None}`（透明显示未分档人数） | |
| C | 分两个字段 `tier_distribution` + `none_count` | |

**User's choice:** A (用户后续选择「全部按推荐」)
**Rationale:** None 档不属「档次分布」概念，混入会误导 HR；none 数量已通过 `sample_size - sum(tiers)` 可推导

---

## Area 3: 输入预排序责任

### Q3.1 — Engine 接受已排序 list 还是内部排序

| Option | Description | Selected |
|--------|-------------|----------|
| A | Engine 接 already-sorted list（caller 用 SQL ORDER BY） | |
| B | Engine 内部用 `eligibility_engine.GRADE_ORDER` 倒序排序（自洽，单一事实源） | ✓ |

**User's choice:** B (推荐默认)
**Rationale:** 合法 sort key 集中维护、Phase 34 Service 不必关心 SQL 细节、与已有 `EligibilityEngine.check_performance` 共用 GRADE_ORDER

---

## Area 4: Result 数据结构形态

### Q4.1 — 输出形态

| Option | Description | Selected |
|--------|-------------|----------|
| A | 简单 dict `{employee_id: tier}` + 副输出 `meta` dict | |
| B | dataclass `TierAssignmentResult(tiers, insufficient_sample, distribution_warning, actual_distribution, sample_size, skipped_invalid_grades)` | ✓ |
| C | 分两次调用（assign + describe） | |

**User's choice:** B (推荐默认)
**Rationale:** 与 `EligibilityResult` 风格一致、IDE 类型提示清晰、Phase 34 Service 消费简单

---

## Area 5: 空 grade / 异常 grade 处理

### Q5.1 — 输入 list 中 grade 为 None / 空字符串 / 非 A-E 字符串如何处理

| Option | Description | Selected |
|--------|-------------|----------|
| A | 跳过且不计入 sample_size，meta 加 `skipped_invalid_grades` 计数器 | ✓ |
| B | 抛异常（让调用方先清洗数据） | |
| C | 计入 sample_size 但归入 tier=None | |

**User's choice:** A (推荐默认)
**Rationale:** 引擎应对脏数据零异常、计数器便于上层报告未分档原因

---

## Claude's Discretion

- 单元测试用例的具体命名 / 文件分割
- 内部 helper 方法命名
- `actual_distribution` 浮点保留位数（推荐 4 位）

## Deferred Ideas

- 绩效档次快照持久化 → Phase 34
- 手动重算档次 API → Phase 34
- HR 端「分布视图 + 黄色 warning 横幅」UI → Phase 34
- 员工端档次徽章 → Phase 35
- 绩效历史展示 → Phase 36
