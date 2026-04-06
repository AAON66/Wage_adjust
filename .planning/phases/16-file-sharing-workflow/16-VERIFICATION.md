---
phase: 16-file-sharing-workflow
verified: 2026-04-05T13:30:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "Upload with allow_duplicate=true saves file AND creates SharingRequest in the SAME transaction"
    status: failed
    reason: "Missing db.commit() after SharingService.create_request() in allow_duplicate upload path. FileService.upload_files() commits internally (line 474), starting a new transaction. The subsequent create_request() flushes but never commits. Session close rolls back the sharing request."
    artifacts:
      - path: "backend/app/api/v1/files.py"
        issue: "Lines 148-154: after create_request() returns, no db.commit() before response. The sharing request is flushed but rolled back on session close."
    missing:
      - "Add db.commit() after the sharing_svc.create_request() call in the allow_duplicate branch (around line 154 of files.py)"
  - truth: "Two test files have assertion mismatches after error messages were changed to Chinese"
    status: failed
    reason: "test_sharing_request.py line 143 expects regex 'already exists' but actual message is Chinese '该文件已存在共享申请，无法重复发起。'. test_sharing_api.py atomicity test fails because sharing request is not persisted (see gap above)."
    artifacts:
      - path: "backend/tests/test_submission/test_sharing_request.py"
        issue: "Line 143: pytest.raises(ValueError, match='already exists') does not match Chinese error message"
      - path: "backend/tests/test_api/test_sharing_api.py"
        issue: "test_upload_with_allow_duplicate_creates_file_and_sharing_request_atomically fails: sr is None because sharing request not committed"
    missing:
      - "Update test_sharing_request.py line 143 regex to match Chinese error message (e.g., match='已存在共享申请')"
      - "Fix the db.commit() gap (first gap), then API atomicity test should pass"
human_verification: []
---

# Phase 16: File Sharing Workflow Verification Report

