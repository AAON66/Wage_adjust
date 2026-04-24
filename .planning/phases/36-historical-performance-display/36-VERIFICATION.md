# Phase 36 VERIFICATION

**状态：** 待人工验证
**预填时间：** 2026-04-24 11:37:41 CST
**执行计划：** `36-04`
**已完成自动工作：** `EvaluationDetail.tsx` 已挂载历史绩效面板，`tsc --noEmit` 已通过
**环境：** backend `uvicorn backend.app.main:app --reload --port 8011` + frontend `cd frontend && npm run dev`

## 本次已交付

- `EvaluationDetail.tsx` 已新增 `PerformanceHistoryPanel` import、state、`canViewPerformanceHistory` 门控
- 已新增 `refreshPerformanceHistory(targetEmployeeId: string)` helper，403/404 静默置空
- 已把历史绩效拉取并入 `refreshSubmissionData()` 的 `Promise.all`
- 已在 `SalaryDetailPanel` 所在 section 后挂载 `PerformanceHistoryPanel`
- `divider` 复用现有 `className="divider"` 约定

## UAT Matrix

| # | 角色 | 路径 | 预期 | 实际 | 结果 |
|---|------|------|------|------|------|
| 1 | admin | `/evaluations/{empA_eval}` | 显示 3 行、按 year DESC、4 列齐全；同页共存断言通过 | 待人工执行 | 待定 |
| 2 | hrbp | `/evaluations/{empA_eval}` | 同 1 | 待人工执行 | 待定 |
| 3 | managerA | `/evaluations/{empA_eval}` | 同部门可见，同 1 | 待人工执行 | 待定 |
| 4 | managerB | `/evaluations/{empA_eval}` | 跨部门 403 或 panel 空态，不崩溃、不泄露 comment | 待人工执行 | 待定 |
| 5 | empX | `/evaluations/{empA_eval}` | 若可进入页面，也不渲染 `PerformanceHistoryPanel` | 待人工执行 | 待定 |
| 6 | admin | `/evaluations/{empC_eval}` | 显示空态「暂无历史绩效记录」与补充说明 | 待人工执行 | 待定 |
| 7 | admin | 任意 evaluation 页面 | Network 出现一次 `/performance/records/by-employee/<uuid>` 且 200 | 待人工执行 | 待定 |
| 8 | empX | `/my-review` | 不出现历史绩效面板，只保留员工端既有内容 | 待人工执行 | 待定 |

## D-10 Never-Do Verification

- [x] `grep -c "PerformanceHistoryPanel" frontend/src/pages/MyReview.tsx` = `0`
- [x] `grep -c "PerformanceHistoryPanel" frontend/src/pages/Approvals.tsx` = `0`
- [x] `grep -c "/performance/me/history" backend/app/api/v1/performance.py` = `0`
- [x] `grep -c "PerformanceHistoryPanel" frontend/src/pages/EvaluationDetail.tsx` = `2`

## SC Coverage

- [ ] SC#1 HR/manager 在 `EvaluationDetail` 底部看到历史绩效 4 列
- [ ] SC#2 `SalaryDetailPanel` 与 `PerformanceHistoryPanel` 在同一页面共存，且 DOM/源码证据通过
- [ ] SC#3 无历史绩效时显示空态，不崩溃
- [ ] SC#4 `department_snapshot` 展示录入时部门，而不是当前部门

## DOM Coexistence Evidence (SC#2)

- 方法：源码 grep
- 命令：`grep -cE "<SalaryDetailPanel|<PerformanceHistoryPanel" frontend/src/pages/EvaluationDetail.tsx`
- 输出：`2`
- 断言：`>= 2`，已满足源码级同文件共存证据
- 备注：浏览器侧 `querySelectorAll` 证据待人工 UAT 时补充

## 自动验证记录

- `npx tsc --noEmit`：通过
- 当前任务代码提交：`dd0414a` `feat(36-04): mount performance history in evaluation detail`

## Screenshots

- 待人工补充：admin / hrbp / managerA / managerB / empX / 空态 / Network / MyReview 截图

## Findings / Gaps

- 暂无自动化阻塞
- 人工验证尚未执行，因此本文件当前不能视为最终验收结果

## Sign-off

- Tester：待填写
- Date：待填写
- Resume signal：`approved` 或 `failed: <描述>`
