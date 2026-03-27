---
phase: 03-approval-workflow-correctness
plan: 02
subsystem: approval-workflow
tags: [tdd, green, approval, audit-log, generation, pessimistic-lock]
dependency_graph:
  requires: [03-01]
  provides: [APPR-01-green, APPR-02-green, APPR-03-green, APPR-04-green]
  affects: [03-03]
tech_stack:
  added: []
  patterns: [with_for_update, generation-column, same-transaction-audit-log, batch_alter_table]
key_files:
  created:
    - alembic/versions/0d80f22f388f_add_generation_to_approval_records.py
  modified:
    - backend/app/models/approval.py
    - backend/app/services/approval_service.py
    - backend/app/services/salary_service.py
decisions:
  - "Actual UniqueConstraint name in DB is uq_approval_records_recommendation_id (not the auto-generated name assumed in plan spec) — drop_constraint uses this name"
  - "submit_for_approval resubmit path: new_generation = current_generation + 1 only when any record in current generation has decision != pending; route updates on un-decided submissions stay at same generation"
  - "decide_approval status computation uses all approval_records (all generations) for rejected/deferred/approved detection — only current-gen records are actionable but all decisions are visible for status rollup"
metrics:
  duration: 27min
  completed_date: 2026-03-27
  tasks_completed: 3
  files_modified: 4
---

# Phase 03 Plan 02: Approval Workflow Backend Fixes Summary

**One-liner:** Pessimistic lock, generation-based history preservation, and same-transaction AuditLog writes for approval and salary changes — turning 5 RED stubs GREEN.

---

## What Was Built

### Task 1: Alembic migration + ApprovalRecord model update

- New migration `0d80f22f388f` adds `generation INTEGER NOT NULL DEFAULT 0` to `approval_records`
- Drops old 2-column constraint `uq_approval_records_recommendation_id`
- Creates new 3-column constraint `uq_approval_records_recommendation_step_generation`
- `ApprovalRecord` model updated with `generation: Mapped[int]` field

### Task 2: ApprovalService fixes (APPR-01, APPR-02, APPR-03)

- `decide_approval` now fetches with `.with_for_update()` (SQLite ignores it; PostgreSQL activates the lock)
- `submit_for_approval` rewritten to be generation-aware: resubmit after rejection inserts new records at `max_generation + 1`, leaving old decided records untouched
- `decide_approval` writes `AuditLog(action='approval_decided')` in the same transaction before `db.commit()`
- `_is_current_step` updated to filter by current generation only
- `list_history` updated to order by `generation asc, step_order asc`

### Task 3: SalaryService audit log (APPR-04)

- `update_recommendation` captures `old_ratio` and `old_status` before mutation
- Writes `AuditLog(action='salary_updated', target_type='salary_recommendation')` in same transaction
- `operator_id=None` — salary service has no auth context

---

## Test Results

```
6 passed in 35.20s

PASS test_concurrent_decide_rejected         (APPR-01 — guard fires on double-decide)
PASS test_audit_log_written_on_decide        (APPR-03 — AuditLog row written on approve)
PASS test_audit_log_written_on_reject        (APPR-03 — AuditLog detail has decision+operator_role)
PASS test_audit_log_written_on_salary_change (APPR-04 — AuditLog row written on salary update)
PASS test_resubmit_preserves_history         (APPR-02 — history len > 2 after reject+resubmit)
PASS test_hrbp_cross_department_queue        (APPR-06 — HRBP sees items with include_all)

Still FAILING (Plan 03 scope):
  test_manager_queue_has_dimension_scores    (APPR-05 — dimension_scores not yet in schema)
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Actual UniqueConstraint name differs from plan spec**
- **Found during:** Task 1 — inspecting live SQLite DB before writing migration
- **Issue:** Plan spec assumed constraint name `uq_approval_records_recommendation_id_step_name`; actual name in DB is `uq_approval_records_recommendation_id`
- **Fix:** Used the actual name in `drop_constraint` call
- **Files modified:** `alembic/versions/0d80f22f388f_add_generation_to_approval_records.py`
- **Commit:** e662fe3

**2. [Rule 1 - Bug] decide_approval status rollup uses all generations**
- **Found during:** Task 2 — reading the existing status computation logic
- **Issue:** After resubmit, `recommendation.approval_records` contains records from all generations. The status rollup (`any rejected → rejected`, `all approved → approved`) must consider all records to correctly reflect the current state after a partial approval in the new generation.
- **Fix:** Left the existing `decisions = [record.decision for record in recommendation.approval_records]` logic unchanged — it correctly reflects the full picture. Only `_is_current_step` and `list_history` needed generation filtering.
- **Files modified:** `backend/app/services/approval_service.py`
- **Commit:** 63bbf58

---

## Known Stubs

None — all application code changes are fully wired. `test_manager_queue_has_dimension_scores` remains RED because `dimension_scores` in the approval queue response schema is Plan 03 scope.

---

## Self-Check: PASSED

Files verified:
- `alembic/versions/0d80f22f388f_add_generation_to_approval_records.py` — FOUND
- `backend/app/models/approval.py` — FOUND
- `backend/app/services/approval_service.py` — FOUND
- `backend/app/services/salary_service.py` — FOUND

Commits verified:
- `e662fe3` — feat(03-02): add generation column to approval_records and update UniqueConstraint
- `63bbf58` — feat(03-02): fix ApprovalService — pessimistic lock, history preservation, audit log writes
- `ae395fa` — feat(03-02): wire AuditLog in SalaryService.update_recommendation (APPR-04)
