---
phase: 35-employee-self-service-experience
plan: 04
type: execute
wave: 2
depends_on:
  - 35-01
  - 35-02
  - 35-03
files_modified:
  - frontend/src/components/performance/MyPerformanceTierBadge.tsx
  - frontend/src/pages/MyReview.tsx
autonomous: false
requirements:
  - ESELF-03

must_haves:
  truths:
    - "员工登录 `/my-review` 页面后，在 `MyEligibilityPanel` 紧邻下方（当前 MyReview.tsx:545 `<MyEligibilityPanel />` 之后）看到独立 `<section className=\"surface px-6 py-8\">` 渲染 `MyPerformanceTierBadge`"
    - "组件 5 种状态渲染正确：tier=1（绿底 #d1fae5/#065f46『1 档』）/ tier=2（黄底 #fef3c7/#92400e『2 档』）/ tier=3（橙底 #ffedd5/#9a3412『3 档』）/ insufficient_sample（灰底 #f3f4f6/#6b7280『本年度全公司绩效样本不足，暂不分档』）/ no_snapshot（灰底『本年度尚无档次数据，请等待 HR 录入后查看』）/ not_ranked（灰底『未找到您本年度的绩效记录，如有疑问请联系 HR』）"
    - "section 左上 eyebrow『本期绩效』+ 标题『本人绩效档次』；右上角『数据更新于 YYYY-MM-DD HH:MM』（Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })；reason='no_snapshot' 或 data_updated_at=null 时显示『数据从未更新』）"
    - "tier in {1,2,3} 时徽章下方一行 small text『YYYY 年度档次（按全公司 20/70/10 分档）』；tier=null 时不显示该行"
    - "错误态：422 unbound / 404 employee_missing / 5xx error 分别显示与 Phase 32.1 MyEligibilityPanel 视觉一致的提示卡 + 重试按钮"
    - "Phase 32.1 MyEligibilityPanel 组件结构、文件内容保持零修改（仅 MyReview.tsx 追加一行 import + 一行渲染）"
    - "徽章**不**显示『优秀 / 合格 / 待提升』等语义标签（D-09）；**不**显示具体排名 / 百分位 / 同档其他人名单（PIPL 红线）"
  artifacts:
    - path: "frontend/src/components/performance/MyPerformanceTierBadge.tsx"
      provides: "员工自助档次徽章组件，5 状态 + 4 错误态 + 时间戳"
      contains: "export function MyPerformanceTierBadge"
      min_lines: 180
    - path: "frontend/src/pages/MyReview.tsx"
      provides: "在 <MyEligibilityPanel /> 紧邻下方渲染 <MyPerformanceTierBadge />"
      contains: "<MyPerformanceTierBadge />"
  key_links:
    - from: "frontend/src/components/performance/MyPerformanceTierBadge.tsx"
      to: "frontend/src/services/performanceService.ts:fetchMyTier"
      via: "useEffect + useState<LoadState> pattern"
      pattern: "fetchMyTier\\("
    - from: "frontend/src/pages/MyReview.tsx:import"
      to: "frontend/src/components/performance/MyPerformanceTierBadge.tsx"
      via: "import { MyPerformanceTierBadge } from '../components/performance/MyPerformanceTierBadge'"
      pattern: "MyPerformanceTierBadge"
    - from: "frontend/src/pages/MyReview.tsx (MyEligibilityPanel 后)"
      to: "<MyPerformanceTierBadge />"
      via: "JSX 兄弟元素紧邻"
      pattern: "<MyEligibilityPanel />[\\s\\S]{0,200}<MyPerformanceTierBadge />"
---

<objective>
为 Phase 35 前端交付可视化成果：新建 `frontend/src/components/performance/MyPerformanceTierBadge.tsx` 组件（镜像 Phase 32.1 `MyEligibilityPanel` 视觉风格 + Phase 32.1 OverallBadge 柔和色盘），在 `frontend/src/pages/MyReview.tsx` 中 `<MyEligibilityPanel />` 紧邻下方渲染该组件，并通过浏览器 UAT 验证 5 种数据状态 + 错误态 + 时间戳。

