# Phase 34: 绩效管理服务与 API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 34-performance-management-service-and-api
**Areas discussed:** 档次持久化形态 / 重算同步性 / 重算并发控制 / department_snapshot 回填 / tier-summary 响应 / 分布视图 UI / 页面信息架构 / 路由命名

---

## Area 1: 档次持久化形态

### Q1.1 — 快照表 schema

| Option | Description | Selected |
|--------|-------------|----------|
| A | `PerformanceTierSnapshot` 一行/年, `tiers_json` 完整映射 | ✓ |
| B | 拆两表 `Snapshot` + `Assignment`，per-employee 一行（便于 SQL JOIN） | |
| C | 仅 meta 不存 tiers，每次查询都重算 | |

**User's choice:** A
**Rationale:** 一行/年简化迁移与查询；tiers_json 单一访问入口避免 N+1；员工查档次属 Phase 35 范围（届时可读 JSON 或加索引列）

### Q1.2 — Redis 缓存 TTL

| Option | Description | Selected |
|--------|-------------|----------|
| A | 长 TTL (24h) + 写穿透（重算后立即写新值，导入后 invalidate） | ✓ |
| B | 短 TTL (5min) 自然过期重算 | |
| C | 不用 Redis，直接读快照表 | |

**User's choice:** A
**Rationale:** HR 查询频率高 + 数据变更可控（仅 import + 手动重算两个入口），写穿透+长 TTL 最优

---

## Area 2: 重算触发同步性

### Q2.1 — 同步重算阻塞预算

| Option | Description | Selected |
|--------|-------------|----------|
| A | confirm 同步阻塞最长 5 秒，超时 → 202 + 后台继续 | ✓ |
| B | 严格同步无超时（必等到重算完成才返回） | |
| C | 完全异步，HR 端轮询 | |

**User's choice:** A
**Rationale:** 5 秒兜底防超时雪崩，但典型 < 200ms 同步完成；保留 202 路径不堵塞 import 主链路

### Q2.2 — 重算失败处理

| Option | Description | Selected |
|--------|-------------|----------|
| A | 不阻塞 import 落库，老快照保留，UI 显示「档次基于旧快照（重算失败，请重试）」 | ✓ |
| B | 重算失败回滚 import（数据一致性优先） | |

**User's choice:** A
**Rationale:** 数据可用性 > 快照新鲜度；HR 仍可看到老档次 + 触发手动重算

---

## Area 3: 重算并发控制

### Q3.1 — 锁机制实现

| Option | Description | Selected |
|--------|-------------|----------|
| A | `SELECT ... FOR UPDATE NOWAIT` 在 PerformanceTierSnapshot.year 行锁，竞争方 409 + retry_after | ✓ |
| B | Redis distributed lock + 30s 过期 | |
| C | 进程级 threading.Lock | |

**User's choice:** A
**Rationale:** DB 行锁与事务一致性绑定；NOWAIT 避免阻塞链路；与 Phase 32 per-import_type 锁风格统一

### Q3.2 — 自动 vs 手动优先级

| Option | Description | Selected |
|--------|-------------|----------|
| A | 先到先得无优先级，竞争方 409 | ✓ |
| B | 手动优先（自动检测到手动锁直接 skip） | |
| C | 自动优先（手动收 409） | |

**User's choice:** A
**Rationale:** 简单可预测；自动重算 idempotent，下次 import 还会触发，手动同样可重试

---

## Area 4: department_snapshot 回填

### Q4.1 — Migration 与字段约束

| Option | Description | Selected |
|--------|-------------|----------|
| A | nullable=True，存量 NULL，UI 显示「—」 | ✓ |
| B | 立即跑数据回填脚本按 employee.department 当前值回填 | |
| C | default='' 空字符串 | |

**User's choice:** A
**Rationale:** 按当前部门回填会注入虚假快照（员工可能已换部门），违反「snapshot」语义；NULL 显式表达「未知」

### Q4.2 — 写入时机

| Option | Description | Selected |
|--------|-------------|----------|
| A | Service create/import 时显式取 employee.department 当时值 | ✓ |
| B | SQLAlchemy event listener 自动从关系拉取 | |
| C | 要求 caller 显式传 department_snapshot 参数 | |

**User's choice:** A
**Rationale:** 显式 > 隐式；Service 层逻辑可见可测；不污染调用方接口

---

## Area 5: `/tier-summary` 响应形态

### Q5.1 — 响应字段

