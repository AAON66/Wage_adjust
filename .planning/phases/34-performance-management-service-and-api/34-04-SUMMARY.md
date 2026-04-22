---
phase: 34-performance-management-service-and-api
plan: 04
subsystem: frontend/pages + frontend/components/performance + frontend/services + frontend/types + frontend/utils
tags: [frontend, ui, react, echarts, performance, phase-34, wave-3]
requirements-completed: [PERF-01, PERF-02, PERF-05, PERF-08]
dependency-graph:
  requires:
    - 34-01 (PerformanceTierSnapshot 模型 + PerformanceRecord.department_snapshot 列)
    - 34-02 (TierCache + 自定义异常 + Settings 配置化)
    - 34-03 (PerformanceService + 5 REST 端点 + import_hook + ConfirmResponse.tier_recompute_status 扩字段)
  provides:
    - HR 独立「绩效管理」页面 /performance（admin + hrbp 限定）
    - 3 section 垂直布局：档次分布 / 绩效记录导入 / 绩效记录列表
    - 6 个 axios service 函数（含 B-3 getAvailableYears）+ 2 个自定义 Error 类
    - 9 个 Phase 34 TypeScript 类型 + ConfirmResponse.tier_recompute_status 扩字段（前后端类型双向对齐）
    - 4 个档次分布子组件（TierStackedBar / TierChip / DistributionWarningBanner / TierDistributionPanel）
    - 2 个列表子组件（PerformanceRecordsFilters / PerformanceRecordsTable）
    - 3 个内联 SVG 图标（RefreshIcon / WarningIcon / ChartIcon）+ NavIcons IconProps.style 扩展（B-4）
    - utils/toast.ts 单实例 toast helper（W-4）
  affects:
    - HR/admin 登录后侧边栏「绩效管理」菜单可见可点
    - Phase 32 ExcelImportPanel 在 performance_grades 路径下首次接入「档次重算状态联动」
    - Phase 35 ESELF-03 员工端档次徽章可基于既有 service 函数扩展
tech-stack:
  added:
    - frontend/src/components/performance/TierStackedBar.tsx (75 行，ECharts 6.0 horizontal stacked bar)
    - frontend/src/components/performance/TierChip.tsx (62 行，TierChip + UnTieredChip)
    - frontend/src/components/performance/DistributionWarningBanner.tsx (96 行，distribution + RecomputeFailedBanner)
    - frontend/src/components/performance/TierDistributionPanel.tsx (236 行，5 状态分支 panel 整合容器)
    - frontend/src/components/performance/PerformanceRecordsFilters.tsx (50 行)
    - frontend/src/components/performance/PerformanceRecordsTable.tsx (213 行，7 列 + 分页器 + skeleton)
    - frontend/src/services/performanceService.ts (158 行，6 函数 + 2 Error 类)
    - frontend/src/utils/toast.ts (32 行，W-4 单实例 toast helper)
  patterns:
    - 复用 echarts 6.0.0 + echarts-for-react 3.0.6（package.json 已装；UI-SPEC §0 反向勘误，禁用 Recharts）
    - 内联 SVG 图标加入 NavIcons.tsx（禁用 lucide-react；零新依赖）
    - axios 复用 api.ts 单实例（不另起 axios.create），长超时 30s 覆盖最坏 5 秒后端阻塞
    - 自定义 Error 类（NoSnapshotError / TierRecomputeBusyError）让调用方 instanceof 分支
    - 单实例 toast helper 用 setTimeout(0) cancel + alert 兜底，TODO 替换为正式 toast 库
    - tierRefreshKey 计数器作为 React key 强制 panel 重新挂载并拉数据，避免 useEffect 依赖膨胀
    - PerformanceRecordsTable 7 列严格按 UI-SPEC §8.2 渲染规则；status-pill 全部用 :root 已定义 token
