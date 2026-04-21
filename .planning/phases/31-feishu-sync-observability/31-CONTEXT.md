# Phase 31: 飞书同步可观测性 - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

让 HR 在独立的「同步日志」页面看到每次飞书同步（五种 sync_type：attendance / performance / salary_adjustments / hire_info / non_statutory_leave）的五类计数器 `{success, updated, unmatched, mapping_failed, failed}`，消除「飞书 API 返回 200 但数据未落库」的诊断盲点。`sync_performance_records / sync_salary_adjustments / sync_hire_info / sync_non_statutory_leave` 四个方法从「仅返回 dict」升级为「写入 FeishuSyncLog」；`sync_attendance` 一同迁移到新 `sync_type + partial` 语义；顶层 status 按 `unmatched+mapping_failed+failed>0 则 partial` 派生；`is_sync_running()` 升级为 per-sync_type 分桶锁；前端新增 `/feishu/sync-logs` 路由页面（admin+hrbp）用 Tab 切分五类 + 五色 badge 展示计数 + 每行 Action 列 CSV 下载。

**Not in scope:**
- 独立 `MetricEvent` 表 / Prometheus / 全局可观测基础设施（v1.5+）
- `ImportService.ImportJob` 的导入日志观测（Phase 32 范畴）
- 导入/同步统一告警推送 / 邮件通知（v1.5+）
- request_id 去重机制（本期 409 锁足够）
- 按百分比阈值（>=50% 失败转 failed）的 partial 派生规则变体（硬切即可）

</domain>

<decisions>
## Implementation Decisions

### 模型扩展（FeishuSyncLog schema）
- **D-01:** 新增 `sync_type: str` 列（NOT NULL），枚举值 `attendance / performance / salary_adjustments / hire_info / non_statutory_leave`，命名与 `feishu_sync_eligibility_task` 的 `sync_type` 参数一致（注意 Celery task 目前 key 名是 `performance_grades`，迁移时统一改为 `performance`，避免双命名）
- **D-02:** 新增 `mapping_failed_count: int` 列（NOT NULL DEFAULT 0），专表「字段类型/格式转换失败」（如 year 无法 `int(float(...))`、grade 不在枚举、adjustment_date 解析失败等）；`skipped_count` 语义收紧为「业务跳过」（如源数据 source_modified_at 更早、无有效字段更新）
- **D-03:** Alembic 迁移用 `op.batch_alter_table` 单次加两列：先 `add_column(sync_type, nullable=True)` → `UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL` → `alter_column(nullable=False)`；`mapping_failed_count` 直接加 `DEFAULT 0 NOT NULL`（SQLite 兼容）
- **D-04:** 保留 `mode` 列不动，语义仍为 `full / incremental`（对 `sync_attendance` 有意义）；四个新 sync_type 方法写入时固定 `mode='full'`；前端列表展示 mode 列时仅对 `sync_type='attendance'` 显示，其他隐藏

### 同步日志页面 UI 形态
- **D-05:** 新增独立前端路由 `/feishu/sync-logs`（对应 `SyncLogsPage.tsx`），`admin + hrbp` 可见；导航菜单新增「同步日志」入口，挂在既有「飞书集成」分组下；`employee / manager` 角色看不到
- **D-06:** 页面顶部 Tab 切换：`全部 / 考勤 / 绩效 / 薪调 / 入职信息 / 社保假勤`，Tab 选中决定 `GET /feishu/sync-logs?sync_type=...&page=&page_size=` 的查询参数；默认 page_size=20，支持分页（Phase 31 不引入游标分页，offset 即可）
- **D-07:** 每行用五色分段 badge 团展示 `{success, updated, unmatched, mapping_failed, failed}`：绿=success, 蓝=updated, 橙=unmatched, 紫=mapping_failed, 红=failed；badge 数值为 0 时置灰弱化；点击任一 badge 展开详情抽屉（抽屉含 error_message、unmatched_employee_nos 全量列表、leading_zero_fallback_count 黄字提示）
- **D-08:** 每行右侧 Action 列放「下载未匹配工号 CSV」按钮，仅当 `unmatched_count > 0` 时启用。CSV 单列 `employee_no`、前 20 行（`unmatched_employee_nos[:20]`）、文件名格式 `sync-log-{log_id}-unmatched.csv`；下载走 `GET /feishu/sync-logs/{log_id}/unmatched.csv` 返回 `text/csv; charset=utf-8`，权限 `admin+hrbp`
- **D-09:** 顶层 status 展示 4 色 badge：`success=绿 / partial=橙 / failed=红 / running=蓝带 spinner`；`rejected` 状态不写日志（D-15），因此 UI 不显示

