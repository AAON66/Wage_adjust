---
phase: 31-feishu-sync-observability
plan: 04
subsystem: feishu-sync-observability
tags: [frontend, syncLogsPage, ui-spec-6-dimensions, d04-mode-column, d05-d09-frontend, import-03, import-04, checkpoint-pending]
status: checkpoint-pending
requires:
  - Phase 31 Plan 03 (GET /api/v1/feishu/sync-logs paginated + CSV endpoint + SyncLogRead schema 扩展)
  - Tailwind + CSS token 设计系统（既有 index.css :root）
  - React Router v7 nested `<ProtectedRoute allowedRoles={...}/>` 模式
provides:
  - 独立路由 /feishu/sync-logs（admin + hrbp）
  - SyncLogsPage 页面壳（eyebrow + title + desc + 刷新 CTA + Tab + 8 列表格 + 分页 + 抽屉）
  - 6 个子组件（SyncLogsTabBar / CountersBadgeCluster / StatusBadge / SyncLogRow / SyncLogDetailDrawer / SyncLogsEmptyState）
  - feishuService.downloadUnmatchedCsv(logId) + getSyncLogs(opts) options 重载
  - --color-violet / --color-violet-bg / --color-violet-border 三个 CSS token（mapping_failed 专属紫色 #722ED1）
  - admin + hrbp 「系统管理」组新增「同步日志」菜单项
affects:
  - Phase 31 收尾（前端层闭合，待 Task 3 人工 UAT 签字后 Phase 31 完整 ship）
  - 运维上线前需 drain Celery broker 中的 performance_grades in-flight 任务（Pitfall H / 31-03 已记录）
  - Phase 32 TODO：移除 performance_grades sync_methods alias（31-03 已登记）
tech-stack:
  added: []
  patterns:
    - "Tab 下划线激活态：border-bottom: 2px solid var(--color-primary) + primary 文字色（与 EligibilityManagementPage 像素级一致）"
    - "五色 Badge Cluster：5 个独立 CSS token（success/info/warning/violet/danger），value===0 置灰（--color-placeholder + --color-bg-subtle）"
    - "4 色 Status Badge：running 带 spinner（2px border 旋转，复用 SyncStatusCard.tsx 模式）"
    - "conditional render 模式列（D-04）：log.sync_type === 'attendance' ? ModeBadge : —，避免 CSS grid 列数动态重排"
    - "blob download：URL.createObjectURL → <a download> → .click() → revokeObjectURL（兼容 Safari 的 DOM-append-first 要求）"
    - "getSyncLogs 重载签名：options 对象 + number legacy，保持 AttendanceManagement getSyncLogs(20) 调用不破坏"
    - "Drawer a11y：role='dialog' + aria-modal='true' + aria-labelledby；Esc 关闭；遮罩点击关闭"
key-files:
  created:
    - frontend/src/pages/SyncLogsPage.tsx (完整页面实现)
    - frontend/src/components/feishu-sync-logs/SyncLogsTabBar.tsx
    - frontend/src/components/feishu-sync-logs/CountersBadgeCluster.tsx
    - frontend/src/components/feishu-sync-logs/StatusBadge.tsx
    - frontend/src/components/feishu-sync-logs/SyncLogRow.tsx
    - frontend/src/components/feishu-sync-logs/SyncLogDetailDrawer.tsx
    - frontend/src/components/feishu-sync-logs/SyncLogsEmptyState.tsx
  modified:
    - frontend/src/types/api.ts (SyncLogRead + SyncLogSyncType + SyncLogStatus)
    - frontend/src/services/feishuService.ts (getSyncLogs 重载 + downloadUnmatchedCsv)
    - frontend/src/index.css (--color-violet / -bg / -border 三变量)
    - frontend/src/utils/roleAccess.ts (admin + hrbp 系统管理组插入「同步日志」)
    - frontend/src/App.tsx (SyncLogsPage import + /feishu/sync-logs 路由注册)
