---
phase: 05-document-deduplication-and-multi-author
plan: 03
subsystem: evaluation, approval, services
tags: [score-scaling, contribution-percentage, multi-author, evidence-merge, approval-contributors]

requires:
  - phase: 05-document-deduplication-and-multi-author
    provides: ProjectContributor model, UploadedFile content_hash/owner_contribution_pct, schemas
provides:
  - EvaluationService score scaling by contribution percentage (D-08)
  - Supplementary material merge into evaluation evidence pool (D-10)
  - ApprovalService project contributors display in approval records (D-11)
  - compute_effective_score static method for downstream consumers
affects: [05-04]

tech-stack:
  added: []
  patterns:
    - "In-memory evidence scaling via copy.copy + make_transient (no DB write for scaled items)"
    - "Three-source evidence pool: own-unshared, own-shared-owner, contributor-shared"
    - "ProjectContributorSummary populated at serialization time in API layer"

key-files:
  created: []
  modified:
    - backend/app/services/evaluation_service.py
    - backend/app/services/approval_service.py
    - backend/app/api/v1/approvals.py
    - backend/tests/test_submission/test_score_scaling.py
    - backend/tests/test_submission/test_approval_contributors.py

key-decisions:
  - "Evidence scaling uses in-memory copy with make_transient to avoid persisting scaled items to DB"
  - "Backward compatible: when no ProjectContributor records exist, all evidence passes at 100% weight"
  - "load_project_contributors is a public method on ApprovalService, called from API serialization layer"

patterns-established:
  - "copy.copy + make_transient pattern for creating detached ORM copies used only for computation"
  - "Service method returns Pydantic schemas directly (load_project_contributors -> list[ProjectContributorSummary])"

requirements-completed: [SUB-04, SUB-05]

duration: 15min
completed: 2026-03-28
---

# Phase 05 Plan 03: Score Scaling + Approval Contributors Summary

**Contribution-based score scaling (80 x 60% = 48) with supplementary material merge and project contributor display in approval records**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-28T03:26:42Z
- **Completed:** 2026-03-28T03:41:51Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Implemented `_load_evidence_for_evaluation` with three evidence sources: own files without contributors (100%), own files with contributors (owner_pct%), and shared projects as contributor (contribution_pct%)
- Implemented D-10 supplementary material merge: contributor supplementary evidence queried via `supplementary_for_file_id` metadata key and merged into same evidence pool at same contribution weight
- Added `_scale_evidence_item` using `copy.copy` + `make_transient` for in-memory scaling without DB persistence
- Added `compute_effective_score` static method implementing D-08 formula
- Modified `generate_evaluation` to use scaled evidence pool for AI evaluation engine
- Added `load_project_contributors` to ApprovalService returning `ProjectContributorSummary` list with owner and contributor entries
- Wired `project_contributors` into approval record serialization in the API layer

## Task Commits

Each task was committed atomically:

1. **Task 1: EvaluationService score scaling + supplementary merge** - `7cbf7df` (feat)
2. **Task 2: ApprovalService contributors in approval records** - `deb117e` (feat)

## Files Modified

- `backend/app/services/evaluation_service.py` - Added _load_evidence_for_evaluation, _scale_evidence_item, compute_effective_score; modified generate_evaluation
- `backend/app/services/approval_service.py` - Added load_project_contributors method with owner/contributor enumeration
- `backend/app/api/v1/approvals.py` - Wired project_contributors into serialize_approval_with_service
- `backend/tests/test_submission/test_score_scaling.py` - Replaced 3 xfail stubs with 5 GREEN tests (3 unit + 2 integration)
- `backend/tests/test_submission/test_approval_contributors.py` - Replaced 2 xfail stubs with 2 GREEN tests

## Decisions Made

- Evidence scaling uses in-memory copy with `make_transient` to avoid persisting scaled items to DB -- keeps the scoring layer pure computation
- Backward compatible: when no ProjectContributor records exist, all evidence passes at 100% weight (no behavioral change for non-shared projects)
- `load_project_contributors` is a public method on ApprovalService, called from the API serialization layer rather than embedded in the service layer's internal logic

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test stubs used incompatible API signatures**
- **Found during:** Task 1 and Task 2
- **Issue:** RED test stubs expected `EvaluationService(session_factory=sf)` and `ApprovalService(session_factory=sf)` with `db=db` keyword args, but actual services take `db: Session` as constructor parameter
- **Fix:** Rewrote tests to use actual service constructor API with proper session management and captured IDs before session close
- **Files modified:** backend/tests/test_submission/test_score_scaling.py, backend/tests/test_submission/test_approval_contributors.py
- **Commits:** 7cbf7df, deb117e

**2. [Rule 1 - Bug] AIEvaluation seed missing required explanation field**
- **Found during:** Task 2
- **Issue:** Test seed data omitted `explanation` field which has NOT NULL constraint
- **Fix:** Added explanation string to test AIEvaluation creation
- **Files modified:** backend/tests/test_submission/test_approval_contributors.py
- **Commit:** deb117e

## Known Stubs

None - all implemented functionality is fully wired with real data sources.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Score scaling and supplementary merge logic ready for Plan 04 (frontend display + E2E validation)
- Approval contributor display wired end-to-end from service to API response schema
- 14 remaining xfail test stubs in test_submission/ are for Plans 02 and 04

---
*Phase: 05-document-deduplication-and-multi-author*
*Completed: 2026-03-28*
