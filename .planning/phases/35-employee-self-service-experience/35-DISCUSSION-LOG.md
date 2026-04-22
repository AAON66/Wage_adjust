# Phase 35: 员工端自助体验 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 35-employee-self-service-experience
**Areas discussed:** 年份选择策略 / 「暂不分档」文案分层 / 徽章视觉与色彩 / 响应 schema 字段与时间戳

---

## 灰区预选（multiSelect）

| Option | Description | Selected |
|--------|-------------|----------|
| 年份选择策略 | /performance/me/tier 无参数路由如何定位「哪一年」的档次快照 | ✓ |
| 「暂不分档」文案分层 | insufficient_sample / no_snapshot / not_ranked 是否分层呈现 | ✓ |
| 徽章视觉与色彩 | 直接复用 HR TierChip 硬色 vs 员工端柔和风格 | ✓ |
| 响应 schema 字段与时间戳 | API 响应体字段设计 + data_updated_at 取值来源 | ✓ |

**User's choice:** 全选（4 个灰区全部讨论）

---

## Area 1 — 年份选择策略

### Q1.1：/performance/me/tier 无参数路由如何决定查哪一年的档次快照？

| Option | Description | Selected |
|--------|-------------|----------|
| 当前自然年 fallback 到最新快照 | 先查 datetime.now().year，未命中 fallback 到最新快照年，响应带 year 字段 | ✓ |
| 仅查当前自然年 | 严格当前年，无快照直接「本年度暂无档次」 | |
| 仅查最新有快照的年 | ORDER BY year DESC LIMIT 1，永远最新 | |
| 同时返回最近 2 年 | 响应为数组，超出 ESELF-03 单点展示范围 | |

**User's choice:** 当前自然年 fallback 到最新快照（Recommended）
**Notes:** 对应 CONTEXT.md D-01

### Q1.2：库里完全无 PerformanceTierSnapshot 行时 /performance/me/tier 返回什么？

| Option | Description | Selected |
|--------|-------------|----------|
| 200 + tier=null + year=null + reason=no_snapshot | 统一走 200 + reason 枚举分层，与其他 null 分支一致 | ✓ |
| 404 + error=no_snapshot_ever | 对齐 Phase 34 /tier-summary 的 D-10 | |
| 200 + tier=null，不显示区分理由 | 抛弃分层能力，与下一题冲突 | |

**User's choice:** 200 + tier=null + year=null + reason=no_snapshot（Recommended）
**Notes:** 对应 CONTEXT.md D-02；隐含决定响应 schema 必有 `reason` 字段

---

## Area 2 — 「暂不分档」文案分层

### Q2.1：三种「暂不分档」场景怎么分层呈现？

| Option | Description | Selected |
|--------|-------------|----------|
| 三种原因都各自文案 | reason 三枚举各对应不同前端文案 | ✓ |
| 统一「暂不分档」文案 | 不区分内部差异 | |
| 合并 (a)+(b) 为「暂不分档」，(c) 独立文案 | 2 档文案 | |

**User's choice:** 三种原因都各自文案（Recommended）
**Notes:** 对应 CONTEXT.md D-03；响应 reason 字段 Literal 三选一

---

## Area 3 — 徽章视觉与色彩

### Q3.1：员工端「本人绩效档次」徽章的视觉与文案风格？

| Option | Description | Selected |
|--------|-------------|----------|
| 完全复用 HR 端 TierChip 硬色（绿/黄/红） | 代码最省，员工心理冲击大 | |
| 柔和三档颜色 + 「1/2/3 档」纯数字标签 | 1档 #d1fae5、2档 #fef3c7、3档 #ffedd5，纯数字文案 | ✓ |
| 柔和三档颜色 + 语义文案（优秀/合格/待提升） | 色同上 + 文字加语义标签 | |

**User's choice:** 柔和三档颜色 + 「1/2/3 档」纯数字标签（Recommended）
**Notes:** 对应 CONTEXT.md D-07/D-08/D-09；新建 MyPerformanceTierBadge 组件，不复用 HR 端 TierChip

### Q3.2：tier=null（三种 reason 任一）时员工端如何渲染？

| Option | Description | Selected |
|--------|-------------|----------|
| 灰底占位徽章 + 分层文案 | 背景 #f3f4f6 文字 #6b7280，三 reason 文案分层 | ✓ |
| 完全隐藏档次 section | tier=null 时组件不渲染 | |
| 显示灰底徽章 + 统一「暂无档次」文案 | reason 后端有但前端丢弃 | |

**User's choice:** 灰底占位徽章 + 分层文案（Recommended）
**Notes:** 对应 CONTEXT.md D-08（灰底占位）+ D-03（文案分层）

---

## Area 4 — 响应 schema 字段与时间戳

### Q4.1：GET /api/v1/performance/me/tier 响应体的字段设计？

| Option | Description | Selected |
|--------|-------------|----------|
| 精简 4 字段 | { year, tier, reason, data_updated_at } | ✓ |
| 精简 4 字段 + 预渲染文案 | 额外 display_label 字段 | |
| 复用 TierSummaryResponse | 全盘 HR 维度字段（违反 ESELF-03 红线） | |

**User's choice:** 精简 4 字段（Recommended）
**Notes:** 对应 CONTEXT.md D-04；data_updated_at 取 PerformanceTierSnapshot.updated_at（D-05）

---

## 收尾

### Q5.1：4 个灰区都讨论完了。继续补问还是准备写 CONTEXT.md？

| Option | Description | Selected |
|--------|-------------|----------|
| 直接写 CONTEXT.md | 范围已稳，6 项决策足够 | ✓ |
| 补问 API 错误码细节 | 未绑定/员工不存在/JWT 失效 | |
| 补问前端组件层结构 | MyPerformanceTierBadge 的目录位置 | |

**User's choice:** 直接写 CONTEXT.md（Recommended）

---

## Claude's Discretion（延续至 CONTEXT.md）

- Service 层 get_my_tier 方法内部是否用 SELECT ... FOR UPDATE（纯读不需要）
- fetchMyTier 失败时的自动重试策略（沿用 Phase 32.1 手动「重试」按钮）
- section 垂直间距具体 px（对齐 MyEligibilityPanel）
- 加载态用 skeleton 还是 spinner（沿用 32.1 SkeletonRows）
- 单元测试命名风格（沿用 Phase 33/34 pytest 模式）
- api/v1/performance.py:206-209 TODO 注释删除与否（实现后直接 delete）
- 错误态（未绑定 / 员工档案缺失）延续 Phase 32.1 MyEligibilityPanel 错误处理模式 — 档次组件在未绑定时不重复渲染未绑定提示

## Deferred Ideas（同步至 CONTEXT.md deferred 区）

见 CONTEXT.md <deferred> 章节 10+ 条。

---

*Phase: 35-employee-self-service-experience*
*Discussion log: 2026-04-22*
