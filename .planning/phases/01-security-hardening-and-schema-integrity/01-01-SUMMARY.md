---
phase: 01-security-hardening-and-schema-integrity
plan: 01
subsystem: database
tags: [alembic, pytest, sqlalchemy, migrations, testing]

requires: []

provides:
  - "8 xfail test stub files covering SEC-01/02/03/04/05/07/08 and DB-03"
  - "Fresh PostgreSQL-compatible Alembic baseline migration (17 tables)"
  - "database.py without startup DDL (ensure_schema_compatibility removed)"
  - "slowapi==0.1.9 and cryptography==44.0.2 pinned in requirements.txt"

affects:
  - 01-02-encryption
  - 01-03-rate-limiting
  - 01-04-role-aware-salary
  - 01-05-startup-guard

tech-stack:
  added:
    - "slowapi==0.1.9 (rate limiting, Plans 03/04)"
    - "cryptography==44.0.2 (explicit pin for AES-GCM, Plan 02)"
  patterns:
    - "All test stubs use @pytest.mark.xfail(reason='REQ-ID: description') — not skip"
    - "Alembic is the sole migration path — no DDL in init_database()"
    - "Autogenerate baseline against empty SQLite DB to capture full schema"

key-files:
  created:
    - "backend/tests/test_security/__init__.py"
    - "backend/tests/test_security/test_encryption.py"
    - "backend/tests/test_security/test_password.py"
    - "backend/tests/test_security/test_storage.py"
    - "backend/tests/test_core/test_startup_guard.py"
    - "backend/tests/test_api/test_rate_limit.py"
    - "backend/tests/test_api/test_public_rate_limit.py"
    - "backend/tests/test_api/test_salary_roles.py"
    - "backend/tests/test_services/test_import_idempotency.py"
    - "alembic/versions/6e4824832f6a_baseline_schema.py"
  modified:
    - "backend/app/core/database.py"
    - "requirements.txt"

key-decisions:
  - "Generate autogenerate baseline against empty SQLite DB (not live DB) to produce op.create_table() calls for all 17 tables"
  - "Clear stale alembic_version row directly via SQL before generating baseline (alembic stamp head failed with missing revision)"
  - "Remove inspect import from database.py after ensure_schema_compatibility() deletion"

patterns-established:
  - "xfail stubs: every future-feature test uses @pytest.mark.xfail with REQ-ID in reason string"
  - "Alembic-only migrations: init_database() only calls create_all (safe for fresh installs) and logs reminder to run alembic upgrade head"

requirements-completed: [DB-01, DB-02]

duration: 5min
completed: 2026-03-26
---

# Phase 01 Plan 01: Wave 0 Test Stubs and Alembic Reset Summary

**21 xfail test stubs across 8 files, fresh 17-table Alembic baseline migration, and ensure_schema_compatibility() removed from startup path**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-26T00:45:40Z
- **Completed:** 2026-03-26T00:49:48Z
- **Tasks:** 3 of 3
- **Files modified:** 12

## Accomplishments

- Created `backend/tests/test_security/` directory with 4 stub files covering SEC-03, SEC-07, SEC-08
- Created 5 additional stub files in existing test directories covering SEC-01, SEC-02, SEC-04, SEC-05, DB-03
- All 21 tests collected by pytest with 0 errors, all marked XFAIL
- Removed 43-line `ensure_schema_compatibility()` function and its call from `init_database()`
- Deleted 4 stale Alembic migration files and generated single fresh PostgreSQL-compatible baseline
- Pinned `slowapi==0.1.9` and `cryptography==44.0.2` in requirements.txt

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Wave 0 test stub files** - `d4c0805` (test)
2. **Task 2: Pin new dependencies in requirements.txt** - `e22100d` (chore)
3. **Task 3: Retire ensure_schema_compatibility() and reset Alembic baseline** - `c85189c` (refactor)

## Files Created/Modified

