# Phase 1: Security Hardening and Schema Integrity - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix production-blocking security vulnerabilities and establish Alembic as the sole migration path. This phase is **backend-only** — no frontend UI changes (roadmap UI hint: no). All 11 requirements (SEC-01~08, DB-01~03) must pass before Phase 2 begins.

What's in scope:
- JWT startup guard, login rate limiting, PII encryption, role-aware API responses
- Public API rate limiting, .env hygiene, path traversal fix, password complexity
- Alembic baseline migration, retire ensure_schema_compatibility(), certification import idempotency

What's NOT in scope:
- python-jose CVE migration (not in requirements — defer to later phase)
- PostgreSQL migration (baseline must be Postgres-compatible, but DB switch itself is not Phase 1 work)
- Any frontend changes
- Celery/Redis wiring beyond rate limiting

</domain>

<decisions>
## Implementation Decisions

### National ID Encryption (SEC-03)
- **D-01:** Use **AES-256-GCM** via the `cryptography` library (not SM4). No Chinese national crypto standard requirement applies to this deployment context.
- **D-02:** Encryption is **reversible** — store ciphertext in the DB column, decrypt for admin display, return masked format (`330104********1234`) for non-admin roles in all API responses.
- **D-03:** Encryption key stored as a new env variable (e.g., `NATIONAL_ID_ENCRYPTION_KEY`), documented as REQUIRED in `.env.example`. Key must be 32 bytes (256-bit), base64-encoded.

### Rate Limiting Backend (SEC-02, SEC-05)
- **D-04:** Use **Redis backend** for both the login rate limiter (SEC-02) and the public API rate limiter (SEC-05). Redis is already in `requirements.txt` (unused); wire it up via `slowapi` + `redis`.
- **D-05:** Graceful degradation: if Redis is unavailable at startup in development (`environment != "production"`), fall back to in-memory backend and log a warning. Production must enforce Redis — refuse to start if Redis unreachable.
- **D-06:** Login rate limit: **10 failed attempts per IP within 15 minutes → HTTP 429**. Track by IP only (not IP+email). After 429, the window continues — no permanent lockout.
- **D-07:** Public API rate limit: use the existing `public_api_rate_limit` config string (`"1000/hour"` default) parsed by slowapi. Apply to all `/api/v1/public/` routes.

### Alembic Migration Strategy (DB-01, DB-02)
- **D-08:** **Full reset** — delete all 4 existing Alembic migration files in `alembic/versions/`. Generate a single fresh baseline migration from the current schema state.
- **D-09:** Baseline migration must use **PostgreSQL-compatible SQL only** — no SQLite-specific syntax, no `TEXT` where `VARCHAR(N)` should be used, standard column types throughout. Goal: this baseline runs cleanly on PostgreSQL when the team switches databases.
- **D-10:** Retire `ensure_schema_compatibility()` in `database.py` entirely — remove the function and all calls to it. Replace the startup behavior with a logged reminder that `alembic upgrade head` must be run before starting the server (or wire it into the lifespan startup if the team prefers auto-migration).
- **D-11:** After Phase 1, the rule is: **all schema changes go through Alembic migrations only**. No DDL in application code.

### Startup Validation (SEC-01)
- **D-12:** On startup, when `environment == "production"`, refuse to start and print a clear config error if any of these are their placeholder defaults: `jwt_secret_key == "change_me"`, `public_api_key == "your_public_api_key"`. Log a loud warning (not hard-fail) for `deepseek_api_key == "your_deepseek_api_key"` since the app can run without DeepSeek in some modes.

### Role-Aware Salary Responses (SEC-04)
- **D-13:** Filter salary recommendation responses by role: `admin`/`hrbp` see full figures (`current_salary`, `recommended_salary`, `adjustment_amount`); `manager` sees only `adjustment_percentage`; `employee` sees only their own `adjustment_percentage`.
- **D-14:** Implement as a response-shaping step in the salary API layer (not in the engine or service layer) — keep business logic and access filtering separate.

### .env Hygiene (SEC-06)
- **D-15:** Run `git rm --cached .env` to remove `.env` from git tracking. Update `.env.example` to mark `JWT_SECRET_KEY`, `PUBLIC_API_KEY`, and `NATIONAL_ID_ENCRYPTION_KEY` as `# REQUIRED — must be changed before production`. Do NOT rotate any secrets — that's a human action outside this phase.

### Claude's Discretion
- Password complexity validator (SEC-08): Choose the regex pattern — at least 8 chars, mixed case + digit or symbol. Claude picks the exact rule.
- Path traversal fix (SEC-07): Add `assert resolved_path.is_relative_to(self.base_dir)` — straightforward, Claude implements directly.
- DB-03 certification idempotency: Use upsert (ON CONFLICT DO NOTHING or equivalent) on `(employee_id, cycle_id, certification_type)`. Claude decides the exact unique constraint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §安全加固 — SEC-01 through SEC-08 full text
- `.planning/REQUIREMENTS.md` §数据库与迁移 — DB-01 through DB-03 full text

### Codebase — Security-Relevant Files
- `backend/app/core/config.py` — Settings class with all placeholder defaults; startup guard goes here
- `backend/app/core/security.py` — JWT encode/decode, password hashing; python-jose usage
- `backend/app/core/database.py` — `ensure_schema_compatibility()` to be retired; Alembic engine config
- `backend/app/core/storage.py` — `LocalStorageService.resolve_path()` path traversal fix target
- `backend/app/api/v1/auth.py` lines 78–91 — Login endpoint; rate limit attachment point
- `backend/app/api/v1/salary.py` lines 71–117 — Role-aware response filtering target
- `backend/app/api/v1/public.py` — Public API; rate limit wiring point
- `backend/app/models/employee.py` line 15 — `national_id` column (plaintext today)
- `backend/app/models/user.py` line 16 — `national_id` column (plaintext today)
- `backend/app/schemas/employee.py` lines 11, 27 — national_id schema fields
- `backend/app/schemas/user.py` lines 19, 30, 32, 41, 45–46 — national_id + password fields
- `backend/app/services/import_service.py` — Certification import; DB-03 idempotency target
- `alembic/versions/` — 4 files to be deleted as part of D-08
- `alembic.ini` — Alembic config; verify `sqlalchemy.url` setup

### Known Issues (from codebase audit)
- `.planning/codebase/CONCERNS.md` §Security Concerns — Full audit of all HIGH/MEDIUM security issues in scope for this phase

</canonical_refs>

<deferred>
## Deferred Ideas

- **python-jose CVE migration** — CONCERNS.md flags CVE-2024-33663/33664 as HIGH. Not in Phase 1 requirements. Worth addressing in a future security patch phase. Suggested fix: migrate to `PyJWT`.
- **HTTPS/TLS enforcement** — Mentioned in CONCERNS.md. Out of scope for this phase; document in deployment guide instead.
- **SQLite → PostgreSQL migration** — User confirmed current DB is SQLite ("不好用"). Phase 1 only ensures Alembic baseline is Postgres-compatible. Actual DB switch is a separate ops task.

</deferred>
