---
phase: 1
slug: security-hardening-and-schema-integrity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | `backend/tests/` (existing) |
| **Quick run command** | `pytest backend/tests/test_core/ backend/tests/test_security/ -x -q` |
| **Full suite command** | `pytest backend/tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_core/ backend/tests/test_security/ -x -q`
- **After every plan wave:** Run `pytest backend/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | DB-01/DB-02 | migration | `alembic upgrade head && alembic check` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | SEC-01 | unit | `pytest backend/tests/test_core/test_startup_guard.py -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | SEC-06 | manual | `git status .env` / `git ls-files .env` | ✅ | ⬜ pending |
| 1-02-01 | 02 | 1 | SEC-03 | unit | `pytest backend/tests/test_security/test_encryption.py -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | SEC-08 | unit | `pytest backend/tests/test_security/test_password.py -q` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | SEC-07 | unit | `pytest backend/tests/test_security/test_storage.py -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | SEC-02 | integration | `pytest backend/tests/test_api/test_rate_limit.py -q` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | SEC-05 | integration | `pytest backend/tests/test_api/test_public_rate_limit.py -q` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | SEC-04 | unit | `pytest backend/tests/test_api/test_salary_roles.py -q` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 3 | DB-03 | unit | `pytest backend/tests/test_services/test_import_idempotency.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_core/test_startup_guard.py` — stubs for SEC-01 startup validation
- [ ] `backend/tests/test_security/test_encryption.py` — stubs for SEC-03 AES-GCM TypeDecorator
- [ ] `backend/tests/test_security/test_password.py` — stubs for SEC-08 complexity validator
- [ ] `backend/tests/test_security/test_storage.py` — stubs for SEC-07 path traversal
- [ ] `backend/tests/test_api/test_rate_limit.py` — stubs for SEC-02 login rate limiting
- [ ] `backend/tests/test_api/test_public_rate_limit.py` — stubs for SEC-05 public API rate limiting
- [ ] `backend/tests/test_api/test_salary_roles.py` — stubs for SEC-04 role-aware responses
- [ ] `backend/tests/test_services/test_import_idempotency.py` — stubs for DB-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `.env` removed from git tracking | SEC-06 | Git index state cannot be automated tested | Run `git ls-files .env` — must return empty |
| App refuses to start with "change_me" JWT secret in production | SEC-01 | Requires env override | Set `ENVIRONMENT=production JWT_SECRET_KEY=change_me`, run server, verify error message |
| Alembic baseline runs clean on PostgreSQL | DB-01/DB-02 | Requires PostgreSQL instance | Run `alembic upgrade head` on a fresh PostgreSQL DB |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
