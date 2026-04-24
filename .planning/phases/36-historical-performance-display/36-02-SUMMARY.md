---
phase: 36-historical-performance-display
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, performance, access-scope, pytest]
requires:
  - phase: 36-01
    provides: PerformanceRecord.comment 与 PerformanceHistoryResponse schema
  - phase: 34-performance-management-service-and-api
    provides: PerformanceService、performance router、AccessScopeService 复用基础
provides:
  - 单员工历史绩效查询 `PerformanceService.list_records_by_employee()`
  - `GET /api/v1/performance/records/by-employee/{employee_id}` 安全读端点
  - admin/hrbp/manager 权限矩阵与空结果 API 集成测试
affects: [36-03, 36-04, historical-performance-display]
tech-stack:
  added: []
  patterns: [require_roles 与 AccessScopeService 双层鉴权, 复用 salary API 测试 helper 构造隔离数据库]
key-files:
  created:
    - backend/tests/test_api/test_performance_history_api.py
  modified:
    - backend/app/services/performance_service.py
    - backend/app/api/v1/performance.py
    - backend/tests/test_services/test_performance_service.py
key-decisions:
  - "单员工历史接口返回 flat items，不分页，并在 Service 层按 year DESC 预排序。"
  - "router 先用 require_roles('admin','hrbp','manager') 挡住 employee，再用 AccessScopeService 做部门范围校验。"
  - "API 集成测试复用 test_salary_api 的 ApiDatabaseContext/build_client/bind_user_departments，避免扩散到全局 fixture。"
patterns-established:
  - "敏感的 employee_id 读接口采用角色白名单 + AccessScopeService 组合，而不是单独依赖部门判断。"
  - "历史类接口返回 {items: []} 空数组而非 404，交由前端渲染空状态。"
requirements-completed: [PERF-07]
duration: 3min
completed: 2026-04-24
---

# Phase 36 Plan 02: 历史绩效 Service 与员工维度 API Summary

**按员工维度交付 year DESC 的历史绩效查询能力，并通过双层权限链将 manager 访问限制在本部门范围内。**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-24T02:50:56Z
- **Completed:** 2026-04-24T02:53:41Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- 在 `PerformanceService` 新增 `list_records_by_employee(employee_id) -> list[PerformanceRecordRead]`，通过 `join(Employee)` 填充 `employee_name`，并按 `PerformanceRecord.year.desc()` 返回单员工全部历史记录。
- 在 `backend/app/api/v1/performance.py` 新增 `GET /performance/records/by-employee/{employee_id}`，返回 `PerformanceHistoryResponse`，串联 `require_roles('admin','hrbp','manager')` 与 `AccessScopeService.ensure_employee_access()`。
- 新建 8 条 API 集成测试，覆盖 admin、hrbp、manager 同部门、manager 跨部门、employee、未登录、404、不存在记录的完整矩阵，并验证旧的 `test_performance_api.py` 无回归。

## Task Commits

每个任务按原子边界提交：

1. **Task 1: Service 层 by-employee 用例（RED）** - `db02fac` (test)
2. **Task 1: PerformanceService.list_records_by_employee() 实现（GREEN）** - `3cada27` (feat)
3. **Task 2: by-employee 历史绩效端点与权限链** - `67ce569` (feat)
4. **Task 3: 权限矩阵 API 集成测试** - `734768a` (test)

## Files Created/Modified

- `backend/app/services/performance_service.py` - 新增 `list_records_by_employee()`，按员工过滤并按 `year DESC` 排序。
- `backend/app/api/v1/performance.py` - 新增 `/records/by-employee/{employee_id}` handler，补齐 `PerformanceHistoryResponse` 与 `AccessScopeService` 接入。
- `backend/tests/test_services/test_performance_service.py` - 新增 6 条 `by_employee` service 测试，覆盖排序、空结果、NULL 字段、隔离和 employee_name join。
- `backend/tests/test_api/test_performance_history_api.py` - 新增 8 条端到端权限矩阵测试，复用 `test_salary_api` 的数据库 helper。

## Decisions Made

