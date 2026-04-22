---
phase: 34
slug: performance-management-service-and-api
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-22
---

# Phase 34 — UI Design Contract

> Phase 34（HR 独立「绩效管理」页面）的视觉与交互契约。
> 由 gsd-ui-researcher 生成，gsd-ui-checker 验证。
> 本契约严格执行 CONTEXT.md 锁定决策 D-11 / D-12 / D-13 / D-14；其他细节按 Claude's Discretion 在本文件锁定。

---

## 0. CONTEXT 反向勘误（必读）

CONTEXT.md 中两处技术栈描述与本仓库实际不符，本 UI-SPEC 以**仓库实际栈**为准，不引入新依赖：

| CONTEXT.md 表述 | 仓库实际 | 本 SPEC 决议 |
|----------------|---------|-------------|
| 「Recharts `<BarChart layout="vertical">`」 | `echarts` 6.0.0 + `echarts-for-react` 3.0.6（`frontend/package.json` line 14-15） | 用 ECharts horizontal stacked bar；视觉、颜色、堆叠语义不变；下文给出完整 `option` 配置 |
| 「lucide-react `<RefreshCw>`」 | 项目零图标库依赖；现有 nav 图标用 `frontend/src/components/icons/NavIcons.tsx` 中的内联 SVG | 在 `frontend/src/components/icons/NavIcons.tsx` 新增 `RefreshIcon`（16×16 stroke-based 内联 SVG），不引入 lucide-react |

executor 在 plan 阶段必须遵循此勘误；planner 任务需指明使用 ECharts + 内联 SVG。

---

## 1. Design System

| Property | Value |
|----------|-------|
| Tool | none（项目零 shadcn / Radix / Headless UI；纯 Tailwind 3.4 + CSS variables 自建组件类） |
| Preset | not applicable |
| Component library | none（自建组件 + `frontend/src/index.css` `@layer components` 内的 utility classes：`.surface` `.section-head` `.action-primary` `.chip-button` `.table-shell` `.table-lite` `.empty-state` `.status-pill` `.toolbar-input`） |
| Icon library | 内联 SVG（`frontend/src/components/icons/NavIcons.tsx`）— 16×16 stroke-based，`stroke="currentColor"` `strokeWidth={1.75}` |
| Charting | `echarts` 6.0.0 + `echarts-for-react` 3.0.6（已装；不新增 Recharts） |
| Font | `"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif`（在 `:root` 全局声明） |

**复用清单（不重新设计）：**

- 整体页面结构：复用 `<AppShell title="绩效管理" description="...">`（`frontend/src/components/layout/AppShell.tsx`）— 与 `EligibilityManagementPage.tsx` 同款外壳
- 导入 section：直接 `<ExcelImportPanel importType="performance_grades" label="绩效等级" onComplete={handleImportComplete} />`（Phase 32 已交付组件，Phase 34 零额外开发）
- 列表表格视觉：基线复用 `.table-shell` + `.table-lite` 样式系统（`frontend/src/index.css` line 526-574）
- Filter 控件：复用 `.toolbar-input`（`frontend/src/index.css` line 283-308）
- Sidebar 菜单项：在现有 `NavMenu` 组件追加「绩效管理」label + roleAccess.ts 配置 `'/performance': ['admin', 'hrbp']`，菜单图标用 `NavIcons.tsx` 内已有的 `LineChartIcon`（如无则复用最接近图标，executor 视情况新增 `PerformanceIcon`）

---

## 2. Spacing Scale

| Token | Value | Usage in Phase 34 |
|-------|-------|------------------|
| xs | 4px | chip 内 icon 与文字间隙、status-pill 内边距 |
| sm | 8px | filter 控件之间间距、stacked bar 与 chip 行的间距、表格行内多元素间距 |
| md | 16px | 三个 section 之间垂直间距（`space-y-4`）、section 内 head 与 body 间距 |
| lg | 24px | section 内边距（`.surface` 内部 padding） |
| xl | 32px | warning 横幅上下 margin 在桌面端的呼吸空间（仅当横幅可见时） |
| 2xl | 48px | 「立即生成档次」空状态垂直内边距（`.empty-state` 默认 40px，本 phase 沿用，归到 2xl 槽位） |
| 3xl | 64px | 不在 Phase 34 使用 |