| Option | Description | Selected |
|--------|-------------|----------|
| A | 平铺 9 字段（year, computed_at, sample_size, insufficient_sample, distribution_warning, tiers_count, actual_distribution, skipped_invalid_grades） | ✓ |
| B | 分两层 meta + distribution 嵌套 | |
| C | 精简版 + /tier-summary/detail 子端点 | |

**User's choice:** A
**Rationale:** 单次请求拿全所需，前端无需嵌套解构；字段平铺利于 OpenAPI 文档清晰

### Q5.2 — 无快照响应

| Option | Description | Selected |
|--------|-------------|----------|
| A | 404 + hint POST /recompute-tiers | ✓ |
| B | 200 + 全空白结构 | |
| C | 自动触发同步重算后返回 | |

**User's choice:** A
**Rationale:** 404 语义明确；hint 引导 HR 显式触发重算，避免隐式 5 秒等待

---

## Area 6: 「档次分布视图」UI 形态

### Q6.1 — 主视觉元素

| Option | Description | Selected |
|--------|-------------|----------|
| A | 3 段水平堆叠条 + chip + warning 横幅 + 重算按钮带 computed_at | ✓ |
| B | 饼图 + chip + warning + 重算按钮 | |
| C | 纯表格 + warning + 重算按钮 | |

**User's choice:** A
**Rationale:** 堆叠条比例直观；chip 提供精确数字；warning 横幅突出异常；computed_at 让 HR 看到快照新鲜度

### Q6.2 — 年份切换

| Option | Description | Selected |
|--------|-------------|----------|
| A | select 下拉 + 默认当前年 + 无快照「立即生成」按钮 | ✓ |
| B | 固定显示最新年份 | |
| C | 年份 tab 横向 | |

**User's choice:** A
**Rationale:** select 占用空间小；「立即生成」按钮覆盖首次使用场景

---

## Area 7: 页面信息架构

### Q7.1 — 三 section 排序

| Option | Description | Selected |
|--------|-------------|----------|
| A | 顶部分布视图 → 中部导入 → 底部列表 | ✓ |
| B | 顶部导入 → 中部分布 → 底部列表 | |
| C | 顶部列表 → 中部分布 → 底部导入 | |

**User's choice:** A
**Rationale:** 全局 → 操作 → 明细的信息流顺序符合 HR 浏览习惯

### Q7.2 — 列表表格

| Option | Description | Selected |
|--------|-------------|----------|
| A | 7 列 + 50/page + 年份+部门 filter | ✓ |
| B | 精简列 + 详情抽屉 | |
| C | 入口跳子页（Phase 36） | |

**User's choice:** A
**Rationale:** 7 列覆盖 HR 日常需要；50/page 平衡加载与浏览

---

## Area 8: 路由命名与 API 前缀

### Q8.1 — 端点结构

| Option | Description | Selected |
|--------|-------------|----------|
| A | `/api/v1/performance/{records,tier-summary,recompute-tiers}` + 复用 eligibility-import + me/tier 留位 | ✓ |
| B | 完全独立 `/api/v1/performance/import/*` | |
| C | `/api/v1/performance-management/*` | |

**User's choice:** A
**Rationale:** 复用 Phase 32 import 设施零成本；命名简洁与 ROADMAP 一致

### Q8.2 — 前端路由 + 菜单 label

| Option | Description | Selected |
|--------|-------------|----------|
| A | `/performance` + 「绩效管理」label + admin/hrbp | ✓ |
| B | `/performance-management` 同 A | |
| C | `/performance` + 「绩效中心」label | |

**User's choice:** A
**Rationale:** 与 ROADMAP SC-1 「绩效管理」表述一致

---

## Claude's Discretion

- 列表表格行高/表头样式（参照 EligibilityBatchTable）
- 重算按钮 loading 图标（lucide-react RefreshCw）
- Recharts 堆叠条高度（推荐 32px）
- 年份 select 在历史无 records 时的 fallback
- Service 层异常类命名

## Deferred Ideas

- 员工端档次徽章 / `/performance/me/tier` → Phase 35
- 历史绩效跨页面展示 → Phase 36
- 多年时间序列趋势 → Phase 36
- 存量回填脚本（D-07 显式不做）
- 绩效全套评审流程 → 远期
- Celery 异步重算队列（本期同步 5s 足够）
- 行点击跳详情子页 → Phase 36
- 批量手动新增绩效（用 Excel 即可）
- /records/{id} update/delete 端点（待真实需求）
