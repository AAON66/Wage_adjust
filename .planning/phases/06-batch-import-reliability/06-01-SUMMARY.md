---
phase: 06-batch-import-reliability
plan: 01
subsystem: api, database
tags: [savepoint, xlsx, openpyxl, audit-log, partial-import, http-207]

requires:
  - phase: 04-audit-log-wiring
    provides: AuditLog model and audit infrastructure
  - phase: 05-submission-evidence-management
    provides: Employee/Certification models, IdentityBindingService
provides:
  - SAVEPOINT-based row-level partial import for employees and certifications
  - xlsx file read/write support (templates + error reports)
  - 5000 row import limit
  - Employee upsert audit logging
  - HTTP 207 Multi-Status response for partial failures
  - Certification upsert (employee_id + certification_type key)
affects: [06-02, 06-03, frontend-import-page]

tech-stack:
  added: [openpyxl==3.1.5]
  patterns: [SAVEPOINT + expire_all session cleanup, HTTP 207 for partial success]

key-files:
  created: []
  modified:
    - backend/app/services/import_service.py
    - backend/app/api/v1/imports.py
    - requirements.txt

key-decisions:
  - "AuditLog 的 operator_role 存储在 detail JSON 中（模型无 operator_role 列）"
  - "认证导入使用 (employee_id, certification_type) 作为 upsert 键"
  - "SAVEPOINT 失败后调用 expire_all() 清理会话状态防止连锁失败"
  - "部分成功时使用 HTTP 207 Multi-Status 而非 201"

patterns-established:
  - "SAVEPOINT per row: try + begin_nested + expire_all on failure"
  - "Dynamic HTTP status: 201 for full success, 207 for partial failure"

requirements-completed: [IMP-01, IMP-02, IMP-03, IMP-04, IMP-05]

duration: 4min
completed: 2026-03-28
---

# Phase 06 Plan 01: Batch Import Reliability Summary

**SAVEPOINT 逐行部分成功导入（员工+认证）、xlsx 读写支持、审计日志、HTTP 207 Multi-Status 响应**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T14:18:34Z
- **Completed:** 2026-03-28T14:22:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 员工和认证导入均改造为 SAVEPOINT 逐行处理，单行失败不影响其他行
- xlsx/xls 文件可正常读取导入，xlsx 模板下载和错误报告导出
- 5000 行导入上限校验，超出时返回明确提示
- 员工 upsert 更新时写入 AuditLog 审计日志（含旧值/新值）
- API 层部分失败返回 HTTP 207 Multi-Status
- 认证导入中缺失员工引用的行被正确记录为失败
- 错误行结果增加 error_column 字段用于精确定位

## Task Commits

Each task was committed atomically:

1. **Task 1: ImportService 核心改造** - `0b58511` (feat)
2. **Task 2: API 层 HTTP 207 响应 + 模板/报告端点扩展** - `190792c` (feat)

## Files Created/Modified
- `backend/app/services/import_service.py` - SAVEPOINT 逐行处理、xlsx 读写、审计日志、5000 行限制、error_column
- `backend/app/api/v1/imports.py` - HTTP 207 响应、模板/报告格式参数、operator_id 传递
- `requirements.txt` - 添加 openpyxl==3.1.5

## Decisions Made
- AuditLog 模型没有 operator_role 列，将 operator_role 存储在 detail JSON 字段中
- 认证导入使用 (employee_id, certification_type) 作为 upsert 键，沿用现有设计
- SAVEPOINT 失败后调用 expire_all() 清理会话中的 stale 对象状态
- 部分成功时使用 HTTP 207 Multi-Status 而非 201

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AuditLog 模型无 operator_role 列**
- **Found during:** Task 1
- **Issue:** 计划要求写入 AuditLog 时使用 operator_role 字段，但实际模型没有此列
- **Fix:** 将 operator_role 存储在 detail JSON 的嵌套字段中
- **Files modified:** backend/app/services/import_service.py
- **Verification:** ImportService 导入无报错
- **Committed in:** 0b58511

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** 审计信息完整记录，无功能损失。

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 批量导入核心改造完成，前端可对接 HTTP 207 状态码和 error_column 字段
- xlsx 模板下载和错误报告导出可供 06-02/06-03 计划使用
- 认证导入的 upsert 路径已完成 SAVEPOINT 改造

---
*Phase: 06-batch-import-reliability*
*Completed: 2026-03-28*