Purpose: 实现 ESELF-03 可视化交付 —— 员工看到 1/2/3 档或样本不足提示。本 plan 完全消费 Plan 03 的 types + fetchMyTier；严格遵守 Phase 32.1 D-03「仅追加不重构」约束 —— 不动 MyEligibilityPanel.tsx，不改 MyReview.tsx 的其他结构。

Output: 1 个新组件（≥ 180 行）+ MyReview.tsx 两处微调（1 行 import + 1 行 JSX）+ 浏览器 UAT 通过。
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/35-employee-self-service-experience/35-CONTEXT.md
@.planning/phases/32.1-employee-eligibility-visibility/32.1-CONTEXT.md
@frontend/src/components/eligibility/MyEligibilityPanel.tsx
@frontend/src/components/performance/TierChip.tsx
@frontend/src/pages/MyReview.tsx
@frontend/src/services/performanceService.ts
@frontend/src/types/api.ts

<interfaces>
<!-- Plan 03 交付 + Phase 32.1 视觉模板 -->

From frontend/src/types/api.ts (Plan 03):
```typescript
export interface MyTierResponse {
  year: number | null;
  tier: 1 | 2 | 3 | null;
  reason: 'insufficient_sample' | 'no_snapshot' | 'not_ranked' | null;
  data_updated_at: string | null;
}
```

From frontend/src/services/performanceService.ts (Plan 03):
```typescript
export async function fetchMyTier(): Promise<MyTierResponse>
```

Phase 32.1 LoadState union 模板（frontend/src/components/eligibility/MyEligibilityPanel.tsx:8-13）—— 本 plan 镜像此模式:
```typescript
type LoadState =
  | { kind: 'loading' }
  | { kind: 'success'; data: EligibilityResultWithTimestamp }
  | { kind: 'unbound' }
  | { kind: 'employee_missing' }
  | { kind: 'error'; message: string };
```

Phase 32.1 OverallBadge 柔和色盘参考（D-12 eligible 绿 / ineligible 红 / pending 黄）:
```typescript
// MyEligibilityPanel.tsx:132-144
eligible: { bg: '#d1fae5', color: '#065f46', ... }
ineligible: { bg: '#fee2e2', color: '#991b1b', ... }
pending: { bg: '#fef3c7', color: '#92400e', ... }
```

Phase 32.1 formatTimestamp 模板（MyEligibilityPanel.tsx:287-302）—— 本 plan 原样复刻:
```typescript
function formatTimestamp(iso: string | null): string {
  if (!iso) return '数据从未更新';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '数据时间无效';
  const formatter = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' });
  return `数据更新于 ${formatter.format(d)}`;
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: 新建 MyPerformanceTierBadge.tsx 组件</name>
  <files>frontend/src/components/performance/MyPerformanceTierBadge.tsx</files>
  <read_first>
    - frontend/src/components/eligibility/MyEligibilityPanel.tsx（完整视觉 / LoadState / formatTimestamp / 错误卡片风格）
    - frontend/src/components/performance/TierChip.tsx（确认不复用 —— D-07 明确要求独立组件）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-07/D-08/D-09/D-10 全部视觉规范 + specifics line 219-222 文案）
    - frontend/src/services/performanceService.ts（Plan 03 fetchMyTier 签名）
    - frontend/src/types/api.ts（Plan 03 MyTierResponse）
  </read_first>
  <action>
新建文件 `frontend/src/components/performance/MyPerformanceTierBadge.tsx`。**完整内容如下（从 D-07/D-08/D-09/D-10 逐字派生，不要改变色值、文案、样式常量）：**

```typescript
import axios from 'axios';
import { useCallback, useEffect, useState } from 'react';

import { fetchMyTier } from '../../services/performanceService';
import type { MyTierResponse } from '../../types/api';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'success'; data: MyTierResponse }
  | { kind: 'unbound' }
  | { kind: 'employee_missing' }
  | { kind: 'error'; message: string };

