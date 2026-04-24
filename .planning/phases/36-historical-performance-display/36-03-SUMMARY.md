---
phase: 36-historical-performance-display
plan: 03
subsystem: ui
tags: [react, typescript, axios, performance-history]
requires:
  - phase: 36-01
    provides: PerformanceRecord.comment 与 PerformanceHistoryResponse 后端契约基线
  - phase: 36-02
    provides: /performance/records/by-employee/{employee_id} 历史绩效 API
provides:
  - 前端 PerformanceRecordItem.comment 类型落位
  - performanceService 历史绩效 typed fetch 封装
  - PerformanceHistoryPanel 四列表格组件与 loading/empty/null 渲染
affects: [36-04, evaluation-detail, historical-performance-display]
tech-stack:
  added: []
  patterns: [typed axios thin wrapper, SalaryHistoryPanel 同风格 section + table-shell]
key-files:
  created:
    - .planning/phases/36-historical-performance-display/36-03-SUMMARY.md
    - frontend/src/components/performance/PerformanceHistoryPanel.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/services/performanceService.ts
key-decisions:
  - "PerformanceHistoryPanel 信任后端 year DESC 排序，不在前端二次排序。"
  - "comment 与 department_snapshot 的 null/空串统一经 renderNullable 显示为「—」。"
  - "service 层保持薄封装，只 return axios data，不新增本地错误分支。"
patterns-established:
  - "历史绩效 panel 复用 SalaryHistoryPanel 的 surface/section-head 视觉语言，但内容退化为纯表格。"
  - "员工维度历史接口在前端统一通过 encodeURIComponent(employeeId) 组装路径。"
requirements-completed: [PERF-07]
duration: 3min
completed: 2026-04-24
---

# Phase 36 Plan 03: 历史绩效前端类型、Service 与独立 Panel Summary

**补齐历史绩效前端类型契约、by-employee 拉取函数，并交付可独立挂载的 4 列历史绩效展示组件。**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-24T03:05:54Z
- **Completed:** 2026-04-24T03:08:54Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- 在 `frontend/src/types/api.ts` 为 `PerformanceRecordItem` 增加 `comment: string | null`，并新增 `PerformanceHistoryResponse`，让 Plan 02 API 的响应在前端有明确类型。
- 在 `frontend/src/services/performanceService.ts` 新增 `fetchPerformanceHistoryByEmployee(employeeId)`，通过 `encodeURIComponent(employeeId)` 访问 `/performance/records/by-employee/{employee_id}`。
- 新建 `frontend/src/components/performance/PerformanceHistoryPanel.tsx`，提供 `employeeName? / records / isLoading` props 契约，渲染 4 列表头、loading、empty 与 null 占位三条路径。

## Task Commits

Each task was committed atomically:

1. **Task 1: TS 类型扩展 — PerformanceRecordItem.comment + PerformanceHistoryResponse** - `3abe40f` (feat)
2. **Task 2: performanceService.ts 新增 fetchPerformanceHistoryByEmployee** - `a6aaa80` (feat)
3. **Task 3: 新建组件 PerformanceHistoryPanel.tsx** - `fe92cba` (feat)

**Plan metadata:** docs-only summary commit（本次按用户边界不包含 `STATE.md` / `ROADMAP.md`）

## Files Created/Modified

- `frontend/src/types/api.ts` - `PerformanceRecordItem.comment` 位于 1172 行，`PerformanceHistoryResponse` 位于 1187 行。
- `frontend/src/services/performanceService.ts` - `fetchPerformanceHistoryByEmployee(employeeId: string): Promise<PerformanceHistoryResponse>` 位于 183-189 行。
- `frontend/src/components/performance/PerformanceHistoryPanel.tsx` - props 契约位于 5-8 行，`renderNullable()` 位于 25-31 行，loading/empty/table 三分支位于 46-146 行。
- `.planning/phases/36-historical-performance-display/36-03-SUMMARY.md` - 记录本 plan 的交付结果、验收证据与执行边界。

## Verification

