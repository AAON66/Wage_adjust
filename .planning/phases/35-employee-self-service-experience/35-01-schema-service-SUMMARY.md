---
phase: 35-employee-self-service-experience
plan: "01"
subsystem: backend/performance
tags: [schema, service, tests, eself-03, pydantic, performance-tier]
dependency_graph:
  requires:
    - 34-performance-management-service-and-api (PerformanceTierSnapshot model, PerformanceService base)
    - 33-performance-tier-engine (tiers_json str(UUID) key contract)
  provides:
    - MyTierResponse Pydantic schema (4-field D-04 contract)
    - PerformanceService.get_my_tier(employee_id) method (D-13 5-step logic)
    - 8 pytest cases covering all business branches
  affects:
    - Plan 35-02 (API handler that calls get_my_tier)
    - Plan 35-03 (frontend type MyTierResponse from D-12)
key_files:
  created: []
  modified:
    - backend/app/schemas/performance.py
    - backend/app/services/performance_service.py
    - backend/tests/test_services/test_performance_service.py
requirements:
  - ESELF-03
---

# Phase 35 Plan 01 Summary

Delivered the Phase 35 backend read contract for employee self-service tiers. `backend/app/schemas/performance.py` now exports `MyTierResponse`, `backend/app/services/performance_service.py` now exposes `get_my_tier(employee_id)`, and the service test suite includes 8 `get_my_tier` cases covering no snapshot, insufficient sample, ranked, not ranked, fallback year lookup, UUID key normalization, and tier/reason invariants.

Verification:
- `./.venv/bin/python -m pytest backend/tests/test_services/test_performance_service.py -k get_my_tier -v --no-header`
