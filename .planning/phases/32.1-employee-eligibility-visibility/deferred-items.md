# Phase 32.1 Deferred Items

Pre-existing issues discovered during execution that are out-of-scope for this plan.

## Pre-existing Test Failures

### test_eligibility_batch.py::TestCheckEmployeesBatch::test_filter_before_paginate_status_filter

- **Discovered:** 2026-04-22 during Phase 32.1-01 regression check
- **Symptom:** `AssertionError: Expected 3 ineligible employees, got total=2`
- **Confirmed pre-existing:** Failure reproduces on `1d029c6` (base commit) before any 32.1-01 changes (verified via `git stash` + repeat run)
- **Owner:** Phase 33+ (or dedicated bug-fix phase)
- **Why deferred:** Not introduced by Phase 32.1-01 (no changes to `check_employees_batch` or batch fixtures). Out of scope per execute-plan scope boundary rule.