/**
 * Phase 35 ESELF-03: 员工自助绩效档次徽章
 *
 * 严格约束（D-07 / D-09 / Out of Scope PIPL 红线）：
 *  - 不显示具体排名 / 具体百分位 / 同档其他人名单
 *  - 不显示『优秀 / 合格 / 待提升』等语义标签（仅『1 档 / 2 档 / 3 档』纯数字）
 *  - 不复用 HR 端 TierChip（D-07「仅追加不重构」）
 *
 * 视觉镜像 Phase 32.1 MyEligibilityPanel（section 布局 / 时间戳 / 错误卡片）。
 * 横向越权天然不可达：fetchMyTier() 永远调 GET /performance/me/tier 无参
 * （由 JWT subject 决定 actor；ESELF-04 红线）。
 */
export function MyPerformanceTierBadge() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  const load = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      const data = await fetchMyTier();
      setState({ kind: 'success', data });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        if (status === 422) {
          setState({ kind: 'unbound' });
          return;
        }
        if (status === 404) {
          setState({ kind: 'employee_missing' });
          return;
        }
      }
      setState({ kind: 'error', message: '档次信息暂时不可用，请稍后重试' });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section
      className="surface px-6 py-8"
      data-testid="my-performance-tier-badge"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
        }}
      >
        <div>
          <p className="eyebrow">本期绩效</p>
          <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">
            本人绩效档次
          </h2>
        </div>
        {state.kind === 'success' ? (
          <span
            className="text-xs"
            style={{ color: 'var(--color-steel)' }}
            data-testid="tier-data-updated-at"
          >
            {formatTimestamp(state.data.data_updated_at)}
          </span>
        ) : null}
      </div>
      {state.kind === 'loading' ? <SkeletonBadge /> : null}
      {state.kind === 'success' ? <TierContent data={state.data} /> : null}
      {state.kind === 'unbound' ? <UnboundCard /> : null}
      {state.kind === 'employee_missing' ? <EmployeeMissingCard /> : null}
      {state.kind === 'error' ? (
        <ErrorCard message={state.message} onRetry={load} />
      ) : null}
    </section>
  );
}

function SkeletonBadge() {
  return (
    <div
      className="mt-4"
      aria-busy="true"
      data-testid="tier-skeleton"
      style={{ height: 56, opacity: 0.6 }}
    >
      <div
        className="surface-subtle animate-pulse"
        style={{ height: 56, width: 160, borderRadius: 999 }}
      />
    </div>
  );
}

/** D-08 三档柔和色盘（desaturated pastel，继承 Phase 32.1 OverallBadge 调性）。 */
const TIER_CONFIG: Record<
  1 | 2 | 3,
  { bg: string; color: string; label: string }
> = {
  1: { bg: '#d1fae5', color: '#065f46', label: '1 档' },
  2: { bg: '#fef3c7', color: '#92400e', label: '2 档' },
  3: { bg: '#ffedd5', color: '#9a3412', label: '3 档' },
};

/** D-08 灰底占位 + D-03 三种 reason 文案（specifics line 219-222）。 */
const NULL_REASON_CONFIG: Record<
  'insufficient_sample' | 'no_snapshot' | 'not_ranked',
  { label: string }
> = {
  insufficient_sample: { label: '本年度全公司绩效样本不足，暂不分档' },
  no_snapshot: { label: '本年度尚无档次数据，请等待 HR 录入后查看' },
  not_ranked: { label: '未找到您本年度的绩效记录，如有疑问请联系 HR' },
};

const GRAY_PLACEHOLDER = { bg: '#f3f4f6', color: '#6b7280' };

function TierContent({ data }: { data: MyTierResponse }) {
  // tier 有值：彩色徽章 + 下方 small text
  if (data.tier === 1 || data.tier === 2 || data.tier === 3) {
    const cfg = TIER_CONFIG[data.tier];
    return (
      <>
        <div className="mt-4">
          <span
            className="status-pill"
            data-testid={`tier-badge-${data.tier}`}
            style={{
              background: cfg.bg,
              color: cfg.color,
              fontSize: 14,
              padding: '6px 12px',
            }}
          >
            {cfg.label}
          </span>
        </div>
        {data.year !== null ? (
          <p
            className="mt-3 text-sm"
            data-testid="tier-rule-note"
            style={{ color: '#6b7280', fontSize: 14 }}
          >
            {data.year} 年度档次（按全公司 20/70/10 分档）
          </p>
        ) : null}
      </>
    );
  }

  // tier=null：灰底占位徽章 + reason 文案
  const reasonKey = data.reason ?? 'no_snapshot';
  const cfg = NULL_REASON_CONFIG[reasonKey];
  return (
    <div className="mt-4">
      <span
        className="status-pill"
        data-testid={`tier-badge-null-${reasonKey}`}
        style={{
          background: GRAY_PLACEHOLDER.bg,
          color: GRAY_PLACEHOLDER.color,
          fontSize: 14,
          padding: '6px 12px',
        }}
      >
        {cfg.label}
      </span>
    </div>
  );
}