key-files:
  created:
    - frontend/src/components/performance/TierStackedBar.tsx
    - frontend/src/components/performance/TierChip.tsx
    - frontend/src/components/performance/DistributionWarningBanner.tsx
    - frontend/src/components/performance/TierDistributionPanel.tsx
    - frontend/src/components/performance/PerformanceRecordsFilters.tsx
    - frontend/src/components/performance/PerformanceRecordsTable.tsx
    - frontend/src/services/performanceService.ts
    - frontend/src/utils/toast.ts
  modified:
    - frontend/src/types/api.ts (+109 行：9 个 Phase 34 类型 + ConfirmResponse.tier_recompute_status 扩字段)
    - frontend/src/components/icons/NavIcons.tsx (+18 行：B-4 IconProps.style 扩展 + svg() merge style + 3 个新图标)
    - frontend/src/utils/roleAccess.ts (+2 行：admin + hrbp operations 组追加「绩效管理」菜单)
    - frontend/src/App.tsx (+2 行：import + Route)
    - frontend/src/pages/PerformanceManagementPage.tsx (Task 1 stub → Task 3 完整 orchestration，195 行)
key-decisions:
  - UI-SPEC §0 反向勘误锁定：用 ECharts 6.0 + echarts-for-react 3.0.6 替代 CONTEXT 提到的
    Recharts；用 NavIcons 内联 SVG 替代 CONTEXT 提到的 lucide-react；零新增 npm 包。
  - B-3：performanceService 暴露 getAvailableYears()，PerformanceManagementPage useEffect 改用
    它替代「拉 200 条 records 凑 distinct」hack；fallback 链「数组空/网络异常 → [今年]」。
  - B-4：NavIcons.tsx IconProps 接口扩 `style?: React.CSSProperties`；svg() helper 用
    `{ flexShrink: 0, ...props.style }` merge；解锁 UI-SPEC §6.2/§9 的 `<WarningIcon style={...}/>`
    与 `<ChartIcon style={...}/>` 调用通过 tsc --noEmit 校验。
  - B-5：PerformanceRecordsTable 来源 chip 颜色映射 100% 用 :root 已定义 token：
    manual=灰底 (`--color-bg-subtle` + `--color-steel`)；excel=蓝底 (`--color-primary-light` +
    `--color-primary`)；feishu=紫底 (`--color-violet-bg` + `--color-violet`，Phase 31 D-07 引入)。
    无未定义 var 引用。
  - W-1：handleImportComplete 根据 ConfirmResponse.tier_recompute_status 5 状态分支 toast 文案
    （completed → 绿；in_progress → 蓝；busy_skipped → 黄；failed → 红；null/skipped → 通用绿）。
  - W-4：utils/toast.ts 单实例 toast helper，cancel 旧 setTimeout 防多 alert 排队卡浏览器；
    标 // TODO Phase 35+ 替换为正式 toast 库（sonner / react-hot-toast 候选）。
  - W-2：Task 1 改 7 文件按 sub-step 1.1-1.8 顺序实施，每完成一组验证后再推进；最终单 commit
    覆盖 7 文件（lint 验证保护）。
  - N-3：明确不在本期范围—行点击跳详情、me/tier 调用、多年趋势 chart 均为 Phase 35/36 范围。
  - tierRefreshKey 用 React `key` prop 强制 TierDistributionPanel 重新挂载（import 完成或重算后），
    比 useEffect 依赖更安全，避免子组件内部 state 残留旧值。
  - 重算按钮 Busy 5 秒冷却用 window.setTimeout 而非 useEffect，与 D-06 行为对齐；其余分支立即
    解除 disabled。
metrics:
  start-time: 2026-04-22T08:30:00Z
  end-time: 2026-04-22T09:00:00Z
  duration-human: ~30 分钟
  tasks-completed: 3 / 3
  files-created: 8
  files-modified: 5
  total-files-touched: 13
  tests-added: 0 (本 plan 是纯前端 UI 无 unit test 增量；浏览器人工冒烟由用户验证)
  regressions: 0 (npm run lint + npm run build 双 0；既有页面/路由不受影响)
---

# Phase 34 Plan 04: HR 端绩效管理页面 + 5 子组件 + 前端 service / 类型 / 路由 / 角色限制