**例外：**
- ECharts stacked bar 高度固定 `32px`（高度本身不属于 spacing scale，而是图表容器尺寸；与 spacing 系统正交）
- `.toolbar-input` 高度 `34px`、`.action-primary` / `.action-secondary` 高度 `34px`（已在 `:root` 组件类锁定，Phase 34 不调整）
- 表格 `<th>` padding `9px 14px`、`<td>` padding `11px 14px`（来自 `.table-lite` 既有规则，Phase 34 不调整）

---

## 3. Typography

项目零自定义 type scale（`tailwind.config.js` 未扩展 `fontSize`），全部由 `:root` 内 component classes 声明。Phase 34 复用现有 4 角色：

| Role | Size | Weight | Line Height | 在 Phase 34 用于 |
|------|------|--------|-------------|---------------|
| Page title | 20px | 600 | 1.3 | AppShell 顶部 "绩效管理"（`.page-title` 类） |
| Section title | 15px | 600 | 1.4 | "档次分布视图" / "绩效记录导入" / "绩效记录列表"（`.section-title` 类） |
| Body / Table cell | 13.5px | 400 | 1.5 | 表格 td、chip 文本、warning 横幅、computed_at 时间戳（`.table-lite` td / inline 默认） |
| Label / Meta | 12px | 500 | 1.5 | 表头 th（uppercase + letter-spacing 0.04em）、status-pill、chip 内统计数字、`.section-note`（13px line-height 1.6） |

**Weights：** `400`（regular）+ `600`（semibold）— 严格 2 档，与 :root 现有规则一致。
**Line heights：** body 1.5（默认）+ heading 1.3-1.4（已在组件类内声明）。

**Phase 34 不引入：** display 角色、新字号、新字重、italic。

---

## 4. Color (60 / 30 / 10)

全部 token 已在 `frontend/src/index.css` `:root` 声明，Phase 34 **零新增 token**。

| Role | Value | Usage in Phase 34 |
|------|-------|------------------|
| Dominant (60%) | `#F5F6F8` (`--color-bg-page`) + `#FFFFFF` (`--color-bg-surface`) | 页面背景 + 三个 section 卡片背景（`.surface`） |
| Secondary (30%) | `#F2F3F5` (`--color-bg-subtle`) + `#E0E4EA` (`--color-border`) | 表头底色（`.table-lite thead`）、filter 区底色、divider |
| Accent (10%) | `#1456F0` (`--color-primary`) | **仅用于以下元素**（accent 严格枚举）： |
|              |                | 1. AppShell sidebar 当前激活菜单项「绩效管理」（已有 nav-link-active 规则） |
|              |                | 2. 「重算档次」`.action-primary` 按钮 |
|              |                | 3. 「立即生成档次」空状态 CTA `.action-primary` 按钮 |
|              |                | 4. filter 控件 focus ring（`box-shadow: 0 0 0 3px rgba(20, 86, 240, 0.10)`） |
|              |                | 5. 分页器当前页码高亮 |
| Destructive | `#F53F3F` (`--color-danger`) | 不在 Phase 34 使用（无删除/危险动作） |

**语义色（不计入 60/30/10，按状态触发）：**

| Status Color | Token | Phase 34 用途 |
|-------------|-------|--------------|
| 成功绿 | `#10b981`（堆叠条 1 档专用）+ `#00B42A` (`--color-success`) + `#E8FFEA` (`--color-success-bg`) | 1 档堆叠条 / chip / 成功 toast 背景 |
| 警告黄 | `#f59e0b`（堆叠条 2 档专用）+ `#FF7D00` (`--color-warning`) + `#FFF3E8` (`--color-warning-bg`) + `#FFD8A8` (`--color-warning-border`) | 2 档堆叠条 / 「分布偏离」黄色 warning 横幅 / 重算 busy toast |
| 危险红 | `#ef4444`（堆叠条 3 档专用）+ `#F53F3F` (`--color-danger`) + `#FFECE8` (`--color-danger-bg`) | 3 档堆叠条 / 重算失败 toast |
| 中性灰 | `#646A73` (`--color-steel`) + `#8F959E` (`--color-placeholder`) | 「未分档」chip 文字 / 「—」NULL 占位文字 / computed_at 时间戳辅助文字 |