### 写入日志的代码落地
- **D-10:** 新增 helper `FeishuService._with_sync_log(self, sync_type: str, fn: Callable, *args, triggered_by=None, **kwargs) -> FeishuSyncLog`：内部 (1) 用独立 `SessionLocal()` session 创建 `status='running'` 的 FeishuSyncLog 并 commit → (2) 调用 `fn(sync_log_id=log.id, ...)` 业务函数（业务函数用 `self.db` 完成 upsert 并 commit）→ (3) 用独立 session 写终态 counters + 派生 status → commit；(4) 业务 fn 抛异常时用独立 session 写 `status='failed'` + `error_message`（沿用 `sync_attendance` 既定模式）
- **D-11:** 定义内部 dataclass `_SyncCounters(success: int, updated: int, unmatched: int, mapping_failed: int, failed: int, leading_zero_fallback: int, total_fetched: int, unmatched_nos: list[str])`；四个 sync_xxx 业务方法改造为返回 `_SyncCounters` 实例；helper 按 dataclass 字段一一填入 FeishuSyncLog，避免 dict key 拼写错误
- **D-12:** `sync_attendance` 也重构到 `_with_sync_log('attendance', ...)` 模式，删除内部手写 FeishuSyncLog 创建/终态代码；向后兼容 mode='full'/'incremental' 语义；现有 `sync_with_retry` 调 `sync_attendance` 的路径保持不变（只是 `sync_attendance` 内部委托到 helper）
- **D-13:** FeishuSyncLog commit 事务与业务 upsert 事务分离：业务 rollback 不会连带 log 回滚，确保「同步失败」能被观测到；独立 session 写 log 终态的 try/except 内部打 `logger.exception` 但不再抛出（避免掩盖业务异常）

### partial 状态与并发触发语义
- **D-14:** `status` 派生规则（硬切）：running 结束时若 `unmatched + mapping_failed + failed > 0` → `status='partial'`；否则 → `status='success'`。业务 fn 抛异常 → `status='failed'`。无百分比阈值，无「全员失败转 failed」额外规则
- **D-15:** `is_sync_running(sync_type: str | None = None)` 升级为 per-sync_type 分桶锁：传 sync_type 时仅查该 type 的 `status='running'` 记录；不传时查所有 running（保留兼容性）。同 sync_type 第二次触发返回 409；不同 sync_type 可并行（`sync_performance` 和 `sync_hire_info` 可同时跑）
- **D-16:** 409 冲突**不写** FeishuSyncLog（避免 `status='rejected'` 污染数据库）：接口直接返回 `{error: 'sync_in_progress', sync_type, message}`；前端按 sync_type 展示「该类型同步正在进行中」提示。SC4 的「两条独立记录」语义解释为：锁释放后的第二次点击正常触发并写入第二条 log（而非 409 也写日志）
- **D-17:** `expire_stale_running_logs(timeout_minutes=30)` 保留现有语义，对所有 sync_type 统一生效；`trigger_sync` / 四个新 Celery task 入口统一先调 `expire_stale_running_logs` 再检查 `is_sync_running(sync_type)`

