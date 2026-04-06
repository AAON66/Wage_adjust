---
plan: 16-02
phase: 16-file-sharing-workflow
status: complete
started: 2026-04-05
completed: 2026-04-06
---

# Plan 16-02 Summary: Frontend File Sharing Workflow

## What Was Built
- SHA-256 hash utility (`fileHash.ts`) using Web Crypto API
- `sharingService.ts`: checkDuplicate, list, approve, reject, revoke, revoke-rejection, pending-count
- `DuplicateWarningModal.tsx`: keyboard handlers, warning icon, monospace filename
- `SharingRequestCard.tsx`: status pills, inline ratio editor (1-99%), reject/revoke/revoke-rejection buttons, cycle-archived guard
- `SharingRequestsPage.tsx`: incoming/outgoing tabs, empty state
- `EvaluationDetail.tsx`: explicit FileQueueItem state machine (7 states), no recursion, graceful degradation
- `MyReview.tsx`: same queue state machine integrated for personal evaluation center
- `FileUploadPanel.tsx`: hashCheckStatus prop for checking/error states
- Navigation: sidebar "共享申请" menu item, `/sharing-requests` route

## Key Decisions
- Queue state machine: pending → checking → (currentDuplicate | clean) → (approvedToUpload | skipped) → completed/failed
- Atomic upload: `allow_duplicate=true&original_file_id=xxx` — no separate createSharingRequest call
- Pre-check before upload: `check_can_create_request()` prevents orphan files
- Upload completes and refreshes file list immediately; parse runs in background

## Deviations From Plan
1. **MyReview.tsx integration**: Plan only specified EvaluationDetail.tsx, but MyReview.tsx (个人评估中心) also has upload — integrated same flow
2. **Revoke approval feature**: Added per user request — original uploader can undo approved/rejected sharing requests
3. **Revoke rejection feature**: Added per user request — prevents accidental permanent rejection
4. **Cycle-archived guard**: Blocks revoke operations when evaluation cycle is archived
5. **Pre-check before upload**: Added `check_can_create_request()` to prevent file upload when sharing request would be blocked
6. **Chinese error messages**: All sharing-related errors in Chinese with alert dialog
7. **Immediate file display**: Upload releases UI immediately, parse runs in background

## Self-Check: PASSED

## key-files
### created
- frontend/src/utils/fileHash.ts
- frontend/src/services/sharingService.ts
- frontend/src/components/evaluation/DuplicateWarningModal.tsx
- frontend/src/components/sharing/SharingRequestCard.tsx
- frontend/src/pages/SharingRequests.tsx

### modified
- frontend/src/pages/EvaluationDetail.tsx
- frontend/src/pages/MyReview.tsx
- frontend/src/components/evaluation/FileUploadPanel.tsx
- frontend/src/types/api.ts
- frontend/src/App.tsx
- frontend/src/utils/roleAccess.ts
- frontend/src/components/icons/NavIcons.tsx
- frontend/src/services/fileService.ts