**3 档堆叠条颜色（D-11 锁定）：**
- 1 档：`#10b981`（emerald-500）
- 2 档：`#f59e0b`（amber-500）
- 3 档：`#ef4444`（red-500）

> 注意：3 档堆叠条故意使用比 `:root` 语义色**饱和度更高**的 Tailwind 标准色，与 GitHub Insights contributor bar 视觉对齐（CONTEXT.md specifics 指定）。`:root` 内的 `--color-success` 等是 UI status 用色，与图表用色分开，executor 不要互换。

**Accent 不允许扩散到：** 表头、表格行、chip 默认态、年份 select 默认态、副标题、分隔线。

---

## 5. Page Layout（D-13 锁定）

```
┌────────────────────────────────────────────────────────────────┐
│ <AppShell                                                       │
│   title="绩效管理"                                              │
│   description="HR 端：导入绩效记录、查看档次分布、手动触发重算">│
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ Section 1: 档次分布视图（.surface）                     │  │
│   │   - section-head: title「档次分布」+ 右侧[年份 select]  │  │
│   │     + [重算档次] button + computed_at 时间戳           │  │
│   │   - 黄色 warning 横幅（条件渲染）                       │  │
│   │   - ECharts horizontal stacked bar (height: 32px)       │  │
│   │   - 三档计数 chip 行（4 个 chip 横向 flex）             │  │
│   └─────────────────────────────────────────────────────────┘  │
│                          ↕ 16px gap                             │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ Section 2: 绩效记录导入（.surface）                     │  │
│   │   - section-head: title「绩效记录导入」                 │  │
│   │   - <ExcelImportPanel importType="performance_grades">  │  │
│   │     ↑ Phase 32 已交付，零额外设计                       │  │
│   └─────────────────────────────────────────────────────────┘  │
│                          ↕ 16px gap                             │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │ Section 3: 绩效记录列表（.surface）                     │  │
│   │   - section-head: title「绩效记录」                     │  │
│   │   - Filter row: [年份 select] [部门 select] [搜索框?]   │  │
│   │   - .table-shell + .table-lite (7 列)                   │  │
│   │   - 分页器（底部）                                      │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│ </AppShell>                                                     │
└────────────────────────────────────────────────────────────────┘
```

**外层间距：** `<div className="space-y-4">` 包裹三个 section（`gap: 16px`，与 `EligibilityManagementPage` 的 `space-y-5` 略小，因为本页 section 数量更少且每 section 内容更密集）。

**所属页面文件：** `frontend/src/pages/PerformanceManagementPage.tsx`（新建）。

---

## 6. Section 1: 档次分布视图（D-11 / D-12 详细规格）

### 6.1 Section Head

```tsx
<div className="section-head">
  <div>
    <h3 className="section-title">档次分布</h3>
    <p className="section-note">基于 PERCENT_RANK 算法对全公司绩效记录分档（1/2/3）</p>
  </div>
  <div className="flex items-center gap-2">
    {/* 年份 select */}
    <select className="toolbar-input" value={year} onChange={...}>
      {availableYears.map((y) => <option key={y} value={y}>{y} 年</option>)}
    </select>
    {/* 重算按钮 */}
    <button
      className="action-primary"
      onClick={handleRecompute}
      disabled={isRecomputing}
      aria-busy={isRecomputing}
    >
      <RefreshIcon className={isRecomputing ? 'animate-spin' : undefined} />
      {isRecomputing ? '重算中…' : '重算档次'}
    </button>
  </div>
</div>
{computedAt && (
  <p className="text-xs" style={{ color: 'var(--color-placeholder)', marginTop: -8, marginBottom: 12 }}>
    最近重算：{formatZhDateTime(computedAt)}
  </p>
)}
```

**computed_at 格式：** `Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(computedAt))` → 「2026年4月22日 18:30」。

**RefreshIcon（新增到 NavIcons.tsx）：**

