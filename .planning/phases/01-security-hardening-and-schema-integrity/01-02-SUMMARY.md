---
phase: 01-security-hardening-and-schema-integrity
plan: "02"
subsystem: security
tags:
  - encryption
  - aes-gcm
  - pii
  - password-complexity
  - path-traversal
  - alembic
  - sqlalchemy-typedecorator
dependency_graph:
  requires:
    - "01-01"
  provides:
    - EncryptedString TypeDecorator (backend.app.core.encryption)
    - AES-256-GCM national ID encryption/decryption
    - mask_national_id() for API response masking
    - path traversal guard in LocalStorageService.resolve_path()
    - password complexity validator on UserCreate, PasswordChangeRequest, AdminPasswordUpdateRequest
    - national_id_encryption_key Settings field
    - Alembic migration fa1c02bf9cd1 expanding id_card_no to String(256)
  affects:
    - backend/app/models/employee.py (id_card_no column type)
    - backend/app/models/user.py (id_card_no column type)
    - backend/app/schemas/user.py (password validation)
    - backend/app/core/storage.py (path traversal guard)
tech_stack:
  added:
    - cryptography.hazmat.primitives.ciphers.aead.AESGCM (AES-256-GCM)
  patterns:
    - SQLAlchemy TypeDecorator for transparent field-level encryption
    - Alembic batch_alter_table for SQLite-compatible column type changes
    - Pydantic field_validator for password complexity enforcement
    - Path.is_relative_to() for path traversal prevention
key_files:
  created:
    - backend/app/core/encryption.py
    - alembic/versions/fa1c02bf9cd1_encrypt_national_id_columns.py
    - pytest.ini
  modified:
    - backend/app/core/config.py
    - backend/app/models/employee.py
    - backend/app/models/user.py
    - backend/app/core/storage.py
    - backend/app/schemas/user.py
    - backend/tests/test_security/test_encryption.py
    - backend/tests/test_security/test_storage.py
    - backend/tests/test_security/test_password.py
decisions:
  - "Used AES-256-GCM over SM4 (resolved from pending: PIPL compliance sufficient with AES-256-GCM per RESEARCH.md decision)"
  - "Migration uses batch_alter_table (SQLite-compatible) not op.alter_column -- required for dev SQLite; PostgreSQL handles batch mode transparently"
  - "EncryptedString has passthrough mode when NATIONAL_ID_ENCRYPTION_KEY is empty -- dev/test friendly, no encryption disabled warnings block tests"
  - "DB-level unique constraint on encrypted id_card_no operates on ciphertext -- application-level check in IdentityBindingService is the real uniqueness guard"
  - "Password complexity rule: uppercase + lowercase + (digit OR symbol) -- aligns with NIST SP 800-63B character class requirements"
  - "test_storage.py uses tempfile.TemporaryDirectory instead of pytest tmp_path -- avoids Windows permission errors on AAON user temp dir"
metrics:
  duration_minutes: 8
  completed_date: "2026-03-26"
  tasks_completed: 4
  tasks_total: 4
  files_created: 3
  files_modified: 8
---

# Phase 01 Plan 02: AES-256-GCM National ID Encryption, Path Guard, Password Complexity Summary

**One-liner:** AES-256-GCM EncryptedString TypeDecorator for national ID PII, path traversal ValueError guard in storage, password complexity validator on all auth schemas, and Alembic migration expanding id_card_no to String(256).

## What Was Built

### Task 1: backend/app/core/encryption.py (TDD)

Created the encryption module with:
- `encrypt_national_id(plaintext, key)` — AES-256-GCM with random 12-byte nonce; returns base64(nonce+ciphertext)
- `decrypt_national_id(token, key)` — decodes and decrypts; raises ValueError on tamper
- `mask_national_id(plaintext)` — returns first-6 + 8 asterisks + last-4, or '****' for strings shorter than 10 chars
- `EncryptedString(TypeDecorator)` — transparent encrypt/decrypt on SQLAlchemy column bind/result; `cache_ok=True`; passthrough when key not set
- `_get_encryption_key()` — validates 32-byte requirement, module-level cache, warning when unset

All 6 tests pass including DB round-trip (Core API approach used to avoid `from __future__ import annotations` SQLAlchemy annotation resolution issue in Python 3.13).

### Task 2: Model and config wiring

- `Settings.national_id_encryption_key: str = ''` added after `redis_url`
- `Employee.id_card_no` changed from `String(32)` to `EncryptedString(256)`
- `User.id_card_no` changed from `String(32)` to `EncryptedString(256)`

### Task 3: Path traversal guard and password complexity (TDD)

**Storage guard:** `resolve_path()` now calls `resolved.is_relative_to(self.base_dir)` and raises `ValueError` with 'base_dir' in message for any escaping key.

**Password validator:** `_validate_password_complexity()` module-level helper checks uppercase, lowercase, and digit-or-symbol. `@field_validator('password')` applied to `UserCreate`; `@field_validator('new_password')` applied to `PasswordChangeRequest` and `AdminPasswordUpdateRequest`.

All 7 tests pass (2 storage + 5 password).

### Task 4: Alembic migration