- `backend/tests/test_security/__init__.py` - New test_security package (empty)
- `backend/tests/test_security/test_encryption.py` - 4 SEC-03 xfail stubs
- `backend/tests/test_security/test_password.py` - 4 SEC-08 xfail stubs
- `backend/tests/test_security/test_storage.py` - 2 SEC-07 xfail stubs
- `backend/tests/test_core/test_startup_guard.py` - 3 SEC-01 xfail stubs
- `backend/tests/test_api/test_rate_limit.py` - 2 SEC-02 xfail stubs
- `backend/tests/test_api/test_public_rate_limit.py` - 1 SEC-05 xfail stub
- `backend/tests/test_api/test_salary_roles.py` - 3 SEC-04 xfail stubs
- `backend/tests/test_services/test_import_idempotency.py` - 2 DB-03 xfail stubs
- `alembic/versions/6e4824832f6a_baseline_schema.py` - Fresh baseline with op.create_table() for all 17 tables
- `backend/app/core/database.py` - Removed ensure_schema_compatibility(), added logger, updated init_database()
- `requirements.txt` - Added slowapi==0.1.9 and cryptography==44.0.2

## Decisions Made

- **Autogenerate against empty DB:** Used a temporary empty SQLite DB for `alembic revision --autogenerate` rather than the live database. The live DB had all tables already, so autogenerate would only produce a delta migration. Running against an empty DB produces `op.create_table()` calls for all 17 tables — the correct PostgreSQL-compatible baseline format.
- **Clear stale alembic_version directly:** `alembic stamp head` failed because the old revision `9a7b6c5d4e3f` no longer existed. Cleared the `alembic_version` table row directly via Python/SQLAlchemy before regenerating.
- **Remove `inspect` import:** After removing `ensure_schema_compatibility()`, the `inspect` import from sqlalchemy was no longer used in `database.py`. Removed to keep the module clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cleared stale alembic_version row before baseline generation**
- **Found during:** Task 3 (Reset Alembic baseline)
- **Issue:** `alembic revision --autogenerate` failed with "Can't locate revision identified by '9a7b6c5d4e3f'" because the live SQLite DB had an alembic_version row pointing to the deleted migration
- **Fix:** Cleared the `alembic_version` table row directly via Python/SQLAlchemy then re-ran autogenerate against an empty temp DB
- **Files modified:** None (live DB state change only)
- **Verification:** `alembic revision --autogenerate` succeeded, produced 17 create_table calls
- **Committed in:** c85189c (Task 3 commit)

**2. [Rule 3 - Blocking] Used empty temp DB for autogenerate to produce create_table baseline**
- **Found during:** Task 3 (Reset Alembic baseline)
- **Issue:** First autogenerate against live DB (which had all tables) produced only a delta migration (removing server_defaults, adding indexes) — not the required full `op.create_table()` baseline
- **Fix:** Generated against a fresh empty SQLite temp DB so autogenerate sees all tables as "added"
- **Files modified:** alembic/versions/ (6e4824832f6a_baseline_schema.py replaces delta migration)
- **Verification:** `grep "op.create_table" alembic/versions/6e4824832f6a_baseline_schema.py` shows 17 create_table calls, no batch_alter_table
- **Committed in:** c85189c (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both auto-fixes were necessary to generate the correct baseline migration format. No scope creep.

## Issues Encountered

- Stale alembic_version row in SQLite DB referencing deleted migration caused initial `alembic revision` failure. Resolved by direct SQL DELETE on alembic_version table.
- First autogenerate attempt produced a delta migration (not a baseline) because the live DB already had all tables. Switched to empty temp DB approach to get full create_table baseline.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 8 test stub files collected by pytest with 0 errors — Plans 02-05 can now implement features and the stubs will automatically transition from XFAIL to PASS
- Alembic is now the sole migration path; Plans that add columns must create new Alembic migration files
- `slowapi` is available in requirements.txt for Plan 03 (rate limiting) and Plan 04
- `cryptography` pin is in place for Plan 02 (AES-GCM PII encryption)
- Fresh SQLite dev DB may need `alembic upgrade head` or `alembic stamp head` after this reset

## Self-Check: PASSED

- FOUND: backend/tests/test_security/__init__.py
- FOUND: backend/tests/test_security/test_encryption.py
- FOUND: backend/tests/test_core/test_startup_guard.py
- FOUND: alembic/versions/6e4824832f6a_baseline_schema.py
- FOUND: backend/app/core/database.py
- FOUND commit: d4c0805 (Task 1)
- FOUND commit: e22100d (Task 2)
- FOUND commit: c85189c (Task 3)

---
*Phase: 01-security-hardening-and-schema-integrity*
*Completed: 2026-03-26*