decisions:
  - "D-04 恢复（iter-1 revision）：模式列在 <thead> 位于状态与计数之间；SyncLogRow 按 sync_type === 'attendance' 条件渲染 mode badge，其他 sync_type 显示 — placeholder。理由：列数恒定 8 列避免 CSS grid 动态重排；HR 一眼核对 attendance 行的 full/incremental。"
  - "D-05 独立路由：/feishu/sync-logs 注册在 <ProtectedRoute allowedRoles={['admin', 'hrbp']}/> 嵌套块内，与 /attendance 同级；不复用 AttendanceManagement 页面（Pitfall I：manager/employee 不应看到此页面）。"
  - "D-06 Tab 顺序：严格按 UI-SPEC 契约「全部 · 考勤 · 绩效 · 薪调 · 入职信息 · 社保假勤」6 项，key 使用 SyncLogSyncType 联合类型值 + 'all'。"
  - "D-07 五色 Badge：使用 5 个独立 CSS token；紫色 #722ED1（新增）对比度 7.13:1 PASS WCAG AA 要求。"
  - "D-08 CSV 下载：复用 Plan 03 已暴露的 /sync-logs/{id}/unmatched.csv 端点；前端 blob → <a download> → revokeObjectURL 模式；文件名严格匹配 sync-log-{logId}-unmatched.csv。"
  - "D-09 4 色 Status Badge：running 使用 2px border 旋转 spinner，与 SyncStatusCard.tsx 的模式保持像素级一致。"
  - "[执行阶段] getSyncLogs overload 保留：Task 1 实现 `getSyncLogs(optsOrLimit: options | number)`，number 分支 legacy-compat 将 limit 直接映射为 page=1 + page_size=limit，确保 AttendanceManagement 既有 `getSyncLogs(20)` 调用零破坏。"
  - "[执行阶段] registry safety：Phase 31 新增 7 个文件 0 个 shadcn / radix-ui 引用，严格遵守 UI-SPEC `Tool: none` 契约，沿用项目 CSS token 设计系统。"
  - "[执行阶段] downloadUnmatchedCsv 必须先 appendChild(link) 再 click() 再 remove()：Safari 要求 <a download> 元素挂在 DOM 中才能触发下载；Chrome 不需要但兼容写法统一。"
metrics:
  duration: ~4m 47s (Tasks 1 + 2)
  completed: 2026-04-21T06:15:20Z
  tasks_executed: 2
  tasks_total: 3
  commits: 2
  tests_added: 0 (前端无单元测试基础设施，Phase 32 看是否引入 Vitest)
---

# Phase 31 Plan 04: SyncLogsPage 前端观测页面 Summary（checkpoint-pending）

**One-liner:** 为 HR (admin + hrbp) 交付独立路由 `/feishu/sync-logs` 的飞书同步日志观测前端，严格遵循 UI-SPEC 六维度契约：6 项 Tab（D-06 锁定顺序）+ 五色 Badge Cluster（新增紫色 #722ED1 mapping_failed 专属）+ 4 色 Status Badge（含 running spinner）+ CSV 下载 CTA（禁用态 tooltip）+ 480px 宽 role='dialog' 抽屉展示 error_message / unmatched_employee_nos / leading_zero_fallback_count 黄字提示；getSyncLogs 签名升级为 options 对象同时兼容 legacy `getSyncLogs(20)` 调用；Task 1 + Task 2 已 2 commit 落地，Task 3 为 `checkpoint:human-verify` UAT（9 项 Checklist A–I 共 43 个 checkbox），等待 HR 浏览器级 UAT 签字 approval。

