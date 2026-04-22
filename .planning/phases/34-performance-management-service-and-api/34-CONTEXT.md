# Phase 34: 绩效管理服务与 API - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

为 HR/admin 提供独立「绩效管理」页面（列表 + 导入 + 档次分布视图）+ `/api/v1/performance/*` REST API + 档次快照表 + Redis 缓存 + 导入回调自动重算 + 手动重算覆盖。

**严格不在范围：**
- 员工端档次徽章 / `/performance/me/tier` 实际实现 → Phase 35（仅声明保留位）
- 历史绩效跨页面展示（评估详情 / 调薪建议详情）→ Phase 36
- 全套绩效评审流程（评分轮次 / 反馈 / 校准）→ 远期 deferred
- 多年时间序列趋势视图 → Phase 36 范围
- 部门 snapshot 存量回填脚本 → 显式不做（D-07：存量行 NULL，UI「—」）

</domain>

<decisions>
## Implementation Decisions

### Area 1 — 档次持久化形态

- **D-01:** 新增 SQLAlchemy 模型 `PerformanceTierSnapshot`（`backend/app/models/performance_tier_snapshot.py`），表结构：
  - `id` (UUID PK, 复用 `UUIDPrimaryKeyMixin`)
  - `year: int` (UNIQUE, 一行/年)
  - `computed_at: datetime` (UTC, `CreatedAtMixin` + `UpdatedAtMixin`)
  - `tiers_json: dict[str, int | None]` (SQLAlchemy `JSON` 类型) — `{employee_id: 1|2|3|null}` 完整映射
  - `sample_size: int`
  - `insufficient_sample: bool`
  - `distribution_warning: bool`
  - `actual_distribution_json: dict[int, float]` (`JSON`) — `{1: 0.22, 2: 0.68, 3: 0.10}`
  - `skipped_invalid_grades: int`
  - Alembic migration: `add_performance_tier_snapshot_table`
- **D-02:** Redis 缓存 key `tier_summary:{year}` + TTL 24 小时 + 写穿透策略：
  - `recompute_tiers(year)` 成功后立即 `redis.set(key, json, ex=86400)`
  - `import confirm` 触发 `invalidate_tier_cache(year)` → `redis.delete(key)` + 后续 confirm 同步重算阶段 set 新值
  - 读路径 `get_tier_summary(year)`：先查 Redis → miss 查表 → 回填 Redis → 返回；表也 miss 时返回 None（路由层转 404）

### Area 2 — 重算触发同步性

- **D-03:** Import confirm 接口同步阻塞重算，最长 5 秒：
  - 落库后调 `recompute_tiers(year)` 同步执行
  - 5 秒未完成 → confirm 返回 `202 Accepted` + body `{ status: 'import_committed', tier_recompute: 'in_progress', hint: 'GET /tier-summary?year=X 轮询 computed_at' }`
  - 5 秒完成 → 正常 200 含 `tier_recompute_completed_at`
  - 后台继续完成的重算（async future / threadpool 落库）— 单年员工 < 5000 时引擎计算 < 200ms，5 秒余量充分
- **D-04:** 重算失败不阻塞 import 落库（数据可用性优先）：
  - Import 已成功（rows committed） + 重算异常 → 写日志 `tier_recompute_error` + 保留旧快照 + Redis cache 不动
  - HR UI 通过 `/tier-summary` 看到 `computed_at` 仍为旧时间，UI 顶部黄色横幅显示「档次基于 YYYY 年 M 月 D 日 HH:MM 旧快照（重算失败，请重试）」+ 「立即重算」按钮调 `POST /recompute-tiers?year=X`

### Area 3 — 重算并发控制

