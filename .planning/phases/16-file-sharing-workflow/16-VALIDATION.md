---
phase: 16
slug: file-sharing-workflow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 + TypeScript tsc |
| **Config file** | backend/tests/ |
| **Quick run command** | `python3 -m pytest backend/tests/ -x -q` |
| **Full suite command** | `python3 -m pytest backend/tests/ -v && cd frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest backend/tests/ -x -q`
- **After every plan wave:** Run `python3 -m pytest backend/tests/ -v && cd frontend && npx tsc --noEmit`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | SHARE-01 | unit | `python3 -m pytest backend/tests/test_services/test_file_sharing.py -v` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | SHARE-02 | unit | `python3 -m pytest backend/tests/test_services/test_sharing_request.py -v` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | SHARE-03 | unit | `python3 -m pytest backend/tests/test_api/test_sharing_api.py -v` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 2 | SHARE-04 | unit | `python3 -m pytest backend/tests/test_services/test_sharing_approval.py -v` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 2 | SHARE-05 | unit | `python3 -m pytest backend/tests/test_services/test_sharing_timeout.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_services/test_file_sharing.py` — stubs for SHARE-01
- [ ] `backend/tests/test_services/test_sharing_request.py` — stubs for SHARE-02
- [ ] `backend/tests/test_api/test_sharing_api.py` — stubs for SHARE-03
- [ ] `backend/tests/test_services/test_sharing_approval.py` — stubs for SHARE-04
- [ ] `backend/tests/test_services/test_sharing_timeout.py` — stubs for SHARE-05

*Existing infrastructure covers test framework — only test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Modal弹窗交互体验 | SHARE-01 | Browser visual interaction | Upload duplicate file, verify modal appears with correct info |
| 共享申请页面导航 | SHARE-03 | Sidebar integration visual | Check sidebar shows "共享申请" menu, page loads correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
