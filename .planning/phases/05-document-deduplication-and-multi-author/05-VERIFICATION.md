---
phase: 05-document-deduplication-and-multi-author
verified: 2026-03-28T04:15:00Z
status: human_needed
score: 7/7 must-haves verified
human_verification:
  - test: "Upload duplicate file and verify rejection message"
    expected: "409 response with Chinese message referencing existing record"
    why_human: "Requires running server and browser interaction to verify full UX flow"
  - test: "ContributorPicker renders correctly with employee dropdown and percentage inputs"
    expected: "Employee search works, percentage validation shows remaining owner share"
    why_human: "Visual component rendering and interaction behavior"
  - test: "Approval page shows ContributorTags for shared projects"
    expected: "Inline badges with owner distinction (filled vs outline) and file-name grouping"
    why_human: "Visual rendering and layout verification"
---

# Phase 5: Document Deduplication and Multi-Author Verification Report

**Phase Goal:** Employees cannot accidentally submit duplicate evidence, and collaborative projects correctly distribute evaluation credit across co-contributors
**Verified:** 2026-03-28T04:15:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Duplicate file upload (same file_name + SHA-256 content_hash) is rejected globally (D-02) | VERIFIED | `FileService._check_duplicate` queries without employee_id filter; `upload_files`, `import_github_file`, `replace_file` all call dedup; 4 passing tests in `test_file_dedup.py` |
| 2 | Contributors assignable during upload with auto-computed owner_pct = 100 - sum(contributor_pcts) | VERIFIED | `_validate_contributors` + `_save_contributors` in FileService; `upload_files` accepts `contributors` param; API accepts `contributors` Form field; 5 passing tests in `test_contributor_service.py` |
| 3 | Contributors can see shared projects in list_files | VERIFIED | `list_files(include_shared=True)` joins via ProjectContributor; test `test_contributor_sees_shared_file` passes |
| 4 | Shared project score scales by contribution percentage (80 x 60% = 48) | VERIFIED | `_load_evidence_for_evaluation` with three-source evidence pool; `_scale_evidence_item` with copy+make_transient; `compute_effective_score` static method; 5 passing tests in `test_score_scaling.py` |
| 5 | Supplementary materials merge into evaluation via ProjectContributor FK (D-10) | VERIFIED | Source C in `_load_evidence_for_evaluation` queries `supplementary_for_file_id` metadata at line 202 of evaluation_service.py |
| 6 | Approval records include all contributors with percentages (D-11) | VERIFIED | `ApprovalService.load_project_contributors` returns `ProjectContributorSummary` list; wired in `api/v1/approvals.py` at line 37/66; 2 passing tests in `test_approval_contributors.py` |
| 7 | Dispute mechanism supports accepted -> disputed -> resolved with all_confirmed and manager_override paths (D-06) | VERIFIED | `dispute_contribution`, `confirm_contribution`, `resolve_dispute_manager`, `resolve_dispute` methods in FileService; API endpoints POST /dispute and POST /resolve in contributors.py; 3 passing tests |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/project_contributor.py` | ProjectContributor model | VERIFIED | 43 lines, FKs to uploaded_files and employee_submissions, UniqueConstraint, CheckConstraint |
| `backend/app/models/uploaded_file.py` | content_hash + owner_contribution_pct | VERIFIED | content_hash String(64) indexed, owner_contribution_pct Float default 100.0, contributors relationship |
| `alembic/versions/005_phase05_content_hash_and_contributors.py` | Schema migration | VERIFIED | upgrade creates columns and table with batch_alter_table, proper revision chain |
| `backend/app/services/file_service.py` | Dedup + contributor + dispute logic | VERIFIED | _compute_hash, _check_duplicate (global), _validate_contributors, _save_contributors, dispute_contribution, confirm_contribution, resolve_dispute_manager, resolve_dispute |
| `backend/app/services/evaluation_service.py` | Score scaling + supplementary merge | VERIFIED | _load_evidence_for_evaluation (3 sources A/B/C + D-10), _scale_evidence_item, compute_effective_score |
| `backend/app/services/approval_service.py` | Contributors in approval records | VERIFIED | load_project_contributors returns ProjectContributorSummary list |
| `backend/app/api/v1/files.py` | Upload with contributors + 409 dedup | VERIFIED | contributors Form param, _is_duplicate_error helper, 409 responses on all 3 upload paths |
| `backend/app/api/v1/contributors.py` | Dispute/resolve endpoints | VERIFIED | POST /dispute + POST /resolve with proper error handling (404, 403, 409) |
| `frontend/src/components/evaluation/ContributorPicker.tsx` | Contributor picker component | VERIFIED | 242 lines, EmployeeSearchSelect dropdown, percentage input, owner share display, validation |
| `frontend/src/components/approval/ContributorTags.tsx` | Contributor tags display | VERIFIED | 48 lines, file-name grouping, owner visual distinction (filled vs outline badge) |
| `frontend/src/services/fileService.ts` | Upload with contributors + DuplicateFileException | VERIFIED | FormData with contributors JSON, 409 handling with DuplicateFileException class |
| `frontend/src/types/api.ts` | TypeScript type extensions | VERIFIED | ContributorInput, ProjectContributorSummary, DuplicateFileError interfaces; project_contributors on ApprovalRecord |
| `frontend/src/components/evaluation/FileUploadPanel.tsx` | Extended with contributor picker | VERIFIED | Props: contributors, onContributorsChange, showContributorPicker, duplicateError; renders ContributorPicker |
| `frontend/src/pages/Approvals.tsx` | ContributorTags in approval detail | VERIFIED | Imports ContributorTags, conditionally renders when project_contributors present |
| `backend/tests/test_submission/` | Test suite (21 tests) | VERIFIED | 21 passed, 0 failed, covers all SUB requirements + D-06 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `project_contributor.py` | `uploaded_file.py` | `ForeignKey('uploaded_files.id')` | WIRED | Line 27, with CASCADE delete |
| `project_contributor.py` | `submission.py` | `ForeignKey('employee_submissions.id')` | WIRED | Line 31, with CASCADE delete |
| `file_service.py` | `project_contributor.py` | ProjectContributor create/query | WIRED | Import at line 19, used in _save_contributors, dispute methods, list_files |
| `api/v1/files.py` | `file_service.py` | upload_files with contributors | WIRED | contributors param parsed from Form JSON, passed to service |
| `api/v1/contributors.py` | `file_service.py` | dispute_contribution + resolve_dispute | WIRED | Both endpoints call service methods with proper error mapping |
| `contributors.py` router | `router.py` | include_router | WIRED | Line 7+35 of router.py |
| `evaluation_service.py` | `project_contributor.py` | Query for score scaling | WIRED | Import at line 15, Source C query at line 163 |
| `approval_service.py` | `project_contributor.py` | Query for approval display | WIRED | Import at line 11, query in load_project_contributors |
| `api/v1/approvals.py` | `approval_service.py` | load_project_contributors call | WIRED | Line 37, result passed to serialization at line 66 |
| `FileUploadPanel.tsx` | `ContributorPicker.tsx` | Import + render | WIRED | Import at line 3, conditional render at line 62 |
| `Approvals.tsx` | `ContributorTags.tsx` | Import + render | WIRED | Import at line 6, conditional render at line 710 |
| `fileService.ts` | `types/api.ts` | ContributorInput + DuplicateFileError | WIRED | Import at line 4, used in upload and error handling |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `ContributorPicker.tsx` | `employees` | `fetchEmployees` API call | Yes (API -> DB query) | FLOWING |
| `ContributorTags.tsx` | `contributors` | Props from `Approvals.tsx` -> `project_contributors` on ApprovalRecord | Yes (API -> ApprovalService.load_project_contributors -> DB query) | FLOWING |
| `fileService.ts` | `uploadSubmissionFiles` | POST to `/api/v1/submissions/{id}/files` | Yes (API -> FileService.upload_files -> DB persist) | FLOWING |
| `evaluation_service.py` | `evidence_with_weights` | `_load_evidence_for_evaluation` -> DB queries on UploadedFile, ProjectContributor, EvidenceItem | Yes (real DB queries) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All phase 05 tests pass | `pytest backend/tests/test_submission/ -q` | 21 passed, 0 failed | PASS |
| TypeScript compiles without errors | `npx tsc --noEmit` | No output (clean) | PASS |
| No TODO/FIXME/placeholder in phase files | `grep -rn TODO/FIXME/PLACEHOLDER` | none found | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SUB-01 | 01, 02, 04 | File dedup by name + content hash, reject duplicate with existing record reference | SATISFIED | Global SHA-256 dedup in FileService, 409 API response, DuplicateFileException in frontend |
| SUB-02 | 01, 02, 04 | Multi-author with contribution percentages summing to 100% | SATISFIED | ContributorInput schema, _validate_contributors, _save_contributors, ContributorPicker UI |
| SUB-03 | 01, 02, 04 | Contributors see shared projects in their file list | SATISFIED | list_files(include_shared=True) with ProjectContributor join |
| SUB-04 | 01, 03 | Score scaled by contribution percentage (80 x 60% = 48) | SATISFIED | _load_evidence_for_evaluation three-source pool, _scale_evidence_item, compute_effective_score |
| SUB-05 | 01, 03, 04 | Approval shows all contributors with percentages | SATISFIED | ApprovalService.load_project_contributors, ContributorTags component, wired in Approvals.tsx |

No orphaned requirements found -- all 5 SUB requirements are claimed by plans and have implementation evidence.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `test_contributor_service.py` | multiple | `db.query(X).get(id)` legacy API | Info | SQLAlchemy 2.0 deprecation warnings; functional but should migrate to `db.get(X, id)` |
| `ContributorPicker.tsx` | 148 | `catch { }` empty catch block | Info | Silently swallows employee fetch errors; acceptable for optional picker |

No blockers or warnings found.

### Human Verification Required

### 1. Duplicate Upload UX Flow

**Test:** Upload a file to an employee submission, then upload the exact same file again (same name, same content)
**Expected:** Second upload returns 409 with Chinese message like "此文件已由 XXX 在 YYYY-MM-DD 提交" displayed in the UI
**Why human:** Requires running backend+frontend servers and real file upload interaction

### 2. Contributor Picker Interaction

**Test:** During file upload, click "添加协作者", search for an employee, enter contribution percentage, verify remaining share display
**Expected:** Employee search dropdown works, percentage input validates, "剩余比例（您的份额）: XX%" updates in real-time
**Why human:** Interactive component behavior and visual rendering

### 3. Approval Page Contributor Tags

**Test:** Navigate to approval detail for an evaluation with shared project files
**Expected:** "项目协作者" section visible with inline tags showing contributor names and percentages, owner distinguished with filled badge
**Why human:** Visual layout, styling, and conditional rendering in real browser

### Gaps Summary

No automated verification gaps found. All 7 observable truths are verified with substantive code, proper wiring, real data flow, and passing tests. Three items require human verification for visual/interactive behavior confirmation.

---

_Verified: 2026-03-28T04:15:00Z_
_Verifier: Claude (gsd-verifier)_