- `cd frontend && npx tsc --noEmit`：通过。
- `grep -nE 'comment: string \\| null;|export interface PerformanceHistoryResponse' frontend/src/types/api.ts`：命中 1172、1187 行。
- `grep -nE 'fetchPerformanceHistoryByEmployee|records/by-employee|PerformanceHistoryResponse' frontend/src/services/performanceService.ts`：命中 183-189 行。
- `grep -nE 'interface PerformanceHistoryPanelProps|export function PerformanceHistoryPanel|暂无历史绩效记录|正在加载该员工的历史绩效记录|renderNullable|title=|周期|绩效等级|评语|部门快照' frontend/src/components/performance/PerformanceHistoryPanel.tsx`：命中 props、三态文本、4 列表头与 tooltip 代码。

## Plan 04 Integration Notes

- 类型导入：`import type { PerformanceHistoryResponse, PerformanceRecordItem } from '../types/api'`
- service 调用：`fetchPerformanceHistoryByEmployee(employeeId).then(({ items }) => setPerformanceHistory(items))`
- 组件挂载：
  `import { PerformanceHistoryPanel } from '../components/performance/PerformanceHistoryPanel'`
  `<PerformanceHistoryPanel employeeName={employeeName} records={performanceHistory} isLoading={isPerformanceHistoryLoading} />`

## Decisions Made

- 绩效等级列使用 `status-pill` 色板而不是裸文本，沿用 Phase 34 `PerformanceRecordsTable` 的视觉语义。
- comment tooltip 采用 `title={record.comment ?? undefined}`，满足 threat model 中“截断不遮蔽全文”的缓解要求。
- 表格主体使用 `table-shell` + `table-lite`，减少新样式面扩张，便于 Plan 04 直接挂载到 `EvaluationDetail`。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 本地环境缺少 `rg`，验收命令回退到 `grep`**
- **Found during:** Summary / verification 收尾
- **Issue:** 终端环境没有 ripgrep，无法使用偏好的 `rg` 收集锚点行号。
- **Fix:** 改用计划本身已接受的 `grep -n` 完成所有验收锚点确认。
- **Files modified:** None
- **Verification:** 所有 `grep` 与 `npx tsc --noEmit` 命令通过
- **Committed in:** n/a

### Execution Boundary

**1. 按用户要求未更新 `STATE.md` / `ROADMAP.md`**
- **Issue:** 标准 execute-plan 工作流要求推进 state/roadmap，但本次 objective 明确禁止修改这两个文件。
- **Action:** 只完成代码文件与 `36-03-SUMMARY.md`，不触碰 `STATE.md`、`ROADMAP.md`，也不创建包含它们的 metadata commit。
- **Impact:** 本 plan 代码与 summary 完整交付，但全局规划状态需由拥有这些文件权限的后续执行者补记。

---

**Total deviations:** 1 auto-fixed（Rule 3: 1）+ 1 个执行边界偏差
**Impact on plan:** 代码交付与验收不受影响；仅项目级状态文档未在本次更新。

## Issues Encountered

- 第一次 `git commit` 因 `.git/index.lock` 权限报错失败，随后用提升权限的提交命令完成，不影响代码内容。
- 上一轮执行被中断时，Task 2 改动已留在工作区；本次先复核 `performanceService.ts` 再继续提交，避免重复编辑。

## User Setup Required

None - 本计划未引入新的外部服务、环境变量或手工配置步骤。

## Known Stubs

None.

## Next Phase Readiness

- Plan 04 可以直接 import `fetchPerformanceHistoryByEmployee` 与 `PerformanceHistoryPanel`，把 state 和 `useEffect` 挂到 `EvaluationDetail.tsx`。
- `PerformanceHistoryPanel` 已满足 4 列顺序、空态、loading、NULL 占位与 tooltip 需求，无需再补组件内逻辑。
- 当前未修改 `EvaluationDetail.tsx`，符合本计划“组件级交付，不触挂载位置”的边界。

## Self-Check: PASSED

- `FOUND: .planning/phases/36-historical-performance-display/36-03-SUMMARY.md`
- `FOUND: 3abe40f`
- `FOUND: a6aaa80`
- `FOUND: fe92cba`

---
*Phase: 36-historical-performance-display*
*Completed: 2026-04-24*