function UnboundCard() {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="tier-unbound-card"
      style={{ background: '#f3f4f6' }}
    >
      <p className="text-sm text-ink">您的账号尚未绑定员工档案。</p>
      <p className="mt-2 text-sm" style={{ color: 'var(--color-steel)' }}>
        请前往账号设置完成绑定，然后再查看本人绩效档次。
      </p>
    </div>
  );
}

function EmployeeMissingCard() {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="tier-employee-missing-card"
      style={{ background: '#fef3c7' }}
    >
      <p className="text-sm text-ink">未找到您的员工档案。</p>
      <p className="mt-2 text-sm" style={{ color: 'var(--color-steel)' }}>
        您的账号绑定了一个不存在的员工记录，请联系 HR 核对。
      </p>
    </div>
  );
}

function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      className="mt-4 surface-subtle px-5 py-5"
      data-testid="tier-error-card"
      style={{ background: '#fef2f2' }}
    >
      <p className="text-sm" style={{ color: 'var(--color-danger)' }}>
        {message}
      </p>
      <button
        type="button"
        className="chip-button mt-3"
        onClick={onRetry}
        data-testid="tier-retry-button"
      >
        重试
      </button>
    </div>
  );
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return '数据从未更新';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) {
      return '数据时间无效';
    }
    const formatter = new Intl.DateTimeFormat('zh-CN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
    return `数据更新于 ${formatter.format(d)}`;
  } catch {
    return '数据时间无效';
  }
}
```

**严格要求（不可偏离）：**
- 徽章文案只能是 `1 档` / `2 档` / `3 档`（D-09）—— 不加『优秀 / 合格 / 待提升』等形容词
- 色值必须精确匹配 D-08：`#d1fae5 / #065f46 / #fef3c7 / #92400e / #ffedd5 / #9a3412 / #f3f4f6 / #6b7280`
- 灰底占位文案必须匹配 specifics line 219-222：`本年度全公司绩效样本不足，暂不分档` / `本年度尚无档次数据，请等待 HR 录入后查看` / `未找到您本年度的绩效记录，如有疑问请联系 HR`（逐字）
- 徽章下方小字必须为 `YYYY 年度档次（按全公司 20/70/10 分档）`（specifics line 222，transparency 合规）
- 组件**不得**复用 `frontend/src/components/performance/TierChip.tsx`（D-07 明确约束；TierChip 是 HR 端 summary 用）
- 组件**不得** import 任何 MyEligibilityPanel 的子组件 / 函数 —— 风格一致通过 CSS class + 柔和色盘派生，不做代码复用
- data-testid 前缀一律 `tier-` 以区别 MyEligibilityPanel 的同名 testid（`tier-data-updated-at` / `tier-skeleton` / `tier-badge-*` / `tier-unbound-card` / `tier-employee-missing-card` / `tier-error-card` / `tier-retry-button` / `tier-rule-note`）
- 组件不接受任何 props —— `MyPerformanceTierBadge()` 零参数，自己用 useEffect 拉取数据（与 MyEligibilityPanel 一致模式）

