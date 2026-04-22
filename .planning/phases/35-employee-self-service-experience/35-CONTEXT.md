# Phase 35: 员工端自助体验 - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

在 Phase 32.1 已建好的 `MyEligibilityPanel` **下方** 追加独立的「本人绩效档次」section（新建 `MyPerformanceTierBadge` 组件），并挂上 Phase 34 预留的 `GET /api/v1/performance/me/tier` 路由 handler（`backend/app/api/v1/performance.py:206-209` TODO Phase 35）。

**本期唯一交付：ESELF-03**（员工看到 1/2/3 档；不显示具体排名/百分位/同档名单）。

**严格不在范围：**
- ESELF-01/02/04/05 由 Phase 32.1 完成，本期不重构 `MyEligibilityPanel`、不动 `/eligibility/me`（32.1 D-03 约束）
- 历史绩效 / `PerformanceHistoryPanel` 跨页面展示 → Phase 36（PERF-07）
- 员工端查看其他年份/切换年份 → 本期无参数路由，仅按 D-01 策略定位单一年份
- 「如何改善档次」建议 / 申诉入口 → v1.5+（ESELF-09）
- 档次趋势展示（过去 N 周期档位变化）→ v1.5+（ESELF-08）
- Distribution warning 黄条 → PERF-06 明确员工端不可见

</domain>

<decisions>
## Implementation Decisions

### 后端 API — 年份定位与全空分支

- **D-01:** `GET /api/v1/performance/me/tier` 用「当前自然年 → 最新有快照年」fallback 策略：
  1. 先查 `PerformanceTierSnapshot` 中 `year == datetime.now().year` 的行
  2. 未命中则 fallback 到 `SELECT year FROM performance_tier_snapshots ORDER BY year DESC LIMIT 1`
  3. 响应体 **必须携带 `year` 字段**，前端显式渲染「2026 年度档次」让员工看到来自哪一年
  4. 不接受 `?year=X` 查询参数（ESELF-04 无参数路由红线）
- **D-02:** 全库完全无 `PerformanceTierSnapshot` 行（HR 从未重算）时，端点返回 **200** + body：
  ```json
  { "year": null, "tier": null, "reason": "no_snapshot", "data_updated_at": null }
  ```
  **不返 404** —— 档次缺失是常态（早期 / 新周期），不应作为错误态；和 Phase 34 `/tier-summary` 的 404 语义区分（HR 端有「立即生成档次」按钮需要 404 触发空态按钮，员工端无此操作入口）

### 后端 API — 三种「tier=null」分层

- **D-03:** 响应体 `reason` 字段是 `Literal['insufficient_sample', 'no_snapshot', 'not_ranked']`，仅在 `tier is None` 时非空，三种语义明确分层：
  - `insufficient_sample`：命中快照行且 `snapshot.insufficient_sample == True`（Phase 33 `PerformanceTierEngine` 样本不足全员 null）
    → 前端文案「本年度全公司绩效样本不足，暂不分档」（对应 ROADMAP SC1）
  - `no_snapshot`：D-02 情形（全库无任何快照，fallback 也命中不到）
    → 前端文案「本年度尚无档次数据，请等待 HR 录入后查看」
  - `not_ranked`：命中快照行、非 insufficient，但 `snapshot.tiers_json.get(employee_id)` 为 null 或键不存在（该员工未录入当年绩效、或其 grade 被 engine skipped）
    → 前端文案「未找到您本年度的绩效记录，如有疑问请联系 HR」

### 后端 API — 响应 schema 与错误态

- **D-04:** Pydantic `MyTierResponse` 精简 4 字段：
  ```python
  class MyTierResponse(BaseModel):
      year: int | None
      tier: Literal[1, 2, 3] | None
      reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None
      data_updated_at: datetime | None  # ISO 8601

      # 语义不变式（在 Service 层保证 / 单测验证）:
      # - tier is None → reason 必非空
      # - tier in {1,2,3} → reason 必为 null
  ```
  **不引入 `display_label` 预渲染字段** —— 文案本地化职责归前端，避免 i18n/样式 与后端耦合