- **D-05:** `recompute_tiers(year)` Service 方法用 `SELECT id FROM performance_tier_snapshots WHERE year=:year FOR UPDATE NOWAIT`：
  - 拿到锁 → 重算 → UPDATE / INSERT 快照 + write Redis → COMMIT 释放锁
  - `NOWAIT` 失败（其他事务持锁中）→ 抛 `TierRecomputeBusyError` → API 层转 `409 Conflict { error: 'tier_recompute_busy', message: '该年度档次正在重算，请稍后重试', retry_after_seconds: 5 }`
  - 若该年度 snapshot 行尚不存在（首次）→ Service 用 `INSERT ... ON CONFLICT DO NOTHING` 先建空行，再走 FOR UPDATE
- **D-06:** 自动 vs 手动无优先级，先到先得：
  - HR 手动调 `POST /recompute-tiers?year=X` 撞上自动重算 → 收 409，UI 提示「系统正在自动重算，请稍后重试」+ 5 秒后启用按钮
  - 自动重算撞上手动 → import confirm 路径捕获 `TierRecomputeBusyError`，返回 202 含 `tier_recompute: 'busy_skipped'` + hint「HR 手动重算已启动，无需再次触发」

### Area 4 — department_snapshot 字段（PERF-08）

- **D-07:** Alembic migration `add_department_snapshot_to_performance_records` 添加：
  - `department_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)`
  - 存量行不回填，保持 NULL；UI 渲染时 NULL → 显示「—」
  - migration 里 NOT 跑数据回填脚本（按当前部门回填会引入虚假数据，违反「快照」语义）
- **D-08:** `PerformanceService.create_record()` 与 `PerformanceService.import_records()` 在写入时取值：
  - 从 `employee.department`（已 join load）当时值赋给 `department_snapshot`
  - `employee.department` 为 NULL 时 → 快照也写 NULL（不抛异常）
  - 实现位置：Service 层显式赋值，**不**用 SQLAlchemy event listener（避免隐式行为），**不**要求 caller 显式传参（Service 自动从 employee 关系拉）

### Area 5 — `/tier-summary` 响应形态

- **D-09:** 平铺 9 字段响应（Pydantic schema `TierSummaryResponse`）：
  ```json
  {
    "year": 2026,
    "computed_at": "2026-04-22T10:30:00Z",
    "sample_size": 1234,
    "insufficient_sample": false,
    "distribution_warning": false,
    "tiers_count": {"1": 247, "2": 864, "3": 123, "none": 0},
    "actual_distribution": {"1": 0.20, "2": 0.70, "3": 0.10},
    "skipped_invalid_grades": 0
  }
  ```
  - `tiers_count` 含 `none` 键（未分档人数 = `sample_size - sum(1+2+3)`），便于 UI 显示「未分档：N 人」
  - `actual_distribution` 仅含 1/2/3（与 Phase 33 D-04 一致）
- **D-10:** 无快照时返回 `404 Not Found`：
  ```json
  {
    "error": "no_snapshot",
    "message": "该年度尚无档次快照",
    "year": 2026,
    "hint": "POST /api/v1/performance/recompute-tiers?year=2026 触发重算"
  }
  ```
  - **不**自动触发同步重算（避免隐式 5 秒等待）
  - UI 收 404 时显示「该年度尚无档次快照」+ 「立即生成档次」按钮调 `POST /recompute-tiers?year=X`

### Area 6 — 「档次分布视图」UI 形态

- **D-11:** 视觉组成（顶部到底部）：
  1. **黄色 warning 横幅**（条件渲染：`distribution_warning === true` 时显示）— 文本「档次分布偏离 20/70/10 超过 ±5%（实际 22%/68%/10%）」
  2. **3 段水平堆叠条**（Recharts `<BarChart layout="vertical">` 单条堆叠）— 1 档绿 `#10b981` / 2 档黄 `#f59e0b` / 3 档红 `#ef4444`，按 `actual_distribution` 比例，宽 100%
  3. **三档计数 chip 行**（横向 flex）— 「1 档 247 人 (20%)」「2 档 864 人 (70%)」「3 档 123 人 (10%)」「未分档 0 人」
  4. **「重算档次」按钮**（右上角）— 显示「最近重算：2026-04-22 18:30」zh-CN locale，点击调 `POST /recompute-tiers?year=X`，loading 时禁用 + 旋转图标
