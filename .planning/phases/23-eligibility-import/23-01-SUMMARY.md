---
phase: 23-eligibility-import
plan: 01
subsystem: database, api
tags: [sqlalchemy, alembic, rate-limiter, feishu, import, excel]

requires:
  - phase: 13-eligibility-engine-data-layer
    provides: EligibilityBatch model and eligibility engine patterns
  - phase: 09-feishu-attendance-integration
    provides: FeishuService base class with token management and record fetching
  - phase: 06-batch-import-reliability
    provides: ImportService with SAVEPOINT-per-row pattern

provides:
  - NonStatutoryLeave ORM model with unique constraint on (employee_id, year)
  - ImportService support for hire_info and non_statutory_leave Excel import types
  - Shared InMemoryRateLimiter module at backend/app/core/rate_limiter.py
  - FeishuService with 60 RPM rate limiting and exponential backoff retry
  - FeishuService sync methods for salary_adjustments, hire_info, non_statutory_leave
  - FeishuService.list_bitable_fields for field mapper UI
  - FeishuService.parse_bitable_url for URL-based table identification

affects: [23-02, 23-03, feishu-integration, import-management]

tech-stack:
  added: []
  patterns:
    - "Shared rate limiter with acquire() (raise) and wait_and_acquire() (blocking) modes"
    - "Feishu API exponential backoff retry on rate-limit (code 99991400 / HTTP 429)"

key-files:
  created:
    - backend/app/models/non_statutory_leave.py
    - backend/app/core/rate_limiter.py
    - alembic/versions/e23_add_non_statutory_leaves.py
    - backend/tests/test_services/test_import_hire_leave.py
  modified:
    - backend/app/services/import_service.py
    - backend/app/services/llm_service.py
    - backend/app/services/feishu_service.py

key-decisions:
  - "InMemoryRateLimiter extracted to core module with dual-mode API (raise vs block)"
  - "FeishuService uses 60 RPM limiter with wait_and_acquire for non-interactive sync"
  - "LlmService re-exports InMemoryRateLimiter for backward compatibility"
  - "parse_bitable_url supports both query-param and path-segment URL formats"

patterns-established:
  - "Rate limiter shared module pattern: core/rate_limiter.py with injectable clock/sleeper"
  - "Feishu sync method pattern: config -> token -> fetch -> emp_map -> upsert -> commit"

requirements-completed: [ELIGIMP-02, FEISHU-01]

duration: 10min
completed: 2026-04-14
---

# Phase 23 Plan 01: Data Layer + Service Extensions Summary

**NonStatutoryLeave 模型 + ImportService hire_info/non_statutory_leave 导入 + InMemoryRateLimiter 共享模块 + FeishuService 限流和 4 种数据类型同步**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-14T02:32:59Z
- **Completed:** 2026-04-14T02:43:08Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- NonStatutoryLeave ORM 模型创建，支持按 (employee_id, year) 唯一约束的幂等 upsert
- ImportService 从 4 种导入类型扩展到 6 种（新增 hire_info 和 non_statutory_leave），含 CSV/XLSX 模板
- InMemoryRateLimiter 提取为 core 共享模块，LlmService 和 FeishuService 均使用
- FeishuService 集成 60 RPM 限流 + 指数退避重试，新增 5 个方法（3 种同步 + 字段列表 + URL 解析）

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for hire_info and non_statutory_leave** - `b3ddde7` (test)
2. **Task 1 (GREEN): NonStatutoryLeave model + ImportService extensions** - `3ea82e6` (feat)
3. **Task 2: InMemoryRateLimiter extraction + FeishuService enhancements** - `67472e2` (feat)

## Files Created/Modified
- `backend/app/models/non_statutory_leave.py` - NonStatutoryLeave ORM 模型
- `backend/app/core/rate_limiter.py` - 共享 InMemoryRateLimiter（acquire + wait_and_acquire）
- `alembic/versions/e23_add_non_statutory_leaves.py` - Alembic 迁移脚本
- `backend/tests/test_services/test_import_hire_leave.py` - 10 个测试用例
- `backend/app/services/import_service.py` - 新增 hire_info 和 non_statutory_leave 导入
- `backend/app/services/llm_service.py` - InMemoryRateLimiter 改为从 core 导入（向后兼容）
- `backend/app/services/feishu_service.py` - 限流集成 + 5 个新方法

## Decisions Made
- InMemoryRateLimiter 采用双模式 API：acquire() 抛异常（适合 LLM 调用），wait_and_acquire() 阻塞等待（适合飞书同步）
- FeishuService 使用 60 RPM 限流器，每次 HTTP 请求前调用 wait_and_acquire()
- LlmService 通过 re-export 保持向后兼容，现有代码无需修改
- parse_bitable_url 同时支持查询参数和路径段两种 URL 格式，仅匹配 feishu.cn 域名

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

6 个预先存在的测试失败（test_import_api_flow、test_public_api_key_and_read_endpoints 等），均为 Phase 23 之前的问题，与本次改动无关。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 数据层基础完成，Plan 02 可以构建 API 路由和 Pydantic schemas
- Plan 03 前端页面可以调用 list_bitable_fields 和 parse_bitable_url 实现字段映射 UI
- FeishuService 同步方法已就绪，Plan 02 的 Celery 任务可以直接调用

## Self-Check: PASSED

All 4 created files verified on disk. All 3 commit hashes found in git log.

---
*Phase: 23-eligibility-import*
*Completed: 2026-04-14*