### Claude's Discretion
- Alembic 迁移文件名 / revision id
- `_SyncCounters` 具体字段顺序 / dataclass 是否加 `@dataclass(frozen=True)`
- `/feishu/sync-logs` 前端页面的具体配色与 badge 视觉语言（沿用现有 Tailwind + var(--color-*) design token 即可）
- `SyncLogsPage.tsx` 是否拆分子组件（如 `SyncLogRow`, `CountersBadgeCluster`, `SyncLogDetailDrawer`）
- Celery task 内部捕获 `HTTPException(409)` 的 idempotent 行为（task 应 retry 还是直接标 failed）
- 旧 Celery task `feishu_sync_eligibility_task` 的 `performance_grades` → `performance` 过渡期兼容策略（可加一次性 alias dict）
- 前端 Tab 中文标签细节文案

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 本阶段需求与上游决策
- `.planning/ROADMAP.md` §"Phase 31: 飞书同步可观测性" — 4 条 Success Criteria
- `.planning/REQUIREMENTS.md` §"调薪资格导入修复（IMPORT）" — IMPORT-03 / IMPORT-04 原始定义
- `.planning/phases/30-employee-no-leading-zero/30-CONTEXT.md` — Phase 30 关于 `leading_zero_fallback_count` 已落地字段与容忍匹配计数器的前置决策（D-03 / D-04）

### 代码集成点
- `backend/app/models/feishu_sync_log.py` — FeishuSyncLog 模型（D-01/D-02/D-03 改动点）
- `backend/app/services/feishu_service.py:321-491` — `sync_attendance` 既定 running log / failed log 模式（D-10/D-12 参考实现）
- `backend/app/services/feishu_service.py:497-600` — `sync_performance_records`（D-10/D-11 改造目标）
- `backend/app/services/feishu_service.py:606-718` — `sync_salary_adjustments`（D-10/D-11 改造目标）
- `backend/app/services/feishu_service.py:724-817` — `sync_hire_info`（D-10/D-11 改造目标）
- `backend/app/services/feishu_service.py:823-927` — `sync_non_statutory_leave`（D-10/D-11 改造目标）
- `backend/app/services/feishu_service.py:1301-1326` — `is_sync_running` + `expire_stale_running_logs`（D-15/D-17 改动点）
- `backend/app/tasks/feishu_sync_tasks.py` — `feishu_sync_eligibility_task`（sync_type key 名统一、409 处理）
- `backend/app/api/v1/feishu.py:189-251` — `trigger_sync / get_sync_logs / get_sync_status` 路由（D-05/D-06/D-08/D-16 扩展点）
- `backend/app/schemas/feishu.py:67-86` — `SyncLogRead` schema（D-01/D-02 字段扩展 + partial status 枚举）
- `frontend/src/components/attendance/SyncStatusCard.tsx` — 既有五色 badge 视觉参考
- `frontend/src/pages/AttendanceManagement.tsx` — 既有 `SyncLogRead` 消费方式（轮询、CSV、status 映射）
- `frontend/src/services/feishuService.ts:35-45` — `getSyncLogs / getLatestSyncStatus` 前端接口
- `frontend/src/types/api.ts:781-797` — `SyncLogRead` 类型定义（D-01/D-02 字段扩展 + status 'partial' 枚举）

