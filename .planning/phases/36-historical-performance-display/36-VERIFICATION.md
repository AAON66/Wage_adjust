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
- `./.venv/bin/pytest backend/tests/test_api/test_performance_history_api.py backend/tests/test_services/test_performance_service.py -q`：`47 passed`
- 真实库 token 权限矩阵复跑（目标员工：`钟卉` / `TOC创新业务`）：
  - admin → `200`，返回 `items[0].comment` / `department_snapshot`
  - 同部门 manager（`leader@test.com`）→ `200`
  - 跨部门 manager（`hr@test.com`）→ `403`
  - employee（`test2@test.com`）→ `403`
  - admin + 不存在 employee_id → `404`
- 数据库 schema 校验：`PRAGMA table_info(performance_records)` 已出现 `comment TEXT` 列
- 当前任务代码提交：`dd0414a` `feat(36-04): mount performance history in evaluation detail`

## Screenshots

- 待人工补充：admin / hrbp / managerA / managerB / empX / 空态 / Network / MyReview 截图

## Findings / Gaps

- 自动化过程中发现真实库最初未执行 `36_01_add_comment_perf` 迁移，导致 `/performance/records/by-employee/{employee_id}` 对真实数据返回 `500`（`sqlite3.OperationalError: no such column: performance_records.comment`）
- 已执行 `./.venv/bin/alembic upgrade head` 修复本地 schema 后复测，admin / 同部门 manager 场景恢复为 `200`
- 当前主库不存在“存在但零历史绩效”的员工（`employees_without_performance_records = 0`），因此 UAT 场景 6 仍需人工或专门构造数据验证空态
- 人工验证尚未执行，因此本文件当前不能视为最终验收结果

## Sign-off

- Tester：待填写
- Date：待填写
- Resume signal：`approved` 或 `failed: <描述>`