**禁止：**
- 不要显示 `data.year` 之外任何年份相关 UI（如 year selector）—— ESELF-04
- 不要显示百分位条 / 直方图 / tier 分布图（Deferred Ideas）
- 不要显示「如何改善档次」按钮 / 申诉按钮（Deferred Ideas v1.5+）
- 不要加 localStorage 缓存 / React Query（Deferred Ideas）
- 不要加 aria-live 公告（超出 Phase 32.1 基线；若无障碍要求升级，留给 v1.5+）
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust/frontend && npx tsc --noEmit 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - 文件 `frontend/src/components/performance/MyPerformanceTierBadge.tsx` 存在
    - `grep -c "^" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 输出 ≥ 180（文件行数）
    - `grep -n "export function MyPerformanceTierBadge()" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中
    - `grep -n "'#d1fae5'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（1 档背景色）
    - `grep -n "'#065f46'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（1 档文字色）
    - `grep -n "'#fef3c7'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（2 档背景色）
    - `grep -n "'#92400e'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（2 档文字色）
    - `grep -n "'#ffedd5'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（3 档背景色）
    - `grep -n "'#9a3412'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（3 档文字色）
    - `grep -n "'#f3f4f6'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（灰底）
    - `grep -n "'#6b7280'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（灰底文字色）
    - `grep -n "'1 档'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中
    - `grep -n "'2 档'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中
    - `grep -n "'3 档'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中
    - `grep -n "本年度全公司绩效样本不足，暂不分档" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（逐字）
    - `grep -n "本年度尚无档次数据，请等待 HR 录入后查看" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（逐字）
    - `grep -n "未找到您本年度的绩效记录，如有疑问请联系 HR" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（逐字）
    - `grep -n "20/70/10 分档" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（transparency 合规文案）
    - `grep -n "本期绩效" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（eyebrow）
    - `grep -n "本人绩效档次" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中（h2 title）
    - `grep -n "fetchMyTier" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中
    - `grep -cE "优秀|合格|待提升" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 输出 0（D-09 禁止形容词）
    - `grep -cE "TierChip|import.*TierChip" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 输出 0（D-07 不复用）
    - `grep -cE "percentile|rank|排名|百分位" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 输出 0（PIPL 红线）
    - `grep -n "Intl.DateTimeFormat('zh-CN'" frontend/src/components/performance/MyPerformanceTierBadge.tsx` 命中
    - `cd frontend && npx tsc --noEmit` 退出码 0
  </acceptance_criteria>
  <done>组件文件创建完成；色值/文案/标题/eyebrow 与 D-07..D-10 逐字一致；tsc 通过；未引用 TierChip / MyEligibilityPanel 子组件；禁止词 0 出现。</done>
</task>

<task type="auto">
  <name>Task 2: 在 MyReview.tsx 渲染 MyPerformanceTierBadge</name>
  <files>frontend/src/pages/MyReview.tsx</files>
  <read_first>
    - frontend/src/pages/MyReview.tsx（当前 line 14 `MyEligibilityPanel` import + line 545 `<MyEligibilityPanel />` 渲染位置 + 周围 5 行 context）
    - .planning/phases/35-employee-self-service-experience/35-CONTEXT.md（D-07 插入位置 —— MyEligibilityPanel 紧邻下方）
  </read_first>
  <action>
在 `frontend/src/pages/MyReview.tsx` 做精确两处修改：

**Modification A — 追加 import（line 14 之后）：**

找到当前第 14 行：
```typescript
import { MyEligibilityPanel } from '../components/eligibility/MyEligibilityPanel';
```

在其**下一行**（即 line 15 位置）追加：
```typescript
import { MyPerformanceTierBadge } from '../components/performance/MyPerformanceTierBadge';
```

**Modification B — 在 <MyEligibilityPanel /> 紧邻下方渲染（当前 line 545 后）：**

找到当前 542-545 行的 block：
```tsx
      {/* Phase 32.1 ESELF-01/02/04/05: 员工自助调薪资格 panel
          位置：在「当前角色 actions」标头之后、「材料与提交概览」section 之前（D-10）
          独立于 employee 匹配 —— panel 直接调 /eligibility/me 由 user.employee_id 决定 */}
      <MyEligibilityPanel />
```

在 `<MyEligibilityPanel />` **紧邻其后**（同级 JSX 兄弟元素），追加：

```tsx
      {/* Phase 35 ESELF-03: 员工自助绩效档次徽章
          位置：在 MyEligibilityPanel 紧邻下方，独立 section（D-07）
          独立于 employee 匹配 —— 组件直接调 /performance/me/tier 由 JWT subject 决定
          数据源与 MyEligibilityPanel 独立（各自显示自己的 data_updated_at，D-05） */}
      <MyPerformanceTierBadge />