- **D-05:** `data_updated_at` 直接取 `PerformanceTierSnapshot.updated_at`（Phase 34 D-01 已有 `UpdatedAtMixin`）
  - reason=`no_snapshot` 时 → `data_updated_at = None`
  - 不与 `EligibilityResult.data_updated_at` 合并，两个 panel 各自显示自己的数据新鲜度（档次 panel 也在右上角显示，格式和资格 panel 一致 — `Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })`，32.1 D-17 沿用）
- **D-06:** 错误态延续 Phase 32.1 `MyEligibilityPanel` 模式，Service 层三种 HTTP 非 200 分支：
  - `current_user.employee_id is None`（未绑定）→ **422** + `{ error, message: '您尚未绑定员工信息' }`
  - `Employee` 查不到（JWT 有效但行被删）→ **404** + `{ error, message: '员工档案缺失' }`
  - 其他异常 → 500 + 通用消息（logger.exception 走 `main.py` 全局 handler）

### 前端 UI — 徽章视觉与文案

- **D-07:** 新建 `frontend/src/components/performance/MyPerformanceTierBadge.tsx` 组件（与 HR 端 `TierChip` 分离，**不复用** `TierChip`，符合 Phase 32.1 D-03「仅追加不重构」）
  - 放置位置：`frontend/src/components/performance/`（与 `TierChip` 同目录，文件名 `My` 前缀自述其自助语义）
  - `MyReview.tsx` 中插入点：`<MyEligibilityPanel />` 紧邻下方（当前 `MyReview.tsx:545` 之后），独立 `<section className="surface px-6 py-8">`
- **D-08:** 三档柔和色盘（desaturated，继承 Phase 32.1 D-12 四色语义行的视觉调性），三档色各为徽章背景 + 文字色：
  - **1 档**：background `#d1fae5` / text `#065f46` / label 「1 档」
  - **2 档**：background `#fef3c7` / text `#92400e` / label 「2 档」
  - **3 档**：background `#ffedd5` / text `#9a3412` / label 「3 档」
  - **灰底占位**：background `#f3f4f6` / text `#6b7280` / label 由 D-03 reason 决定
  - 徽章尺寸/样式沿用 Phase 32.1 OverallBadge（`status-pill` + `fontSize: 14, padding: '6px 12px'`）
- **D-09:** 徽章文案 **仅「1 档 / 2 档 / 3 档」纯数字**，不加「优秀 / 合格 / 待提升」等语义标签：
  - 避免绑死「档次 ↔ 优劣语义」，未来若比例或三档定义调整，后端/HR 无需同步改员工端文案
  - 避免员工端与 HR 端（Phase 34 TierChip 仅显示数字）双重文案维护
- **D-10:** section 结构：
  - 左上 eyebrow `本期绩效` + 标题 `本人绩效档次`（与 `MyEligibilityPanel` 的 `本期调薪` + `本人调薪资格` 标题对齐）
  - 右上角 `数据更新于 YYYY-MM-DD HH:MM`（D-05 时间戳，reason=no_snapshot 时显示「数据从未更新」，与 32.1 panel 的 unbound/null 行为一致）
  - 主体：单一徽章（tier=1/2/3 或灰底 reason 文案）
  - 徽章下方一行 small text（`#6b7280`，14px）：「YYYY 年度档次（按全公司 20/70/10 分档）」—— tier 有值时显示；tier=null 时不显示该行

### 前端集成点

- **D-11:** `frontend/src/services/performanceService.ts`（Phase 34 已建）新增函数：
  ```typescript
  export async function fetchMyTier(): Promise<MyTierResponse> {
    const { data } = await api.get<MyTierResponse>('/performance/me/tier');
    return data;
  }
  ```
- **D-12:** `frontend/src/types/api.ts` 新增类型（与后端 D-04 契约对齐）：
  ```typescript
  export interface MyTierResponse {
    year: number | null;
    tier: 1 | 2 | 3 | null;
    reason: 'insufficient_sample' | 'no_snapshot' | 'not_ranked' | null;
    data_updated_at: string | null;  // ISO 8601
  }
  ```

### Service 层查询约定