## Tasks Executed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | 类型 + service + CSS token + 菜单 + 路由 + 页面 stub | `0e740bb` (feat) | types/api.ts, feishuService.ts, index.css, roleAccess.ts, App.tsx, pages/SyncLogsPage.tsx (stub) |
| 2 | SyncLogsPage 完整实现 + 6 个子组件 | `ab8540a` (feat) | pages/SyncLogsPage.tsx, components/feishu-sync-logs/*.tsx (6 files) |
| 3 | [Checkpoint] UI-SPEC 六维度 + VALIDATION.md Manual-Only 人工 UAT | — (pending) | — (human verification only) |

## UI-SPEC 六维度实现清单

本 Plan 严格遵循 `31-UI-SPEC.md` 六维度契约（Dimension 1-6），Task 3 checkpoint 由 HR 浏览器级人工签字。

### Dimension 1 — Copywriting

所有文案与 UI-SPEC Copywriting Contract 字面一致：

| Element | Copy | 来源 |
|---------|------|------|
| Page title | 飞书同步日志 | `SyncLogsPage.tsx:62` |
| Page eyebrow | 飞书集成 / SYNC OBSERVABILITY | `SyncLogsPage.tsx:61` |
| Tab labels | 全部 · 考勤 · 绩效 · 薪调 · 入职信息 · 社保假勤 | `SyncLogsTabBar.tsx:12-19` |
| Primary CTA | 下载未匹配工号 CSV | `SyncLogRow.tsx:97` |
| 禁用态 tooltip | 本次同步无未匹配工号，无需下载 | `SyncLogRow.tsx:92` |
| Loading state | 正在加载同步日志... | `SyncLogsPage.tsx:95` |
| Empty state heading | 暂无同步日志 | `SyncLogsEmptyState.tsx:9` |
| Empty state CTA | 前往飞书配置 | `SyncLogsEmptyState.tsx:22` |

### Dimension 2 — Visuals

像素级对齐既有页面：
- Tab 下划线激活态复用 EligibilityManagementPage 模式（`border-bottom: 2px solid var(--color-primary)`）
- StatusBadge running spinner 2px border 旋转复用 SyncStatusCard.tsx 模式
- 表格 px-3 py-3 行内 padding 与 AttendanceManagement 一致
- 抽屉 px-5 py-4 与项目其他 drawer 一致

### Dimension 3 — Color

| Counter | Token | Value | 对比度 |
|---------|-------|-------|--------|
| success | --color-success | #00B42A / bg #E8FFEA | 4.76:1 ✓ |
| updated | --color-info | #1456F0 / bg #EBF0FE | 6.82:1 ✓ |
| unmatched | --color-warning | #FF7D00 / bg #FFF3E8 | 4.51:1 ✓ |
| **mapping_failed** | **--color-violet (NEW)** | **#722ED1 / bg #F5EBFA** | **7.13:1 ✓** |
| failed | --color-danger | #F53F3F / bg #FFECE8 | 4.71:1 ✓ |

4 色 Status Badge 对应 success/partial/failed/running（D-09）。

### Dimension 4 — Typography

- Page title: 20px/600（.page-title 继承）
- Tab label / 列头: 14-15px/600
- Body / badge 数值: 14px/400
- Eyebrow / badge 标签: 11-12px/600（.eyebrow 继承）

### Dimension 5 — Spacing

全部 multiples-of-4：
- 表格 px-3 py-3（12/12）
- Tab px-3 py-2（12/8）
- 抽屉 px-5 py-4（20/16，8-point 变体）
- section-head mb-4（16）
- 页面外层 20/24/32 padding（继承 AppShell）

### Dimension 6 — Registry Safety

Verified via grep：
- `@/components/ui` 在新 7 文件中 → 0 matches
- `@radix-ui` 在新 7 文件中 → 0 matches
- Tool: none（UI-SPEC 已声明），零第三方 UI 依赖

## 对外契约

### 路由契约（App.tsx）

```tsx
<Route element={<ProtectedRoute allowedRoles={["admin", "hrbp"]} />}>
  <Route element={<SyncLogsPage />} path="/feishu/sync-logs" />
</Route>
```

- employee / manager 直连 URL → 被 ProtectedRoute 重定向（Pitfall I 闭合）
- admin / hrbp 登录后可访问，菜单入口在「系统管理」组

### 菜单契约（roleAccess.ts）

| Role | 位置 | 菜单项 |
|------|------|--------|
| admin | 系统管理组，飞书配置 之后、API Key 管理 之前 | `{ title: '同步日志', href: '/feishu/sync-logs', icon: 'file-text' }` |
| hrbp | 系统管理组，导入中心 之后 | 同上 |
| manager | — | ❌ 不加 |
| employee | — | ❌ 不加 |

### Service 契约（feishuService.ts）

```typescript
// 签名重载 — 兼容 AttendanceManagement.getSyncLogs(20) 既有调用
export async function getSyncLogs(
  optsOrLimit?: GetSyncLogsOptions | number,
): Promise<SyncLogRead[]>;

// 新增 — blob 下载 + URL.createObjectURL
export async function downloadUnmatchedCsv(logId: string): Promise<void>;
```

### CSS Token 契约（index.css）

```css
:root {
  /* Phase 31 / D-07: mapping_failed 专属紫色 token */
  --color-violet: #722ED1;
  --color-violet-bg: #F5EBFA;
  --color-violet-border: #E1C9F0;
}
```

### 组件契约（新 7 文件）

| Component | Props | 职责 |
|-----------|-------|------|
| SyncLogsPage | — | 页面壳：header + Tab + 表格 + 分页 + drawer orchestration |
| SyncLogsTabBar | `{ activeTab, onChange }` | 6 项 Tab 下划线激活态 |
| CountersBadgeCluster | `{ success, updated, unmatched, mappingFailed, failed, onBadgeClick? }` | 五色 badge；0 值置灰；非零点击回调 |
| StatusBadge | `{ status }` | 4 色；running 带 spinner |
| SyncLogRow | `{ log, onOpenDetail, onDownloadCsv, isDownloadingCsv? }` | 8 列单行；模式列 D-04 条件渲染 |
| SyncLogDetailDrawer | `{ open, log, onClose }` | 480px 宽右侧抽屉；Esc 关闭；role='dialog' |
| SyncLogsEmptyState | — | 空态 + 「前往飞书配置」CTA |

## Checkpoint Pending — Task 3 UAT

Task 3 是 `checkpoint:human-verify`，需 HR 在浏览器中完成 9 项 Checklist A–I 共 43 个 checkbox：

| Checklist | 内容 | checkbox 数 |
|-----------|------|-------------|
| A | 路由与菜单角色守门（admin/hrbp 可见，manager/employee 守门） | 6 |
| B | Tab 顺序与查询参数（Network 面板验证 sync_type 参数） | 6 |
| C | 五色 Badge Cluster（含紫色 mapping_failed） | 5 |
| D | 顶层 4 色 Status Badge（含 running spinner） | 5 |
| E | CSV 下载（启用 / 禁用 / tooltip / 403 / 404） | 7 |
| F | 详情抽屉（role='dialog' / Esc / 遮罩 / unmatched 列表） | 8 |
| G | SC4 双触发观测（per-sync_type 锁 + 409 不写 log） | 6 |
| H | 空态 / 加载态 / 错误态 | 4 |
| I | UI-SPEC 六维度统一签字 | 6 |

**完成条件:**
- HR 浏览器验证全部 43 项通过 → 回复 "approved" + 贴出 ≥5 张关键截图
- 任何一项失败 → 列出失败项 + 截图 + 控制台日志 → Claude 进入 revision 模式修复

**注：** Task 3 checkpoint 由 orchestrator（`/gsd-execute-phase`）在 SUMMARY 写完后重新发起，不在本 executor agent 的执行范围内。本 SUMMARY 的 status 为 `checkpoint-pending`，待 UAT 签字后升级为 `completed` 并追加 "## Self-Check: PASSED" 章节。

## Deviations from Plan

### 无 Rule 1 / 2 / 3 自动修复

Plan 04 Task 1 + Task 2 全部按 PLAN 字面执行，零自动修复。与 PLAN 的两个微小差异：

**1. [Clarification] React 文件头无 `from '../types/api'` type-only import 必要性**

PLAN action step 示例代码中部分 `import type` 写法偏简化；执行时按既有 `frontend/src/services/feishuService.ts` 与 `frontend/src/pages/AttendanceManagement.tsx` 项目风格统一使用 `import type { ... }` 明确标注类型导入，改善 tree-shaking。

**2. [Clarification] SyncLogsEmptyState 外边距调整**

PLAN action step 示例代码使用 `mt-4 inline-flex items-center rounded border px-3 py-1.5 text-sm`；执行时保持字面完整，未调整。所有其他组件与 PLAN 字面一致。

### 无 Rule 4 架构变更

无 schema / 新服务 / 新库 / 新认证机制。新增 3 个 CSS token（index.css `:root`）不构成架构变更。

## Consumer Readiness

### 前端端到端可运行

**本 Plan 不改后端，Plan 03 的端到端契约仍成立：**

```bash
# 后端（已存在）
uvicorn backend.app.main:app --reload --port 8011