Wave 3 落地：将 Wave 1 的数据持久化（PerformanceTierSnapshot + department_snapshot）+ Wave 2 的 5 个 REST 端点 + import_hook 串成 HR/admin 可直接使用的浏览器端体验。3 section 垂直排列覆盖 ROADMAP 5 个 SC 全部入口；零新增第三方 UI 依赖；UI-SPEC §0 反向勘误（ECharts 替 Recharts / 内联 SVG 替 lucide-react）严格执行。

## What Got Built

### Task 1: 基础设施 7 文件（commit `71f804e`）

**`frontend/src/types/api.ts`** (+109 行)：
- `TierCounts` / `ActualDistribution` 嵌套类型
- `TierSummaryResponse` (D-09 平铺 9 字段)
- `PerformanceRecordItem` / `PerformanceRecordsListResponse` / `PerformanceRecordCreatePayload`
- `RecomputeTriggerResponse`
- `NoSnapshotErrorDetail` / `TierRecomputeBusyDetail`
- **B-3 新增**：`AvailableYearsResponse`
- **W-1 同步**：`ConfirmResponse` 加 `tier_recompute_status?: 'completed' | 'in_progress' | 'busy_skipped' | 'failed' | 'skipped' | null`

**`frontend/src/services/performanceService.ts`** (158 行新建)：6 个 axios async 函数
```ts
getTierSummary(year)             // catch 404 → throw NoSnapshotError
recomputeTiers(year)              // 30s long timeout，catch 409 → throw TierRecomputeBusyError
getPerformanceRecords({...})
createPerformanceRecord(payload)
getAvailableYears()               // B-3 替代 200-records hack
```
- 复用 `import api from './api'`，零新建 axios.create
- 自定义 Error 类带 readonly `year` / `hint` / `retryAfterSeconds` 字段，调用方 `instanceof` 分支

**`frontend/src/components/icons/NavIcons.tsx`** (B-4 修复 + 3 新图标)：
- IconProps 接口扩 `style?: React.CSSProperties`
- svg() helper merge style：`{ flexShrink: 0, ...props.style }`
- 新增 RefreshIcon / WarningIcon / ChartIcon（24x24 viewBox，stroke=currentColor）

**`frontend/src/utils/toast.ts`** (32 行新建，W-4)：
```ts
export type ToastVariant = 'success' | 'info' | 'warning' | 'error';
export function showToast(message: string, variant?: ToastVariant): void
```
单实例：activeTimeoutId cancel 旧 setTimeout 再 schedule 新 alert（防多 alert 卡浏览器）；console.log 标 variant 便于调试；标 // TODO Phase 35+ 替换正式 toast 库。

**`frontend/src/utils/roleAccess.ts`**：admin + hrbp `operations` 菜单组各追加 1 项「绩效管理」/ `/performance` / icon=`bar-chart`；manager + employee 不加。

**`frontend/src/App.tsx`**：import `PerformanceManagementPage` + 在 admin+hrbp ProtectedRoute 块内加 `<Route element={<PerformanceManagementPage />} path="/performance" />`。

**`frontend/src/pages/PerformanceManagementPage.tsx`** (stub)：AppShell 占位；Task 3 用真实 orchestration 替换。

### Task 2: Section 1 档次分布 4 组件（commit `757a6ca`）

**`TierStackedBar.tsx`** (75 行)：ECharts horizontal stacked bar
- 高度 32px，宽度 100%
- 1 档 #10b981（borderRadius 左侧 4px）/ 2 档 #f59e0b / 3 档 #ef4444（borderRadius 右侧 4px）
- tooltip：`{seriesName}：{count} 人 ({pct}%)`（1 位小数）

**`TierChip.tsx`** (62 行)：TierChip + UnTieredChip
- `<span className="status-pill">` 不可点击形态
- 8x8 圆点 + label + `<strong>{count}</strong> 人 ({pct}%)`
- UnTieredChip 用 `--color-border` 边框 + `--color-placeholder` 圆点