- **D-13:** `PerformanceService.get_my_tier(employee_id: UUID) -> MyTierResponse`（新增方法，放 `backend/app/services/performance_service.py`）：
  1. 先查「当前年」snapshot（`SELECT * FROM performance_tier_snapshots WHERE year = :current_year`）
  2. 未命中 → `SELECT * FROM ... ORDER BY year DESC LIMIT 1`
  3. 仍无 → 返回 `{year=None, tier=None, reason='no_snapshot', data_updated_at=None}`
  4. 命中快照 → 先判 `snapshot.insufficient_sample`，真 → 返回 `{year, tier=None, reason='insufficient_sample', data_updated_at=snapshot.updated_at}`
  5. 否则从 `snapshot.tiers_json.get(str(employee_id))` 取值：
     - 值为 1/2/3 → 返回 `{year, tier, reason=None, data_updated_at=snapshot.updated_at}`
     - 值为 null 或键不存在 → 返回 `{year, tier=None, reason='not_ranked', data_updated_at=snapshot.updated_at}`
  - **注意**：`tiers_json` 的 key 存的是字符串（JSON 序列化 UUID），Service 层 lookup 时需 `str(employee_id)`；参考 `performance_service.py:289 snapshot.tiers_json = result.tiers` 观察 Phase 33 engine 输出的 key 类型

### Claude's Discretion

- Service 层 `get_my_tier` 方法内部是否用 SELECT ... FOR UPDATE（不需要 — 纯读无写）
- fetchMyTier 失败时的自动重试策略（沿用 Phase 32.1 panel 手动「重试」按钮足矣）
- section 垂直间距具体 px（参照 `MyEligibilityPanel` 保持整页密度一致）
- 加载态用 skeleton 还是 spinner（沿用 Phase 32.1 D `SkeletonRows` 单 row 变体）
- 单元测试命名风格（沿用 Phase 33/34 pytest 模式）
- 是否在 `api/v1/performance.py` 保留 TODO 注释删除（delete 即可）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 34 复用基础设施（必读）
- `backend/app/models/performance_tier_snapshot.py` — `PerformanceTierSnapshot` 模型 + `tiers_json` 字段（D-13 的数据源）
- `backend/app/api/v1/performance.py:206-209` — Phase 35 TODO 保留位（handler 挂载点）
- `backend/app/services/performance_service.py:216-242` `get_tier_summary` / `379-415` `_snapshot_to_summary` — 快照读取模式参考（但本期**不**走 Redis cache，读库即可）
- `backend/app/schemas/performance.py` — 新增 `MyTierResponse` 的放置位置（与 `TierSummaryResponse` 同文件）
- `.planning/phases/34-performance-management-service-and-api/34-CONTEXT.md` §D-01/D-09/D-10 — 快照表 schema / Phase 34 响应形态对照

### Phase 32.1 沿用模式（必读）
- `frontend/src/components/eligibility/MyEligibilityPanel.tsx` — section 布局 / 错误态分支 / 时间戳渲染 / Skeleton / 徽章样式都是本期镜像样板
- `frontend/src/pages/MyReview.tsx:545` — `<MyEligibilityPanel />` 插入点，Phase 35 的 `<MyPerformanceTierBadge />` 紧邻其后
- `frontend/src/services/eligibilityService.ts` — `fetchMyEligibility` 函数是 D-11 `fetchMyTier` 的模板
- `frontend/src/types/api.ts` — `EligibilityResultWithTimestamp` 类型是 D-12 `MyTierResponse` 的模板
- `backend/app/api/v1/eligibility.py` — `GET /me` 端点模式（`Depends(get_current_user)` + `current_user.employee_id` 校验）是 `GET /performance/me/tier` 的模板
- `.planning/phases/32.1-employee-eligibility-visibility/32.1-CONTEXT.md` §D-03/D-04/D-10/D-14/D-17 — 无参数路由 / 错误态 / section 布局 / 时间戳渲染约定

### Phase 33 引擎契约（本期不改，仅读取输出）
- `backend/app/engines/performance_tier_engine.py` — `TierAssignmentResult.tiers / insufficient_sample` 字段语义（D-03 `insufficient_sample` 分支的源头）
- `.planning/phases/33-performance-tier-engine/33-CONTEXT.md` §D-01..D-11 — 引擎「样本不足全员 null」契约（D-03 落地的基石）

