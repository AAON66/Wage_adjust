---
phase: 22-ai
plan: "02"
title: "Async API Migration for Evaluations and Imports"
subsystem: api
tags: [async, celery, api-migration, evaluations, imports]
dependency_graph:
  requires: ["22-01"]
  provides: ["async-evaluation-trigger", "async-import-trigger"]
  affects: ["frontend-polling", "test-fixtures"]
tech_stack:
  added: []
  patterns: ["celery-delay-dispatch", "base64-file-serialization"]
key_files:
  created: []
  modified:
    - backend/app/api/v1/evaluations.py
    - backend/app/api/v1/imports.py
    - backend/tests/test_api/test_evaluation_api.py
    - backend/tests/test_api/test_import_207.py
decisions:
  - "Tests for evaluation/import behavior moved to service-layer helpers since endpoints are now async"
metrics:
  duration: "13m"
  completed: "2026-04-12"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 22 Plan 02: Async API Migration for Evaluations and Imports Summary

Migrated generate/regenerate evaluation and create_import_job endpoints from synchronous execution to Celery async dispatch, returning 202 + task_id for frontend polling.

## What Was Done

### Task 1: Migrate evaluations generate/regenerate to async

- Changed `POST /evaluations/generate` from 201 + EvaluationRead to 202 + TaskTriggerResponse
- Changed `POST /evaluations/regenerate` from 201 + EvaluationRead to 202 + TaskTriggerResponse
- Removed `settings` dependency injection (task obtains settings internally)
- Preserved synchronous `AccessScopeService.ensure_submission_access()` permission check
- All other endpoints (get, manual-review, hr-review, confirm) remain synchronous and unchanged
- Added new test `test_evaluation_api_generate_returns_202_async` for async contract
- Refactored existing evaluation tests to use `generate_evaluation_sync()` service helper

### Task 2: Migrate imports create_import_job to async

- Changed `POST /imports/jobs` from 201/207 + ImportJobRead to 202 + TaskTriggerResponse
- Added synchronous validation: import_type check + empty file check before Celery dispatch
- File content is base64-encoded and passed to `run_import_task.delay()`
- Removed `JSONResponse` import (no longer needed)
- Removed `db` dependency from create_import_job (no longer needed for this endpoint)
- All other import endpoints (list, get, delete, template, export) remain synchronous
- Rewrote import tests: async endpoint contract tests + service-layer behavior tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test suite failures due to async migration**
- **Found during:** Task 1 and Task 2
- **Issue:** Existing tests expected 201 status and full response bodies from generate/import endpoints
- **Fix:** Refactored tests to verify 202 + task_id for async endpoints; moved integration logic testing to service-layer helpers
- **Files modified:** backend/tests/test_api/test_evaluation_api.py, backend/tests/test_api/test_import_207.py
- **Commits:** fbb8d17, d45069a

**2. [Rule 1 - Bug] Error response format uses 'message' not 'detail'**
- **Found during:** Task 2
- **Issue:** Test assertions checked `response.json()['detail']` but the app's exception handler normalizes to `{'error': ..., 'message': ...}`
- **Fix:** Updated test assertions to use `response.json()['message']`
- **Files modified:** backend/tests/test_api/test_import_207.py
- **Commit:** d45069a

## Verification

- `python3 -c "from backend.app.api.v1.evaluations import router"` - no import errors
- `python3 -c "from backend.app.api.v1.imports import router"` - no import errors
- `python3 -m pytest backend/tests/test_api/test_evaluation_api.py` - 6 passed
- `python3 -m pytest backend/tests/test_api/test_import_207.py` - 10 passed
- 416 other tests pass; 7 pre-existing failures unrelated to this plan

## Self-Check: PASSED

- [x] backend/app/api/v1/evaluations.py exists and contains `generate_evaluation_task.delay(`
- [x] backend/app/api/v1/imports.py exists and contains `run_import_task.delay(`
- [x] Commit fbb8d17 exists (Task 1)
- [x] Commit d45069a exists (Task 2)
