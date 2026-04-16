---
phase: 20-employee-company
plan: 02
subsystem: ui
tags: [react, typescript, employee, ui]
requires:
  - phase: 20-01
    provides: Employee CRUD and detail payloads now include optional company values
provides:
  - Frontend employee API types aligned with the shared company contract
  - EmployeeArchiveManager create and edit form support for optional company values
  - Evaluation detail profile cards show company while list/admin summary views stay company-free
affects:
  - employee detail ui
  - employee archive manager
  - employee list visibility guardrails
tech-stack:
  added: []
  patterns:
    - Shared employee payload fields are added once in frontend types and then consumed selectively by each UI surface
    - Employee company remains a detail-only render concern even though it exists on the shared contract
key-files:
  created: []
  modified:
    - frontend/src/types/api.ts
    - frontend/src/components/employee/EmployeeArchiveManager.tsx
    - frontend/src/pages/EvaluationDetail.tsx
key-decisions:
  - "Kept company on the shared frontend employee contract and enforced EMP-02 strictly at render boundaries instead of splitting list/detail types."
  - "Retained the pre-existing EvaluationDetail module-helper tooltip edit and added company within the existing top profile-card grid."
patterns-established:
  - "Optional employee profile fields should flow through EmployeeCreatePayload, EmployeeUpdatePayload, and EmployeeRecord together to avoid frontend contract drift."
  - "When a shared employee field is detail-only, the list/admin summary surfaces must stay unchanged and be protected by lint/grep guardrails."
requirements-completed: [EMP-01, EMP-02]
duration: 3 min
completed: 2026-04-09
---

# Phase 20 Plan 02: Employee Company Frontend Summary

**Frontend employee types, admin form wiring, and detail-page profile cards now carry optional company values without exposing them on list or archive summary surfaces.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-09T04:11:08Z
- **Completed:** 2026-04-09T04:13:47Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `company` to the shared frontend employee record, create payload, and update payload contracts.
- Extended `EmployeeArchiveManager` so admins can create, edit, and clear `company` from the existing employee form.
- Added a detail-only `所属公司` profile card on `/employees/:employeeId` while keeping `/employees` and the admin archive list company-free.

## Task Commits

Each task was committed atomically:

1. **Task 1: 对齐 frontend employee types，并在 EmployeeArchiveManager 表单中增加 company 字段** - `6659c0e` (feat)
2. **Task 2: 在员工详情页展示 company，并保留列表页 non-display 边界** - `b083a6d` (feat)

**Plan metadata:** Deferred to the orchestrator because this executor was explicitly instructed not to update `.planning/STATE.md` or `.planning/ROADMAP.md`.

## Files Created/Modified

- `frontend/src/types/api.ts` - adds `company` to the shared employee frontend contracts.
- `frontend/src/components/employee/EmployeeArchiveManager.tsx` - wires `company` into the admin create/edit form state and input controls without changing archive summary cards.
- `frontend/src/pages/EvaluationDetail.tsx` - shows `employee.company ?? '未设置'` in the existing top profile-card grid and keeps the current-cycle control in that same area.
- `.planning/phases/20-employee-company/20-02-SUMMARY.md` - records plan outcomes, commits, and verification.

## Decisions Made

- Reused the existing shared employee contract for all company-aware frontend flows so the backend payload from Plan 20-01 propagates without local type drift.
- Preserved the existing uncommitted module-helper tooltip change in `EvaluationDetail.tsx` while adding the company card, rather than reverting or rewriting that local UI change.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- A transient `.git/index.lock` conflict appeared when staging Task 1 files in parallel; restaging serially resolved it without affecting the task diff or commits.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Frontend and backend employee contracts are aligned for optional `company` values.
- Employee detail views now satisfy the detail-only display requirement while list/admin summary surfaces remain unchanged.

## Self-Check: PASSED

- Found summary file: `.planning/phases/20-employee-company/20-02-SUMMARY.md`
- Found task commits: `6659c0e`, `b083a6d`
