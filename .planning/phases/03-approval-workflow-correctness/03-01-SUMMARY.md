---
phase: 03-approval-workflow-correctness
plan: 01
subsystem: approval-workflow
tags: [tdd, test-stubs, approval, audit-log, red-baseline]
dependency_graph:
  requires: []
  provides: [APPR-01-red, APPR-02-red, APPR-03-red, APPR-04-red, APPR-05-red, APPR-06-green]
  affects: [03-02, 03-03]
tech_stack:
  added: []
  patterns: [pytest-service-isolation, file-sqlite-per-test, department-scope-binding]
key_files:
  created: []
  modified:
    - backend/tests/test_services/test_approval_service.py
    - backend/tests/test_api/test_approval_api.py
    - backend/tests/test_services/test_salary_service.py
decisions:
  - "Department scope binding required: list_approvals filters by can_access_employee, which checks department membership. Service-layer tests must bind the hrbp/manager user to the employee's department before calling list_approvals."
  - "test_hrbp_cross_department_queue passes immediately because hrbp1 is both in Engineering and the designated approver — this is acceptable per plan spec."
metrics:
  duration: 20min
  completed_date: 2026-03-26
  tasks_completed: 2
  files_modified: 3
---

# Phase 03 Plan 01: Approval Workflow Failing Test Stubs Summary

**One-liner:** Six named test stubs establishing RED baseline for approval workflow correctness — double-decide guard, history preservation, audit log writes, and dimension scores in queue response.

---

## What Was Built

Created the RED baseline for Phase 3 approval workflow correctness. Seven new test functions were added across three test files, establishing exactly the failing assertions that Plans 02 and 03 must turn green.

### Test Stubs Added

**backend/tests/test_services/test_approval_service.py** — 3 new functions:

| Function | Requirement | Expected Status |
|----------|-------------|-----------------|
| `test_concurrent_decide_rejected` | APPR-01 | PASSES immediately (existing guard) |
| `test_audit_log_written_on_decide` | APPR-03 | FAILS — AuditLog write not wired |
| `test_audit_log_written_on_reject` | APPR-03 | FAILS — AuditLog write not wired |

**backend/tests/test_api/test_approval_api.py** — 3 new functions:

| Function | Requirement | Expected Status |
|----------|-------------|-----------------|
| `test_resubmit_preserves_history` | APPR-02 | FAILS — history reset on resubmit |
| `test_manager_queue_has_dimension_scores` | APPR-05 | FAILS — schema missing `dimension_scores` |
| `test_hrbp_cross_department_queue` | APPR-06 | PASSES (hrbp is designated approver) |

**backend/tests/test_services/test_salary_service.py** — 1 new function:

| Function | Requirement | Expected Status |
|----------|-------------|-----------------|
| `test_audit_log_written_on_salary_change` | APPR-04 | FAILS — AuditLog write not wired |

---

## Decisions Made

1. **Department scope binding added to service tests:** `list_approvals` calls `AccessScopeService.can_access_employee`, which checks that the user's departments include the employee's department. The existing `seed_workflow_entities` helper creates an hrbp with no departments. Added `_bind_user_to_department` helper to new tests to bind the hrbp user to Engineering before calling `list_approvals`. This is required for the tests to reach the assertions under test rather than failing on setup.

2. **`test_hrbp_cross_department_queue` passes immediately:** The plan explicitly states "may PASS or FAIL — either outcome is acceptable as long as it runs without crash." The current `include_all=true` path for HRBP already returns items when the HRBP is the designated approver and shares the employee's department. This is acceptable green behavior.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `_bind_user_to_department` helper**
- **Found during:** Task 1 verification
- **Issue:** `seed_workflow_entities` creates hrbp with no department memberships. `list_approvals` calls `can_access_employee`, which for hrbp/manager roles checks `employee.department in user._department_names()`. Without binding, `list_approvals` returns empty list, making the test fail at setup rather than at the assertion under test.
- **Fix:** Added `_bind_user_to_department(session_factory, *, user_id, department_name)` helper in `test_approval_service.py` and called it in all three new service tests. Pattern mirrors `bind_user_departments` in the API test helper.
- **Files modified:** `backend/tests/test_services/test_approval_service.py`
- **Commit:** 634c5cc

---

## Test Run Summary

```
8 failed, 48 passed (service + approval API test files only)

Pre-existing failures (not caused by this plan):
  - test_submit_decide_and_list_workflow (pre-existing: same department issue in original helper)
  - test_dashboard_service_returns_overview_distribution_and_heatmap (pre-existing)
  - test_integration_service_returns_public_payload_sources (pre-existing)

New RED baseline from this plan:
  FAIL test_audit_log_written_on_decide         (AssertionError: len(logs) >= 1)
  FAIL test_audit_log_written_on_reject         (AssertionError: len(logs) >= 1)
  FAIL test_resubmit_preserves_history          (AssertionError: len(items) > 2)
  FAIL test_manager_queue_has_dimension_scores  (AssertionError: 'dimension_scores' in first_item)
  FAIL test_audit_log_written_on_salary_change  (AssertionError: len(logs) >= 1)

New passing stubs (guard already exists / behavior already correct):
  PASS test_concurrent_decide_rejected          (ValueError guard fires correctly)
  PASS test_hrbp_cross_department_queue         (HRBP sees their own items with include_all)
```

Zero regressions from previously passing tests.

---

## Known Stubs

None — this plan creates test stubs intentionally. The failing assertions are the point. There are no unintentional stubs in application code.

---

## Self-Check: PASSED

Files verified:
- `backend/tests/test_services/test_approval_service.py` — FOUND
- `backend/tests/test_api/test_approval_api.py` — FOUND
- `backend/tests/test_services/test_salary_service.py` — FOUND

Commits verified:
- `634c5cc` — test(03-01): add failing test stubs for APPR-01 and APPR-03
- `78b234f` — test(03-01): add failing integration and service test stubs for APPR-02, APPR-04, APPR-05, APPR-06
