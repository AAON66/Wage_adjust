---
phase: 07-dashboard-and-cache-layer
plan: 03
subsystem: ui
tags: [react, echarts, dashboard, drilldown, grid, cycle-selector]

requires:
  - phase: 07-dashboard-and-cache-layer
    provides: "Plan 01 后端 SQL 聚合 + Redis 缓存 + API 端点"
  - phase: 07-dashboard-and-cache-layer
    provides: "Plan 02 前端 ECharts 组件 + usePolling hook"
provides:
  - "Dashboard.tsx 双列网格重构（KPI 卡片 + 4 个 ECharts 图表 + 部门下钻）"
  - "周期选择器联动刷新（含状态重置）"
  - "部门洞察表格行展开下钻（DepartmentDrilldown 页内展开）"
  - "员工角色双重排除（ProtectedRoute + roleAccess.ts）"
  - "503 Redis 不可用错误状态传递到图表组件"
affects: [07-dashboard-and-cache-layer]

tech-stack:
  added: []
  patterns: ["dual-column CSS Grid layout", "cycle selector state reset on change", "department row expand/collapse"]

key-files:
  created: []
  modified:
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/components/dashboard/DepartmentInsightTable.tsx
    - frontend/src/components/dashboard/AILevelChart.tsx
    - frontend/src/components/dashboard/SalaryDistChart.tsx
    - frontend/src/components/dashboard/ApprovalPipelineChart.tsx
---

## 概要

Dashboard.tsx 全面重构为双列网格布局，集成全部 ECharts 图表组件，实现周期选择器联动刷新、部门表格页内下钻展开、员工角色双重排除、503 错误状态传递。人工验证通过。

## 自检: 通过

- [x] Dashboard.tsx 使用 CSS Grid 双列布局
- [x] 周期选择器切换后所有图表和状态重置
- [x] 部门表格行可展开/收起下钻
- [x] 员工角色无看板入口且 API 返回 403
- [x] Redis 不可用时图表显示 503 错误提示
- [x] Y 轴冗余标签已移除
- [x] TypeScript 编译零错误
