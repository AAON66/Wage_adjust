---
phase: 22-ai
plan: 01
subsystem: async-tasks
tags: [celery, async, polling, evaluation, import]
dependency_graph:
  requires: [phase-19-celery-foundation]
  provides: [celery-evaluation-task, celery-import-task, task-polling-endpoint, task-status-schema]
  affects: [backend/app/celery_app.py, backend/app/services/import_service.py]
tech_stack:
  added: []
  patterns: [celery-bind-task, auto-retry-with-backoff, task-ownership-check]
key_files:
  created:
    - backend/app/schemas/task.py
    - backend/app/tasks/evaluation_tasks.py
    - backend/app/tasks/import_tasks.py
    - backend/app/api/v1/tasks.py
    - backend/tests/test_evaluation_tasks.py
    - backend/tests/test_import_tasks.py
    - backend/tests/test_tasks_api.py
  modified:
    - backend/app/celery_app.py
    - backend/app/api/v1/router.py
    - backend/app/services/import_service.py
    - backend/tests/test_celery_app.py
decisions:
  - "Task ownership enforced via user_id in meta + admin bypass (T-22-01 mitigation)"
  - "Coarse-grained progress for import tasks (before/after dispatch) -- fine-grained per-row callback deferred"
  - "File bytes passed to import task as base64 to keep Celery JSON serialization"
metrics:
  duration: 229s
  completed: 2026-04-12
---

# Phase 22 Plan 01: Celery Async Task Infrastructure Summary

Celery evaluation/import task modules with auto-retry, ownership-gated polling endpoint, and TaskStatusResponse schema for async job tracking.

## What Was Done

### Task 1: Core task modules, schema, and polling endpoint (80dea99)

- Created `TaskStatusResponse` and `TaskTriggerResponse` Pydantic schemas in `backend/app/schemas/task.py`
- Created `generate_evaluation_task` Celery task with `bind=True`, `max_retries=2`, `retry_backoff=True`, `soft_time_limit=300`
- Created `run_import_task` Celery task with progress reporting via `self.update_state(state='PROGRESS')`, `soft_time_limit=600`
- Created `GET /tasks/{task_id}` polling endpoint that maps Celery states (PENDING/STARTED/PROGRESS/SUCCESS/FAILURE) to normalized status values (pending/running/completed/failed)
- Implemented T-22-01 mitigation: task ownership check via `user_id` stored in task meta; admin role bypasses the check
- Registered both task modules in `celery_app.conf.include` and added tail imports
- Added `progress_callback: Callable[[int, int, int], None] | None` parameter to `ImportService.run_import()`

### Task 2: Unit tests for tasks and polling endpoint (3b33cfc)

- Extended `test_celery_app.py` with 4 new tests for task registration and include verification
- Created `test_evaluation_tasks.py` with 5 tests verifying task name, retries, time limits, backoff
- Created `test_import_tasks.py` with 5 tests verifying task name, retries, time limits, backoff
- Created `test_tasks_api.py` with 6 tests covering all Celery state-to-status mappings via mocked `AsyncResult`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed auth mock in test_tasks_api.py**
- **Found during:** Task 2
- **Issue:** Initial auth mock using `monkeypatch.setattr` did not properly override FastAPI dependency injection, causing 401 responses
- **Fix:** Used `app.dependency_overrides[get_current_user]` directly as the sole override mechanism
- **Files modified:** backend/tests/test_tasks_api.py
- **Commit:** 3b33cfc

## Verification

All verifications passed:
1. `celery_app.conf.include` contains 3 task modules (test_tasks, evaluation_tasks, import_tasks)
2. All 30 tests pass across 4 test files
3. Route `/tasks/{task_id}` registered in api_router

## Self-Check: PASSED