```

**明确禁止：**
- 不要修改 MyEligibilityPanel import 行
- 不要移动 `<MyEligibilityPanel />` 的位置
- 不要把两个组件包在同一个 `<div>` / `<section>` 里 —— 各自独立 section（D-07）
- 不要传 props 给 `<MyPerformanceTierBadge />` —— 零参数组件（Task 1 约束）
- 不要在 `<MyPerformanceTierBadge />` 之前/之后插入其他 panel（如历史绩效 —— 那是 Phase 36 的 scope）
- 不要改动 MyReview.tsx 其他部分（toast / DuplicateWarningModal / 文件上传 section 等）
  </action>
  <verify>
    <automated>cd /Users/mac/PycharmProjects/Wage_adjust/frontend && npx tsc --noEmit 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "import { MyPerformanceTierBadge } from '../components/performance/MyPerformanceTierBadge';" frontend/src/pages/MyReview.tsx` 命中 1 行
    - `grep -n "<MyPerformanceTierBadge />" frontend/src/pages/MyReview.tsx` 命中 1 行
    - `grep -n "<MyEligibilityPanel />" frontend/src/pages/MyReview.tsx` 命中（原位保留）
    - `grep -Pzo "(?s)<MyEligibilityPanel />.{0,300}<MyPerformanceTierBadge />" frontend/src/pages/MyReview.tsx` 命中（两者相邻 300 字符内，注释允许存在）
    - `cd frontend && npx tsc --noEmit` 退出码 0
    - `git diff frontend/src/pages/MyReview.tsx | grep -cE "^\-" | head -1`（统计删除行数）输出 ≤ 1（仅计 git diff 头；正常 import 追加不删除任何行）
  </acceptance_criteria>
  <done>MyReview.tsx 仅两处变更：1 行 import 追加 + 1 行 JSX 追加（加注释块）；tsc 通过；其他部分 0 修改。</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: 浏览器 UAT 验证 5 种数据状态 + 3 种错误态 + 合规红线</name>
  <files>frontend/src/components/performance/MyPerformanceTierBadge.tsx, frontend/src/pages/MyReview.tsx</files>
  <what-built>
Phase 35 员工自助档次徽章完整交付：后端 `GET /api/v1/performance/me/tier` + 前端 `MyPerformanceTierBadge` 组件。在 MyReview 页面 `MyEligibilityPanel` 下方应看到独立 `本人绩效档次` section，支持 5 种数据状态 + 3 种错误态 + 时间戳显示。
  </what-built>
  <action>
人工浏览器 UAT —— 对照 `<how-to-verify>` 11 条 Test Case，逐项执行并记录实际结果。具体环境启停、数据构造、操作步骤见 `<how-to-verify>`。执行者必须使用真实浏览器（Chrome / Firefox 任一最新稳定版）+ F12 Network 面板 + Elements 面板验证 DOM。
  </action>
  <how-to-verify>

**前置准备：**
1. 后端启动：`cd /Users/mac/PycharmProjects/Wage_adjust && .venv/bin/uvicorn backend.app.main:app --reload`
2. 前端启动：`cd /Users/mac/PycharmProjects/Wage_adjust/frontend && npm run dev`
3. 浏览器打开 `http://localhost:5174`
4. 若 DB 为空，先用 admin 账号导入 performance_records（Phase 32 导入页）并点击「重算档次」（Phase 34 绩效管理页）生成 snapshot

**Test Case 1 — tier=1 绿底徽章（员工有档次，当前年）：**
1. 确保当前年 PerformanceTierSnapshot 存在且某员工在 tiers_json 里 = 1
2. 用该员工账号登录（或 admin/hrbp/manager 绑定到该员工后登录）
3. 导航到 `/my-review`
4. 预期在 `本人调薪资格` section 下方看到独立 `本期绩效 / 本人绩效档次` section
5. 徽章背景色：绿（近似 #d1fae5），文字色深绿（#065f46），文案：`1 档`
6. 徽章下方一行小字（灰 #6b7280）：`2026 年度档次（按全公司 20/70/10 分档）`
7. 右上角：`数据更新于 YYYY年MM月DD日 HH:MM`（zh-CN medium + short，无秒）

