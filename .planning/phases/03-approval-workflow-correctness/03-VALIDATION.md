---
phase: 3
slug: approval-workflow-correctness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest backend/tests/test_approval/ -q --tb=short` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short` |
| **Frontend lint** | `cd frontend && npm run lint` |
| **Estimated runtime** | ~30 seconds (unit), ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite + frontend lint
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 03-01 | APPR-01 | unit | `pytest backend/tests/test_approval/ -k test_pessimistic_lock -q` | ⬜ pending |
| 03-02 | APPR-02 | unit | `pytest backend/tests/test_approval/ -k test_resubmit_history -q` | ⬜ pending |
| 03-03 | APPR-03, APPR-04 | unit | `pytest backend/tests/test_approval/ -k test_audit_log -q` | ⬜ pending |
| 03-04 | APPR-05, APPR-06 | unit | `pytest backend/tests/test_approval/ -k test_queue -q` | ⬜ pending |
| 03-05 | APPR-07 | lint + manual | `cd frontend && npm run lint` | ⬜ pending |
| 03-06 | ALL | unit | `pytest backend/tests/test_approval/ -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_approval/` — test stubs for APPR-01 through APPR-07
- [ ] `backend/tests/test_approval/__init__.py` — package init
- [ ] Existing `backend/tests/conftest.py` covers DB fixtures (SQLite in-memory StaticPool from Phase 1/2)

*Existing infrastructure covers all phase requirements — no new framework installs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Manager queue shows dimension scores on same screen | APPR-05 | UI layout requires browser | Start app, log in as manager, open approval queue — confirm dimension score table is visible alongside pending evaluation |
| HR/HRBP can compare adjustment percentages side by side | APPR-06 | Multi-row UI comparison | Log in as HRBP, open approval list — confirm `final_adjustment_ratio` values are visible and comparable across rows |
| Rejection history visible on resubmission | APPR-02 | UI state verification | Reject an evaluation, have employee resubmit, open approval queue — confirm prior rejection reason/date visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