- **D-12:** 年份切换：
  - `<select>` 下拉，选项来自 `SELECT DISTINCT year FROM performance_records ORDER BY year DESC`，默认当前年（`new Date().getFullYear()`）
  - 切换 → 调 `GET /tier-summary?year=X`
  - 收 404 → 显示空状态「该年度尚无档次快照」+ 「立即生成档次」按钮（触发 `POST /recompute-tiers?year=X` 后重新拉 summary）

### Area 7 — 页面信息架构

- **D-13:** 单页 3 section 垂直排列（`PerformanceManagementPage.tsx`）：
  1. **顶部「档次分布视图」section** — D-11/D-12 全部内容
  2. **中部「绩效记录导入」section** — 复用 `<ExcelImportPanel import_type="performance_grades">`（Phase 32 已交付，零额外开发）
  3. **底部「绩效记录列表」section** — D-14 列表表格
- **D-14:** 列表表格 7 列（按推荐 A）：
  - 员工工号 / 姓名 / 年份 / 绩效等级 / 部门快照（NULL → 「—」）/ 来源（manual / excel / feishu）/ 录入时间（zh-CN format）
  - 分页 50 条/页
  - Filter 控件（表格上方）：年份 select + 部门 select（部门列表来自 `SELECT DISTINCT department FROM employees`）
  - 暂不实现：行点击跳详情（Phase 36 范围）

### Area 8 — 路由命名与 API 前缀

- **D-15:** 后端端点（新建 `backend/app/api/v1/performance.py`）：
  - `GET  /api/v1/performance/records?year=X&department=Y&page=N&page_size=50` — 列表（admin/hrbp）
  - `POST /api/v1/performance/records` — 单条新增（admin/hrbp，body 含 employee_id/year/grade/source；Service 自动写 department_snapshot）
  - `GET  /api/v1/performance/tier-summary?year=X` — 单年快照（admin/hrbp）
  - `POST /api/v1/performance/recompute-tiers?year=X` — 手动重算（admin/hrbp）
  - **保留位但不实现**：`GET /api/v1/performance/me/tier` — 路由文件中 `# TODO Phase 35` 标记，本期不挂 handler
  - **导入复用**：HR 在前端 `<ExcelImportPanel import_type="performance_grades">` 调用现有 `/api/v1/eligibility-import/excel/preview` + `/confirm`（不另起 `/performance/import` 端点，避免分叉）
  - 导入 confirm 成功后 import_service 调用新 hook `PerformanceService.invalidate_tier_cache(year)` + 同步 `recompute_tiers(year)`（D-03/D-05 路径）
- **D-16:** 前端：
  - 路由 `/performance` (`<Route path="/performance" element={<PerformanceManagementPage />} />`)
  - 菜单 label 「绩效管理」
  - `roleAccess.ts` 限制 `admin` + `hrbp` 可见可访问；employee/manager 菜单 hidden + URL 直访由后端 `require_roles(['admin', 'hrbp'])` 兜底返回 403

### Claude's Discretion

- 列表表格的具体行高 / 表头样式（参照 `EligibilityBatchTable` 风格）
- 「重算档次」按钮 loading 动画图标（`<RefreshCw>` lucide-react 已用即复用）
- Recharts 堆叠条的高度（推荐 32px）、tooltip 是否显示
- 年份 select 在历史无 performance_records 时的 fallback（推荐：当前年单选 + disabled）
- Service 层异常类的命名（`TierRecomputeBusyError` / `TierRecomputeFailedError` 等）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 33 Engine 接口（必读）
- `backend/app/engines/performance_tier_engine.py` — `PerformanceTierEngine.assign(emp_grade_list)` 输入输出契约
- `backend/app/engines/__init__.py` — top-level exports (`PerformanceTierEngine`, `PerformanceTierConfig`, `TierAssignmentResult`)
- `.planning/phases/33-performance-tier-engine/33-CONTEXT.md` § decisions D-01..D-11 — 引擎行为契约（ties 算法 / 样本不足 / distribution_warning）