- 端点返回 shape 冻结为 `PerformanceHistoryResponse(items: list[PerformanceRecordRead])`，不引入分页字段。
- `employee` 角色即使访问本人数据，也必须被 `require_roles('admin','hrbp','manager')` 直接拦下，避免落入 `AccessScopeService` 的 self-access 分支。
- `hrbp` 测试通过绑定 `Dept-A` 与 `Dept-B` 两个部门来模拟当前代码库中的“全范围”可见性，而不修改访问控制实现。

## Verification

- `./.venv/bin/pytest backend/tests/test_services/test_performance_service.py -x -v -k "by_employee"`：6 passed，0 failed，约 0.16s
- `./.venv/bin/python -c "from backend.app.api.v1.performance import router; print([r.path for r in router.routes])"`：输出包含 `/performance/records/by-employee/{employee_id}`
- `./.venv/bin/pytest backend/tests/test_api/test_performance_history_api.py -x -v`：8 passed，0 failed，约 1.90s
- `./.venv/bin/pytest backend/tests/test_api/test_performance_api.py -x -v`：20 passed，0 failed，约 3.12s

## 权限矩阵结果

| 场景 | 结果 |
|------|------|
| admin 访问有 2 条记录员工 | PASS |
| hrbp 访问有 2 条记录员工 | PASS |
| manager 访问同部门员工 | PASS |
| manager 访问跨部门员工 | PASS（403） |
| employee 访问任意员工 | PASS（403） |
| 未登录访问 | PASS（401） |
| admin 访问不存在员工 | PASS（404） |
| admin 访问无历史记录员工 | PASS（200 + `items: []`） |

## API Contract 冻结快照

- **Path:** `GET /api/v1/performance/records/by-employee/{employee_id}`
- **Dependencies:** `get_db` → `get_app_settings` → `require_roles('admin', 'hrbp', 'manager')` → `AccessScopeService.ensure_employee_access()`
- **成功响应:** `200 OK` + `PerformanceHistoryResponse(items=[PerformanceRecordRead, ...])`
- **错误响应:** `403`（跨部门或 employee 角色）、`404`（员工不存在）、`401`（未登录）
- **排序与空态:** `items` 由后端按 `year DESC` 预排序；无记录时返回 `{"items": []}`

## Helper 选择记录

- 采用 `from backend.tests.test_api.test_salary_api import ApiDatabaseContext, build_client, bind_user_departments, register_and_login_user`
- 未出现跨测试模块 import 导致的 fixture/收集问题，因此没有回退到本文件复制 helper

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] API 错误响应断言对齐全局错误包装**
- **Found during:** Task 3（权限矩阵 API 集成测试）
- **Issue:** 计划用例草案按裸 `detail` 断言 403/404，但当前项目通过全局异常处理器统一包装错误响应，导致 `response.json()['detail']` 不稳定。
- **Fix:** 测试改为断言 `response.text` 包含中文错误文案，仍然覆盖 403/404 语义与具体消息。
- **Files modified:** `backend/tests/test_api/test_performance_history_api.py`
- **Verification:** `./.venv/bin/pytest backend/tests/test_api/test_performance_history_api.py -x -v`
- **Committed in:** `734768a`

---

**Total deviations:** 1 auto-fixed（Rule 3: 1）
**Impact on plan:** 仅是测试断言与现有错误包格式对齐，无范围扩张，API 契约与安全目标不变。

## Issues Encountered

- `DetachedInstanceError`：测试 seed 阶段在 session 关闭后读取 ORM 对象属性会失败，已在同一任务中改为先固化 `employee_id` 字符串再传递。

## User Setup Required

None - 本计划未引入新的外部服务、环境变量或手工配置步骤。

## Known Stubs

None.

## Next Phase Readiness

- Plan 03/04 可以直接依赖 `GET /api/v1/performance/records/by-employee/{employee_id}` 拉取员工历史绩效。
- 前端只需消费既有 `PerformanceRecordRead` 字段：`year / grade / comment / department_snapshot / employee_name`。
- 当前未触碰 `STATE.md`、`ROADMAP.md`，符合本次执行边界。

## Self-Check: PASSED

- `FOUND: .planning/phases/36-historical-performance-display/36-02-SUMMARY.md`
- `FOUND: db02fac`
- `FOUND: 3cada27`
- `FOUND: 67ce569`
- `FOUND: 734768a`