**Test Case 2 — tier=2 黄底 / tier=3 橙底：**
1. 更换员工（或手动修改 tiers_json）到 tier=2 + tier=3
2. 逐一验证：
   - tier=2：背景 #fef3c7 黄，文字 #92400e，文案 `2 档`
   - tier=3：背景 #ffedd5 橙，文字 #9a3412，文案 `3 档`
3. 下方小字在 2/3 档仍正确显示年份和『按全公司 20/70/10 分档』

**Test Case 3 — insufficient_sample（样本不足）：**
1. 构造一个 PerformanceTierSnapshot 使 insufficient_sample=True（可在 HR 端把 performance_tier_min_sample_size 调大到 1000，触发重算）
2. 或直接操作 DB：`UPDATE performance_tier_snapshots SET insufficient_sample = 1 WHERE year = 2026;`
3. 刷新员工页面
4. 预期：灰底徽章（#f3f4f6 / #6b7280），文案：`本年度全公司绩效样本不足，暂不分档`
5. 徽章下方**不**显示『20/70/10』小字（tier=null 时不渲染 rule-note）

**Test Case 4 — no_snapshot（全库无快照）：**
1. 删除所有 PerformanceTierSnapshot 行：`DELETE FROM performance_tier_snapshots;`
2. 刷新员工页面
3. 预期：灰底徽章，文案：`本年度尚无档次数据，请等待 HR 录入后查看`
4. 右上时间戳显示：`数据从未更新`

**Test Case 5 — not_ranked（员工不在 tiers_json）：**
1. 恢复一个 PerformanceTierSnapshot 但 tiers_json 里没有当前员工 id
2. 刷新员工页面
3. 预期：灰底徽章，文案：`未找到您本年度的绩效记录，如有疑问请联系 HR`

**Test Case 6 — fallback 到旧年：**
1. 删除当前年快照，保留 2025 年快照（tiers_json 含当前员工）
2. 刷新员工页面
3. 预期：徽章显示正确档次；下方小字显示 `2025 年度档次（按全公司 20/70/10 分档）`（注意 year 是 2025 非当前年）

**Test Case 7 — 未绑定 422：**
1. 用一个未绑定员工的 user 账号登录（或在 DB 手动置 `users.employee_id = NULL`）
2. 访问 `/my-review`
3. 预期：灰底卡片（#f3f4f6）`您的账号尚未绑定员工档案。请前往账号设置完成绑定，然后再查看本人绩效档次。`
4. （同时 MyEligibilityPanel 也会显示 unbound，两者视觉一致）

**Test Case 8 — 员工被删 404：**
1. 员工账号登录 → 用 admin 在数据库删除其 Employee 行（保留 User）
2. 刷新员工页面
3. 预期：黄底卡片（#fef3c7）`未找到您的员工档案。您的账号绑定了一个不存在的员工记录，请联系 HR 核对。`

**Test Case 9 — 5xx 错误 + 重试：**
1. 停止后端服务
2. 刷新员工页面
3. 预期：红色 `档次信息暂时不可用，请稍后重试` + `重试` 按钮（data-testid="tier-retry-button"）
4. 点击「重试」按钮应触发重新请求

**Test Case 10 — 合规 / PIPL 红线：**
1. 任一成功状态（Test Case 1-6）打开浏览器 Network 面板查看 `/api/v1/performance/me/tier` 响应体
2. 预期：响应 JSON 仅 4 个 key（year / tier / reason / data_updated_at）；绝对不应出现 `peer_ids` / `percentile` / `rank` / `tiers_json` / `sample_size` 等字段
3. 页面 DOM 检查（F12 → Elements）：徽章文案不包含『优秀』『合格』『待提升』等形容词，不显示任何数字排名或百分位条

**Test Case 11 — 视觉连贯性：**
1. 在 tier=1 状态下同时观察 MyEligibilityPanel 和 MyPerformanceTierBadge
2. 预期：两个 section 间距合理（继承 AppShell 默认垂直节流），eyebrow / h2 标题字重字号一致，柔和色盘视觉调性一致（绿色相同基调）

**通过条件：** Test Case 1-11 全部通过。
  </how-to-verify>
  <verify>
    <automated>echo "MANUAL_UAT_REQUIRED: 人工按 how-to-verify 执行 Test Case 1-11 并在 <resume-signal> 反馈 approved/failed"</automated>
  </verify>
  <resume-signal>
