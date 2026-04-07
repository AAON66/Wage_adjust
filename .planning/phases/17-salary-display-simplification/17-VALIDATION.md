---
phase: 17
slug: salary-display-simplification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 (backend) / tsc --noEmit (frontend) |
| **Config file** | `pytest.ini` (backend), `frontend/tsconfig.json` (frontend) |
| **Quick run command** | `cd frontend && npx tsc --noEmit` |
| **Full suite command** | `cd frontend && npx tsc --noEmit && cd .. && python -m pytest backend/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx tsc --noEmit`
- **After every plan wave:** Run `cd frontend && npx tsc --noEmit && cd .. && python -m pytest backend/tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | DISP-01 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 17-01-02 | 01 | 1 | DISP-02 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 17-01-03 | 01 | 1 | DISP-03 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Summary layer shows 3 indicator cards + featured ratio | DISP-01 | Visual layout verification | Load evaluation detail, verify salary module shows summary cards only |
| Expand/collapse toggles detail visibility | DISP-02 | Interactive behavior | Click "展开详情", verify detail sections appear; click "收起", verify they hide |
| Eligibility badge shows correct status color + inline rule expand | DISP-03 | Visual + interactive | Verify badge color matches eligibility status; click badge, verify 4 rules expand inline |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