```tsx
export function RefreshIcon(props: IconProps) {
  return svg(props, (
    <>
      <path d="M21 12a9 9 0 1 1-3.5-7.1" />
      <polyline points="21 4 21 10 15 10" />
    </>
  ));
}
```

旋转动画用 Tailwind `animate-spin`（已在 Tailwind 默认 utilities 中）。

### 6.2 黄色 Warning 横幅（条件渲染）

**触发：** `tierSummary.distribution_warning === true`
**渲染：**

```tsx
<div
  role="alert"
  style={{
    padding: '12px 16px',
    borderRadius: 6,
    background: 'var(--color-warning-bg)',
    border: '1px solid var(--color-warning-border)',
    color: 'var(--color-warning)',
    fontSize: 13.5,
    lineHeight: 1.5,
    marginBottom: 16,
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
  }}
>
  <WarningIcon size={16} style={{ marginTop: 2, flexShrink: 0 }} />
  <span>
    档次分布偏离 20/70/10 超过 ±5%（实际{' '}
    <strong>
      {pct(actual_distribution['1'])}/{pct(actual_distribution['2'])}/{pct(actual_distribution['3'])}
    </strong>
    ）。建议复核绩效原始数据或调整评估口径。
  </span>
</div>
```

**WarningIcon：** 三角形感叹号，新增到 `NavIcons.tsx`（路径见 executor plan）。

**重算失败横幅变体（D-04）：** 重算失败时同样使用此 warning 横幅样式，文本替换为「档次基于 {旧 computed_at} 的旧快照（重算失败，请重试）」+ 内联「立即重算」链接（用 `chip-button` 样式 + `color: var(--color-warning)` 覆盖）。

### 6.3 ECharts Horizontal Stacked Bar

**容器：** 高度固定 32px，宽度 100%，圆角 4px。

```tsx
<div style={{ height: 32, width: '100%', marginBottom: 12 }}>
  <ReactECharts
    option={{
      grid: { left: 0, right: 0, top: 0, bottom: 0, containLabel: false },
      tooltip: {
        trigger: 'item',
        backgroundColor: '#FFFFFF',
        borderColor: '#E0E4EA',
        borderWidth: 1,
        textStyle: { color: '#1F2329', fontSize: 13 },
        padding: [6, 10],
        formatter: (p: { seriesName: string; value: number; data: { count: number } }) =>
          `${p.seriesName}：${p.data.count} 人 (${(p.value * 100).toFixed(1)}%)`,
      },
      xAxis: { type: 'value', show: false, max: 1 },
      yAxis: { type: 'category', show: false, data: [''] },
      series: [
        {
          name: '1 档',
          type: 'bar',
          stack: 'total',
          data: [{ value: actual_distribution['1'], count: tiers_count['1'] }],
          itemStyle: { color: '#10b981', borderRadius: [4, 0, 0, 4] },
          barWidth: '100%',
        },
        {
          name: '2 档',
          type: 'bar',
          stack: 'total',
          data: [{ value: actual_distribution['2'], count: tiers_count['2'] }],
          itemStyle: { color: '#f59e0b' },
          barWidth: '100%',
        },
        {
          name: '3 档',
          type: 'bar',
          stack: 'total',
          data: [{ value: actual_distribution['3'], count: tiers_count['3'] }],
          itemStyle: { color: '#ef4444', borderRadius: [0, 4, 4, 0] },
          barWidth: '100%',
        },
      ],
    }}
    style={{ height: '100%', width: '100%' }}
  />
</div>
```

**条内是否显示 label：** **不显示**（条高 32px，文字会拥挤；具体数字下移到 chip 行 + tooltip）。
**Tooltip：** 鼠标 hover 单段 → 「1 档：247 人 (20.0%)」（数字 + 中文，1 位小数）。

### 6.4 三档计数 Chip 行

**布局：** `flex flex-wrap gap-2`，4 个 chip 横向排列。
**Chip 样式：** 复用 `.chip-button` 但**不可点击**（使用 `<span>` 替换 `<button>`，移除 `cursor: pointer`，去掉 hover 态）。

```tsx
<div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
  <TierChip color="#10b981" label="1 档" count={247} pct={0.20} />
  <TierChip color="#f59e0b" label="2 档" count={864} pct={0.70} />
  <TierChip color="#ef4444" label="3 档" count={123} pct={0.10} />
  <UnTieredChip count={0} />
</div>
```

