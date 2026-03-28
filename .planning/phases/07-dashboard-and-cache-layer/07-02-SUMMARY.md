---
phase: 07-dashboard-and-cache-layer
plan: 02
subsystem: frontend-dashboard-charts
tags: [echarts, dashboard, usePolling, kpi, charts]
dependency_graph:
  requires: [echarts, echarts-for-react]
  provides: [AILevelChart, SalaryDistChart, ApprovalPipelineChart, DepartmentDrilldown, KpiCards, usePolling]
  affects: [Dashboard.tsx integration in Plan 03]
tech_stack:
  added: [echarts@6.0.0, echarts-for-react@3.0.6]
  patterns: [usePolling with AbortController, ServiceUnavailableBanner reuse, ECharts BASE option sharing]
key_files:
  created:
    - frontend/src/components/dashboard/AILevelChart.tsx
    - frontend/src/components/dashboard/SalaryDistChart.tsx
    - frontend/src/components/dashboard/ApprovalPipelineChart.tsx
    - frontend/src/components/dashboard/DepartmentDrilldown.tsx
    - frontend/src/components/dashboard/KpiCards.tsx
    - frontend/src/hooks/usePolling.ts
  modified:
    - frontend/package.json
    - frontend/src/types/api.ts
    - frontend/src/services/dashboardService.ts
decisions:
  - ServiceUnavailableBanner exported from AILevelChart and reused by SalaryDistChart and ApprovalPipelineChart
  - KpiCards uses inline <style> for responsive grid to avoid external CSS dependency
  - DepartmentDrilldown uses 200px mini chart with tighter grid padding
metrics:
  duration: 3min
  completed: "2026-03-28T16:52:00Z"
  tasks: 2
  files: 11
---

# Phase 07 Plan 02: 前端 ECharts 图表组件 + usePolling hook + 看板 API 客户端 Summary

安装 ECharts 6.0 依赖，创建 5 个 ECharts 图表组件（AI 等级分布、调薪幅度、审批流水线、部门下钻、KPI 卡片）和 usePolling hook（含 AbortController 请求取消 + 503 Redis 不可用检测），新增 5 个 dashboardService API 函数和 3 个 TypeScript 类型定义。

## Task Completion

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | 安装 ECharts + 新增 TypeScript 类型 + API 客户端函数 + usePolling hook | 67bef97 | package.json, api.ts, dashboardService.ts, usePolling.ts |
| 2 | 创建 ECharts 图表组件（含 503 错误状态 UI）+ KPI 卡片 | 978d54b | AILevelChart.tsx, SalaryDistChart.tsx, ApprovalPipelineChart.tsx, DepartmentDrilldown.tsx, KpiCards.tsx |

## Decisions Made

1. **ServiceUnavailableBanner 复用**: 从 AILevelChart 导出 ServiceUnavailableBanner 组件，SalaryDistChart 和 ApprovalPipelineChart 直接引用，避免重复代码
2. **KpiCards 响应式 CSS**: 使用 inline `<style>` 标签实现 4/2/1 列响应式网格，避免引入额外 CSS 文件依赖
3. **DepartmentDrilldown 迷你图表**: 使用 200px 容器高度和紧凑 grid padding (8px) 适配下钻面板布局

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- TypeScript 编译 (`tsc --noEmit`): PASS
- ECharts 依赖安装验证: PASS
- 所有 6 个新文件存在: PASS
- AbortController 在 usePolling 中使用: PASS
- 503 错误 UI 文案验证: PASS

## Known Stubs

None - all components are fully implemented with real data bindings. Integration into Dashboard.tsx is deferred to Plan 03 as designed.

## Self-Check: PASSED

- All 6 created files exist on disk
- Both task commits (67bef97, 978d54b) verified in git log