**`DistributionWarningBanner.tsx`** (96 行)：DistributionWarningBanner + RecomputeFailedBanner
- `role="alert"` + 黄色横幅（`--color-warning-bg/border/text`）
- WarningIcon size=16 style={{ marginTop: 2, flexShrink: 0 }} ← **B-4 用法验证点**
- pct() helper 把 0.22 转 "22%"
- RecomputeFailedBanner 含旧 computed_at 时间戳 zh-CN 格式化 + 「立即重算」chip-button

**`TierDistributionPanel.tsx`** (236 行)：5 状态分支整合
1. summary=null && !noSnapshot && !error → 32+12+32 px 灰色 skeleton 占位（无文字、无动画）
2. error 非空 → 红色 error banner
3. noSnapshot=true → 空状态卡片（ChartIcon style={{ color: 'var(--color-placeholder)' }} + 「立即生成档次」按钮）
4. summary && distribution_warning → 黄色警告横幅 + bar + chips
5. summary && !distribution_warning → bar + chips
- handleRecompute：成功 toast + onRecomputed callback + reload；catch BusyError → toast warning + 5s 冷却 disabled；其他错误 → toast error
- showToast 替代 alert（W-4）

### Task 3: Section 3 列表 + 页面 orchestration（commit `0c51395`）

**`PerformanceRecordsFilters.tsx`** (50 行)：年份 select + 部门 select；`toolbar-input` 样式；暂不实现搜索框（D-14）

**`PerformanceRecordsTable.tsx`** (213 行)：7 列表格 + 分页器
- caption sr-only「绩效记录列表（共 N 条）」
- 工号 `font-variant-numeric: tabular-nums`，保留前导零字符串原样
- 部门快照 null → 「—」灰色 placeholder
- 等级 GRADE_STYLE map（A 绿 / B 灰 / C-D-E 黄）
- **B-5 SOURCE_STYLE map**：
  - manual → 灰底 `--color-bg-subtle` + `--color-steel` 「手动」
  - excel → 蓝底 `--color-primary-light` + `--color-primary` 「导入」
  - feishu → 紫底 `--color-violet-bg` + `--color-violet` 「飞书」
- skeleton 5 行 / 「暂无数据」空状态
- 录入时间 zh-CN format「2026/04/22 14:30」
- 分页器：「共 N 条 · 第 X/Y 页」+ 上下页按钮 disabled 控制

**`PerformanceManagementPage.tsx`** (重写为 195 行)：
- 6 个 useState：selectedYear / availableYears / departments / filterYear / filterDepartment / tableState / tierRefreshKey
- **B-3 useEffect**：mount 时 `getAvailableYears().then(...).catch(...)`；fallback 链「数组空 → [今年]」+「网络异常 → [今年]」
- useEffect 拉 fetchDepartmentNames
- useEffect filter 变化时 loadRecords(page=1)
- **W-1 handleImportComplete**：5 状态分支 toast 文案（参照 plan 规范完整复制）+ tierRefreshKey++
- handleRecomputed：tierRefreshKey++ + 重拉 records
- 3 section JSX 严格按 D-13 顺序：分布 → 导入 → 列表

## Phase 34 整体收尾

| Wave | Plan | 文件 | 关键产物 | Commits |
|------|------|------|---------|---------|
| 1 | 34-01 | 4 | PerformanceTierSnapshot 模型 + 2 alembic migration + department_snapshot 列 | ae20d62, fb53fb4, 02a8529, 952311f |
| 1 | 34-02 | 3 | TierCache Redis 缓存层 + 自定义异常 + Settings 字段 | 0bcd945, f2b733f, d2f1c1e |
| 2 | 34-03 | 9 | PerformanceService + 5 REST 端点 + import_hook + B-1/B-2/B-3/W-1 修复 + 39 cases 测试 | 108b397, 768ded5, 7a8f722, ec2e20e |
| 3 | 34-04 | 13 | HR 独立「绩效管理」页面 + 6 子组件 + service / types / 路由 / 菜单 / 图标 / toast helper | 71f804e, 757a6ca, 0c51395 |

**ROADMAP Success Criteria 落地映射：**

