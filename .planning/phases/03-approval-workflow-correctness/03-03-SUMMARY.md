---
phase: 03-approval-workflow-correctness
plan: 03
subsystem: approval-workflow
tags: [schema, frontend, dimension-scores, approval-queue]
dependency_graph:
  requires: [03-02]
  provides: [APPR-05-green, APPR-06-green, APPR-07-green]
  affects: []
tech_stack:
  added: []
  patterns: [selectinload-chain, pydantic-from-attributes, tailwind-table]
key_files:
  created: []
  modified:
    - backend/app/schemas/approval.py
    - backend/app/services/approval_service.py
    - backend/app/api/v1/approvals.py
    - frontend/src/types/api.ts
    - frontend/src/pages/Approvals.tsx
decisions:
  - "DimensionScoreRead already existed in backend/app/schemas/evaluation.py — imported directly, not redefined"
  - "dimension_scores defaults to [] in ApprovalRecordRead so existing callers require no changes"
metrics:
  duration: 6min
  completed_date: 2026-03-27
  tasks_completed: 2
  files_modified: 5
---

# Phase 03 Plan 03: Dimension Scores in Approval Queue Summary

**One-liner:** Eager-load AIEvaluation.dimension_scores into the approval list response and render a 5-column breakdown table in the Approvals.tsx detail panel.

---

## What Was Built

### Task 1: Add dimension_scores to approval backend response (APPR-05, APPR-06)

- Imported `DimensionScoreRead` into `backend/app/schemas/approval.py`
- Added `dimension_scores: list[DimensionScoreRead] = []` to `ApprovalRecordRead`
- Extended `_approval_query()` selectinload chain with `AIEvaluation.dimension_scores`
- Imported `DimensionScoreRead` into `backend/app/api/v1/approvals.py`
- Populated `dimension_scores` in `serialize_approval_with_service` via `model_validate`

### Task 2: Add dimension score panel to Approvals.tsx (APPR-07)

- Added `dimension_scores: DimensionScoreRecord[]` to `ApprovalRecord` interface in `frontend/src/types/api.ts`
- Added "评估维度明细" section in the `selectedApproval` detail panel in `Approvals.tsx`
- Table columns: 维度代码 | 权重 | 原始得分 | 加权得分 | AI说明 (truncated at 60 chars)
- Empty state: "暂无维度评分数据" when `dimension_scores` is empty

---

## Test Results

```
15 passed, 1 pre-existing failure (out of scope)

PASS test_manager_queue_has_dimension_scores   (APPR-05)
PASS test_hrbp_cross_department_queue          (APPR-06)
PASS test_concurrent_decide_rejected           (APPR-01)
PASS test_audit_log_written_on_decide          (APPR-03)
PASS test_audit_log_written_on_reject          (APPR-03)
PASS test_resubmit_preserves_history           (APPR-02)
PASS test_audit_log_written_on_salary_change   (APPR-04)

PRE-EXISTING FAIL: test_submit_decide_and_list_workflow
  — HRBP user not bound to employee department in seed_workflow_entities
  — Confirmed failing before this plan's changes (git stash verified)
  — Logged to deferred-items.md
```

Frontend:
```
npm run lint  — 0 errors
npm run build — success (530 kB bundle, pre-existing chunk size warning)
```

---

## Deviations from Plan

None — plan executed exactly as written. `DimensionScoreRead` already existed in `evaluation.py` (Step 1 of Task 1 action was a no-op).

---

## Known Stubs

None — dimension_scores is fully wired from DB through schema to frontend render.

---

## Self-Check: PASSED

Files verified:
- `backend/app/schemas/approval.py` — FOUND
- `backend/app/services/approval_service.py` — FOUND
- `backend/app/api/v1/approvals.py` — FOUND
- `frontend/src/types/api.ts` — FOUND
- `frontend/src/pages/Approvals.tsx` — FOUND

Commits verified:
- `4bd260a` — feat(03-03): add dimension_scores to ApprovalRecordRead schema and approval query
- `6fd158c` — feat(03-03): add dimension score panel to Approvals.tsx (APPR-07)
