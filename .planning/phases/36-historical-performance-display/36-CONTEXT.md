# Phase 36: 历史绩效展示 - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

在 `EvaluationDetail` 页面底部挂载 `PerformanceHistoryPanel`（按员工维度拉取历史绩效），以 4 列（周期/等级/评语/部门快照）按 `year DESC` 排列，服务于 HR+manager 在审批时查看员工绩效连续性。由于 `SalaryDetailPanel` 已是 `EvaluationDetail.tsx` 同页内嵌 section，挂一次即两语境共用。

**严格不在范围：**
- 员工 `MyReview` 展示本人历史绩效表 → 显式 deferred 到 v1.5+（保护员工端绩效数据敏感性）
- `Approvals` 审批列表页打开详情 drawer/modal 后再挂 panel → 本期用户主动进评估详情页浏览，不做 Approvals 内联
- 独立 `SalaryDetail` 新页面 / EvaluationDetail 2304 行文件重构 → 显式不做
- 按半年度 / 季度粒度存储绩效（新增 `cycle_start_date: date` 字段）→ 保持 `year: int` 粒度
- 存量 `PerformanceRecord` 行的 `comment` 字段数据回填 → NULL 保持不动，UI 渲染「—」
- 飞书同步 `sync_performance_records` 增加 `comment` 字段映射 → 本期不改飞书 mapping（飞书表格无对应字段；manual/excel 两类来源支持 comment 写入即可，feishu 来源 comment 保持 None）

</domain>

<decisions>
## Implementation Decisions

### Area 1 — 数据模型补齐（评语字段 + 周期粒度）

- **D-01:** 「周期」列以 `year: int` 粒度展示（不新增 `cycle_start_date: date` 字段）：
  - UI 显示文本：`${record.year} 年度`（zh-CN locale）
  - 排序：`ORDER BY year DESC`（SC#1 里的 `cycle_start_date` 倒序语义在本期解读为「按年度倒序」）
  - `PerformanceRecord` 模型不新增日期字段；Phase 34 Alembic 结构保持 schema 稳定
  - 未来若真有半年度/季度粒度需求 → 新 phase 单独处理（Deferred）
- **D-02:** `PerformanceRecord` 新增 `comment: Mapped[str | None]` 字段：
  - 类型：`sqlalchemy.Text`（允许长文本，不设长度上限，与绩效评语使用场景一致）
  - Nullable：是（存量行保持 NULL）
  - Alembic migration 名：`add_comment_to_performance_records`
  - migration 不做数据回填（遵循 Phase 34 D-07「快照类字段不虚构历史」同款原则）
  - Pydantic schema `PerformanceRecordRead` 新增 `comment: str | None`
  - TS 类型 `PerformanceRecordItem` 新增 `comment: string | null`
- **D-03:** `comment` 字段的写入支持：
  - `POST /api/v1/performance/records` 请求体 `PerformanceRecordCreateRequest` 新增可选 `comment: str | None = None`
  - `PerformanceService.create_record()` 写入 comment（允许 None）
  - `ImportService` `import_type='performance_grades'` 的 `REQUIRED_COLUMNS` 保持不变（grade 仍必填），**新增可选列 `comment`**（`COLUMN_ALIASES` 支持「评语」「comment」「备注」三种表头别名）
  - 飞书同步 `sync_performance_records` 对 `comment` 写 None（飞书多维表格本期无对应字段；若未来飞书加字段再扩展 mapping）
  - `_import_performance_grades` 在上传 excel 无 comment 列时按 None 入库，已存在 comment 列时按值入库

### Area 2 — Manager 访问入口（新端点）