**Phase Goal:** Upload with duplicate file triggers warning but allows continuing, auto-creates sharing request, original uploader can approve/reject with adjustable contribution ratio
**Verified:** 2026-04-05T13:30:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User uploading a duplicate file sees a warning but can continue | VERIFIED | DuplicateWarningModal.tsx renders modal with "文件内容重复" title; EvaluationDetail.tsx and MyReview.tsx both implement FileQueueItem state machine with 7 states; computeFileSHA256 + checkDuplicate wired |
| 2 | System auto-creates sharing request on duplicate upload | FAILED | Code path exists in files.py lines 148-154 but missing db.commit() after create_request(). FileService.upload_files() commits at line 474 starting new transaction; sharing request flush is rolled back on session close |
| 3 | Original uploader can see, approve, or reject sharing requests | VERIFIED | SharingRequests.tsx page with incoming/outgoing tabs; approve_request() and reject_request() in SharingService with permission checks; API endpoints in sharing.py; revoke_approval() and revoke_rejection() added as extra features |
| 4 | Approval includes adjustable contribution ratio (1-99%) | VERIFIED | SharingRequestApproveRequest schema has Field(ge=1, le=99); SharingRequestCard.tsx renders inline ratio editor with number input; approve_request() creates ProjectContributor and updates owner_contribution_pct |
| 5 | Requests older than 72h auto-marked expired | VERIFIED | _expire_stale_requests() called by both list_requests() and get_pending_count(); uses ID-list subquery to avoid timezone evaluator bug; 7 dedup tests pass confirming hash-only matching |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/sharing_request.py` | SharingRequest ORM model | VERIFIED | 36 lines, UUIDPrimaryKeyMixin + CreatedAtMixin, UniqueConstraint on (requester_file_id, original_file_id), all D-09 fields |
| `backend/app/schemas/sharing.py` | Pydantic schemas | VERIFIED | CheckDuplicateRequest with submission_id, CheckDuplicateResponse, SharingRequestRead with cycle_archived, ApproveRequest with Field(ge=1, le=99) |
| `backend/app/services/sharing_service.py` | SharingService lifecycle | VERIFIED | 273 lines, create/approve/reject/revoke_approval/revoke_rejection/list/pending-count + lazy expiry + check_can_create_request pre-check |
| `backend/app/api/v1/sharing.py` | Sharing API router | VERIFIED | 162 lines, list/approve/reject/revoke/revoke-rejection/pending-count endpoints, _enrich_sharing_request with cycle_archived |
| `backend/app/services/file_service.py` | Refactored _check_duplicate | VERIFIED | hash-only (no file_name), .order_by(created_at.asc()), check_duplicate_for_sharing with submission_id, skip_duplicate_check parameter |
| `backend/app/api/v1/files.py` | check-duplicate + atomic upload | PARTIAL | check_file_duplicate endpoint correct; allow_duplicate path creates file+request but missing commit for sharing request |
| `alembic/versions/d16_add_sharing_requests.py` | Migration | VERIFIED | File exists, creates sharing_requests table |
| `frontend/src/utils/fileHash.ts` | SHA-256 hash utility | VERIFIED | 10 lines, crypto.subtle.digest with hex output |
| `frontend/src/services/sharingService.ts` | Sharing API client | VERIFIED | checkDuplicate, list, approve, reject, revoke, revoke-rejection, pending-count; no createSharingRequest (atomic) |
| `frontend/src/components/evaluation/DuplicateWarningModal.tsx` | Warning modal | VERIFIED | 152 lines, keyboard handlers, warning icon, monospace filename, "文件内容重复" title, "继续上传" button |
| `frontend/src/components/sharing/SharingRequestCard.tsx` | Table row component | VERIFIED | 250 lines, status pills, inline ratio editor, revoke/revoke-rejection with cycle-archived guard |
| `frontend/src/pages/SharingRequests.tsx` | Sharing requests page | VERIFIED | 181 lines, incoming/outgoing tabs, empty state, error handling, revoke handlers |
| `frontend/src/pages/EvaluationDetail.tsx` | Queue state machine | VERIFIED | FileQueueItem type with 7 states, computeFileSHA256 + checkDuplicate wired, DuplicateWarningModal rendered, uploadSubmissionFilesWithDuplicate used |
| `frontend/src/pages/MyReview.tsx` | Queue state machine (extra) | VERIFIED | Same FileQueueItem state machine integrated for personal evaluation center |
| `backend/tests/test_submission/test_sharing_request.py` | Service tests | PARTIAL | 1 of 10+ tests fails: regex mismatch on Chinese error message |
| `backend/tests/test_api/test_sharing_api.py` | API auth tests | PARTIAL | 1 of 12 tests fails: atomicity test (sharing request not committed) |
| `backend/tests/test_submission/test_file_dedup.py` | Dedup tests | VERIFIED | All 7 tests pass, hash-only matching confirmed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| files.py | file_service.py | check_duplicate_for_sharing | WIRED | Line 76 calls service.check_duplicate_for_sharing(payload.content_hash, payload.submission_id) |
| sharing.py | sharing_service.py | SharingService | WIRED | All endpoints instantiate SharingService(db) and call appropriate methods |
| sharing_service.py | sharing_request.py | ORM queries | WIRED | select/update/get on SharingRequest throughout |
| sharing_service.py | file_service.py | shared db session | WIRED | Both services use same db session passed from API layer |
| EvaluationDetail.tsx | fileHash.ts | computeFileSHA256 | WIRED | Line 33 import, called during queue processing at line 1127 |
| EvaluationDetail.tsx | sharingService.ts | checkDuplicate | WIRED | Line 32 import, called at line 1128 with submission.id |
| EvaluationDetail.tsx | DuplicateWarningModal.tsx | conditional render | WIRED | Line 2290-2297 renders modal when queue has currentDuplicate item |
| EvaluationDetail.tsx | upload API | allow_duplicate=true | WIRED | Line 1079 calls uploadSubmissionFilesWithDuplicate |
| App.tsx | SharingRequests.tsx | Route | WIRED | Line 445: Route path="/sharing-requests" |
| roleAccess.ts | /sharing-requests | Nav menu | WIRED | All 4 roles have "共享申请" menu item with href="/sharing-requests" |
| NavIcons.tsx | share icon | SVG | WIRED | Line 142: share key mapped to IconShare component |
| router.py | sharing.py | include_router | WIRED | Line 23 import, line 40 api_router.include_router(sharing_router) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| SharingRequests.tsx | requests | listSharingRequests() | API /sharing-requests with DB query | FLOWING |
| SharingRequestCard.tsx | request | props from SharingRequests | Passed from parent fetch | FLOWING |
| DuplicateWarningModal.tsx | uploaderName, uploadedAt | checkDuplicate() | API /files/check-duplicate with DB query | FLOWING |
| EvaluationDetail.tsx | fileQueue | computeFileSHA256 + checkDuplicate | Web Crypto + API | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend app starts | python -c "from backend.app.main import create_app; app = create_app()" | Imports succeed | PASS |
| TypeScript compiles | cd frontend && npx tsc --noEmit | Exit 0, no errors | PASS |
| Dedup tests pass | pytest test_file_dedup.py | 7/7 passed | PASS |
| Sharing service tests | pytest test_sharing_request.py | 1 FAILED (regex mismatch on Chinese msg) | FAIL |
| Sharing API tests | pytest test_sharing_api.py | 1 FAILED (atomicity: sharing request not committed) | FAIL |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| SHARE-01 | 16-01, 16-02 | Warning on duplicate upload, allow continue | SATISFIED | DuplicateWarningModal + hash check + queue state machine all verified |
| SHARE-02 | 16-01, 16-02 | Auto-create sharing request on duplicate upload | BLOCKED | Code path exists but missing db.commit() prevents persistence |
| SHARE-03 | 16-01, 16-02 | Original uploader can approve/reject | SATISFIED | SharingRequests page + approve/reject endpoints + permission checks |
| SHARE-04 | 16-01, 16-02 | Adjustable contribution ratio | SATISFIED | Field(ge=1, le=99) + inline ratio editor + owner_contribution_pct update |
| SHARE-05 | 16-01, 16-02 | 72h auto-expire | SATISFIED | Lazy expiry in both list_requests and get_pending_count |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/app/api/v1/files.py | 148-156 | Missing db.commit() after create_request() in allow_duplicate branch | BLOCKER | Sharing request flushed but rolled back on session close |
| backend/tests/test_submission/test_sharing_request.py | 143 | Regex 'already exists' does not match Chinese error message | WARNING | Test incorrectly fails; actual error message is correct Chinese text |

### Human Verification Required

No additional human verification items needed. The user has already human-verified the UI flows. The remaining gaps are code-level issues identifiable through automated testing.

### Gaps Summary

Two related gaps block full goal achievement:

1. **Missing db.commit() in atomic upload path (BLOCKER):** In `backend/app/api/v1/files.py`, the `allow_duplicate=true` branch calls `service.upload_files()` which commits internally, then calls `sharing_svc.create_request()` which only flushes. No `db.commit()` follows, so the sharing request is lost when the session closes. This breaks SHARE-02 (auto-create sharing request). Fix: add `db.commit()` after `create_request()` in the allow_duplicate branch, or restructure so the file upload commit happens after the sharing request is created.

2. **Test regex mismatch (WARNING):** Error message in `create_request()` was changed to Chinese during implementation but `test_sharing_request.py` line 143 still expects English `'already exists'`. Fix: update regex to `'已存在共享申请'`.

Both gaps share the same root cause area (the allow_duplicate code path in files.py). The commit fix will resolve the API atomicity test, and the regex fix will resolve the service test.

**Note on extra features:** The implementation exceeds plan scope with revoke approval, revoke rejection, cycle-archived guards, pre-check before upload, MyReview.tsx integration, Chinese error messages, and immediate file display. All extra features are properly wired and functional.

---

_Verified: 2026-04-05T13:30:00Z_
_Verifier: Claude (gsd-verifier)_