### Phase 32 复用基础设施（必读）
- `backend/app/services/import_service.py` — `import_type='performance_grades'` 已支持（lines 56-66 REQUIRED_COLUMNS）；preview/confirm/cancel 流程
- `backend/app/api/v1/eligibility_import.py` — `/excel/preview` + `/excel/{job_id}/confirm` + `/excel/{job_id}/cancel` + `/templates/{import_type}` 端点（前端 `import_type=performance_grades` 直接复用）
- `backend/app/schemas/import_preview.py` — `PreviewCounters`、`PreviewResponse` schema 复用
- `frontend/src/components/eligibility-import/` — 6 子组件 + `ImportPreviewPanel`、`ExcelImportPanel`（Phase 32 CONTEXT 明确写「下游可复用」）
- `.planning/phases/32-eligibility-import-completion/` — Phase 32 CONTEXT.md / SUMMARY.md（导入流细节 + 已知 a11y minor defect 列表）

### 现有相邻代码
- `backend/app/models/performance_record.py` — 当前 5 字段（employee_id / employee_no / year / grade / source），Phase 34 + `department_snapshot`
- `backend/app/services/eligibility_service.py` — Service 风格参考（Settings 注入、`require_roles` 调用模式、SQLAlchemy 查询惯例）
- `backend/app/api/v1/eligibility.py` — API router 风格参考（response_model、依赖注入、HTTPException 错误处理）
- `frontend/src/pages/EligibilityManagementPage.tsx` — HR 独立页面参考（页面布局、AppShell 引用、roleAccess 检查）
- `frontend/src/utils/roleAccess.ts` — 路由角色限制配置位置

### 需求与目标
- `.planning/REQUIREMENTS.md` line 20-27 — PERF-01/02/05/08 原文
- `.planning/ROADMAP.md` line 179-189 — Phase 34 Goal + 5 个 Success Criteria
- `CLAUDE.md` — 项目编码规范（Service 层职责、Pydantic schema、role-based access、Alembic 唯一 migration 路径、`from __future__ import annotations`）

