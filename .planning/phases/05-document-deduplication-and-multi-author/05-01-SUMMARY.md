---
phase: 05-document-deduplication-and-multi-author
plan: 01
subsystem: database, models, testing
tags: [sqlalchemy, alembic, pydantic, deduplication, multi-author, content-hash]

requires:
  - phase: 04-audit-log-wiring
    provides: Alembic migration chain (revision 9a7b6c5d4e3f)
provides:
  - ProjectContributor association model with FK to uploaded_files and employee_submissions
  - content_hash and owner_contribution_pct columns on UploadedFile
  - ContributorInput/ContributorRead/DuplicateFileError Pydantic schemas
  - ProjectContributorSummary schema on ApprovalRecordRead
  - Alembic migration 005 (revision a5b6c7d8e9f0)
  - 19 RED test stubs covering SUB-01 through SUB-05 and D-06 dispute mechanism
affects: [05-02, 05-03, 05-04]

tech-stack:
  added: []
  patterns:
    - "ProjectContributor association table pattern with contribution_pct and status lifecycle"
    - "Global content_hash dedup on UploadedFile (D-02 decision)"
    - "xfail test stubs as RED phase of TDD for all SUB requirements"

key-files:
  created:
    - backend/app/models/project_contributor.py
    - alembic/versions/005_phase05_content_hash_and_contributors.py
    - backend/tests/test_submission/__init__.py
    - backend/tests/test_submission/test_file_dedup.py
    - backend/tests/test_submission/test_contributor_service.py
    - backend/tests/test_submission/test_score_scaling.py
    - backend/tests/test_submission/test_approval_contributors.py
  modified:
    - backend/app/models/uploaded_file.py
    - backend/app/models/submission.py
    - backend/app/schemas/file.py
    - backend/app/schemas/approval.py

key-decisions:
  - "Global dedup scope (D-02): content_hash uniqueness checked across all employees, not per-employee"
  - "ContributorRead schema omits employee_name/employee_id to keep it model-aligned; enrichment deferred to service layer"

patterns-established:
  - "test_submission/ package for Phase 05 test organization"
  - "xfail(reason='RED: SUB-XX ...') convention for requirement-linked test stubs"

requirements-completed: [SUB-01, SUB-02, SUB-03, SUB-04, SUB-05]

duration: 5min
completed: 2026-03-28
---

# Phase 05 Plan 01: Data Foundation Summary

**ProjectContributor model, UploadedFile content_hash/owner_contribution_pct extension, Alembic migration, and 19 RED test stubs covering all SUB requirements and D-06 dispute mechanism**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-28T03:17:31Z
- **Completed:** 2026-03-28T03:22:59Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Created ProjectContributor association model with uploaded_file/submission FKs, contribution_pct, status lifecycle
- Extended UploadedFile with content_hash (SHA-256 index) and owner_contribution_pct columns
- Created Alembic migration 005 with batch_alter_table for SQLite compatibility
- Added ContributorInput, ContributorRead, DuplicateFileError, ProjectContributorSummary Pydantic schemas
- Created 19 xfail test stubs spanning all 5 SUB requirements plus D-06 dispute mechanism

## Task Commits

Each task was committed atomically:

1. **Task 1: Create models and migration** - `1406af8` (feat)
2. **Task 2: Create RED test stubs** - `6c6bf0e` (test)

## Files Created/Modified

- `backend/app/models/project_contributor.py` - ProjectContributor association table model
- `backend/app/models/uploaded_file.py` - Added content_hash, owner_contribution_pct, contributors relationship
- `backend/app/models/submission.py` - Added contributed_projects relationship
- `backend/app/schemas/file.py` - Added ContributorInput, ContributorRead, DuplicateFileError schemas
- `backend/app/schemas/approval.py` - Added ProjectContributorSummary and project_contributors to ApprovalRecordRead
- `alembic/versions/005_phase05_content_hash_and_contributors.py` - Migration adding columns and table
- `backend/tests/test_submission/test_file_dedup.py` - 4 SUB-01 dedup tests
- `backend/tests/test_submission/test_contributor_service.py` - 10 SUB-02/SUB-03/D-06 tests
- `backend/tests/test_submission/test_score_scaling.py` - 3 SUB-04 score scaling tests
- `backend/tests/test_submission/test_approval_contributors.py` - 2 SUB-05 approval display tests

## Decisions Made

- Global dedup scope per D-02: content_hash uniqueness checked across all employees, not per-employee (CONTEXT.md overrides RESEARCH.md recommendation)
- ContributorRead schema kept model-aligned without employee_name/employee_id; enrichment deferred to service layer in Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - this plan intentionally creates test stubs (xfail) as part of TDD RED phase. All 19 tests are designed to fail until Plans 02-04 implement the corresponding logic.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Models, schemas, and migration ready for Plan 02 (dedup service + contributor CRUD)
- All 19 test stubs provide clear acceptance criteria for Plans 02-04
- Pre-existing test failures (3) are unrelated to Phase 05 changes

---
*Phase: 05-document-deduplication-and-multi-author*
*Completed: 2026-03-28*