**TierChip 内部：**

```tsx
<span
  className="status-pill"
  style={{
    padding: '4px 10px',
    fontSize: 13,
    background: '#FFFFFF',
    border: `1px solid ${color}`,
    color: 'var(--color-ink)',
    gap: 6,
  }}
>
  <span
    style={{
      display: 'inline-block',
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: color,
      flexShrink: 0,
    }}
  />
  {label} <strong style={{ fontWeight: 600 }}>{count}</strong> 人 ({(pct * 100).toFixed(0)}%)
</span>
```

**UnTieredChip：** 同样 status-pill 形态，但边框用 `var(--color-border)`，圆点改为 `var(--color-placeholder)`，文字「未分档 N 人」。

---

## 7. Section 2: 绩效记录导入（D-13 复用声明）

**实现：** 整段直接复用 `<ExcelImportPanel importType="performance_grades" label="绩效等级" onComplete={handleImportComplete} />`。

**视觉契约：** **完全沿用 Phase 32 ExcelImportPanel 全套视觉**（7-state union：idle / uploading / previewing / confirming / done / cancelled / error），本 Phase 34 **零新增视觉规范**。Phase 32 SUMMARY 中已记录的 minor a11y 缺陷不在本 Phase 修复范围。

**交互契约：**
- `onComplete` 回调触发后，PerformanceManagementPage 必须：
  1. Toast「{inserted} 条新增 / {updated} 条更新成功」
  2. 重新拉取 `GET /tier-summary?year={当前选中年}`（D-03 路径）
  3. 重新拉取 `GET /performance/records?...{当前 filter}`
- import confirm 返回 202（重算 in_progress）时，section-head 的 computed_at 文字临时改为「档次正在重算…」+ 启动 5 秒一次的轮询，直到 `computed_at` 时间戳变化或 30 秒超时（超时显示 toast「重算超时，请刷新页面查看最新档次」）。

---

## 8. Section 3: 绩效记录列表（D-14 锁定）

### 8.1 Filter Row

```tsx
<div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
  <select className="toolbar-input" style={{ minWidth: 120 }} value={filterYear} onChange={...}>
    <option value="">全部年份</option>
    {availableYears.map((y) => <option key={y} value={y}>{y} 年</option>)}
  </select>
  <select className="toolbar-input" style={{ minWidth: 160 }} value={filterDepartment} onChange={...}>
    <option value="">全部部门</option>
    {departments.map((d) => <option key={d} value={d}>{d}</option>)}
  </select>
  {/* 暂不实现搜索框，留至未来需求 */}
</div>
```

部门列表来源：复用现有 `fetchDepartmentNames()`（`frontend/src/services/eligibilityService.ts`），无需新建 API。

### 8.2 表格 7 列规格

| # | 列名 | data key | 推荐宽度 | 渲染规则 |
|---|------|----------|---------|---------|
| 1 | 员工工号 | `employee_no` | 120px | 等宽数字（`font-variant-numeric: tabular-nums`），保留前导零（`'00123'` 字符串原样渲染） |
| 2 | 姓名 | `employee_name` | 100px | 默认 `.table-lite td` 样式 |
| 3 | 年份 | `year` | 80px | `{year} 年` |
| 4 | 绩效等级 | `grade` | 80px | `<span className="status-pill">` 显示等级（如 A / B / C），背景按等级映射（A 用 `--color-success-bg`，B 用 `--color-bg-subtle`，C 用 `--color-warning-bg`；具体映射 executor 在 plan 中确定） |
| 5 | 部门快照 | `department_snapshot` | flex 1 | 非空显示文本；`null` 显示 `<span style={{ color: 'var(--color-placeholder)' }}>—</span>`（D-07） |
| 6 | 来源 | `source` | 100px | `<span className="status-pill">` 文本映射：`manual`→「手动」（灰底）、`excel`→「导入」（蓝底 `--color-primary-light` `--color-primary`）、`feishu`→「飞书」（紫底 `--color-violet-bg` `--color-violet`） |
| 7 | 录入时间 | `created_at` | 160px | `Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })` → 「2026/04/22 14:30」 |

