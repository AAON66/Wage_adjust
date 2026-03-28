---
phase: 07-dashboard-and-cache-layer
plan: 01
subsystem: dashboard-backend
tags: [redis, cache, sql-aggregation, dashboard-api, rbac]
dependency_graph:
  requires: []
  provides: [CacheService, dashboard-sql-aggregation, dashboard-api-endpoints]
  affects: [frontend-dashboard, approval-workflow-cache]
tech_stack:
  added: [redis-cache-layer]
  patterns: [sql-group-by-aggregation, user-id-cache-isolation, event-based-invalidation]
key_files:
  created:
    - backend/app/core/redis.py
    - backend/app/services/cache_service.py
    - backend/tests/test_services/test_cache_service.py
  modified:
    - backend/app/services/dashboard_service.py
    - backend/app/api/v1/dashboard.py
    - backend/app/schemas/dashboard.py
    - backend/tests/test_services/test_dashboard_service.py
    - backend/tests/test_api/test_dashboard_api.py
decisions:
  - "缓存 key 使用 user_id 而非 role，防止 manager 跨部门数据泄漏"
  - "KPI 摘要端点不走 Redis 缓存，直接查库支持 30 秒轮询"
  - "Redis 不可用时缓存端点返回 503 而非静默降级"
  - "所有看板端点统一使用 require_roles 鉴权，employee 角色返回 403"
metrics:
  duration: 6min
  completed: "2026-03-28T16:55:00Z"
  tasks: 2
  files: 8
  tests_added: 24
---

# Phase 07 Plan 01: 后端看板服务改造 Summary

**SQL 聚合 + Redis 缓存层 + 新 API 端点，缓存 key 使用 user_id 隔离，KPI 端点不缓存直查库**

## What Was Built

### Task 1: Redis 连接管理 + CacheService + DashboardService SQL 聚合改造
- **backend/app/core/redis.py**: 懒加载单例 Redis 客户端，首次调用 ping() 验证连接，不提供内存回退
- **backend/app/services/cache_service.py**: 缓存封装服务，key 格式 `dashboard:{cycle_id}:{user_id}:{chart_type}`，支持 get/set/invalidate_cycle/invalidate_for_event
- **backend/app/services/dashboard_service.py**: 新增 5 个 SQL 聚合方法（ai_level_distribution、salary_distribution、approval_pipeline、kpi_summary、department_drilldown），使用 func.count/func.avg + group_by，无全表扫描

### Task 2: API 端点 + Schema + 测试
- **4 个新端点**: GET /dashboard/kpi-summary、salary-distribution、approval-pipeline、department-drilldown
- **鉴权升级**: 所有 11 个看板端点使用 require_roles('admin','hrbp','manager')，employee 角色返回 403
- **KPI 不缓存**: kpi-summary 端点直接查库，不依赖 Redis，支持 30 秒前端轮询
- **503 错误处理**: 缓存端点 Redis 不可用时返回 HTTP 503 + 错误提示
- **Schema 更新**: 新增 KpiSummaryResponse、ApprovalPipelineResponse、DepartmentDrilldownResponse；DistributionItemRead 增加 percentage 字段

## Decisions Made

1. **缓存 key 使用 user_id 而非 role** -- 原方案使用 role 作为 key 组成部分，但同角色的不同 manager 管理不同部门，会导致缓存数据泄漏。使用 user_id 确保每个用户的缓存完全隔离。
2. **KPI 摘要不走缓存** -- 30 秒前端轮询与 5-15 分钟缓存 TTL 矛盾，KPI 端点直接查库返回实时数据。
3. **Redis 为必须依赖** -- 缓存端点 Redis 不可用时返回 503，不静默降级到无缓存模式。
4. **require_roles 鉴权** -- employee 角色在 API 层直接收到 403，而非依赖前端隐藏。

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| test_cache_service.py | 10 | All passed |
| test_dashboard_service.py (new SQL) | 6 | All passed |
| test_dashboard_api.py | 10 | All passed |

关键测试:
- `test_user_isolation`: 验证不同 user_id 的缓存完全隔离
- `test_employee_role_gets_403`: employee 角色访问看板返回 403
- `test_kpi_summary_works_without_redis`: KPI 端点在 Redis 不可用时仍返回 200
- `test_cached_endpoint_returns_503_when_redis_down`: 缓存端点 Redis 不可用时返回 503

## Commits

| Hash | Message |
|------|---------|
| 48c8b47 | feat(07-01): Redis 连接管理 + CacheService 缓存封装 + DashboardService SQL 聚合改造 |
| 9beb6ea | feat(07-01): 新增看板 API 端点 + require_roles 鉴权 + KPI 不缓存 + 完整测试 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 已有 API 测试需要 Redis mock**
- **Found during:** Task 2
- **Issue:** 改造 ai-level-distribution 端点使用缓存后，已有测试 `test_dashboard_snapshot_and_child_endpoints` 和 `test_dashboard_is_scoped_by_bound_departments` 因无 Redis 连接而失败 (503)
- **Fix:** 为已有测试添加 `patch('backend.app.api.v1.dashboard.get_redis')` mock
- **Files modified:** backend/tests/test_api/test_dashboard_api.py

## Known Stubs

None -- all endpoints are wired to real SQL queries and Redis cache layer.

## Self-Check: PASSED

- All 8 key files verified present
- Commits 48c8b47 and 9beb6ea verified in git log
- 26 tests passed (10 cache + 6 SQL + 10 API)