- **SC-1**：HR + admin 在导航菜单看到「绩效管理」入口；employee/manager 看不到 ✓
  - roleAccess.ts admin/hrbp operations 组追加菜单 + App.tsx ProtectedRoute allowedRoles=['admin', 'hrbp'] + 后端 require_roles 三重防护
- **SC-2**：HR 上传 Excel 后 Preview + diff 落库后 tier 视图刷新 + W-1 toast 文案根据 tier_recompute_status 分支 ✓
  - ExcelImportPanel 7-state 复用 + handleImportComplete 5 分支 toast + tierRefreshKey 强制 panel 重新挂载
- **SC-3**：HR 点击「重算档次」按钮触发重算 + UI 显示重算完成时间戳 ✓
  - TierDistributionPanel handleRecompute + Intl.DateTimeFormat zh-CN 长格式
- **SC-4**：列表显示 department_snapshot 列；NULL 显示「—」 ✓
  - PerformanceRecordsTable 第 5 列 + null 分支灰色 placeholder
- **SC-5**：/records 与 /tier-summary 数据来自同一后端 Service，前端不做二次计算 ✓
  - 前端 service 仅做 axios 透传 + Error 包装；零数据再聚合

**4 个 PERF 需求 UI 层全部 ready：**
- PERF-01：HR 入口 + 列表 + 筛选 ✓
- PERF-02：手动 + Excel 导入双路径接入（手动在 Phase 34 后续可补 form；Excel 已 ready）
- PERF-05：tier-summary + recompute UI ✓
- PERF-08：department_snapshot 7 列展示 ✓

## Deviations from Plan

无架构层面偏离。所有改动按 plan 的 task / sub-step 顺序落地。

**小幅自主决策（不构成偏离）：**

1. **TierDistributionPanel handleRecompute 的 finally 块**：W-1 plan 文本未要求 finally 显式 setIsRecomputing(false)，但 Busy 分支在 setTimeout 5s 后再次 set，其他分支需立即解除；改为 `setIsRecomputing((prev) => prev === true ? false : prev)` 幂等保护，避免误覆盖 Busy 的延迟重置。

2. **GradeCell 颜色映射在 PerformanceRecordsTable.tsx 内联**（plan 留 executor discretion）：A 绿 / B 灰中性 / C/D/E 黄，全部用 :root 已定义 token。

3. **toolbar-input minWidth 设置**：filter 部门 select 用 minWidth=160（match UI-SPEC §8.1 wireframe）；年份用 minWidth=120。

4. **section 内边距 padding=24**：手动加在 `<section className="surface" style={{ padding: 24 }}>` 内联；与 EligibilityManagementPage 既有视觉对齐。

## 浏览器冒烟测试结果

执行人本期未做实际浏览器登录冒烟（要求用户在前后端启动后人工验证）；自动化层面已完成：

- ✓ npm run lint (tsc --noEmit) 退出码 0
- ✓ npm run build (tsc -b && vite build) 退出码 0；transformed 824 modules；built in 3.54s
- ✓ grep "lucide-react|from 'recharts'" frontend/src/ 无匹配
- ✓ grep "style?: React.CSSProperties" frontend/src/components/icons/NavIcons.tsx 命中 1 行
- ✓ grep "getAvailableYears" frontend/src/services/performanceService.ts 命中
- ✓ grep "getAvailableYears" frontend/src/pages/PerformanceManagementPage.tsx 命中
- ✓ grep "AvailableYearsResponse" frontend/src/types/api.ts 命中
- ✓ grep "showToast" frontend/src/utils/toast.ts 命中
- ✓ grep "tier_recompute_status" frontend/src/pages/PerformanceManagementPage.tsx 命中（W-1 分支）
- ✓ grep -E "manual|excel|feishu" frontend/src/components/performance/PerformanceRecordsTable.tsx ≥ 3 行（B-5）
- ✓ grep "/performance" frontend/src/utils/roleAccess.ts 命中 2 处（admin + hrbp）
- ✓ grep "PerformanceManagementPage" frontend/src/App.tsx 命中 import + Route
- ✓ grep "performance_grades" frontend/src/pages/PerformanceManagementPage.tsx 命中