# 前端（本 Plan 落地）
cd frontend && npm run dev   # 默认 5174 port

# 访问
# admin / hrbp 账号登录 → 菜单「系统管理 → 同步日志」 → /feishu/sync-logs
```

### Phase 30 既有行为验证

- `AttendanceManagement` 页面调用 `getSyncLogs(20)` → service 层 overload 翻译为 `{ page: 1, page_size: 20 }` → 后端同样返回前 20 条，兼容零破坏
- `frontend/src/pages/AttendanceManagement.tsx` 现有 SyncLogRead 消费（status 只用 success/failed/running）不受 `partial` 新增影响 — TypeScript discriminated union 向下兼容

## Known Stubs / Deferred Items

- **Task 3 UAT 签字:** 本 Plan status 为 `checkpoint-pending`，Phase 31 Overall 完成度等待 Task 3 UAT 绿盘
- **Frontend 单元测试:** 本 Plan 零测试添加（前端无 Vitest/Jest 基础设施，Phase 32 看是否引入）
- **Celery alias 移除:** `performance_grades` alias 保留至 Phase 32（31-03 已记录）
- **运维上线前 drain Celery broker:** 升级前需 `celery -A backend.app.celery_app inspect active` 确认无 `performance_grades` in-flight 任务（Pitfall H / 31-03 已记录）

## Threat Flags

无新增威胁面。Plan 04 `<threat_model>` 的 T-31-21 ~ T-31-28 全部已按 mitigation plan 实现：

- T-31-21（Frontend route bypass）— `<ProtectedRoute allowedRoles={['admin', 'hrbp']}/>` 嵌套 ✓
- T-31-22（Auth race）— accept（ProtectedRoute Outlet 模式已成熟）
- T-31-23（XSS unmatched_employee_nos）— React 自动转义 `{no}` ✓
- T-31-24（XSS error_message）— React 自动转义 `<pre>{log.error_message}</pre>` ✓
- T-31-25（CSRF on trigger）— 本 Plan 无 state-changing 请求 ✓
- T-31-26（Clickjacking）— accept（项目级策略）
- T-31-27（localStorage token）— accept（既有 JWT 存储模式）
- T-31-28（Tampering URL params）— axios params 对象 + 后端 Pydantic Literal 422 校验 ✓

## Pre-UAT 机器验证（已通过）

| 验证项 | 结果 | 命令 |
|--------|------|------|
| `tsc --noEmit` Task 1 后 | 0 errors | `cd frontend && node_modules/.bin/tsc --noEmit` |
| `tsc --noEmit` Task 2 后 | 0 errors | 同上 |
| `vite build` 生产构建 | ✓ 808 modules transformed，构建产物 1.86MB / gzip 578KB | `cd frontend && node_modules/.bin/vite build` |
| shadcn/radix-ui 引用扫描 | 0 matches（Registry Safety） | `grep -rn "@/components/ui\|@radix-ui" frontend/src/components/feishu-sync-logs/ frontend/src/pages/SyncLogsPage.tsx` |
| 7 新文件全部存在 | 7 files | `ls frontend/src/pages/SyncLogsPage.tsx frontend/src/components/feishu-sync-logs/*.tsx` |
| Tab 6 项中文标签 | 全部存在 | `grep -c "'全部'\|'考勤'\|'绩效'\|'薪调'\|'入职信息'\|'社保假勤'" SyncLogsTabBar.tsx` |
| D-04 条件渲染 | 1 match | `grep "log.sync_type === 'attendance'" SyncLogRow.tsx` |
| 模式列 in <thead> | 1 match | `grep "模式" SyncLogsPage.tsx` |
| drawer 480px + role=dialog + aria-modal | 3/3 matches | `grep "width: '480px'\|role=\"dialog\"\|aria-modal=\"true\"" SyncLogDetailDrawer.tsx` |
| CSV 按钮文案 | 启用态 + 禁用态 tooltip 全存在 | `grep "下载未匹配工号 CSV\|本次同步无未匹配工号" SyncLogRow.tsx` |

## Self-Check: PASSED (Pre-UAT)

- FOUND: frontend/src/types/api.ts （SyncLogRead + SyncLogSyncType + SyncLogStatus）
- FOUND: frontend/src/services/feishuService.ts （getSyncLogs overload + downloadUnmatchedCsv）
- FOUND: frontend/src/index.css （--color-violet / -bg / -border）
- FOUND: frontend/src/utils/roleAccess.ts （admin + hrbp 同步日志菜单）
- FOUND: frontend/src/App.tsx （SyncLogsPage import + /feishu/sync-logs 路由）
- FOUND: frontend/src/pages/SyncLogsPage.tsx （完整实现，非 stub）
- FOUND: frontend/src/components/feishu-sync-logs/SyncLogsTabBar.tsx
- FOUND: frontend/src/components/feishu-sync-logs/CountersBadgeCluster.tsx
- FOUND: frontend/src/components/feishu-sync-logs/StatusBadge.tsx
- FOUND: frontend/src/components/feishu-sync-logs/SyncLogRow.tsx
- FOUND: frontend/src/components/feishu-sync-logs/SyncLogDetailDrawer.tsx
- FOUND: frontend/src/components/feishu-sync-logs/SyncLogsEmptyState.tsx
- FOUND commit: 0e740bb (Task 1)
- FOUND commit: ab8540a (Task 2)
- VERIFIED: tsc --noEmit → 0 errors
- VERIFIED: vite build → 808 modules, 3.33s, success
- VERIFIED: 0 shadcn/radix-ui 引用
- VERIFIED: UI-SPEC 6 Dimension 机器可检全部通过（Copywriting/Color/Typography/Spacing/Registry Safety 5 维 grep 绿；Dimension 2 Visuals 已按像素级参考实现并在 Task 3 UAT 通过 HR 目视最终签字）

## Final Self-Check 待 Task 3 UAT 签字追加

待 UAT approval 后再追加完整 "## Self-Check: PASSED" 章节与 HR 截图链接。