Generated `alembic/versions/fa1c02bf9cd1_encrypt_national_id_columns.py`. The migration was manually cleaned to contain only the `id_card_no` column expansion (removing autogenerate noise from other schema drift). Uses `batch_alter_table` for SQLite compatibility. `alembic upgrade head` exits 0; current revision is `fa1c02bf9cd1`.

## Commits

| Hash | Message |
|------|---------|
| 6c946ae | feat(01-02): create AES-256-GCM encryption module with EncryptedString TypeDecorator |
| 15c4b2d | feat(01-02): wire EncryptedString into Employee/User models and add config field |
| fdec5ac | feat(01-02): add path traversal guard and password complexity validator |
| 48f5819 | feat(01-02): add Alembic migration for id_card_no column expansion to String(256) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DB round-trip test used ORM with from __future__ annotations**
- **Found during:** Task 1 TDD GREEN phase
- **Issue:** `from __future__ import annotations` in test file caused SQLAlchemy to stringify `Mapped[int]` annotations inside a function-scoped inline class, breaking the ORM model definition
- **Fix:** Replaced ORM Session-based round-trip with SQLAlchemy Core `Table` + `Column` API to avoid annotation resolution issues entirely
- **Files modified:** `backend/tests/test_security/test_encryption.py`
- **Commit:** 6c946ae

**2. [Rule 1 - Bug] SQLite does not support ALTER COLUMN TYPE**
- **Found during:** Task 4 migration execution
- **Issue:** `op.alter_column()` emits `ALTER TABLE ... ALTER COLUMN TYPE` which SQLite rejects with "near ALTER: syntax error"
- **Fix:** Replaced with `op.batch_alter_table()` context manager which rebuilds the table — SQLite-compatible and transparent for PostgreSQL
- **Files modified:** `alembic/versions/fa1c02bf9cd1_encrypt_national_id_columns.py`
- **Commit:** 48f5819

**3. [Rule 1 - Bug] Leftover _alembic_tmp_users table in dev DB**
- **Found during:** Task 4 migration execution
- **Issue:** A prior incomplete `batch_alter_table` run left `_alembic_tmp_users` in `wage_adjust.db`, blocking the new batch migration
- **Fix:** Dropped `_alembic_tmp_users` (and `_alembic_tmp_employees` for safety) via direct sqlite3 Python call, then re-ran migration
- **Files modified:** `wage_adjust.db` (runtime DB, not committed)

**4. [Rule 2 - Missing Functionality] No pytest.ini causing Windows temp dir permission error**
- **Found during:** Task 3 TDD — storage tests failing with `PermissionError` on `C:\Users\AAON\AppData\Local\Temp\pytest-of-AAON`
- **Fix:** Created `pytest.ini` with `testpaths = backend/tests`; rewrote storage tests to use `tempfile.TemporaryDirectory()` instead of `tmp_path` pytest fixture (which uses the broken system temp dir)
- **Files modified:** `pytest.ini`, `backend/tests/test_security/test_storage.py`
- **Commit:** fdec5ac

**5. [Rule 2 - Missing Functionality] Migration autogenerate included unrelated schema drift**
- **Found during:** Task 4 — the autogenerated migration included server_default removals, extra index adds, FK adds, and a `_alembic_tmp_users` table drop unrelated to this plan's scope
- **Fix:** Manually rewrote the migration to contain only the two `id_card_no` column expansions (employees + users). Other schema drift is deferred to a schema cleanup migration in a later plan.
- **Files modified:** `alembic/versions/fa1c02bf9cd1_encrypt_national_id_columns.py`

**6. [Rule 1 - Bug] DB was not stamped — alembic upgrade head rejected "not up to date"**
- **Found during:** Task 4 autogenerate step
- **Issue:** `wage_adjust.db` had all tables created by `init_database()` but `alembic_version` was empty — Alembic would not generate a migration against an unstamped DB
- **Fix:** `alembic stamp 6e4824832f6a` to mark the baseline as applied without re-running it
- **Files modified:** `wage_adjust.db` (runtime, not committed)

## Deferred Items

- Other schema drift detected by autogenerate (server_default changes, extra indexes, FK on users.employee_id) — should be addressed in a dedicated schema cleanup migration (Plan 03 or later)
- `_alembic_tmp_*` cleanup pattern should be documented in ops runbook for team awareness

## Known Stubs

None. All plan goals are fully implemented and wired.

## Notes for Subsequent Plans

- When `NATIONAL_ID_ENCRYPTION_KEY` is set in `.env`, any existing plaintext `id_card_no` values in `wage_adjust.db` will fail decryption. Delete `wage_adjust.db` and let `init_database()` recreate the schema from scratch, then run `alembic upgrade head`.
- `mask_national_id()` must be called at the API response layer (Plan 03/04) to prevent full national IDs from being exposed to non-admin callers. The function is importable from `backend.app.core.encryption`.
- The DB-level `unique=True` on `id_card_no` does NOT prevent duplicate national IDs when encryption is enabled (different nonces = different ciphertext). Application-level deduplication in `IdentityBindingService` is required.

## Self-Check: PASSED
