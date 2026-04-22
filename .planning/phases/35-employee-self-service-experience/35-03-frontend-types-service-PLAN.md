---
phase: 35-employee-self-service-experience
plan: 03
type: execute
wave: 2
depends_on:
  - 35-01
  - 35-02
files_modified:
  - frontend/src/types/api.ts
  - frontend/src/services/performanceService.ts
autonomous: true
requirements:
  - ESELF-03

must_haves:
  truths:
    - "`frontend/src/types/api.ts` 导出 `MyTierResponse` interface，4 字段与后端 Pydantic MyTierResponse 一一对应（tier 为 1|2|3|null 字面量联合；reason 为 3 字面量联合|null）"
    - "`frontend/src/services/performanceService.ts` 导出 `fetchMyTier` 异步函数，调用 `api.get('/performance/me/tier')` 且无任何 params/query"
    - "`npm run lint`（即 `tsc --noEmit`）通过，无新 TypeScript 报错"
    - "fetchMyTier 不吞异常 —— axios 抛出的 422/404 错误原样 re-throw，调用方（Plan 04 MyPerformanceTierBadge 组件）据此分支渲染"
  artifacts:
    - path: "frontend/src/types/api.ts"
      provides: "export interface MyTierResponse（4 字段契约）"
      contains: "export interface MyTierResponse"
    - path: "frontend/src/services/performanceService.ts"
      provides: "export async function fetchMyTier(): Promise<MyTierResponse>"
      contains: "fetchMyTier"
  key_links:
    - from: "frontend/src/services/performanceService.ts:fetchMyTier"
      to: "frontend/src/types/api.ts:MyTierResponse"
      via: "import type + Promise<MyTierResponse>"
      pattern: "fetchMyTier\\(\\): Promise<MyTierResponse>"
    - from: "frontend/src/services/performanceService.ts:fetchMyTier"
      to: "backend GET /api/v1/performance/me/tier"
      via: "api.get<MyTierResponse>('/performance/me/tier')"
      pattern: "/performance/me/tier"
---

<objective>
为 Phase 35 前端建立类型契约与服务层入口：在 `frontend/src/types/api.ts` 新增 `MyTierResponse` interface（D-12 精准 4 字段，字面量联合），在 `frontend/src/services/performanceService.ts` 新增 `fetchMyTier()` 函数（D-11 无参 GET）。

Purpose: 实现前端消费 Plan 02 `/performance/me/tier` 端点的基础设施。本 plan 不做 UI 渲染（由 Plan 04 处理），不动 MyReview.tsx / MyEligibilityPanel。

Output: 1 个新 interface + 1 个新 service 函数，`tsc --noEmit` 通过。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/35-employee-self-service-experience/35-CONTEXT.md
@.planning/phases/32.1-employee-eligibility-visibility/32.1-CONTEXT.md
@frontend/src/types/api.ts
@frontend/src/services/performanceService.ts
@frontend/src/services/eligibilityService.ts
@frontend/src/services/api.ts

<interfaces>
<!-- 后端契约（Plan 01 + 02 已交付）对照 -->

Backend Pydantic (backend/app/schemas/performance.py):
```python
class MyTierResponse(BaseModel):
    year: int | None
    tier: Literal[1, 2, 3] | None
    reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None
    data_updated_at: datetime | None  # ISO 8601 字符串
```

前端参考模板 (frontend/src/services/eligibilityService.ts:91-94 Phase 32.1 D-18):
```typescript
export async function fetchMyEligibility(): Promise<EligibilityResultWithTimestamp> {
  const response = await api.get<EligibilityResultWithTimestamp>('/eligibility/me');
  return response.data;
}
```

既有 performance 类型（Phase 34 — 本 plan 仅追加）:
```typescript
// frontend/src/types/api.ts — line 1145-1156 附近
export interface TierSummaryResponse { ... }
export interface PerformanceRecordItem { ... }
// Phase 35 新增 MyTierResponse 放在此 section 末尾
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 新增 MyTierResponse TypeScript interface</name>
  <files>frontend/src/types/api.ts</files>
  <read_first>
    - frontend/src/types/api.ts（line 1128-1223 的「Phase 34 绩效管理」section，新 interface 紧邻 `AvailableYearsResponse` 之后）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-12 精确 interface 定义）
    - .planning/codebase/CONVENTIONS.md（interface 命名 + `as const` 字面量联合风格）
  </read_first>
  <behavior>
    - tier 字段能被 TypeScript narrow 到 `1 | 2 | 3 | null` 之一（`if (tier === 1)` 有效）
    - reason 字段能被 narrow 到 3 字面量之一（`if (reason === 'insufficient_sample')` 有效）
    - data_updated_at 与 Phase 32.1 `EligibilityResultWithTimestamp.data_updated_at` 保持类型一致（`string | null`）
  </behavior>
  <action>
在 `frontend/src/types/api.ts` 末尾「Phase 34 绩效管理」section 的最后（即 `export interface AvailableYearsResponse { years: number[]; }` 之后），追加一个新 section 注释和 interface：

```typescript
// ===================== Phase 35 员工自助档次 (ESELF-03) =====================

