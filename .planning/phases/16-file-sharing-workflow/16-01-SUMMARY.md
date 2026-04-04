---
phase: 16-file-sharing-workflow
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, file-upload, sharing, dedup, pytest]

# Dependency graph
requires:
  - phase: 05-phase05
    provides: ProjectContributor model, content_hash column, owner_contribution_pct
  - phase: c14-eligibility
    provides: Alembic head revision for migration chain
provides:
  - SharingRequest ORM model with per-file-pair UniqueConstraint
  - Hash-only duplicate detection with deterministic oldest-first ordering (D-01)
  - SharingService with create/approve/reject/list/pending-count + 72h lazy expiry
  - check-duplicate API with submission_id target-employee context
  - Atomic upload+SharingRequest creation in single transaction
  - API auth tests covering 401, 403, context resolution, atomicity
affects: [16-02-frontend-sharing, file-upload-ux, contribution-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy expiry on every query — no background task needed for 72h timeout"
    - "Atomic multi-service transaction (FileService + SharingService in same db.commit)"
    - "ID-list subquery pattern to avoid SQLAlchemy evaluator timezone errors"

key-files:
  created:
    - backend/app/models/sharing_request.py
    - backend/app/schemas/sharing.py
    - backend/app/services/sharing_service.py
    - backend/app/api/v1/sharing.py
    - alembic/versions/d16_add_sharing_requests.py
    - backend/tests/test_submission/test_sharing_request.py
    - backend/tests/test_api/test_sharing_api.py
  modified:
    - backend/app/services/file_service.py
    - backend/app/api/v1/files.py
    - backend/app/api/v1/router.py
    - backend/tests/test_submission/test_file_dedup.py

key-decisions:
  - "Refactored _check_duplicate to hash-only (no filename) per D-01 — all 4 call sites updated"
  - "Added .order_by(created_at.asc()) to dedup query for deterministic oldest-first selection (review #5)"
  - "check_duplicate_for_sharing uses submission_id to resolve target employee (review #4 — supports HR/admin uploads)"
  - "skip_duplicate_check parameter on FileService.upload_files/upload_file enables atomic upload path"
  - "No public POST /sharing-requests endpoint — only created atomically via upload with allow_duplicate=true (review #3 — eliminates forged-request risk)"
  - "Lazy expiry called by BOTH list_requests AND get_pending_count (review #6)"
  - "D-15 enforcement via app-level query (content_hash + original_submission_id + status IN pending/approved/rejected); expired excluded per D-19"
  - "ID-list subquery for stale update avoids SQLAlchemy in-memory evaluator timezone-comparison bug"

patterns-established:
  - "Lazy expiry pattern: run expiry logic inside every read call instead of background worker"
  - "Atomic cross-service transaction: services share db session, single commit at the end"

requirements-completed: [SHARE-01, SHARE-02, SHARE-03, SHARE-04, SHARE-05]

# Metrics
duration: 8min
completed: 2026-04-04
---

# Phase 16 Plan 01: File Sharing Workflow Backend Summary

**SharingRequest model + hash-only dedup refactor + atomic upload+request creation + 72h lazy expiry — all HIGH review concerns resolved.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-04T19:53:20Z
- **Completed:** 2026-04-04T20:01:00Z
- **Tasks:** 2
- **Files modified:** 11 (7 created, 4 modified)
- **Tests:** 29 total (17 unit + 12 API)

## Accomplishments

- **SharingRequest model** with all D-09 fields and UniqueConstraint on (requester_file_id, original_file_id)
- **Hash-only dedup** (D-01) — removed file_name from _check_duplicate signature; deterministic oldest-first selection
- **SharingService** with full lifecycle: create, approve, reject, list, pending-count; 72h lazy expiry run on every read
- **check-duplicate API** with submission_id target-employee context (review #4)
- **Atomic upload+share endpoint** — POST /submissions/{id}/files?allow_duplicate=true&original_file_id=xxx creates file AND SharingRequest in same transaction (review #2)
- **No public create endpoint** — eliminates forged-request attack (review #3)
- **Alembic migration** d16_sharing_requests (chained after c14_add_eligibility_overrides)
- **29 tests all passing** — 17 service-level + 12 API-level covering 401/403/atomicity

## Task Commits

1. **Task 1: SharingRequest model + migration + refactor _check_duplicate + SharingService + schemas + unit tests** — `386c98c` (feat)
2. **Task 2: Sharing API endpoints + check-duplicate + atomic upload + router + API auth tests** — `f13be6c` (feat)

## Files Created/Modified

### Created
- `backend/app/models/sharing_request.py` — SharingRequest ORM model
- `backend/app/schemas/sharing.py` — CheckDuplicate*, SharingRequest* Pydantic schemas
- `backend/app/services/sharing_service.py` — SharingService with lifecycle + lazy expiry
- `backend/app/api/v1/sharing.py` — sharing-requests endpoints (list, approve, reject, pending-count)
- `alembic/versions/d16_add_sharing_requests.py` — migration creating sharing_requests table
- `backend/tests/test_submission/test_sharing_request.py` — 10 service tests
- `backend/tests/test_api/test_sharing_api.py` — 12 API auth tests

### Modified
- `backend/app/services/file_service.py` — refactored `_check_duplicate` (hash-only, ordered), added `check_duplicate_for_sharing`, added `skip_duplicate_check` parameter
- `backend/app/api/v1/files.py` — added `/files/check-duplicate` endpoint, modified upload to support atomic sharing via query params
- `backend/app/api/v1/router.py` — registered sharing_router
- `backend/tests/test_submission/test_file_dedup.py` — updated for new hash-only signature, added oldest-first ordering test

## Decisions Made

- **Hash-only dedup (D-01):** Removed `file_name` from `_check_duplicate` signature entirely. All 4 call sites (upload_files, upload_file, import_github_file, replace_file) updated. Different filenames with same content are now detected as duplicates.
- **Deterministic selection (review #5):** Added `.order_by(UploadedFile.created_at.asc())` so "original" is always the oldest file with that hash.
- **Submission-based target context (review #4):** `check_duplicate_for_sharing` resolves target employee via `submission_id` parameter, not via `current_user`. Supports HR/admin uploading on behalf of employees.
- **Atomic upload+share (review #2):** Added `skip_duplicate_check` flag to `FileService` methods. The API handler calls both services and commits once, rolling back if the sharing request can't be created (D-15 conflict).
- **No public create endpoint (review #3):** `POST /sharing-requests` does NOT exist. Sharing requests can only be created via the upload endpoint with `allow_duplicate=true&original_file_id=X`. This prevents forged requests for files not yet uploaded.
- **Lazy expiry on both paths (review #6):** `_expire_stale_requests()` is called by BOTH `list_requests()` AND `get_pending_count()`. Also called in API endpoints that commit after service calls so expiry persists.
- **D-15 semantics:** Enforced at app-level via query on (content_hash + original_submission_id + status IN pending/approved/rejected). Expired excluded per D-19 — enables re-request after timeout.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] SQLAlchemy evaluator timezone comparison error**
- **Found during:** Task 1 (running test_list_requests_marks_stale_as_expired)
- **Issue:** `update().where(created_at < cutoff)` fails with "can't compare offset-naive and offset-aware datetimes" because SQLAlchemy's in-memory evaluator (used to sync session state) compares a naive datetime from the cached ORM object against the timezone-aware cutoff.
- **Fix:** Changed `_expire_stale_requests` to use an ID-list subquery: SELECT matching IDs first, then UPDATE by id IN (...). This avoids the in-memory evaluator entirely.
- **Files modified:** backend/app/services/sharing_service.py
- **Verification:** test_list_requests_marks_stale_as_expired + test_get_pending_count_runs_lazy_expiry both pass.
- **Committed in:** 386c98c (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** The fix was purely internal to `_expire_stale_requests` implementation. All external contracts unchanged. No scope creep.

## Issues Encountered

- **Python binary path:** `python` not on PATH in worktree shell; used `.venv/bin/python` directly. Not a code issue.

## User Setup Required

**Database migration required:**
```bash
alembic upgrade head
```
This applies `d16_sharing_requests` which creates the `sharing_requests` table.

## Next Phase Readiness

- Backend sharing workflow complete and tested
- Ready for Plan 16-02 (frontend sharing UI: warning banner, request list, approve modal)
- `frontend/src/services/` needs new `sharingService.ts` matching these endpoints
- Pending UI components: duplicate-warning dialog, incoming/outgoing request list, approval modal with ratio slider

---
*Phase: 16-file-sharing-workflow*
*Completed: 2026-04-04*

## Self-Check: PASSED

Verified:
- backend/app/models/sharing_request.py exists with `class SharingRequest` + UniqueConstraint — FOUND
- backend/app/schemas/sharing.py exists with all required classes — FOUND
- backend/app/services/sharing_service.py exists with _expire_stale_requests, get_pending_count, create_request — FOUND
- backend/app/api/v1/sharing.py exists with router, list, approve, reject, pending-count — FOUND
- alembic/versions/d16_add_sharing_requests.py exists with sharing_requests table — FOUND
- backend/tests/test_submission/test_sharing_request.py (10 tests) — FOUND, ALL PASS
- backend/tests/test_api/test_sharing_api.py (12 tests) — FOUND, ALL PASS
- Commit 386c98c — FOUND
- Commit f13be6c — FOUND
