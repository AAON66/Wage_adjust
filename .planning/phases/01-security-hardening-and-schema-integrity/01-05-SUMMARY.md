---
phase: 01-security-hardening-and-schema-integrity
plan: "05"
subsystem: backend
tags: [git-hygiene, env-config, certification, import, idempotency, db-schema]
dependency_graph:
  requires: ["01-01", "01-02"]
  provides: ["SEC-06", "DB-03"]
  affects: ["import_service", "certification_model", "env_config"]
tech_stack:
  added: []
  patterns:
    - "SELECT-then-update-or-insert (application-level upsert) for idempotent import"
    - "SQLAlchemy UniqueConstraint on composite key (employee_id, certification_type)"
key_files:
  created:
    - backend/tests/test_services/test_import_idempotency.py
  modified:
    - .gitignore
    - .env.example
    - backend/app/models/certification.py
    - backend/app/services/import_service.py
decisions:
  - ".env added to .gitignore; git rm --cached .env required as human action (cannot be automated)"
  - "Upsert pattern: SELECT existing by (employee_id, certification_type), update if found, insert if not — dialect-agnostic, works on SQLite and PostgreSQL"
  - "UniqueConstraint name: uq_certifications_employee_type — dev DB must be re-seeded after this change"
  - "NATIONAL_ID_ENCRYPTION_KEY documented in .env.example with AES-256-GCM key generation instructions"
metrics:
  duration: "12min"
  completed: "2026-03-26"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 5
---

# Phase 01 Plan 05: .env Hygiene and Certification Import Idempotency Summary

**One-liner:** Git .env hygiene fix (.gitignore + .env.example with REQUIRED markers) and DB-03 certification upsert with UniqueConstraint on (employee_id, certification_type).

## What Was Built

### SEC-06: .env Hygiene

- Added `.env` to `.gitignore` (was completely absent before this plan)
- Rewrote `.env.example` with:
  - Section headers for readability
  - `NATIONAL_ID_ENCRYPTION_KEY` (new field added in Plan 02, now documented)
  - `# REQUIRED — must be changed before production` markers on JWT_SECRET_KEY, PUBLIC_API_KEY, and NATIONAL_ID_ENCRYPTION_KEY sections
  - AES-256-GCM key generation instructions for NATIONAL_ID_ENCRYPTION_KEY
- **Pending human action:** `git rm --cached .env && git commit` — cannot be automated (requires terminal access)

### DB-03: Certification Import Idempotency

- Added `UniqueConstraint('employee_id', 'certification_type', name='uq_certifications_employee_type')` to `Certification` model
- Replaced blind insert in `_import_certifications()` with SELECT-then-update-or-insert pattern:
  - Checks for existing record by (employee_id, certification_type)
  - If found: updates certification_stage, bonus_rate, issued_at, expires_at in-place
  - If not found: creates new record
- Returns `status='success'` for both new inserts and updates (idempotent re-imports)
- Replaced 2 xfail stub tests with 3 real idempotency tests

## Commits

| Hash | Description |
|------|-------------|
| 357c143 | chore(01-05): add .env to .gitignore and update .env.example with REQUIRED markers |
| 8f68b9f | feat(01-05): certification UniqueConstraint and idempotent import upsert (DB-03) |

## Test Results

```
41 passed, 1 skipped in 28.09s
```

All Phase 1 tests pass. No xfail markers remain in `test_import_idempotency.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] .gitignore was missing .env entry entirely**
- **Found during:** Pre-task verification (git ls-files .env showed .env tracked; grep showed .env not in .gitignore)
- **Issue:** .gitignore only excluded `.venv/` and other paths — `.env` was not listed, which is why it was being tracked
- **Fix:** Added `.env` on its own line to .gitignore before committing .env.example changes
- **Files modified:** .gitignore
- **Commit:** 357c143

**2. [Rule 1 - Bug] Test DB setup used in-memory SQLite which couldn't share tables across sessions**
- **Found during:** Task 3 RED phase — all 3 tests failed with "no such table: departments"
- **Issue:** `create_session_factory(settings)` creates its own engine internally; `Base.metadata.create_all` on a different engine didn't help for `sqlite:///:memory:` (separate connections = separate databases)
- **Fix:** Switched to file-based SQLite with `init_database()` using same pattern as existing `test_import_service.py`
- **Files modified:** backend/tests/test_services/test_import_idempotency.py
- **Commit:** 8f68b9f (included in same task commit)

### Pending Human Action (Not a Deviation)

Task 1 was `type="checkpoint:human-action"` — the plan explicitly identified `git rm --cached .env` as a human-only action. This remains outstanding:

```bash
git rm --cached .env
git commit -m "chore(sec-06): remove .env from git tracking"
```

After this, `git ls-files .env` should return empty.

## Known Stubs

None — all plan goals achieved. The only outstanding item is the human-action git command above.

## Phase 1 Completion Note

This is the final plan (5 of 5) in Phase 01. All 11 requirements (SEC-01~08, DB-01~03) are implemented. The one remaining human action is removing `.env` from the git index.

## Self-Check: PASSED

Files exist:
- FOUND: D:/wage_adjust/.gitignore (contains .env)
- FOUND: D:/wage_adjust/.env.example (contains NATIONAL_ID_ENCRYPTION_KEY, REQUIRED markers)
- FOUND: D:/wage_adjust/backend/app/models/certification.py (contains UniqueConstraint)
- FOUND: D:/wage_adjust/backend/app/services/import_service.py (contains upsert pattern)
- FOUND: D:/wage_adjust/backend/tests/test_services/test_import_idempotency.py (3 real tests, no xfail)

Commits verified:
- FOUND: 357c143 (chore: .gitignore and .env.example)
- FOUND: 8f68b9f (feat: certification upsert)

Tests: 41 passed, 1 skipped.
