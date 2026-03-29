---
phase: 08-employee-self-service-ui
plan: 02
subsystem: ui
tags: [react, myreview, step-bar, radar-chart, salary-card, employee-self-service]

requires:
  - phase: 08-employee-self-service-ui
    provides: "Plan 01 员工自助 UI 子组件（步骤条、雷达图、维度卡片、调薪卡片）"
provides:
  - "MyReview 页面完整集成：步骤条 + 雷达图 + 维度卡片 + 调薪百分比 + 条件渲染"
  - "员工可独立查看评估状态、结果和调薪建议"
affects: [08-employee-self-service-ui]

tech-stack:
  added: []
  patterns: ["conditional section rendering based on evaluation/approval status", "sequential API calls with dependency chain"]

key-files:
  created: []
  modified:
    - frontend/src/pages/MyReview.tsx
---

## 概要

将 Plan 01 创建的所有组件集成到 MyReview 页面。实现条件渲染：无评估→引导提示、有评估→步骤条+状态、confirmed→雷达图+维度卡片、approved→调薪百分比。人工验证通过。

## 自检: 通过

- [x] 步骤条正确显示审批阶段
- [x] 雷达图渲染 5 维度中文标签
- [x] 维度卡片显示得分/权重/说明
- [x] 调薪百分比仅 approved 后显示
- [x] 空状态显示引导提示
- [x] 周期切换数据正确更新
- [x] TypeScript 编译零错误