- **D-04:** 新增 `GET /api/v1/performance/records/by-employee/{employee_id}`：
  - 路径参数：`employee_id: str`（UUID）
  - Query 参数：无（不分页、不按 year filter；单员工一次性返回全部历史）
  - 响应 schema：`PerformanceRecordsByEmployeeResponse { items: PerformanceRecordItem[] }`（按 `year DESC` 预排序）
  - 角色：`require_roles('admin', 'hrbp', 'manager')`
  - 权限拦截：**复用 `AccessScopeService.ensure_employee_access(current_user, employee_id)`**（与 evaluations/salary 端点一致的 pattern）
    - admin/hrbp：全员可见
    - manager：仅自己直属下属可见；跨部门触发 `PermissionError` → API 层 catch 转 HTTP 403
    - employee 角色：被 `require_roles` 直接挡回 403（不进 service 层）
  - 挂载：`backend/app/api/v1/performance.py` router 新增 handler；按钮顺序插在现有 `GET /records`（列表分页）后、`POST /records` 前
- **D-05:** 返回 shape **不分页、直接 flat items 数组**：
  - 理由：单员工历史绩效即便任职 20 年也不会超过 20 行，分页字段反而浪费
  - Service 层新增 `list_records_by_employee(employee_id: str) -> list[PerformanceRecordItem]`
  - 空结果返回 `{ items: [] }`（200 OK）— 前端判断 `items.length === 0` 渲染空状态
- **D-06:** 权限失败的错误响应：
  - manager 跨部门 → `AccessScopeService.ensure_employee_access` 抛 `PermissionError` → router 层 catch 转 `HTTPException(403, detail='无权查看该员工的历史绩效')`
  - employee 角色触达 → `require_roles('admin','hrbp','manager')` 直接挡回 403
  - employee_id 不存在员工表 → `AccessScopeService.ensure_employee_access` 返回 None → router 转 404
  - 绑定 pytest 覆盖：admin 正常返回、hrbp 正常返回、manager 同部门下属正常、manager 跨部门 403、employee 403、员工不存在 404

### Area 3 — 展示位置（PerformanceHistoryPanel 挂载）

- **D-07:** `PerformanceHistoryPanel` 仅挂载到 `EvaluationDetail.tsx`，在 `SalaryDetailPanel`（当前行 2147）之后作为同页独立 section：
  - 挂载位置：`SalaryHistoryPanel`（现有）之前 或 之后的垂直相邻位置（Claude's Discretion 决定视觉顺序）
  - 不挂载到 `Approvals.tsx`、`MyReview.tsx`、`EmployeeAdmin.tsx` 等其他页面
  - 复用共享语义：HR/manager 进入 `/evaluations/:id` 路由后，同一个 panel 同时服务于「评估详情 section」与「调薪建议 section」的上下文
- **D-08:** 新建 `frontend/src/components/performance/PerformanceHistoryPanel.tsx`：
  - 目录：`components/performance/`（与 Phase 34 交付的 `TierChip`、`TierDistributionPanel`、`PerformanceRecordsTable` 同目录，领域聚合）
  - Props 契约：
    ```typescript
    interface PerformanceHistoryPanelProps {
      employeeName?: string;
      records: PerformanceRecordItem[];
      isLoading: boolean;
    }
    ```
  - 样式：参照 `SalaryHistoryPanel`（`surface px-6 py-6 lg:px-7` + `section-head` + 表格）；4 列表头：周期 / 绩效等级 / 评语 / 部门快照
  - 空状态：`!isLoading && records.length === 0` → 显示 dashed border 空态卡，文案「暂无历史绩效记录」+ hint「该员工尚未录入任何年度绩效」
  - Loading 状态：`isLoading === true` → 显示「正在加载该员工的历史绩效记录...」
  - 行内 NULL 处理：`comment === null` 或 `department_snapshot === null` → 渲染「—」
  - 不依赖 recharts / ECharts（纯表格，无图表）
