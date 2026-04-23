---
phase: 35-employee-self-service-experience
plan: "02"
subsystem: backend/performance-api
tags: [api, performance-tier, self-service, eself-03]
dependency_graph:
  requires:
    - 35-01 (MyTierResponse + PerformanceService.get_my_tier)
  provides:
    - GET /api/v1/performance/me/tier handler
    - API test coverage for self-service tier query
  affects:
    - 35-03 (frontend service contract)
    - 35-04 (frontend badge integration)
key_files:
  created: []
  modified:
    - backend/app/api/v1/performance.py
    - backend/tests/test_api/test_performance_api.py
requirements:
  - ESELF-03
---

# Phase 35 Plan 02 Summary

Added `GET /api/v1/performance/me/tier` as the self-service API path for Phase 35. The handler uses `get_current_user`, returns `422` for unbound users, returns `404` for stale employee bindings, and delegates successful reads to `PerformanceService.get_my_tier(current_user.employee_id)`.

Replaced the old placeholder API test with 8 real `me_tier` tests covering employee and admin happy paths, `insufficient_sample`, `no_snapshot`, `not_ranked`, `422` unbound, `404` missing employee, and a negative assertion that the response body exposes only `year`, `tier`, `reason`, and `data_updated_at`.

Verification:
- `./.venv/bin/python -m pytest backend/tests/test_api/test_performance_api.py -k me_tier -v --no-header`
- `./.venv/bin/python -m pytest backend/tests/test_api/test_performance_api.py -v --no-header`