### 需求与目标
- `.planning/REQUIREMENTS.md` line 14 — ESELF-03 原文（不显示排名/百分位/同档名单）
- `.planning/REQUIREMENTS.md` line 25 — PERF-06 明确「员工端不可见分布偏离警告」
- `.planning/ROADMAP.md` line 195-205 — Phase 35 Goal + 4 个 Success Criteria
- `.planning/REQUIREMENTS.md` line 89-103 — Out of Scope 合规红线（员工端看到具体排名/百分位/同档其他人 / 精确分数 → PIPL 红线）
- `CLAUDE.md` — 项目编码规范（`from __future__ import annotations` / PEP 604 union / Pydantic v2 / `require_roles` / Service 层不抛 raw Exception）

### 依赖与路由
- `backend/app/dependencies.py` — `get_current_user` + `require_roles` 依赖注入
- `backend/app/api/v1/__init__.py` 或 `main.py` — router 已注册，本期只是挂新 handler，无新路由文件

### Codebase 维度
- `.planning/codebase/CONVENTIONS.md` — 命名 / 类型注解 / import 顺序
- `.planning/codebase/TESTING.md` — pytest 组织（Service 层 + API 层测试结构）
- `.planning/codebase/STRUCTURE.md` — backend 分层（api / services / engines / models / schemas）

### STATE.md 已固化的决策
- 「员工端自助路由无参数（`/eligibility/me`、`/performance/me/tier`），不接受 `{employee_id}` 变体」
- 「绩效档次按全公司范围 20/70/10 分档」

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PerformanceTierSnapshot`** (Phase 34 交付)：`tiers_json` + `insufficient_sample` + `updated_at` 即 D-13 需要的全部数据源
- **`PerformanceService`** (Phase 34 交付)：本期只加一个 `get_my_tier(employee_id)` 方法，不需新 Service
- **`get_current_user` dep** (`backend/app/dependencies.py`)：JWT 鉴权自动注入 `User`（`current_user.employee_id` 复用 Phase 32.1 校验模式）
- **`MyEligibilityPanel`** (Phase 32.1 交付)：整个 section 视觉/错误态/时间戳的镜像样板
- **`MyReview.tsx`**：插入点明确（`MyEligibilityPanel` 紧邻下方），Phase 32.1 已在注释里预留了结构
- **`performanceService.ts`** (Phase 34 交付)：fetchMyTier 直接加函数即可
- **`types/api.ts`**：`MyTierResponse` interface 直接加，模板为 `EligibilityResultWithTimestamp`
- **`surface` Tailwind 类**：section 包裹样式复用
- **`status-pill` 类**：徽章基础样式复用（Phase 32.1 OverallBadge 已用）

### Established Patterns
- **无参数 `/me` 端点**：参见 `backend/app/api/v1/eligibility.py` `GET /me`，模式 = `Depends(get_current_user)` → 校验 `employee_id` → Service 调用
- **`/me` 路由必须在 `/{employee_id}` 之前注册**（FastAPI 路由匹配规则，32.1 CONTEXT line 147 警告）
- **Pydantic v2 `ConfigDict(from_attributes=True)` + `Literal[...]`** 用于 union 枚举
- **`from __future__ import annotations`** 必须顶部
- **Service 层不抛 raw `Exception`**；未绑定 → 在 API 层 `raise HTTPException(422, ...)`（模拟 Phase 32.1 `eligibility.py` 自访问校验模式）
- **Snapshot `tiers_json` key 为 str(UUID)**（Phase 33 engine 输出格式），Service 层 `tiers_json.get(str(employee_id))` lookup
- **前端 section 用 `<section className="surface px-6 py-8">`** + eyebrow/h2 标题结构（Phase 32.1 D-10 + `MyEligibilityPanel` line 54-68 样板）
- **时间戳格式** = `Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })`（Phase 32.1 D-17）

### Integration Points
- **`backend/app/api/v1/performance.py`** 第 206-209 行的 TODO 替换为真实 handler；删除 `# TODO Phase 35` 注释
- **`backend/app/services/performance_service.py`** 新增 `get_my_tier` 方法（建议放在 `get_tier_summary` 附近以保持「读路径方法」聚合）
- **`backend/app/schemas/performance.py`** 新增 `MyTierResponse` Pydantic 类
- **`frontend/src/components/performance/MyPerformanceTierBadge.tsx`** 新建组件（含子组件 `TierChipSoft` / `NullPlaceholder` / `TimestampLine`，参照 `MyEligibilityPanel` 内联子组件模式）
- **`frontend/src/pages/MyReview.tsx`** `<MyEligibilityPanel />` 紧邻下方 import + 渲染 `<MyPerformanceTierBadge />`
- **`frontend/src/services/performanceService.ts`** 新增 `fetchMyTier` 函数
- **`frontend/src/types/api.ts`** 新增 `MyTierResponse` interface
- **角色**：本期 `/performance/me/tier` 任何已登录用户可调（`Depends(get_current_user)` 已足够），无需 `require_roles`（employee/manager/hrbp/admin 都可查自己的档次；越权天然不可达，无 `{employee_id}` 变体）