- **D-09:** 数据拉取策略：
  - 在 `EvaluationDetail.tsx` 初始化 `useEffect`（现有行 568 附近 `Promise.all` 块）并行调用新建的 `fetchPerformanceHistoryByEmployee(employee_id)`
  - 新增 state：`const [performanceHistory, setPerformanceHistory] = useState<PerformanceRecordItem[]>([])` + `const [isPerformanceHistoryLoading, setIsPerformanceHistoryLoading] = useState(false)`
  - 角色门控：`canViewPerformanceHistory = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager'`（与 `canViewSalaryHistory` 同款）
  - employee 角色不挂 panel（即便通过 URL 直访 `/evaluations/:id`，也不触发拉取、不渲染 panel —  权衡：employee 角色访问 EvaluationDetail 本身是否允许，保留现状，本期不改）
  - service 层：`frontend/src/services/performanceService.ts` 新增 `fetchPerformanceHistoryByEmployee(employeeId: string): Promise<{ items: PerformanceRecordItem[] }>`
  - API timeout：普通超时即可（非 long-running，无需 `LONG_RUNNING_TIMEOUT`）

### Area 4 — 员工自助严格隔离

- **D-10:** 员工 `MyReview` 页面**不**展示本人历史绩效表：
  - 不新建 `/performance/me/history` 端点
  - 不在 `MyReview.tsx` 挂 `PerformanceHistoryPanel`
  - Phase 35 已交付的本人「绩效档次徽章」（1/2/3 档）保持不变，不升级为全历史视图
  - 理由：严守 SC#1「HR/manager 打开员工评估详情页」的角色边界；绩效数据全历史对员工自助端属于敏感信息披露（尤其跨年度对比可能引发绩效焦虑）
  - v1.5+ 若产品决定向员工放开 → 新 phase 明确走 PRD

### Claude's Discretion

- `PerformanceHistoryPanel` 与 `SalaryHistoryPanel` 在 EvaluationDetail 内的视觉垂直顺序（推荐：绩效历史在上、调薪历史在下，符合「从业绩到薪酬」叙事）
- 4 列表头样式：`eyebrow` / `status-pill` / `section-note` 等已有 utility 类的选择
- 空态卡的 dashed border 具体颜色（推荐沿用 `SalaryHistoryPanel` 的 `var(--color-border)`）
- 年份列是否加 badge 标注「本期」（如果 record.year === 当前 AIEvaluation 的评估年度）— 可做可不做
- `comment` 列长文本的截断策略（推荐：CSS line-clamp-2 + hover 显示 tooltip 全文）
- Service 层 `list_records_by_employee` 的 query pattern（推荐：`select(PerformanceRecord).where(employee_id=X).order_by(PerformanceRecord.year.desc())`）
- `PerformanceRecordsByEmployeeResponse` Pydantic schema 命名（可选 `PerformanceHistoryResponse` 等同义）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 34 交付的基础设施（必读）
- `backend/app/api/v1/performance.py` — 现有 5 端点 router；新端点 `by-employee/{employee_id}` 在此文件追加 handler
- `backend/app/services/performance_service.py` — 现有 `PerformanceService`；新增 `list_records_by_employee()` 方法
- `backend/app/models/performance_record.py` — 现有 6 字段模型（含 `department_snapshot`）；本期 Alembic migration 追加 `comment` 字段
- `backend/app/schemas/performance.py` — 现有 Pydantic schemas；新增 `PerformanceRecordsByEmployeeResponse`、扩展 `PerformanceRecordRead`/`PerformanceRecordCreateRequest` 加 `comment`
- `.planning/phases/34-performance-management-service-and-api/34-CONTEXT.md` § Area 4 D-07/D-08 — department_snapshot 字段语义 + Service 层取值口径（本期 comment 遵循同款 NULL 语义）
- `.planning/phases/34-performance-management-service-and-api/34-CONTEXT.md` § Area 8 D-15 — 现有 5 端点路由前缀；新端点与现有风格对齐

### 访问控制与相邻 API 风格（必读）
- `backend/app/services/access_scope_service.py` — `AccessScopeService.ensure_employee_access()` 契约；本期端点复用
- `backend/app/api/v1/evaluations.py` line 79-185 — AccessScopeService 在 router 层的调用 pattern（参考模板）
- `backend/app/dependencies.py` — `require_roles()` factory 现成；新端点传 `('admin','hrbp','manager')` 三元组
- `.planning/codebase/CONVENTIONS.md` — `from __future__ import annotations`、PEP 604 union、`Mapped[str | None]` 等规约
- `.planning/codebase/STRUCTURE.md` — backend 分层：api → services → models；禁跨层依赖