### 既定模式参考
- `.planning/codebase/CONVENTIONS.md` — Pydantic v2、`from __future__ import annotations`、keyword-only 参数
- `.planning/codebase/ARCHITECTURE.md` — `api/ → services/ → engines/ → models/` 分层方向
- `.planning/codebase/TESTING.md` — pytest 单元测试与 helper 测试模式
- `.planning/research/PITFALLS.md` — Pitfall 16（Alembic batch_alter_table 的 SQLite 兼容）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FeishuSyncLog` 模型 — 大部分字段已就绪（total_fetched/synced_count/updated_count/skipped_count/unmatched_count/failed_count/leading_zero_fallback_count/error_message/unmatched_employee_nos），Phase 31 只加 `sync_type` + `mapping_failed_count` 两列
- `sync_attendance` 的 running log / 独立 session failed log 模式 — D-10/D-12 直接复用
- `_lookup_employee` + `fallback_counter` dict — 四方法已按 Phase 30 模式接入，无需再动
- `SyncStatusCard.tsx` 的五色 badge 视觉语言 — 可抽离为 `CountersBadgeCluster` 组件复用到 `/feishu/sync-logs` 页面
- `expire_stale_running_logs(timeout_minutes=30)` — 僵死日志清理机制已有，D-17 沿用
- `unmatched_employee_nos` 字段（Text JSON）— 已保存前 100 条，D-08 CSV 只取前 20

### Established Patterns
- Alembic `op.batch_alter_table` + backfill 两阶段迁移 — Phase 30/v1.0 起既定
- `_with_X_session` / 独立 session 写终态 log 的模式 — sync_attendance 既定
- 业务方法返回 dict 供 Celery task 转发 state 更新 — `feishu_sync_eligibility_task` 既定（D-11 升级到 dataclass 时 Celery update_state 需同步改 `counters.asdict()`）
- 前端 `SyncLogRead` 轮询 5s 间隔 — AttendanceManagement 既定模式
- `require_roles('admin', 'hrbp')` 角色门控 — 新路由沿用

### Integration Points
- **Alembic 迁移** — `alembic/versions/` 新加 revision，走 `op.batch_alter_table`，与 Phase 30 的 leading_zero_fallback_count 迁移是同一张表的后续变更
- **FeishuService._with_sync_log** — 新方法，位于 `sync_attendance` 之上作为共用基础设施
- **`feishu_sync_eligibility_task` 接口** — sync_type key 名统一（`performance_grades` → `performance`）需前端导入页面 / 后端 Celery 入口同步改
- **前端路由注册** — `frontend/src/App.tsx` 新增 `<Route path="/feishu/sync-logs" element={<SyncLogsPage/>}/>`
- **前端导航菜单** — `frontend/src/components/layout/` 下 nav 组件新增「同步日志」项，`admin+hrbp` 可见
- **`SyncLogRead` 类型** — `frontend/src/types/api.ts` 增加 `sync_type`、`mapping_failed_count` 字段；`status` 枚举加 `'partial'`
- **CSV 导出端点** — `/feishu/sync-logs/{log_id}/unmatched.csv` 新增 GET 路由，返回 `StreamingResponse` 或 `Response(content=..., media_type='text/csv')`

</code_context>

<specifics>
## Specific Ideas

- HR 在同一页面同时看到 Phase 30 的 `leading_zero_fallback_count` 黄字提示（已在 SyncStatusCard 实现）与 Phase 31 的五类计数器 — 保持视觉一致
- 五色 badge 配色参考现有 `SyncStatusCard` 的 `var(--color-success, #00B42A)` / `var(--color-warning, #FF7D00)` / `var(--color-danger, #F53F3F)` token，紫色可新增 `var(--color-violet, #722ED1)` 作 mapping_failed 专属色，蓝色复用 `var(--color-info, #1456F0)` 作 updated
- Tab 顺序按业务优先级：`全部 / 考勤 / 绩效 / 薪调 / 入职信息 / 社保假勤`（绩效优先于薪调，与 v1.4 milestone 的「绩效导入链路」主旋律一致）
- 同 sync_type 分桶锁是 per-sync_type 行级而非全局 — HR 可同时触发「绩效」和「入职信息」同步，不互阻

</specifics>

<deferred>
## Deferred Ideas

- 基于 request_id 的去重幂等（比 sync_type 锁更严格）— v1.5+，当前锁够用
- 409 被拒事件写 `status='rejected'` 日志 — 会产生数据库噪声，HR 价值有限
- 按百分比阈值派生 failed vs partial（>=50% 失败转 failed）— 硬切规则够用
- CSV 多列（employee_no + 失败原因 + 行号）— 仅工号即可让 HR 去飞书源表格查
- 一键导出「近 30 天所有未匹配」聚合 CSV — HR 可按日志逐条下载合并
- 顶部聚合 KPI 横幅（今日同步失败总数 / 周趋势图）— v1.5+ 独立观测面板
- mode 列彻底删除或扩展为 manual/scheduled — Phase 31 不触碰
- sync_attendance 的 skipped_count 语义重新分类到 mapping_failed — 风险大，等实战数据验证
- 日志保留期 / 定时清理（例如 90 天前自动归档）— 当前表不大，v1.5+ 再看

</deferred>

---

*Phase: 31-feishu-sync-observability*
*Context gathered: 2026-04-21*
