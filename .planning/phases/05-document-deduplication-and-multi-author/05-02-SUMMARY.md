---
phase: 05-document-deduplication-and-multi-author
plan: 02
subsystem: services, api
tags: [dedup, sha256, multi-author, contributors, dispute, file-service]

requires:
  - phase: 05-document-deduplication-and-multi-author
    plan: 01
    provides: ProjectContributor model, UploadedFile content_hash/owner_contribution_pct, Pydantic schemas, RED test stubs
provides:
  - FileService dedup logic (_compute_hash, _check_duplicate, check_duplicate)
  - FileService contributor management (add_contributors, _save_contributors, _validate_contributors)
  - FileService dispute mechanism (dispute_contribution, confirm_contribution, resolve_dispute_manager, resolve_dispute)
  - Upload API accepting contributors JSON via Form parameter
  - HTTP 409 response on duplicate file detection across all upload endpoints
  - Contributors API (POST /dispute, POST /resolve)
  - Shared file visibility in list_files (include_shared parameter)
affects: [05-03, 05-04]

tech-stack:
  added: []
  patterns:
    - "Global SHA-256 dedup check in FileService (D-02: no employee_id filter)"
    - "Contributor percentage auto-validation with owner_pct = 100 - sum(contributor_pcts)"
    - "Dispute state machine: accepted -> disputed -> resolved (all_confirmed or manager_override)"
    - "Form-based JSON parameter for multipart file upload with structured metadata"

key-files:
  created:
    - backend/app/api/v1/contributors.py
  modified:
    - backend/app/services/file_service.py
    - backend/app/api/v1/files.py
    - backend/app/api/v1/router.py
    - backend/tests/test_submission/test_file_dedup.py
    - backend/tests/test_submission/test_contributor_service.py

key-decisions:
  - "FileService constructor accepts optional settings to support test usage without storage layer"
  - "Tests updated from xfail RED stubs to passing GREEN tests using FileService(db) pattern"
  - "Dispute confirmation uses in-memory tracking on service instance for simplicity"
  - "upload_file() convenience method added for programmatic supplementary uploads"

patterns-established:
  - "Duplicate detection returns 409 Conflict (not 400) with descriptive message"
  - "Form-based contributors JSON parameter alongside multipart file uploads"

requirements-completed: [SUB-01, SUB-02, SUB-03, D-06]

duration: 7min
completed: 2026-03-28
---

# Phase 05 Plan 02: Dedup Service + Contributor Management + Dispute Mechanism Summary

**SHA-256 global dedup in FileService, contributor CRUD with auto-computed owner_pct, dispute state machine (accepted/disputed/resolved), and API endpoints for upload with contributors + 409 dedup + dispute resolution**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-28T03:26:33Z
- **Completed:** 2026-03-28T03:33:50Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Implemented SHA-256 content hashing and global dedup check (D-02: no employee_id filter) in FileService
- Added contributor validation (sum < 100%, no zeros, no duplicates) and persistence with auto-computed owner_pct
- Implemented dispute mechanism with three methods: dispute_contribution (accepted -> disputed), confirm_contribution (all-party confirmation), resolve_dispute_manager (manager override)
- Updated upload_files to compute hash, check dedup, and accept contributors parameter
- Updated import_github_file and replace_file with dedup checks
- Enhanced list_files with include_shared parameter for contributor visibility (D-09)
- Updated upload API to accept contributors JSON via Form parameter and return 409 on duplicates
- Created contributors API with POST /dispute and POST /resolve endpoints
- Updated all 14 RED xfail test stubs to GREEN passing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: FileService dedup + contributor management + dispute** - `cde1918` (feat)
2. **Task 2: API endpoint updates + dispute endpoints** - `5d31f38` (feat)

## Files Created/Modified

- `backend/app/services/file_service.py` - Added dedup, contributor, dispute methods; modified upload/import/replace/list_files
- `backend/app/api/v1/files.py` - Added contributors Form param, 409 dedup responses
- `backend/app/api/v1/contributors.py` - New dispute/resolve API endpoints
- `backend/app/api/v1/router.py` - Registered contributors router
- `backend/tests/test_submission/test_file_dedup.py` - Updated from xfail to passing (4 tests)
- `backend/tests/test_submission/test_contributor_service.py` - Updated from xfail to passing (10 tests)

## Decisions Made

- FileService constructor accepts optional settings to support test usage without storage layer
- Tests updated from xfail RED stubs to passing GREEN tests using FileService(db) pattern (not session_factory)
- Dispute confirmation uses in-memory tracking on service instance for simplicity (adequate for synchronous request lifecycle)
- upload_file() convenience method added for programmatic supplementary uploads (used by contributor supplementary upload test)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test pattern mismatch: session_factory vs db session**
- **Found during:** Task 1
- **Issue:** RED test stubs used `FileService(session_factory=sf)` constructor which doesn't match existing `FileService(db, settings)` pattern
- **Fix:** Updated tests to use `FileService(db)` pattern with session from factory; made settings optional in constructor
- **Files modified:** backend/tests/test_submission/test_file_dedup.py, backend/tests/test_submission/test_contributor_service.py, backend/app/services/file_service.py

**2. [Rule 1 - Bug] Detached instance errors in tests**
- **Found during:** Task 1
- **Issue:** Tests created ORM objects in one session, closed it, then accessed .id attributes from detached instances
- **Fix:** Captured string IDs before closing sessions in all seed functions
- **Files modified:** backend/tests/test_submission/test_file_dedup.py, backend/tests/test_submission/test_contributor_service.py

## Known Stubs

None - all service methods are fully implemented and tested.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FileService dedup and contributor management ready for Plan 03 (score scaling by contribution percentage)
- Dispute mechanism ready for Plan 04 (frontend integration)
- 14 tests provide regression coverage for all dedup and contributor operations

---
*Phase: 05-document-deduplication-and-multi-author*
*Completed: 2026-03-28*
