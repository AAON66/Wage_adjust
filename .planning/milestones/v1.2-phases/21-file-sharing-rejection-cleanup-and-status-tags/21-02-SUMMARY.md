---
phase: 21-file-sharing-rejection-cleanup-and-status-tags
plan: 02
subsystem: ui
tags: [react, typescript, sharing, file-list, myreview]
requires:
  - phase: 21-01
    provides: sharing_status/sharing_status_label/sharing_cleanup_notices backend contract
provides:
  - Shared FileList pending badge for requester-owned pending sharing copies
  - MyReview cleanup feedback for reject/timeout auto-delete using existing toast surface
  - Removal of revoke-rejection client/UI wiring so rejected requests stay terminal in the frontend
affects:
  - submission file list ui
  - my review page
  - sharing requests page
tech-stack:
  added: []
  patterns:
    - Consume sharing cleanup semantics from the shared file-list payload instead of creating a parallel status system
    - Keep rejected-terminal behavior consistent across API client and sharing history UI by removing revoke-rejection affordances
key-files:
  created: []
  modified:
    - frontend/src/types/api.ts
    - frontend/src/components/evaluation/FileList.tsx
    - frontend/src/pages/MyReview.tsx
    - frontend/src/services/sharingService.ts
    - frontend/src/pages/SharingRequests.tsx
    - frontend/src/components/sharing/SharingRequestCard.tsx
key-decisions:
  - "Reused FileList as the only pending-sharing badge surface so MyReview and EvaluationDetail stay aligned without extra page logic."
  - "Mapped sharing_cleanup_notices to the existing MyReview toast surface and deduplicated by request/status/resolved_at to avoid repeated prompts."
patterns-established:
  - "Sharing badges live beside parse-status pills as separate UI state, never inside PARSE_STATUS_LABELS."
  - "When a sharing state becomes terminal by product rule, remove both the client API helper and every corresponding CTA from the UI."
requirements-completed: [SHARE-07, SHARE-08]
duration: 17 min
completed: 2026-04-09
---

# Phase 21 Plan 02: File Sharing Status UI Summary

**Shared FileList now renders `待同意`, MyReview explains auto-deleted sharing copies, and the frontend no longer exposes `撤销拒绝`.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-09T08:49:36Z
- **Completed:** 2026-04-09T09:06:44Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended the shared frontend file-list contract so `UploadedFileRecord` can carry sharing badge fields and submission-level `sharing_cleanup_notices`.
- Added a second `待同意` pill in `FileList`, leaving parse-status rendering untouched so MyReview and EvaluationDetail both inherit the same behavior.
- Wired MyReview to summarize reject/timeout cleanup notices through the existing toast surface and removed all revoke-rejection client/UI entry points.

## Task Commits

Each task was committed atomically:

1. **Task 1: 对齐 frontend file-list contract，并把 `待同意` 标签接到共享 FileList 行上** - `764442b` (feat)
2. **Task 2: 在 MyReview 复用现有反馈表面解释 reject / timeout auto-delete，不新增通知中心** - `fd736ba` (feat)

**Plan metadata:** Deferred to the orchestrator because this executor flow was instructed not to update `.planning/STATE.md` or `.planning/ROADMAP.md`.

## Files Created/Modified

- `frontend/src/types/api.ts` - adds `sharing_status`, `sharing_status_label`, and `sharing_cleanup_notices` to the shared file-list contract.
- `frontend/src/components/evaluation/FileList.tsx` - renders `待同意` as a second status pill while preserving existing parse-status labels.
- `frontend/src/pages/MyReview.tsx` - consumes cleanup notices, deduplicates them per submission, and shows requester-facing reject/timeout explanations through the existing toast UI.
- `frontend/src/services/sharingService.ts` - removes the revoke-rejection client helper so rejected requests cannot be restored from the frontend.
- `frontend/src/pages/SharingRequests.tsx` - drops revoke-rejection page wiring while preserving revoke-approval behavior.
- `frontend/src/components/sharing/SharingRequestCard.tsx` - removes the rejected-state CTA and confirm flow for `撤销拒绝`.

## Decisions Made

- Kept the badge logic entirely inside the shared `FileList` path so admin `EvaluationDetail` picked up `待同意` automatically, with no extra page-specific branching.
- Used notice deduplication in `MyReview` keyed by request/status/resolved timestamp so a refresh loop does not spam the same auto-delete toast repeatedly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The executor agent stalled after staging Task 2 even though the diff was complete and lint-ready. The orchestrator verified the staged changes, ran the planned frontend checks, and completed the final Task 2 commit plus summary without changing scope.

## Verification

- `npm --prefix frontend run lint` -> passed
- `grep -n "待同意" frontend/src/components/evaluation/FileList.tsx` -> matched
- `grep -n "sharing_status" frontend/src/types/api.ts` -> matched
- `grep -n "sharing_cleanup_notices" frontend/src/pages/MyReview.tsx` -> matched
- `grep -n "showToast" frontend/src/pages/MyReview.tsx` -> matched
- `if grep -q "revokeSharingRejection\\|撤销拒绝" frontend/src/services/sharingService.ts frontend/src/pages/SharingRequests.tsx frontend/src/components/sharing/SharingRequestCard.tsx; then exit 1; fi` -> passed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase verifier can now check the full SHARE-06/07/08 surface: backend cleanup semantics are present and the frontend is consuming the new file-list contract.
- Remaining validation is manual-only: verify `待同意` in MyReview/EvaluationDetail, confirm timeout delete feedback is understandable, and confirm `/sharing-requests` no longer shows `撤销拒绝`.

## Self-Check: PASSED

- Found summary file: `.planning/phases/21-file-sharing-rejection-cleanup-and-status-tags/21-02-SUMMARY.md`
- Found task commits: `764442b`, `fd736ba`
