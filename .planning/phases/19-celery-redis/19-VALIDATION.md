---
phase: 19
slug: celery-redis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | backend/tests/ (existing test structure) |
| **Quick run command** | `python -m pytest backend/tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest backend/tests/ -v --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest backend/tests/ -v --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | ASYNC-01 | — | N/A | unit | `python -m pytest backend/tests/test_celery_app.py -v` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | ASYNC-04 | — | N/A | integration | `python -m pytest backend/tests/test_api/test_health.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_celery_app.py` — stubs for ASYNC-01 (Celery app creation, task discovery)
- [ ] `backend/tests/test_api/test_health.py` — stubs for ASYNC-04 (health check endpoint)

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Worker process starts via CLI | ASYNC-01 | Requires running celery worker process | Run `celery -A backend.app.celery_app worker --loglevel=info` and verify startup logs |
| docker-compose services start | ASYNC-04 | Requires Docker runtime | Run `docker-compose up` and verify all services connect |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