**表格容器：** `<div className="table-shell"><table className="table-lite">...</table></div>`（已有样式）。
**行为：** 行 hover 改背景为 `var(--color-bg-hover)`（`.table-lite tbody tr:hover` 已定义）；**不**实现行点击跳详情（D-14：暂不实现，Phase 36 范围）。
**A11y：** `<table>` 必须含 `<caption className="sr-only">绩效记录列表</caption>`（screen reader only，复用 Tailwind `sr-only` 工具类）。

### 8.3 分页器

50 条/页（D-14 锁定）。最简形态：

```tsx
<div style={{
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '12px 16px',
  borderTop: '1px solid var(--color-border)',
  background: '#FFFFFF',
}}>
  <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>
    共 {total} 条 · 第 {page}/{totalPages} 页
  </span>
  <div style={{ display: 'flex', gap: 4 }}>
    <button className="chip-button" disabled={page === 1} onClick={() => setPage(page - 1)}>上一页</button>
    <button className="chip-button" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button>
  </div>
</div>
```

**Phase 34 不实现：** 跳页输入框、页码列表（10+ 页时再考虑，本期不做）。

---

## 9. 「立即生成档次」空状态 CTA

**触发：** `GET /tier-summary?year=X` 返回 `404 { error: 'no_snapshot' }`（D-10 / D-12）。
**位置：** 替换 Section 1 的 stacked bar + chip 行（warning 横幅 + section-head 仍保留，以便用户切换年份）。

```tsx
<div className="empty-state" style={{ padding: '40px 24px' }}>
  <ChartIcon size={32} style={{ color: 'var(--color-placeholder)', margin: '0 auto 12px' }} />
  <h4 style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)', marginBottom: 4 }}>
    {year} 年尚无档次快照
  </h4>
  <p style={{ fontSize: 13, color: 'var(--color-steel)', marginBottom: 16, maxWidth: 360, marginInline: 'auto' }}>
    系统尚未为该年度生成档次。请先通过「绩效记录导入」上传数据，或直接生成档次。
  </p>
  <button className="action-primary" onClick={handleGenerateNow}>
    <RefreshIcon />
    立即生成档次
  </button>
</div>
```

**ChartIcon：** 32×32 内联 SVG（柱状图轮廓），新增到 `NavIcons.tsx`。

---

## 10. Loading / Error / Toast 状态

### 10.1 Loading 状态

| 场景 | 展示 |
|------|-----|
| 首次加载 tier-summary | Section 1 stacked bar 区域显示 `<div className="surface" style={{ height: 32 + 12 + 32, background: 'var(--color-bg-subtle)' }} />` 骨架（无文字、无动画，避免抖动） |
| 重算按钮按下后 | 按钮 `disabled={true}` + `aria-busy="true"` + RefreshIcon 旋转 + 文字改为「重算中…」 |
| 列表加载中 | 表格 `<tbody>` 渲染 5 行 skeleton（每行 7 个 `<td>` 内放 `<div className="bg-[var(--color-bg-subtle)] h-3 rounded" />`） |
| 切换年份 | Stacked bar 区域显示加载骨架（同首次加载） |

### 10.2 Error 状态

| HTTP 状态 | 处理 |
|----------|-----|
| 401 | 走 axios interceptor 全局退出登录流程（已有，无需 Phase 34 处理） |
| 403 | section 内显示 `<div className="empty-state">当前账号没有查看绩效管理的权限</div>`（理论上 hrbp/admin 不会触发；URL 直访保护） |
| 404（tier-summary） | 显示 §9 「立即生成档次」空状态 |
| 409（重算 busy） | Toast 红色「系统正在自动重算，请稍后重试」+ 5 秒后自动启用按钮（D-06） |
| 500 | Toast 红色「服务端错误（500），请稍后再试或联系管理员」 |
| 网络异常 | Toast 红色「网络异常，无法加载数据」 |

### 10.3 Toast 规范

项目当前未引入 toast 库。Phase 34 **不引入新依赖**，executor 用项目已有的 toast 模式（如全局 `<ToastContainer>` 已存在则复用；如不存在，使用 `alert` 兜底并在 plan 中标记为 follow-up tech debt）。