### 前端挂载点与复用组件（必读）
- `frontend/src/pages/EvaluationDetail.tsx` line 16-17 — `SalaryDetailPanel`、`SalaryHistoryPanel` import 参照
- `frontend/src/pages/EvaluationDetail.tsx` line 505-568 — history state 与并行拉取 pattern（新 panel 挂同款 `useEffect`）
- `frontend/src/components/salary/SalaryHistoryPanel.tsx` — 组件样式/loading/空态模板（新 panel 参照视觉语言）
- `frontend/src/services/performanceService.ts` line 125-144 — service 层现有 fetch pattern（新增 fetchPerformanceHistoryByEmployee 函数）
- `frontend/src/types/api.ts` line 1158-1182 — `PerformanceRecordItem` / `PerformanceRecordsListResponse` 现有类型（扩展 + 新增 `PerformanceHistoryResponse`）

### 需求与目标
- `.planning/REQUIREMENTS.md` line 26 — PERF-07 原文「四列：周期 / 绩效等级 / 评语 / 部门快照 四列，按 `cycle_start_date` 倒序」
- `.planning/ROADMAP.md` line 207-217 — Phase 36 Goal + 4 个 Success Criteria + Depends on Phase 34
- `CLAUDE.md` — 项目编码规范（Service 层职责、Pydantic schema、role-based access、Alembic 唯一 migration 路径）

