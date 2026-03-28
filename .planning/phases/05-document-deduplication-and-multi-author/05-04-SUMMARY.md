---
phase: 05-document-deduplication-and-multi-author
plan: 04
subsystem: frontend
tags: [dedup-ux, contributor-picker, approval-tags, file-upload, frontend]

requires:
  - phase: 05-document-deduplication-and-multi-author
    plan: 02
    provides: Upload API with contributors FormData, 409 duplicate response
  - phase: 05-document-deduplication-and-multi-author
    plan: 03
    provides: project_contributors in approval records API response
provides:
  - ContributorPicker component for selecting collaborators with percentage allocation
  - ContributorTags component for displaying contributors in approval detail
  - DuplicateFileException class for typed 409 error handling
  - FileUploadPanel extended with contributor picker and duplicate error display
affects: []

tech-stack:
  added: []
  patterns:
    - "DuplicateFileException wraps 409 response into typed error with Chinese user message"
    - "ContributorPicker fetches employee list once and provides dropdown + percentage input per row"
    - "ContributorTags groups contributors by file_name and distinguishes owner with filled badge"

key-files:
  created:
    - frontend/src/components/evaluation/ContributorPicker.tsx
    - frontend/src/components/approval/ContributorTags.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/services/fileService.ts
    - frontend/src/components/evaluation/FileUploadPanel.tsx
    - frontend/src/pages/Approvals.tsx

key-decisions:
  - "ContributorPicker loads full employee list (page_size=200) for simplicity; adequate for typical org sizes"
  - "DuplicateFileException formats Chinese message with Intl.DateTimeFormat for consistent date display"
  - "ContributorTags uses file-name grouping to show which contributors are on which shared file"

patterns-established:
  - "Typed exception class (DuplicateFileException) for API error codes that need UI-specific handling"
  - "Conditional component rendering based on optional array field presence"

requirements-completed: [SUB-01, SUB-02, SUB-03, SUB-05]

duration: 4min
completed: 2026-03-28
---

# Phase 05 Plan 04: Frontend Dedup UX + Contributor Picker + Approval Tags Summary

**ContributorPicker for collaborator allocation during upload, DuplicateFileException for 409 dedup UX, and ContributorTags for approval detail contributor display with owner visual distinction**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T03:45:47Z
- **Completed:** 2026-03-28T03:50:00Z
- **Tasks:** 2 (of 3; Task 3 is human-verify checkpoint)
- **Files modified:** 6

## Accomplishments

- Added ContributorInput, ProjectContributorSummary, and DuplicateFileError interfaces to shared types
- Added project_contributors optional field to ApprovalRecord interface
- Updated uploadSubmissionFiles to accept optional contributors array, serialized as JSON in FormData
- Added 409 response handling with DuplicateFileException that formats Chinese error message
- Created ContributorPicker component: employee dropdown (fetched from API), percentage input, add/remove rows, real-time "your share" calculation, validation (max 99% total)
- Extended FileUploadPanel with new props: contributors, onContributorsChange, showContributorPicker, duplicateError
- Created ContributorTags component: file-name grouping, contribution percentage badges, owner vs contributor visual distinction (filled vs outline badge)
- Wired ContributorTags into Approvals page detail panel between dimension scores and action buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Types + fileService + ContributorPicker + FileUploadPanel** - `73403fd` (feat)
2. **Task 2: ContributorTags + Approvals page integration** - `af594c1` (feat)

## Files Created/Modified

- `frontend/src/types/api.ts` - Added ContributorInput, ProjectContributorSummary, DuplicateFileError; extended ApprovalRecord
- `frontend/src/services/fileService.ts` - Added contributors param to upload, DuplicateFileException class, 409 handling
- `frontend/src/components/evaluation/ContributorPicker.tsx` - New component for selecting collaborators with percentages
- `frontend/src/components/evaluation/FileUploadPanel.tsx` - Extended with contributor picker slot and duplicate error display
- `frontend/src/components/approval/ContributorTags.tsx` - New component for inline contributor tags with owner distinction
- `frontend/src/pages/Approvals.tsx` - Added ContributorTags in approval detail panel

## Decisions Made

- ContributorPicker loads full employee list (page_size=200) for simplicity; adequate for typical org sizes
- DuplicateFileException formats Chinese message with Intl.DateTimeFormat for consistent date display
- ContributorTags uses file-name grouping to show which contributors are on which shared file

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all components are fully functional with real data bindings. The ContributorPicker and duplicate error handling will be actively used once a page-level component wires the new FileUploadPanel props (showContributorPicker, onContributorsChange, duplicateError) to state management and the uploadSubmissionFiles call with contributors.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.