/**
 * Phase 35 D-12: GET /api/v1/performance/me/tier 响应契约
 *
 * 与后端 Pydantic MyTierResponse 一一对应：
 *   - tier 有值 ↔ reason 为 null（员工有档次）
 *   - tier=null ↔ reason 非空（3 种语义分层）
 *
 * 不含 display_label / percentile / rank 等字段 —— 文案本地化由前端负责（D-04）；
 * 排名/百分位属 PIPL 红线不返回（REQUIREMENTS line 89-103）。
 */
export interface MyTierResponse {
  year: number | null;
  tier: 1 | 2 | 3 | null;
  reason: 'insufficient_sample' | 'no_snapshot' | 'not_ranked' | null;
  /** ISO 8601 字符串；snapshot.updated_at；reason='no_snapshot' 时为 null */
  data_updated_at: string | null;
}
```

**明确禁止：**
- 不要用 `type MyTierResponse = ...` —— 用 `interface`（项目约定，frontend/src/types/api.ts 其他接口统一用 interface）
- 不要把 `tier` 声明为 `number | null` 宽类型 —— 必须 `1 | 2 | 3 | null` 字面量联合，确保 Plan 04 组件 switch/if 能精准 narrow
- 不要把 `reason` 声明为 `string | null` —— 必须 3 字面量联合
- 不要加 `display_label?: string` 或其他预渲染字段 —— D-04 明确由前端做本地化
- 不要把 `data_updated_at` 声明为 `Date | null` —— 后端返回 ISO 字符串，前端 `new Date(iso)` 做本地化

放置位置严格在 `AvailableYearsResponse` 之后、文件结尾之前；不要改动任何既有 interface。
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust/frontend && npx tsc --noEmit 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "export interface MyTierResponse {" frontend/src/types/api.ts` 命中 1 行
    - `grep -n "tier: 1 | 2 | 3 | null;" frontend/src/types/api.ts` 命中
    - `grep -n "reason: 'insufficient_sample' | 'no_snapshot' | 'not_ranked' | null;" frontend/src/types/api.ts` 命中
    - `grep -n "data_updated_at: string | null;" frontend/src/types/api.ts` 命中（ESELF-03 + ESELF-05 对齐）
    - `grep -n "year: number | null;" frontend/src/types/api.ts` 在 MyTierResponse 20 行范围内命中
    - `grep -cE "display_label|percentile|rank" frontend/src/types/api.ts`（执行前统计既有数量 N，Plan 04 执行后仍为 N，即本 plan 不新增这些字段）
    - `cd frontend && npx tsc --noEmit` 退出码 0
  </acceptance_criteria>
  <done>interface 已添加，`tsc --noEmit` 通过，4 字段类型与后端完全一致。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 新增 fetchMyTier service 函数</name>
  <files>frontend/src/services/performanceService.ts</files>
  <read_first>
    - frontend/src/services/performanceService.ts（现有 import block + 函数组织）
    - frontend/src/services/eligibilityService.ts（line 91-94 fetchMyEligibility 模板）
    - frontend/src/services/api.ts（axios instance 基础 URL + JWT 拦截器；确认无需额外配置）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-11 函数签名）
  </read_first>
  <behavior>
    - 调用 GET /performance/me/tier（无任何 query/body）
    - 返回 Promise<MyTierResponse>
    - 不 catch 任何异常 —— 错误（422/404/网络 error）原样 throw 给调用方处理
  </behavior>
  <action>
在 `frontend/src/services/performanceService.ts` 中执行两步：

**Step A — 补充 import：**

找到文件顶部现有 import block：
```typescript
import type {
  AvailableYearsResponse,
  NoSnapshotErrorDetail,
  PerformanceRecordCreatePayload,
  PerformanceRecordItem,
  PerformanceRecordsListResponse,
  RecomputeTriggerResponse,
  TierRecomputeBusyDetail,
  TierSummaryResponse,
} from '../types/api';
```

在字母序位置追加 `MyTierResponse`（在 `NoSnapshotErrorDetail` 之后即可）：
```typescript
import type {
  AvailableYearsResponse,
  MyTierResponse,
  NoSnapshotErrorDetail,
  PerformanceRecordCreatePayload,
  PerformanceRecordItem,
  PerformanceRecordsListResponse,
  RecomputeTriggerResponse,
  TierRecomputeBusyDetail,
  TierSummaryResponse,
} from '../types/api';
```

**Step B — 追加 fetchMyTier 函数：**

在文件**末尾**（即 `export async function getAvailableYears()` 函数之后）追加：