</code_context>

<specifics>
## Specific Ideas

- 「本年度尚无档次数据，请等待 HR 录入后查看」文案 —— 避免说「HR 失职 / 等 HR 配置好」等员工可能曲解为 HR 不作为的措辞；保持中性描述「录入后查看」
- 「未找到您本年度的绩效记录」文案 —— 避免说「您未获得档次」等暗示「你不够格」的表达；聚焦数据维度「未找到记录」+ 引导「联系 HR」
- 档次徽章的"柔和色盘"继承 Phase 32.1 `OverallBadge` 的 desaturated pastel 风格 —— 视觉连贯、减弱员工心理冲击（尤其 3 档员工看到的不是刺眼红而是温和橙）
- 徽章下方小字「YYYY 年度档次（按全公司 20/70/10 分档）」—— 透明标注规则来源，合规（披露元规则不披露个人排序数据，符合 PIPL）+ 减少员工猜测
- 测试覆盖优先级：
  1. **Service 层 `get_my_tier`**：4 个分支（tier 有值 / insufficient_sample / no_snapshot / not_ranked）+ fallback 路径（当前年无，fallback 到 2025）+ tiers_json key 是 str(UUID) 的 lookup 正确性
  2. **API 层**：happy path（admin/hrbp/manager/employee 各角色调用都应 200）+ 未绑定 422 + 员工档案缺失 404
  3. **前端 MyPerformanceTierBadge 组件**：5 种渲染状态（3 档值 + 灰底 3 种 reason）+ 时间戳格式化 + 错误态复用
- pytest 用例预期 ≥ 12 个（Service ~7 + API ~5）
- 前端测试：vitest 单测覆盖 `MyPerformanceTierBadge` 5 状态 + 手工浏览器 UAT 4 项（当前年有档次 / 当前年 insufficient / 完全无快照 / fallback 到旧年）

</specifics>

<deferred>
## Deferred Ideas

- **员工端档次趋势展示**（过去 N 周期档次变化）→ Phase 36 或 v1.5+（ESELF-08）
- **员工申诉 / 复核入口**（「申请复核我的档次」按钮）→ v1.5+（ESELF-09）
- **「如何改善档次」个性化建议**（如「再提升一个等级就能进 2 档」）→ v1.5+
- **员工端跨年份切换**（`?year=X` 或 `<select>` 下拉）→ 违反 ESELF-04，若未来要支持需重新评估
- **员工端看到档次分布可视化**（直方图 / 分布条）→ 合规红线（Out of Scope），不做
- **员工端看 distribution_warning**（20/70/10 偏离）→ PERF-06 明确员工端不可见，不做
- **管理员/HR 视角查看员工自助页面**（模拟员工视图）→ 管理员用 HR 端 `/performance` 即可，不做员工视图代理
- **档次变更通知**（档次变化时 email/飞书推送）→ 远期通知系统统一规划
- **徽章视觉与 Phase 32.1 OverallBadge 统一到共享组件**（重构出 `<SoftStatusPill>` 基类）→ 两个组件各自独立即可，DRY 重构留给有第三方复用场景时
- **API 缓存策略**（`/performance/me/tier` 是否走 Phase 34 TierCache） → 本期读库即可（snapshot 表很小，每年 1 行；查询极轻），性能优化留给瓶颈出现时
- **前端 service 层缓存**（`@tanstack/react-query` / SWR） → 本期每次进 page 重新查，沿用 Phase 32.1 策略

</deferred>

---

*Phase: 35-employee-self-service-experience*
*Context gathered: 2026-04-22*