**推荐 toast 文案（zh-CN）：**

| 场景 | 颜色 | 文案 |
|------|-----|------|
| 重算成功 | 绿（`--color-success-bg` 底） | `档次重算完成（共 {sample_size} 人）` |
| 重算 busy（409） | 黄（`--color-warning-bg` 底） | `系统正在自动重算，请稍后重试` |
| 重算失败 | 红（`--color-danger-bg` 底） | `档次重算失败：{error_message}` |
| 导入完成 | 绿 | `导入成功：{inserted} 条新增 / {updated} 条更新` |
| 导入 + 重算 in_progress | 蓝（`--color-info-bg` 底） | `导入完成，档次正在后台重算…` |

---

## 11. 响应式行为

**Desktop-first**，但 ≥ 768px 必须可用（HR 桌面办公场景）。

| Breakpoint | 行为 |
|-----------|-----|
| ≥ 1024px | AppShell sidebar 240px + main 区 |
| 768px – 1024px | AppShell sidebar 隐藏（`.app-sidebar { display: none; }` 已是默认）；main 区铺满；section-head 内的 「年份 select + 重算按钮」可换行（`flex-wrap`） |
| < 768px | 表格水平滚动（`<div style={{ overflowX: 'auto' }}>` 包裹 `.table-shell`），不缩列；filter 控件竖排堆叠（`flex-direction: column`） |

**Phase 34 不优化：** 移动端原生体验（< 480px），HR 默认在 PC 端使用，移动端能展示即可。

---

## 12. 可访问性（A11y）

- **Warning 横幅：** `role="alert"` + 文本含具体百分比，screen reader 可读出
- **重算按钮：** `aria-busy={isRecomputing}` + 按钮内文字（不仅 icon）
- **表格：** `<caption className="sr-only">绩效记录列表（共 {total} 条）</caption>` + 每个 `<th>` 含可读文字
- **年份 select / 部门 select：** 上方 `<label>`（visible 或 sr-only，executor 选择）
- **空状态 CTA 按钮：** 按钮文字「立即生成档次」自描述，icon 仅装饰（`aria-hidden="true"`）
- **Tooltip（ECharts）：** 主信息已在 chip 行展示；ECharts 的 tooltip 是辅助增强，不依赖鼠标的用户从 chip 行可获得全部信息
- **Focus ring：** 全部按钮 / select 已通过 `:focus-visible` 在 `:root` 内统一样式（蓝色 outline + box-shadow），Phase 34 不覆盖
- **Color contrast：** 黄/绿/红 chip 文字用 `var(--color-ink)`（深灰 #1F2329）而非彩色文字，对比度满足 WCAG AA（白底 #1F2329 对比度 14:1）

---

## 13. Copywriting Contract

| Element | 中文 Copy |
|---------|----------|
| 页面 title | `绩效管理` |
| 页面 description | `HR 端：导入绩效记录、查看档次分布、手动触发档次重算` |
| Sidebar 菜单 label | `绩效管理` |
| Section 1 title | `档次分布` |
| Section 1 note | `基于 PERCENT_RANK 算法对全公司绩效记录分档（1/2/3）` |
| Section 2 title | `绩效记录导入` |
| Section 3 title | `绩效记录` |
| Primary CTA 1（重算） | `重算档次` / loading 时 `重算中…` |
| Primary CTA 2（空状态） | `立即生成档次` |
| Empty state heading | `{year} 年尚无档次快照` |
| Empty state body | `系统尚未为该年度生成档次。请先通过「绩效记录导入」上传数据，或直接生成档次。` |
| Warning 横幅（distribution） | `档次分布偏离 20/70/10 超过 ±5%（实际 {p1}/{p2}/{p3}）。建议复核绩效原始数据或调整评估口径。` |
| Warning 横幅（重算失败） | `档次基于 {old_computed_at} 的旧快照（重算失败，请重试）。` |
| computed_at 标签 | `最近重算：{zh-CN datetime}` |
| Filter「全部年份」 | `全部年份` |
| Filter「全部部门」 | `全部部门` |
| 部门快照 NULL | `—`（em dash，placeholder 灰） |
| 来源 label 映射 | `manual` → `手动` / `excel` → `导入` / `feishu` → `飞书` |
| 分页文案 | `共 {total} 条 · 第 {page}/{totalPages} 页` / `上一页` / `下一页` |
| Error 403 | `当前账号没有查看绩效管理的权限。` |
| Error 500 | `服务端错误（500），请稍后再试或联系管理员。` |
| Error network | `网络异常，无法加载数据。` |
| Toast 重算成功 | `档次重算完成（共 {sample_size} 人）` |
| Toast 重算 busy | `系统正在自动重算，请稍后重试` |
| Toast 重算失败 | `档次重算失败：{error_message}` |
| Toast 导入完成 | `导入成功：{inserted} 条新增 / {updated} 条更新` |
| Toast 导入触发后台重算 | `导入完成，档次正在后台重算…` |