### 测试参考
- `.planning/codebase/TESTING.md` — pytest 组织（Service 层测试 + API 层测试分离）
- `backend/tests/test_performance_*.py`（Phase 34 交付的 25+ 测试）— 测试文件命名、fixture 风格

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PerformanceService`（Phase 34 交付）** — `list_records()` 已存在；新增 `list_records_by_employee()` 贴合现有风格
- **`AccessScopeService.ensure_employee_access`** — 本期核心依赖，跨部门 manager 拦截免重复造轮子
- **`PerformanceRecordItem` TS 类型 + 6 字段** — 仅需扩展 `comment: string | null`
- **`SalaryHistoryPanel` 组件** — 视觉模板（eyebrow/section-title/空态卡/loading 文案）可抄
- **`EvaluationDetail.tsx` 并行拉取 pattern**（行 568 `Promise.all`）— 新 panel 并入同一个 `useEffect`
- **`require_roles('admin','hrbp','manager')`** — 仅参数变化，依赖函数现成
- **`frontend/src/services/performanceService.ts` 现有 6 个 service 函数** — 新增函数风格对齐即可
- **`ImportService.REQUIRED_COLUMNS['performance_grades']`** — 仅追加可选 `comment` 列，现有校验逻辑不动

### Established Patterns
- **`from __future__ import annotations` 必须在所有后端模块顶部** — CLAUDE.md 强制
- **Service 层抛自定义异常或 `PermissionError`，API 层 catch 转 HTTPException** — 与 Phase 34 的 `TierRecomputeBusyError` 同款
- **Alembic 唯一 migration 路径** — 本期 migration 仅 schema 变更，不跑 UPDATE 回填
- **Pydantic v2 `BaseModel` + `ConfigDict(from_attributes=True)`** — schema 扩展 `comment` 字段无额外工作
- **前端 fetch 函数直接返回 response body、不抛错**  — axios interceptor 统一处理 401
- **Phase 34 D-07 的「快照字段 NULL 不回填」原则** — 本期 `comment` 字段沿用同款 NULL 语义

### Integration Points
- **`backend/app/api/v1/performance.py`** — 新 handler 追加到 line 85 后（现有 `POST /records` 之前）
- **`backend/app/services/performance_service.py`** — `PerformanceService` 类新增方法 `list_records_by_employee()`
- **`backend/app/schemas/performance.py`** — 新增 `PerformanceHistoryResponse` schema；扩展 `PerformanceRecordRead` / `PerformanceRecordCreateRequest`
- **`backend/app/models/performance_record.py`** — 新增 `comment: Mapped[str | None] = mapped_column(Text, nullable=True)`
- **新 Alembic 迁移文件** — `add_comment_to_performance_records`（仅 schema，无数据回填）
- **`backend/app/services/import_service.py`** — `_import_performance_grades` 支持可选 `comment` 列 + `COLUMN_ALIASES` 增加别名
- **`frontend/src/types/api.ts`** — `PerformanceRecordItem` 追加 `comment: string | null`；新增 `PerformanceHistoryResponse`
- **`frontend/src/services/performanceService.ts`** — 新增 `fetchPerformanceHistoryByEmployee(employeeId)` 函数
- **`frontend/src/components/performance/PerformanceHistoryPanel.tsx`** — 新建组件文件
- **`frontend/src/pages/EvaluationDetail.tsx`** — import + state + `useEffect` 并行拉取 + 在 JSX 底部渲染 `<PerformanceHistoryPanel />`
- **`backend/tests/test_performance_*.py`** — 新增测试文件 / 追加到现有文件（Service 方法单测 + API 端点测 + 权限矩阵测）

</code_context>

<specifics>
## Specific Ideas

- 4 列表头固定顺序：**周期 / 绩效等级 / 评语 / 部门快照**（与 SC#1 原文一致）
- 绩效等级列显示原始字母（A/B/C/D/E），不做 icon/emoji 装饰（与 Phase 34 `PerformanceRecordsTable` 视觉保持一致）
- 部门快照 NULL → 「—」，与 Phase 34 D-07 同款
- 评语 NULL → 「—」
- 空态文案：「暂无历史绩效记录」+ 补充说明「该员工尚未录入任何年度绩效」
- Loading 文案：「正在加载该员工的历史绩效记录...」
- 表格行排序稳定：`ORDER BY year DESC`；同年度多条（理论上被 `UniqueConstraint('employee_id','year')` 限制为 1 条）— 实际无平票
- 测试覆盖优先级：
  1. **Service 层**：`list_records_by_employee()` 按 year DESC 排序 + 空列表 + 不存在员工
  2. **API 权限矩阵**：admin / hrbp / manager（同部门）/ manager（跨部门→403）/ employee（→403）/ 未登录（→401）
  3. **AccessScopeService 集成**：mock 手工构造 Employee 跨部门数据
  4. **前端组件**：PerformanceHistoryPanel 4 列渲染 + 空态 + loading + comment/department_snapshot NULL → 「—」
  5. **Alembic migration**：up/down 可逆；存量行 comment 值为 NULL
- pytest 用例预期 ≥ 12 个（Service ~3 + API 权限矩阵 ~6 + component smoke ~3）

</specifics>

<deferred>
## Deferred Ideas

- **员工 MyReview 展示本人历史绩效表** → v1.5+，届时走独立 PRD 明确员工端绩效披露尺度
- **`/performance/me/history` 无参数路由** → 同上，本期不交付
- **多年时间序列趋势图**（如近 3 年绩效等级走势 line chart） → v1.5+ dashboard
- **半年度/季度粒度 `cycle_start_date` 存储** → 新 phase 重写存储层，本期 year 足够
- **飞书同步 `sync_performance_records` 支持 comment 字段映射** → 飞书多维表格加字段后再扩展；本期 feishu 来源 comment 恒为 None
- **Approvals 列表页内联展示历史绩效 drawer** → 超出 SC；用户主动进 EvaluationDetail 即可
- **独立 SalaryDetail 新页面** → EvaluationDetail 2304 行重构风险大，本期不做
- **`PerformanceRecord` 表的 comment 存量行回填脚本** → 显式不做（语义冲突，参照 Phase 34 D-07 逻辑）
- **行点击跳「员工绩效详情子页」** → 可选 UX 增强，本期 4 列即可

</deferred>

---

*Phase: 36-historical-performance-display*
*Context gathered: 2026-04-22*
