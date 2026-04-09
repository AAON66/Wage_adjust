---
phase: 20
slug: employee-company
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
updated: 2026-04-09
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + TypeScript `tsc --noEmit` via `npm run lint` |
| **Config file** | `backend/tests/` and `frontend/package.json` |
| **Quick run command** | `python3 -m pytest backend/tests/test_services/test_employee_service.py backend/tests/test_services/test_import_service.py backend/tests/test_services/test_import_xlsx.py backend/tests/test_api/test_employee_cycle_api.py backend/tests/test_api/test_import_api.py -q && npm --prefix frontend run lint` |
| **Full suite command** | `python3 -m pytest backend/tests/ -q && npm --prefix frontend run lint` |
| **Estimated runtime** | targeted feedback ~40s; full suite ~90s |

---

## Sampling Rate

- **After backend task commits:** Run the targeted employee/import pytest set within 40 seconds
- **After frontend task commits:** Run `npm --prefix frontend run lint` plus file-level grep checks for detail/list visibility
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Backend suite must be green and frontend lint must pass
- **Max feedback latency:** 40 seconds for targeted checks; 90 seconds for full phase validation

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | EMP-01 | T-20-01 | schema + service writes preserve trimmed nullable company without breaking employee CRUD | unit/api | `python3 -m pytest backend/tests/test_services/test_employee_service.py backend/tests/test_api/test_employee_cycle_api.py -q` | ✅ | pending |
| 20-01-02 | 01 | 1 | EMP-01 | T-20-02, T-20-03 | import writes, clears, and preserves company correctly across CSV/XLSX/template/API paths | unit/api | `python3 -m pytest backend/tests/test_services/test_import_service.py backend/tests/test_services/test_import_xlsx.py backend/tests/test_api/test_import_api.py -q` | ✅ | pending |
| 20-02-01 | 02 | 2 | EMP-01 | T-20-04 | admin form payload and shared frontend types carry company without TS drift | typecheck | `npm --prefix frontend run lint` | ✅ | pending |
| 20-02-02 | 02 | 2 | EMP-02 | T-20-05 | detail page renders company while employee list and archive list remain company-free | lint/grep | `npm --prefix frontend run lint && grep -n "employee.company" frontend/src/pages/EvaluationDetail.tsx && if grep -q "employee.company" frontend/src/pages/Employees.tsx; then exit 1; fi` | ✅ | pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/test_services/test_employee_service.py` — existing employee service coverage scaffold
- [x] `backend/tests/test_services/test_import_service.py` — existing CSV import coverage scaffold
- [x] `backend/tests/test_services/test_import_xlsx.py` — existing XLSX/template coverage scaffold
- [x] `backend/tests/test_api/test_employee_cycle_api.py` — existing employee API flow coverage scaffold
- [x] `backend/tests/test_api/test_import_api.py` — existing import API flow coverage scaffold
- [x] `frontend/package.json` lint script — existing TypeScript strict gate

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| employee detail card information hierarchy still reads cleanly after adding company | EMP-02 | repo has no UI snapshot/E2E coverage | open `/employees/:employeeId`, confirm `所属公司` appears in the top profile-card group and not in a new standalone section |
| employee archive right-side list remains free of company text | EMP-02 | no component-level DOM tests in repo | open `/employee-admin`, verify left form has company field while right archive cards still show only existing summary lines |

---

## Validation Sign-Off

- [x] All planned tasks have `<automated>` verify or an existing Wave 0 dependency
- [x] Sampling continuity maintained across backend and frontend changes
- [x] Wave 0 covers all referenced verification surfaces
- [x] No watch-mode flags
- [x] Feedback latency stays under 90s for full phase validation
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-09