**Destructive actions：** Phase 34 **零** destructive 动作（不实现单条删除/批量删除，删除留待未来需求）。

---

## 14. Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| 项目无 shadcn / 无第三方 registry | 不适用 | not applicable — Phase 34 零新增第三方 UI 组件依赖 |

**新增依赖：** **零**。
- ECharts / echarts-for-react：已在 package.json
- Tailwind 3.4：已在 package.json
- 内联 SVG 图标：自写到 `NavIcons.tsx`
- Toast：复用项目既有方案（如不存在则 plan 阶段决议是否引入或用 alert 兜底）

---

## 15. 设计契约 → 执行映射（给 planner 用）

| Section | 新建 / 复用 | 文件位置 |
|---------|-----------|---------|
| Page 容器 | 新建 | `frontend/src/pages/PerformanceManagementPage.tsx` |
| Section 1 容器 | 新建 | `frontend/src/components/performance/TierDistributionPanel.tsx` |
| Stacked bar 子组件 | 新建 | `frontend/src/components/performance/TierStackedBar.tsx`（封装 ECharts option） |
| Tier chip 子组件 | 新建 | `frontend/src/components/performance/TierChip.tsx` |
| Warning 横幅子组件 | 新建 | `frontend/src/components/performance/DistributionWarningBanner.tsx` |
| Section 2 | 复用 | `<ExcelImportPanel importType="performance_grades">`（Phase 32 现成） |
| Section 3 容器 | 新建 | `frontend/src/components/performance/PerformanceRecordsTable.tsx` |
| Filter 子组件 | 新建 | `frontend/src/components/performance/PerformanceRecordsFilters.tsx` |
| 服务层 | 新建 | `frontend/src/services/performanceService.ts` — 暴露 `getTierSummary(year)` / `recomputeTiers(year)` / `getRecords(filter)` |
| 类型 | 新建 | `frontend/src/types/api.ts` 内追加 `TierSummaryResponse` `PerformanceRecord` `PerformanceRecordsListResponse` |
| 路由 | 改 | `frontend/src/App.tsx` 加 `<Route path="/performance" element={<PerformanceManagementPage />} />` |
| 角色权限 | 改 | `frontend/src/utils/roleAccess.ts` 加 `'/performance': ['admin', 'hrbp']` |
| Sidebar 菜单 | 改 | `frontend/src/components/layout/AppShell.tsx`（或 NavMenu）加菜单项 |
| 图标 | 改 | `frontend/src/components/icons/NavIcons.tsx` 加 `RefreshIcon` `WarningIcon` `ChartIcon` |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — §13 全部 zh-CN 文案锁定，含 toast / error / empty / tooltip
- [ ] Dimension 2 Visuals: PASS — §5/§6/§8 layout 与 ASCII wireframe 锁定；ECharts option 全量给出
- [ ] Dimension 3 Color: PASS — §4 60/30/10 split 明确；accent 用例严格枚举为 5 项
- [ ] Dimension 4 Typography: PASS — §3 严格 4 角色 + 2 weight，复用 :root 既有 component classes
- [ ] Dimension 5 Spacing: PASS — §2 全部 4 倍数；例外仅 ECharts 容器与 input 高度，已说明正交性
- [ ] Dimension 6 Registry Safety: PASS — §14 零新增第三方依赖

**Approval:** pending
