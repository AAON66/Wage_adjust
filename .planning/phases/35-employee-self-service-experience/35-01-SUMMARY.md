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
tech_stack:
  added:
    - Literal typing for tier/reason fields (from typing import Literal)
  patterns:
    - Pydantic v2 Literal union for constrained enum fields
    - SQLAlchemy scalar() with ORDER BY year DESC LIMIT 1 for fallback
    - str(employee_id) normalization for tiers_json UUID key lookup
key_files:
  created: []
  modified:
    - backend/app/schemas/performance.py
    - backend/app/services/performance_service.py
    - backend/tests/test_services/test_performance_service.py
decisions:
  - "MyTierResponse uses Literal[1,2,3]|None for tier (not int|None) to expose legal value domain in OpenAPI"
  - "Service layer returns MyTierResponse for all branches; no raw Exception raises (API layer handles 422/404)"
  - "No Redis cache for get_my_tier (reads DB directly, snapshot table is < 20 rows lifetime)"
  - "str(employee_id) normalization covers both UUID object and str inputs for tiers_json key lookup"
metrics:
  duration_minutes: 3
  completed_date: "2026-04-22"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
requirements:
  - ESELF-03
---

# Phase 35 Plan 01: Schema + Service for get_my_tier — Summary

**One-liner:** MyTierResponse 4-field Pydantic schema (D-04 contract) + PerformanceService.get_my_tier() 5-branch fallback logic + 8 pytest cases covering all business branches including str(UUID) key normalization.

---

## What Was Built

### Task 1: MyTierResponse Pydantic Schema

Added `MyTierResponse` class to `backend/app/schemas/performance.py` after `AvailableYearsResponse`.

Exact fields per D-04 contract:
- `year: int | None`
- `tier: Literal[1, 2, 3] | None` — enforces legal value domain in OpenAPI schema
- `reason: Literal['insufficient_sample', 'no_snapshot', 'not_ranked'] | None`
- `data_updated_at: datetime | None`

Added `from typing import Literal` import. No forbidden fields (display_label, percentile, rank, as_of) present.

### Task 2: PerformanceService.get_my_tier Method

Added `get_my_tier(employee_id: str) -> MyTierResponse` method to `backend/app/services/performance_service.py`, placed after `get_tier_summary` to keep read-path methods grouped.

5-step D-13 logic:
1. Query current year snapshot (`WHERE year == datetime.now().year`)
2. Fallback to `ORDER BY year DESC LIMIT 1` if not found
3. Return `{year=None, tier=None, reason='no_snapshot', data_updated_at=None}` if no snapshot at all
4. Return `insufficient_sample` branch if `snapshot.insufficient_sample is True`
5. Lookup `tiers_json.get(str(employee_id))`: return tier (1/2/3) or `not_ranked`

Key implementation decisions:
- `str(employee_id)` normalization handles both UUID object and str inputs
- No Redis cache (reads DB directly per D-13 Deferred Ideas)
- No raw Exception raises; all branches return `MyTierResponse`
- `MyTierResponse` imported and added to schemas import list

### Task 3: 8 pytest Cases

Added 8 `test_get_my_tier_*` functions to `backend/tests/test_services/test_performance_service.py`:

| Test | Branch |
|------|--------|
| `test_get_my_tier_returns_no_snapshot_when_db_empty` | A: no snapshot in DB |
| `test_get_my_tier_returns_insufficient_sample_when_flag_true` | B: insufficient_sample=True |
| `test_get_my_tier_returns_tier_when_employee_in_tiers_json` | C: tier value 2 returned |
| `test_get_my_tier_accepts_uuid_object_and_stringifies_key` | str(UUID) normalization |
| `test_get_my_tier_returns_not_ranked_when_key_missing` | D-1: key absent from tiers_json |
| `test_get_my_tier_returns_not_ranked_when_value_is_none` | D-2: value None in tiers_json |
| `test_get_my_tier_falls_back_to_latest_year_when_current_missing` | E: fallback to older year |
| `test_get_my_tier_invariant_tier_implies_reason_none` | invariant: tier→reason=None |

All imports (`datetime`, `UUID`, `MyTierResponse`) added at file top level, not inline per MINOR #4 constraint. All test functions use `db_session` fixture name (not `db`) per conftest convention.

---

## Verification Results

- All 8 new pytest cases PASS
- All 29 total tests in test_performance_service.py PASS (21 existing + 8 new)
- `python -c "from backend.app.schemas.performance import MyTierResponse; from backend.app.services.performance_service import PerformanceService; print('imports OK')"` — OK
- No forbidden fields in MyTierResponse (display_label/percentile/rank/as_of)
- Fixture name check: `grep -cE "def test_get_my_tier.*\(db," = 0`, `grep -cE "def test_get_my_tier.*\(db_session" = 8`

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Known Stubs

None - all implemented functionality is wired to real data sources.

---

## Threat Surface Scan

No new network endpoints added in this plan (API handler deferred to Plan 02). No new trust boundary surfaces introduced. MyTierResponse schema physically cannot expose other employees' IDs, rankings, or percentile data (threat T-35-01-01 mitigated by 4-field schema constraint, verified by acceptance criteria grep check).

## Self-Check: PASSED

Files exist:
- `backend/app/schemas/performance.py` contains `class MyTierResponse(BaseModel)` — FOUND
- `backend/app/services/performance_service.py` contains `def get_my_tier` — FOUND
- `backend/tests/test_services/test_performance_service.py` contains 8 `test_get_my_tier_*` functions — FOUND

Commits exist:
- `09ba890` feat(35-01): add MyTierResponse Pydantic schema — FOUND
- `371de46` feat(35-01): add PerformanceService.get_my_tier method — FOUND
- `ce0ae86` test(35-01): add 8 pytest cases for PerformanceService.get_my_tier — FOUND