**待用户人工冒烟（提交前提示）：**
1. 启动 backend `uvicorn backend.app.main:app --reload`（端口 8011）
2. 启动 frontend `npm run dev`（端口 5174 或自动分配）
3. admin 登录 → 侧边栏看到「绩效管理」 → 点击进入 /performance
4. 上半部 ECharts 堆叠条渲染（即使后端无数据也应显示「2026 年尚无档次快照」空状态）
5. 中部 ExcelImportPanel idle 态可见；下半部表格表头 7 列正确
6. employee 登录 → 菜单不显示「绩效管理」 + 直访 /performance → 后端 require_roles 返回 403

## Known Stubs

无功能性 stub。utils/toast.ts 的 alert 兜底是有意为之的 MVP 占位（标 `// TODO Phase 35+`），不影响 ROADMAP Phase 34 任何 SC。

## Threat Flags

无新增威胁面。本 plan 严格在 plan 的 `<threat_model>` 范围内交付：

- T-34-FE-01（URL 直访）：roleAccess.ts admin/hrbp 限定 + App.tsx ProtectedRoute + 后端 require_roles 三重防护 ✓
- T-34-FE-02（信息泄露）：tier-summary 仅展示聚合数字，无 employee_id 明细 ✓
- T-34-FE-03（伪造重算）：后端 require_roles + 行锁；前端 disabled 仅 UX 层 ✓
- T-34-FE-04（DoS 反复点击）：isRecomputing state disabled + 409 后强制 5s 冷却 ✓
- T-34-FE-05（XSS via department_snapshot）：React 默认 escape；零 dangerouslySetInnerHTML ✓
- T-34-FE-06（多 toast 卡浏览器）：W-4 utils/toast.ts 单实例 helper ✓

## Self-Check: PASSED

**Created files exist:**
- FOUND: frontend/src/components/performance/TierStackedBar.tsx
- FOUND: frontend/src/components/performance/TierChip.tsx
- FOUND: frontend/src/components/performance/DistributionWarningBanner.tsx
- FOUND: frontend/src/components/performance/TierDistributionPanel.tsx
- FOUND: frontend/src/components/performance/PerformanceRecordsFilters.tsx
- FOUND: frontend/src/components/performance/PerformanceRecordsTable.tsx
- FOUND: frontend/src/services/performanceService.ts
- FOUND: frontend/src/utils/toast.ts

**Modified files contain expected changes:**
- FOUND: frontend/src/types/api.ts (AvailableYearsResponse + tier_recompute_status)
- FOUND: frontend/src/components/icons/NavIcons.tsx (IconProps.style + 3 new icons)
- FOUND: frontend/src/utils/roleAccess.ts (/performance 命中 2 处)
- FOUND: frontend/src/App.tsx (PerformanceManagementPage import + Route)
- FOUND: frontend/src/pages/PerformanceManagementPage.tsx (3 section 完整 orchestration)

**Commits exist:**
- FOUND: 71f804e — Task 1 (infrastructure 7 files)
- FOUND: 757a6ca — Task 2 (Section 1 distribution 4 components)
- FOUND: 0c51395 — Task 3 (Section 3 list + orchestration)

**Success criteria：**
- [x] All 3 tasks executed
- [x] Each task committed individually with --no-verify
- [x] SUMMARY.md created
- [x] B-3 grep `getAvailableYears` 命中 service + page
- [x] B-4 grep `style?: React.CSSProperties` 命中 NavIcons
- [x] B-5 grep -E "manual|excel|feishu" 命中 RecordsTable ≥ 3 行
- [x] W-1 grep `tier_recompute_status` 命中 page 分支判断
- [x] W-4 utils/toast.ts 文件存在含 showToast
- [x] UI-SPEC §0 compliance: `grep -E "lucide-react|from 'recharts'"` frontend/src/ 无输出
- [x] tsc --noEmit (lint) 退出码 0
- [x] npm run build 退出码 0
- [x] roleAccess.ts /performance 命中 admin + hrbp 各 1 处
- [x] App.tsx 含 `<Route path="/performance"`