### Codebase 维度
- `.planning/codebase/CONVENTIONS.md` — 命名 / 类型注解 / import 顺序约定
- `.planning/codebase/TESTING.md` — pytest 组织模式（Service 层 + API 层测试结构）
- `.planning/codebase/STRUCTURE.md` — backend 分层（api / services / engines / models / schemas）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PerformanceTierEngine` (Phase 33 交付)** — 核心档次计算，`PerformanceService.recompute_tiers(year)` 直接调
- **`ImportService` (Phase 32 交付)** — 已支持 `import_type='performance_grades'`，preview/confirm 全套，Phase 34 仅在 confirm 成功 hook 处加调用 `PerformanceService.invalidate_tier_cache(year)` + `recompute_tiers(year)`
- **`<ExcelImportPanel>` (Phase 32 交付)** — 7-state union 组件 + 6 子组件，导入 section 直接 `<ExcelImportPanel import_type="performance_grades" />` 即可
- **`<EligibilityBatchTable>` 风格** — 列表表格视觉/分页/filter pattern 复用
- **Redis 客户端** — Phase 19 Celery 基建已配置，`backend/app/core/redis_client.py`（如存在）或新建 helper
- **`require_roles(['admin', 'hrbp'])` 依赖** — `backend/app/dependencies.py` 现成
- **`AccessScopeService`** — admin 全见、hrbp 全见、manager/employee 无访问 — Phase 34 简单沿用 `require_roles` 即可（无需 per-row 过滤）

### Established Patterns
- **`from __future__ import annotations` 必须在所有后端模块顶部** — CLAUDE.md 强制
- **PEP 604 union 语法**（`int | None` 而非 `Optional[int]`）
- **Service 层不抛 raw `Exception`** — 用自定义异常类（如 `TierRecomputeBusyError`），API 层 catch → HTTPException
- **Alembic 唯一 migration 路径** — 禁止用 `Base.metadata.create_all`，必须 `alembic revision --autogenerate`
- **Pydantic v2 `BaseModel` + `ConfigDict(from_attributes=True)`** — Service 返回 ORM 对象，API 层经 Pydantic 序列化
- **`@lru_cache` 装饰 `get_settings()` 注入 Settings** — 单测便于覆盖

### Integration Points
- **`backend/app/api/v1/__init__.py` (或 main.py)** — 注册新 router `from backend.app.api.v1.performance import router`
- **`backend/app/services/import_service.py`** — 在 `confirm_import_job()` 末尾增加：
  ```python
  if import_type == 'performance_grades':
      from backend.app.services.performance_service import PerformanceService
      perf_service = PerformanceService(db, settings)
      perf_service.invalidate_tier_cache(affected_years)
      perf_service.recompute_tiers_async(affected_years)  # 5s timeout per D-03
  ```
- **`frontend/src/App.tsx`** — `<Route path="/performance" element={<PerformanceManagementPage />} />`
- **`frontend/src/utils/roleAccess.ts`** — 加 `'/performance': ['admin', 'hrbp']`
- **Sidebar 菜单组件**（路径需确认 — 可能 `frontend/src/components/AppShell/` 或 `Sidebar.tsx`）— 加「绩效管理」menu item
- **`.env.example`** — 如需新 Redis key prefix，加 `PERFORMANCE_TIER_REDIS_PREFIX=tier_summary`

</code_context>

<specifics>
## Specific Ideas

- 「档次分布视图」3 段堆叠条参照 GitHub Insights 的 contributor 进度条样式（绿/黄/红比例分明 + tooltip 显示具体百分比）
- warning 横幅文字必须显示**实际百分比**而非泛泛说「偏离了」，便于 HR 即时判断偏离程度（如「档次分布偏离 20/70/10 超过 ±5%（实际 22%/68%/10%）」）
- 重算按钮成功后 toast「档次重算完成（共 1234 人）」+ 自动刷新 summary
- 测试覆盖优先级：
  1. **Service 层**：`PerformanceService.recompute_tiers()` 含锁竞争（两个事务同时调）、Engine 输出落表正确性、cache invalidate 语义
  2. **API 层**：4 个端点的 happy path + 403（employee/manager）+ 404（无快照）+ 409（busy）
  3. **import_service hook**：confirm `performance_grades` 后 `recompute_tiers` 被触发的集成测试（mock Engine 即可，重点测 hook 接线）
  4. **前端**：`PerformanceManagementPage` 渲染 + 年份切换 + 重算按钮 loading + 404 空状态
- pytest 用例预期 ≥ 25 个（Service ~12 + API ~10 + import_hook ~3）

</specifics>

<deferred>
## Deferred Ideas

- **员工端档次徽章 / `/performance/me/tier`** → Phase 35（本期仅声明保留位）
- **历史绩效跨页面展示**（评估详情页 + 调薪建议详情页 +「历史绩效」表）→ Phase 36
- **多年时间序列趋势视图**（如近 3 年档次分布趋势）→ Phase 36 或 dashboard 范围
- **存量 PerformanceRecord 的 department_snapshot 数据回填脚本** → 显式不做（D-07 决定）
- **绩效全套评审流程**（评分轮次 / 反馈 / 校准 / 申诉）→ 远期
- **Celery 异步重算队列** → 本期同步阻塞 5s 已足够（< 5000 员工），Phase 19 Celery 基建本期不消费
- **行点击跳「员工绩效详情」子页** → Phase 36
- **批量手动新增绩效**（HR 在 UI 上多行编辑表单） → 用 Excel 导入即可，不开发
- **`/performance/records/{id}` 单条删除/更新端点** → 本期仅 list + create，update/delete 待真实需求

</deferred>

---

*Phase: 34-performance-management-service-and-api*
*Context gathered: 2026-04-22*