用户在完成上述 11 条 UAT 后回复：
- `approved` —— 全部通过，plan 完成
- `failed: <描述>` —— 具体哪条失败（贴截图或 DOM 片段）
  </resume-signal>
  <acceptance_criteria>
    - 用户在 resume-signal 回复 `approved`（ 11 条 Test Case 全部通过）
    - 若失败，执行者修复后重跑 Task 1 或 Task 2 直到 UAT 通过
  </acceptance_criteria>
  <done>11 条 Test Case 全部通过；用户书面回复 `approved`；Phase 32.1 MyEligibilityPanel 视觉完整（`git diff frontend/src/components/eligibility/MyEligibilityPanel.tsx` 输出为空，作为 PR 前最终 sanity check）。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 员工浏览器 → Frontend React app | 员工通过 DOM / Network 面板可见自己的响应体；非越权场景 |
| Frontend → Backend (Plan 02) | fetchMyTier 调用 `/performance/me/tier`；无参数路由，越权天然不可达 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-35-04-01 | A02 Sensitive Data Exposure / I | MyPerformanceTierBadge 徽章文案 | mitigate | 徽章只显示 `1 档/2 档/3 档` 或 3 种中性 reason 文案；不含具体排名 / 百分位 / 同档名单。Task 1 acceptance 负向 `grep -cE "percentile\|rank\|排名\|百分位" = 0` + Task 3 UAT Test Case 10 DOM 检查 |
| T-35-04-02 | A02 / I | data_updated_at 时间戳 | accept | 显示精度到分钟（无秒）；不泄露系统内部 tick 或 DB 行版本 |
| T-35-04-03 | I | 用户心理冲击 | mitigate (UX 合规考量) | 3 档色值选择 `#ffedd5` 温和橙（非红），避免刺眼；CONTEXT.md specifics line 221 明确要求降低 3 档员工心理冲击 |
| T-35-04-04 | A01 Broken Access Control | fetchMyTier 无 params | mitigate | 组件完全不接受 props，service 函数签名 `fetchMyTier(): Promise<MyTierResponse>` 无参；TypeScript 类型检查保证调用方不能传额外参数 |
| T-35-04-05 | T (Tampering) | Browser devtools 修改 state | accept | 员工在自己浏览器修改 React state 只影响自己的显示；真实数据由后端响应决定，不存在越权面 |
| T-35-04-06 | R (Repudiation) | 前端无审计 | accept | 员工读自己档次无需审计；后端访问日志已足够 |
| T-35-04-07 | D (DoS) | 重试按钮刷屏 | accept | 用户手动点击频率有限；无自动重试循环（Deferred Ideas 明确「沿用 Phase 32.1 手动重试」） |
</threat_model>

<verification>
- Task 3 UAT Test Case 1-11 全部通过
- `cd frontend && npx tsc --noEmit` 退出码 0
- `cd frontend && npm run build` 退出码 0（可选，确认生产构建也通过）
- 组件 grep 静态断言（色值、文案、禁止词）全部通过
- MyReview.tsx 仅两处变更（import + JSX），其他部分 git diff 为空
</verification>

<success_criteria>
1. `MyPerformanceTierBadge` 组件存在，5 种 tier 状态 + 3 种错误状态全部可渲染
2. 色值、文案、布局与 D-07..D-10 逐字一致（grep 验证 + UAT 目视）
3. MyReview.tsx 中 `<MyPerformanceTierBadge />` 在 `<MyEligibilityPanel />` 紧邻下方
4. Phase 32.1 MyEligibilityPanel 组件零修改（`git diff frontend/src/components/eligibility/MyEligibilityPanel.tsx` 输出为空 —— 可作为最终 PR 前的 sanity check）
5. 无具体排名 / 百分位 / 同档名单（PIPL 红线；Task 1 acceptance + Task 3 UAT 双重保证）
6. 时间戳 zh-CN medium + short 格式，reason='no_snapshot' 时显示『数据从未更新』
</success_criteria>

<output>
After completion, create `.planning/phases/35-employee-self-service-experience/35-04-SUMMARY.md`
</output>