```typescript
/**
 * Phase 35 D-11: 员工自助查询本人绩效档次（无参数路由，ESELF-03 / ESELF-04）
 *
 * 后端端点：GET /api/v1/performance/me/tier
 * 错误码：
 *   - 401 未鉴权（axios 拦截器可能触发 token refresh）
 *   - 422 未绑定员工 → 前端展示「请前往账号设置绑定」
 *   - 404 员工档案缺失 → 前端展示「员工档案缺失，请联系 HR」
 *   - 500 服务异常 → 前端展示通用错误 + 重试按钮
 *
 * 不做 try/catch —— axios 异常原样 throw，由调用方（MyPerformanceTierBadge 组件）
 * 用 `axios.isAxiosError(err) && err.response?.status === 422` 模式分支处理，
 * 保持与 Phase 32.1 MyEligibilityPanel 错误态风格一致。
 */
export async function fetchMyTier(): Promise<MyTierResponse> {
  const { data } = await api.get<MyTierResponse>('/performance/me/tier');
  return data;
}
```

**明确禁止：**
- 不要传 params：`api.get('/performance/me/tier', { params: ... })` 禁止 —— 无参数路由（ESELF-04）
- 不要包 try/catch —— 错误透传
- 不要在这里做 axios.isAxiosError 分支判断 —— 那是调用方（组件层）的职责
- 不要新建 custom error class（如 `TierNotRankedError`）—— 直接用 MyTierResponse 的 reason 字段表达「tier 为 null 但不是错误」语义；真正的错误态（422/404）走 axios error
- 不要新建 LONG_TIMEOUT 常量 —— 普通 GET，默认 axios timeout 即可（参考 fetchMyEligibility）

保持与 `fetchMyEligibility` 函数结构风格完全一致（解构 `data`、无 try/catch、JSDoc block 注释）。
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust/frontend && npx tsc --noEmit 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "export async function fetchMyTier(): Promise<MyTierResponse>" frontend/src/services/performanceService.ts` 命中 1 行
    - `grep -n "api.get<MyTierResponse>('/performance/me/tier')" frontend/src/services/performanceService.ts` 命中 1 行
    - `grep -nE "'/performance/me/tier',\s*\{" frontend/src/services/performanceService.ts` 不命中（即未传第二参数 options，保证无 params/query）
    - `grep -n "import type {" frontend/src/services/performanceService.ts` 附近 15 行内应含 `MyTierResponse,`
    - `cd frontend && npx tsc --noEmit` 退出码 0
    - `grep -cE "try\s*\{[\s\S]{0,100}fetchMyTier" frontend/src/services/performanceService.ts` 输出 0（fetchMyTier 本体无 try/catch）
  </acceptance_criteria>
  <done>fetchMyTier 导出、import 齐全、tsc 通过、无 params 传递。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser (React app) → Backend API | axios 实例走 HTTPS + JWT Bearer；本 plan 不增加新的 trust 面，仅调用既有 `/performance/me/tier`（Plan 02 交付） |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-03-01 | A01 Broken Access Control / E | fetchMyTier 调用面 | mitigate | 函数签名无参 `fetchMyTier()`；无 overload 允许传 employee_id；TypeScript 类型系统强制 —— 调用方想传额外参数会触发 `Argument of type ...` 编译错误（Task 1 acceptance `npx tsc --noEmit` 退出码 0 即证明） |
| T-35-03-02 | A02 Sensitive Data Exposure | 响应类型契约 | mitigate | `MyTierResponse` interface 4 字段，不含 ranking/percentile/peer_ids 字段；即使 backend 意外回传这些字段，前端 TypeScript 类型不暴露访问路径（虽然运行时对象上可能有多余字段，但 TypeScript 严格模式 + response_model 约束已在 Plan 02 层面裁剪） |
| T-35-03-03 | I (Info Disclosure) | axios 拦截器日志 | accept | 现有 api.ts 拦截器不把响应体写入 console；浏览器 devtools 当然可见，但那是 user 自己的账号数据，非越权泄露 |
| T-35-03-04 | R (Repudiation) | 前端无审计 | accept | 员工读自己档次无状态变更，无需前端审计（后端访问日志足够） |
</threat_model>

<verification>
- `cd frontend && npx tsc --noEmit` 退出码 0（无新类型错误）
- 所有 grep 静态断言通过
- MyTierResponse interface 与后端 Pydantic MyTierResponse 4 字段一一对应
</verification>

<success_criteria>
1. `MyTierResponse` interface 存在于 `frontend/src/types/api.ts`，字段与后端严格对齐
2. `fetchMyTier` 函数存在于 `frontend/src/services/performanceService.ts`，无 params
3. `npm run lint` 通过
4. 既有 Phase 34 `fetchTierSummary` / `getPerformanceRecords` 等函数未被修改
</success_criteria>

<output>
After completion, create `.planning/phases/35-employee-self-service-experience/35-03-SUMMARY.md`
</output>
