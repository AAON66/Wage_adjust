# Phase 1: Security Hardening and Schema Integrity - Research

**Researched:** 2026-03-25
**Domain:** FastAPI security hardening, AES-256-GCM encryption, slowapi rate limiting, Alembic migration management
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**National ID Encryption (SEC-03)**
- D-01: Use AES-256-GCM via the `cryptography` library (not SM4).
- D-02: Encryption is reversible — store ciphertext in the DB column, decrypt for admin display, return masked format (`330104********1234`) for non-admin roles.
- D-03: Encryption key stored as `NATIONAL_ID_ENCRYPTION_KEY` env variable, 32 bytes (256-bit), base64-encoded.

**Rate Limiting Backend (SEC-02, SEC-05)**
- D-04: Use Redis backend for both login rate limiter and public API rate limiter via `slowapi` + `redis`.
- D-05: Graceful degradation — Redis unavailable in dev → in-memory fallback with warning; production must refuse to start if Redis unreachable.
- D-06: Login rate limit: 10 failed attempts per IP within 15 minutes → HTTP 429. Track by IP only. No permanent lockout.
- D-07: Public API rate limit: `public_api_rate_limit` config string (`"1000/hour"` default) applied to all `/api/v1/public/` routes.

**Alembic Migration Strategy (DB-01, DB-02)**
- D-08: Full reset — delete all 4 existing Alembic migration files. Generate one fresh baseline migration.
- D-09: Baseline migration must use PostgreSQL-compatible SQL only. No SQLite-specific syntax.
- D-10: Retire `ensure_schema_compatibility()` entirely. Replace with logged reminder or lifespan auto-migration.
- D-11: After Phase 1, all schema changes via Alembic only. No DDL in application code.

**Startup Validation (SEC-01)**
- D-12: On `environment == "production"`, refuse to start if `jwt_secret_key == "change_me"` or `public_api_key == "your_public_api_key"`. Loud warning (not hard-fail) for `deepseek_api_key == "your_deepseek_api_key"`.

**Role-Aware Salary Responses (SEC-04)**
- D-13: Filter by role: `admin`/`hrbp` see full figures; `manager` sees only `adjustment_percentage`; `employee` sees only their own `adjustment_percentage`.
- D-14: Implement as response-shaping step in the salary API layer (not engine or service).

**.env Hygiene (SEC-06)**
- D-15: `git rm --cached .env`. Update `.env.example` to mark `JWT_SECRET_KEY`, `PUBLIC_API_KEY`, `NATIONAL_ID_ENCRYPTION_KEY` as `# REQUIRED — must be changed before production`.

### Claude's Discretion

- Password complexity validator (SEC-08): Choose the regex pattern — at least 8 chars, mixed case + digit or symbol.
- Path traversal fix (SEC-07): Add `assert resolved_path.is_relative_to(self.base_dir)` — straightforward.
- DB-03 certification idempotency: Use upsert (ON CONFLICT DO NOTHING or equivalent) on `(employee_id, cycle_id, certification_type)`. Claude decides exact unique constraint.

### Deferred Ideas (OUT OF SCOPE)

- python-jose CVE migration (CVE-2024-33663/33664) — not in Phase 1 requirements. Defer to later phase.
- HTTPS/TLS enforcement — out of scope; document in deployment guide.
- SQLite → PostgreSQL migration — Phase 1 only ensures Alembic baseline is Postgres-compatible. DB switch is separate.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEC-01 | Refuse to start in production when JWT secret is default "change_me" | Startup guard pattern in FastAPI lifespan |
| SEC-02 | Login endpoint returns HTTP 429 after 10 failed attempts per IP in 15 minutes | slowapi + Redis rate limiting, failed-attempt tracking |
| SEC-03 | National ID encrypted at rest with AES-256-GCM; masked in non-admin API responses | cryptography library TypeDecorator for SQLAlchemy |
| SEC-04 | Salary recommendation endpoint returns different fields by role | Role-aware Pydantic response shaping in API layer |
| SEC-05 | Public API rate limit config is actually enforced on `/api/v1/public/` | slowapi attached to router with Redis backend |
| SEC-06 | `.env` removed from git tracking; `.env.example` documents required fields | `git rm --cached .env`, gitignore update |
| SEC-07 | `LocalStorageService.resolve_path()` validates path stays within `base_dir` | `Path.is_relative_to()` assertion |
| SEC-08 | Password complexity enforced on backend (mixed case + digit or symbol) | Pydantic v2 `field_validator` with regex |
| DB-01 | Alembic baseline migration generated from current schema | Alembic `revision --autogenerate` workflow |
| DB-02 | `ensure_schema_compatibility()` retired; no DDL at startup | Remove from `database.py`, lifespan update |
| DB-03 | Certification import is idempotent — no duplicate rows on re-import | SQLAlchemy 2.0 upsert with unique constraint |
</phase_requirements>

---

## Summary

Phase 1 is a pure backend hardening phase with no frontend changes. The codebase is already well-structured (FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Alembic 1.14), and all required libraries are either already installed (`cryptography` is a transitive dependency of `python-jose[cryptography]`, `redis==5.2.1` is in requirements.txt) or need to be added (`slowapi`).

The three clusters of work are largely independent: (1) security patches to config, auth, storage, schemas, and salary API; (2) PII encryption via a SQLAlchemy TypeDecorator; and (3) Alembic reset and migration baseline. The certification idempotency fix (DB-03) requires both a schema migration (adding a unique constraint) and an import code change, linking cluster 3 to cluster 2.

The most nuanced implementation challenge is the AES-256-GCM TypeDecorator: the nonce must be stored alongside the ciphertext (prepended as 12 bytes before the base64 payload), the column needs to expand from `VARCHAR(32)` to `VARCHAR(256)` to hold the ciphertext, and the existing plaintext data in the dev database requires a data migration or documented manual re-seed. The rate limiting is straightforward with slowapi but requires careful handling of the Redis fallback — slowapi's `_RateLimiter` accepts a `storage_uri` parameter that can point to Redis or fall back to in-memory.

**Primary recommendation:** Implement in this order: SEC-06 (git hygiene, no code) → SEC-07 (2-line fix) → SEC-08 (validator) → SEC-01 (startup guard) → SEC-02/SEC-05 (slowapi install + wiring) → SEC-03 (TypeDecorator + migration) → SEC-04 (salary response shaping) → DB-01/DB-02/DB-03 (Alembic reset + cert upsert).

---

## Standard Stack

### Core (already installed)
| Library | Version in requirements.txt | Purpose | Notes |
|---------|------------------------------|---------|-------|
| `cryptography` | transitive dep of `python-jose[cryptography]` | AES-256-GCM encryption | Must add explicitly to requirements.txt |
| `redis` | 5.2.1 | Redis client for rate limiting backend | Already in requirements.txt, unused |
| `alembic` | 1.14.0 | Database migrations | Already configured; needs reset |
| `pydantic` | 2.10.3 | Schema validation, password validator | Full v2 API available |

### To Add
| Library | Latest Stable | Purpose | Why |
|---------|---------------|---------|-----|
| `slowapi` | 0.1.9 | Rate limiting for FastAPI/Starlette | Standard FastAPI rate limit library; wraps `limits` |

**Installation:**
```bash
pip install slowapi
```

Add to `requirements.txt`:
```
slowapi==0.1.9
cryptography==44.0.2   # pin explicitly, currently pulled in as transitive
```

**Version verification:** slowapi 0.1.9 is the latest stable release as of early 2026. `cryptography` should be pinned explicitly since it is currently only a transitive dependency — if `python-jose` is removed later, cryptography would drop out.

---

## Architecture Patterns

### Recommended Project Structure Changes

No new directories needed. Changes touch existing files only:

```
backend/app/
├── core/
│   ├── config.py          # SEC-01: startup guard, new NATIONAL_ID_ENCRYPTION_KEY field
│   ├── database.py        # DB-01/02: remove ensure_schema_compatibility(), update init_database()
│   ├── storage.py         # SEC-07: path traversal guard
│   └── encryption.py      # SEC-03: NEW — AES-256-GCM TypeDecorator + mask helper
├── api/v1/
│   ├── auth.py            # SEC-02: slowapi decorator on login endpoint
│   ├── salary.py          # SEC-04: role-aware response shaping
│   └── public.py          # SEC-05: slowapi rate limiter on router
├── schemas/
│   ├── user.py            # SEC-08: password complexity validator
│   └── salary.py          # SEC-04: role-filtered response schema variants
├── models/
│   ├── employee.py        # SEC-03: id_card_no column type change
│   ├── user.py            # SEC-03: id_card_no column type change
│   └── certification.py   # DB-03: add UniqueConstraint
├── services/
│   └── import_service.py  # DB-03: upsert instead of insert for certifications
└── main.py                # SEC-01/SEC-02/SEC-05: add Limiter, startup guard call
alembic/versions/
└── XXXX_baseline.py       # DB-01: single fresh baseline
```

---

### Pattern 1: AES-256-GCM SQLAlchemy TypeDecorator

**What:** A custom `TypeDecorator` that transparently encrypts on `process_bind_param` (write to DB) and decrypts on `process_result_value` (read from DB). The nonce (12 bytes for GCM) is stored prepended to the ciphertext, then the whole thing is base64-encoded.

**Why this approach:** The TypeDecorator sits below the ORM layer — services and engines receive plaintext strings, never ciphertext. Encryption is invisible to all callers above `core/`.

**Key storage:** The 32-byte key is base64-encoded in `NATIONAL_ID_ENCRYPTION_KEY` env var. At runtime, `base64.b64decode(key_str)` gives the raw bytes. Store the decoded bytes in a module-level cache (initialized once at import time from `get_settings()`).

**Nonce handling:** Generate a fresh `os.urandom(12)` for every encryption call. Prepend nonce to ciphertext before base64 encoding. On decrypt, split the first 12 bytes as nonce, the rest as ciphertext.

**Column size:** Current `String(32)` holds a 18-char national ID. After encryption: 12-byte nonce + 18-byte plaintext padded + 16-byte GCM tag = ~46 bytes raw, base64-encoded ≈ 64 chars. Add room for longer IDs and future growth — use `String(256)` in the migration.

**Masking helper:** A pure function `mask_national_id(plaintext: str) -> str` that returns `first_6 + "********" + last_4`. Called in the salary API layer and any schema serializer that needs to mask.

```python
# Source: cryptography library official docs — https://cryptography.io/en/latest/hazmat/primitives/aead/
from __future__ import annotations
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_national_id(plaintext: str, key: bytes) -> str:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_national_id(token: str, key: bytes) -> str:
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()

def mask_national_id(plaintext: str) -> str:
    if len(plaintext) < 10:
        return "****"
    return plaintext[:6] + "********" + plaintext[-4:]
```

**TypeDecorator wiring:**
```python
# Source: SQLAlchemy docs — https://docs.sqlalchemy.org/en/20/core/custom_types.html#augmenting-existing-types
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

class EncryptedString(TypeDecorator):
    impl = String(256)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        key = _get_encryption_key()   # from settings, cached
        return encrypt_national_id(value, key)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        key = _get_encryption_key()
        return decrypt_national_id(value, key)
```

**CRITICAL: Existing data.** The dev database (`wage_adjust.db`) currently has plaintext `id_card_no` values. The Alembic baseline migration changes the column type but does NOT re-encrypt existing rows. The plan must include a one-time data migration step (or document that dev DB must be re-seeded). For production (new deployment), this is not an issue.

---

### Pattern 2: slowapi Rate Limiting on FastAPI

**What:** `slowapi` wraps the `limits` library and attaches per-route or per-router rate limits to FastAPI endpoints. It uses a `Limiter` object attached to `app.state.limiter`, and `_rate_limit_exceeded_handler` registered as an exception handler.

**Redis backend configuration:**
```python
# Source: slowapi docs — https://slowapi.readthedocs.io/en/latest/
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379/0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Graceful degradation pattern (D-05):**
```python
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

def create_limiter(settings) -> Limiter:
    if settings.environment == "production":
        # Hard fail if Redis is not reachable — verified during startup guard
        return Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        r.ping()
        logger.info("Rate limiter using Redis backend at %s", settings.redis_url)
        return Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable — rate limiter falling back to in-memory (dev only)")
        return Limiter(key_func=get_remote_address)  # defaults to in-memory
```

**Login rate limit (SEC-02) — tracking failed attempts only:**

The requirement is "10 failed attempts per IP within 15 minutes". Standard slowapi decorates the entire endpoint (counting all requests). To count only failures, a different approach is needed: use a Redis counter manually incremented on `401` response, checked at the top of the login handler. This avoids penalizing successful logins.

```python
# Login handler pattern (SEC-02 — failed attempts only)
@router.post('/login', response_model=TokenPair)
@limiter.limit("10/15minutes")   # fallback: limits total requests if Redis unavailable
def login_user(request: Request, payload: UserLogin, ...):
    ...
```

NOTE: Standard `@limiter.limit` counts ALL requests, not just failures. For strict "failed attempts only" behavior, implement a separate Redis counter:
- Key: `login_failed:{ip}` with TTL of 15 minutes
- Increment on `401` response
- Check at start of handler: if counter >= 10, raise `HTTPException(429)`
- On successful login, optionally reset counter (not required by D-06)

This manual counter pattern is more reliable than slowapi for "failures only" semantics.

**Public API rate limit (SEC-05):**
```python
# Apply to entire public router prefix via a dependency
@router.get('/employees/{employee_no}/latest-evaluation')
@limiter.limit("1000/hour")
def get_latest_employee_evaluation(request: Request, ...):
    ...
```

Or apply via a middleware-level route filter on the `/api/v1/public/` prefix. The per-route decorator is simpler to implement and matches the existing pattern.

**CRITICAL NOTE:** slowapi decorators require `request: Request` to be a parameter of the decorated function. All public API route functions currently lack `request: Request`. This parameter must be added to each decorated function.

---

### Pattern 3: FastAPI Lifespan Startup Guard (SEC-01)

**What:** The existing `lifespan()` in `main.py` calls `init_database()` synchronously. Add a validation step before it.

```python
# backend/app/core/config.py — add validation method
def validate_production_secrets(self) -> None:
    """Raise RuntimeError if running in production with placeholder secrets."""
    if self.environment != "production":
        return
    errors = []
    if self.jwt_secret_key == "change_me":
        errors.append("JWT_SECRET_KEY is set to the default 'change_me' placeholder.")
    if self.public_api_key == "your_public_api_key":
        errors.append("PUBLIC_API_KEY is set to the default placeholder.")
    if errors:
        raise RuntimeError(
            "PRODUCTION STARTUP BLOCKED — insecure configuration detected:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
    if self.deepseek_api_key == "your_deepseek_api_key":
        logger.warning("DEEPSEEK_API_KEY is set to the default placeholder — AI evaluation will use stub mode.")
```

Call from lifespan:
```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    settings.validate_production_secrets()   # raises RuntimeError → prevents startup
    load_model_modules()
    init_database()
    ...
```

`RuntimeError` during lifespan causes uvicorn to log the error and exit with non-zero status — exactly the right behavior. The error message is printed to stderr before exit.

---

### Pattern 4: Role-Aware Salary Response Shaping (SEC-04)

**What:** The salary API layer already uses `serialize_recommendation()`. Add role-based filtering there.

**Current `SalaryRecommendationRead` schema** exposes: `current_salary`, `recommended_salary`, `recommended_ratio`, `ai_multiplier`, `certification_bonus`, `final_adjustment_ratio`. The requirement is:
- `admin`/`hrbp`: all fields
- `manager`: only `adjustment_percentage` (i.e., `final_adjustment_ratio`)
- `employee`: only their own `adjustment_percentage`

**Pattern — multiple response schemas + filter function in API layer:**

```python
# backend/app/schemas/salary.py — add restricted schema
class SalaryRecommendationEmployeeRead(BaseModel):
    """Minimal view for employees: adjustment percentage only."""
    id: str
    evaluation_id: str
    final_adjustment_ratio: float
    status: str
    created_at: datetime

class SalaryRecommendationManagerRead(BaseModel):
    """Manager view: adjustment percentage only (no absolute figures)."""
    id: str
    evaluation_id: str
    final_adjustment_ratio: float
    recommended_ratio: float
    status: str
    created_at: datetime
```

```python
# backend/app/api/v1/salary.py — filter helper
def shape_recommendation_for_role(recommendation, role: str):
    if role in ('admin', 'hrbp'):
        return serialize_recommendation(recommendation)   # full SalaryRecommendationRead
    if role == 'manager':
        return SalaryRecommendationManagerRead(...)
    # employee
    return SalaryRecommendationEmployeeRead(...)
```

**NOTE:** The `response_model` annotation on the FastAPI route accepts a `Union` type or can be omitted (use `Any`) when the response type is dynamic. Use `response_model=None` and return the appropriate Pydantic model instance directly — FastAPI will serialize it correctly.

---

### Pattern 5: Pydantic v2 Password Complexity Validator (SEC-08)

**What:** Add a `field_validator` on `password` in `UserCreate` and `PasswordChangeRequest`. The `min_length=8` Field constraint runs before the validator; the validator adds complexity.

**Recommended regex rule (Claude's discretion):** At least one uppercase letter, at least one lowercase letter, and at least one digit or special character. This balances security with usability for enterprise internal tools.

```python
# backend/app/schemas/user.py
import re
from pydantic import field_validator

PASSWORD_COMPLEXITY_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[\d\W]).{8,}$'
)
PASSWORD_COMPLEXITY_MSG = (
    "密码必须包含大写字母、小写字母，以及数字或特殊字符。"
)

class UserCreate(BaseModel):
    password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not PASSWORD_COMPLEXITY_PATTERN.match(v):
            raise ValueError(PASSWORD_COMPLEXITY_MSG)
        return v
```

Apply the same validator to `PasswordChangeRequest`, `AdminPasswordUpdateRequest` via a mixin or shared validator.

**IMPORTANT:** The validator must also be applied to `UserLogin` is NOT appropriate — login should accept any password (even old ones that don't meet the new policy). Apply only to creation/change endpoints.

---

### Pattern 6: Path Traversal Fix (SEC-07)

**What:** Add `is_relative_to()` assertion in `LocalStorageService`.

```python
# backend/app/core/storage.py
def resolve_path(self, storage_key: str) -> Path:
    resolved = (self.base_dir / storage_key).resolve()
    if not resolved.is_relative_to(self.base_dir):
        raise ValueError(f"Storage key resolves outside base directory: {storage_key!r}")
    return resolved
```

`Path.is_relative_to()` was added in Python 3.9. This project uses Python 3.x with `match` patterns (requires 3.10+), so this is safe.

The fix must be applied to `resolve_path()` only — `save_bytes()` constructs its own path with `uuid4().hex` prefix and is safe. The `delete()` and `read_bytes()` methods both call `resolve_path()` so they inherit the fix automatically.

---

### Pattern 7: Alembic Baseline Reset (DB-01, DB-02)

**Current state:**
- 4 migration files exist: `d432371fb104`, `8f4e5a1c9b2d`, `3c1d2e4f5a6b`, `9a7b6c5d4e3f`
- `alembic.ini` has `sqlalchemy.url = sqlite+pysqlite:///./wage_adjust.db` (hardcoded SQLite URL)
- `alembic/env.py` already overrides `sqlalchemy.url` from `settings.database_url` at runtime — the hardcoded `alembic.ini` URL is only a fallback
- The 4 migration files are NOT executed automatically on startup; `ensure_schema_compatibility()` applies schema changes instead

**Reset procedure (exact commands):**
```bash
# 1. Delete all existing migration files
rm alembic/versions/d432371fb104_initial_schema.py
rm alembic/versions/8f4e5a1c9b2d_add_must_change_password_to_users.py
rm alembic/versions/3c1d2e4f5a6b_add_user_employee_binding_and_handbooks.py
rm alembic/versions/9a7b6c5d4e3f_add_evaluation_workflow_scoring_fields.py

# 2. Drop alembic_version table from dev database (SQLite)
sqlite3 wage_adjust.db "DROP TABLE IF EXISTS alembic_version;"

# 3. Generate fresh autogenerated baseline from current SQLAlchemy models
# (env.py already reads from settings.database_url, so this uses SQLite in dev)
alembic revision --autogenerate -m "baseline_schema"

# 4. Stamp the baseline as already applied (dev DB already has the schema)
alembic stamp head

# 5. Verify
alembic current   # should show the new revision as current
```

**PostgreSQL compatibility requirements for the generated migration (D-09):**

The autogenerated migration will target SQLite. Before committing, manually review and adjust:

1. Column types: Replace any `TEXT` with `VARCHAR(N)` where N is known. SQLAlchemy's `String(N)` already generates `VARCHAR(N)` for PostgreSQL. The autogenerate output should already be correct if models use `String(N)` consistently — verified: all models use `String(N)` or `Mapped[str]` with explicit `String(N)` in `mapped_column`.

2. `FLOAT` vs `NUMERIC`: `Float` columns in SQLAlchemy generate `FLOAT` for both SQLite and PostgreSQL — compatible.

3. `DATETIME` vs `TIMESTAMP`: SQLAlchemy `DateTime(timezone=True)` generates `TIMESTAMP WITH TIME ZONE` on PostgreSQL and `DATETIME` on SQLite — compatible.

4. Boolean: `Boolean` generates `BOOLEAN` on PostgreSQL and `INTEGER` on SQLite — compatible at SQLAlchemy level.

5. SQLite-specific constraint issue: The autogenerated migration will include `batch_alter_table` context for SQLite (since SQLite can't do inline `ADD CONSTRAINT`). For PostgreSQL these would need to be `op.create_unique_constraint(...)` calls. The migration must be written to be **dialect-agnostic or PostgreSQL-targeted**.

**Recommendation:** After `alembic revision --autogenerate`, manually review the generated file and rewrite any `with op.batch_alter_table(...)` blocks as plain `op.add_column()` / `op.create_unique_constraint()` calls that work on PostgreSQL. Add a comment: `# Baseline — runs on PostgreSQL. SQLite dev uses init_database() create_all().`

**Alternatively:** Keep the migration PostgreSQL-only and document that `alembic upgrade head` is only required in production. Dev continues to use `Base.metadata.create_all()` via `init_database()`.

**Lifespan change for DB-02 (retiring ensure_schema_compatibility):**

Replace in `backend/app/core/database.py`:
```python
def init_database(engine_instance: Engine | None = None) -> None:
    """Create all registered tables for the configured engine."""
    target_engine = engine_instance or engine
    Base.metadata.create_all(bind=target_engine)
    # REMOVED: ensure_schema_compatibility(target_engine)
```

In `main.py` lifespan, add a log message:
```python
logger.info(
    "Database initialized. Run 'alembic upgrade head' before first start "
    "or after any schema change."
)
```

Do NOT auto-run `alembic upgrade head` in lifespan — this would cause issues in test environments and requires Alembic to be configured correctly for the current database. Manual step is safer and aligns with standard production practice.

---

### Pattern 8: DB-03 Certification Import Idempotency

**Current behavior:** `_import_certifications()` in `import_service.py` always creates a new `Certification` row — no uniqueness check. Re-importing adds duplicate rows, causing `certification_bonus` to be summed multiple times.

**Decision (Claude's discretion):** Add a unique constraint on `(employee_id, certification_type)`. The `certification_stage` and `bonus_rate` should be updatable if the certification changes — so the unique key should be `(employee_id, certification_type)` only, and the upsert should update `certification_stage`, `bonus_rate`, `issued_at`, `expires_at` on conflict.

Rationale: An employee can only have one record per certification type at a time. If they get re-certified (new `issued_at`), the record is updated, not duplicated.

**SQLAlchemy 2.0 upsert for SQLite:**
```python
# Source: SQLAlchemy docs — https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#insert-on-conflict
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

stmt = sqlite_insert(Certification).values(
    employee_id=employee.id,
    certification_type=cert_type,
    certification_stage=cert_stage,
    bonus_rate=bonus_rate,
    issued_at=issued_at,
    expires_at=expires_at,
)
stmt = stmt.on_conflict_do_update(
    index_elements=['employee_id', 'certification_type'],
    set_={
        'certification_stage': stmt.excluded.certification_stage,
        'bonus_rate': stmt.excluded.bonus_rate,
        'issued_at': stmt.excluded.issued_at,
        'expires_at': stmt.excluded.expires_at,
    }
)
self.db.execute(stmt)
```

**For PostgreSQL compatibility:** Use `from sqlalchemy.dialects.postgresql import insert as pg_insert` with the same API. To support both databases without dialect-specific imports, use a database-agnostic approach:

```python
# Dialect-agnostic upsert (SQLAlchemy 2.0)
from sqlalchemy import select

existing = self.db.scalar(
    select(Certification).where(
        Certification.employee_id == employee.id,
        Certification.certification_type == cert_type,
    )
)
if existing is None:
    cert = Certification(...)
    self.db.add(cert)
else:
    existing.certification_stage = cert_stage
    existing.bonus_rate = bonus_rate
    existing.issued_at = issued_at
    existing.expires_at = expires_at
    self.db.add(existing)
```

This is slightly more verbose but works on both SQLite and PostgreSQL without dialect-specific imports. Given that the Alembic baseline is being written for PostgreSQL compatibility and the codebase may migrate, the dialect-agnostic select+update approach is preferred.

**Schema change required:** Add `UniqueConstraint('employee_id', 'certification_type', name='uq_certifications_employee_certification')` to the `Certification` model. This generates a migration via the baseline or a separate Alembic revision.

Since Phase 1 resets Alembic with a full baseline, the unique constraint on `Certification` is part of the baseline migration — no separate migration file is needed.

---

### Anti-Patterns to Avoid

- **Encrypting at the schema layer (Pydantic validators):** Encryption belongs in the TypeDecorator (database layer), not in Pydantic serializers. Pydantic schemas deal with plaintext or masked values only.
- **Using `encrypt(value)` without a per-value nonce:** AES-GCM is non-deterministic by design. Never use a fixed nonce — it destroys semantic security. Always `os.urandom(12)`.
- **Storing the encryption key in config.py defaults:** The `NATIONAL_ID_ENCRYPTION_KEY` default must be empty string or `None`, not a placeholder. A missing key should cause `EncryptedString.process_bind_param` to raise, not silently store plaintext.
- **Making `ensure_schema_compatibility()` a migration shim:** Already identified. Remove entirely — any future migration must go through Alembic.
- **Running `alembic upgrade head` inside lifespan:** This creates side effects in test environments (tests call `init_database()` directly). Keep migration as an explicit pre-deploy step.
- **Applying slowapi `@limiter.limit` without `request: Request` parameter:** slowapi requires `request: Request` in the decorated function signature. Missing it causes `RateLimitExceeded` to fail silently or raise a different exception.
- **Setting `response_model` to a concrete type when the response shape varies by role:** Use `response_model=None` and return validated Pydantic instances directly. FastAPI serializes them correctly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AES-256-GCM encryption | Custom XOR cipher, `Fernet`, home-grown block cipher | `cryptography.hazmat.primitives.ciphers.aead.AESGCM` | GCM provides authenticated encryption; handles nonce, ciphertext, and tag in one call |
| Rate limiting counter | Redis INCR + manual TTL management | `slowapi` + `limits` | Handles sliding windows, burst limits, multiple storage backends, FastAPI integration |
| Path traversal defense | String prefix matching (`storage_key.startswith('../')`) | `Path.is_relative_to()` | String checks miss URL-encoded traversals; `Path.resolve()` normalizes first |
| Pydantic field-level encryption | Custom `__get_validators__` in Pydantic v2 | SQLAlchemy `TypeDecorator` | TypeDecorator encrypts at the DB boundary; Pydantic operates on plaintext — correct separation |

---

## Runtime State Inventory

> Not a rename/refactor phase. However, SEC-03 (AES-256-GCM encryption of `id_card_no`) involves a data change to existing rows.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `wage_adjust.db` (SQLite dev DB) contains plaintext `id_card_no` in `employees` and `users` tables | After TypeDecorator is installed, existing plaintext values will be read successfully but re-writes will encrypt them. A one-time re-encryption script should be run on the dev DB, OR dev DB should be re-seeded. Document in plan. |
| Live service config | None — no external services wired yet | None |
| OS-registered state | None | None |
| Secrets/env vars | `NATIONAL_ID_ENCRYPTION_KEY` does not exist in `.env` or `.env.example` yet | Must be added to `.env.example` as REQUIRED; a dev key must be generated and added to `.env` before tests run |
| Build artifacts | None | None |

**Critical data migration note:** The `EncryptedString` TypeDecorator reads existing plaintext values without error (base64 decode of a short plaintext will fail or produce garbage). A migration script or re-seed of the dev database is required. The plan must include a Wave 0 task to generate the `NATIONAL_ID_ENCRYPTION_KEY` and a documented re-seed step.

---

## Common Pitfalls

### Pitfall 1: EncryptedString TypeDecorator breaks existing plaintext rows on decrypt

**What goes wrong:** After the TypeDecorator is installed, any existing plaintext `id_card_no` value (`"330104199901010123"`) is passed to `process_result_value`. The code tries `base64.b64decode("330104199901010123")` which either raises `binascii.Error` or produces garbled bytes that fail GCM authentication, crashing the row read.

**Why it happens:** The TypeDecorator is transparent — it runs on every DB read. Old plaintext values are not valid ciphertext.

**How to avoid:** Either (a) clear all `id_card_no` values in the dev database before enabling the TypeDecorator (acceptable for dev), or (b) add a migration script that reads all plaintext values, encrypts them, and writes back. In production (new deployment), all rows are inserted after the TypeDecorator is installed, so this is not an issue.

**Warning signs:** `cryptography.exceptions.InvalidTag` or `binascii.Error` on any query that joins or loads `employees`/`users` with `id_card_no`.

---

### Pitfall 2: slowapi limiter not attached to app.state causes AttributeError

**What goes wrong:** Decorating a route with `@limiter.limit(...)` without first attaching the limiter to `app.state.limiter` causes `AttributeError: 'State' object has no attribute 'limiter'` at request time.

**Why it happens:** slowapi looks for `request.app.state.limiter` internally.

**How to avoid:** In `create_app()` or `lifespan`, add `app.state.limiter = limiter` and register the exception handler: `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`.

---

### Pitfall 3: Alembic autogenerate misses SQLite-incompatible ALTER TABLE

**What goes wrong:** The autogenerated baseline uses `with op.batch_alter_table(...)` for constraints and column modifications (SQLite requirement). This syntax works on SQLite but generates different SQL than the clean PostgreSQL `ALTER TABLE ... ADD CONSTRAINT` form.

**Why it happens:** Alembic detects SQLite and emits `batch_alter_table` to work around SQLite's limited ALTER TABLE support.

**How to avoid:** After `alembic revision --autogenerate`, inspect the file and rewrite `batch_alter_table` blocks to use direct `op.add_column()`, `op.create_unique_constraint()`, `op.create_index()` calls. Add a comment noting this migration targets PostgreSQL. For dev SQLite, `Base.metadata.create_all()` via `init_database()` handles schema creation.

---

### Pitfall 4: Login rate limit counts all requests, not just failures

**What goes wrong:** `@limiter.limit("10/15minutes")` on the login endpoint blocks the 11th login attempt regardless of success/failure, locking out legitimate users after 10 logins in 15 minutes.

**Why it happens:** slowapi counts HTTP requests, not application-level outcomes.

**How to avoid:** Implement the failed-attempt counter manually in Redis (key: `login_failed:{ip_address}`, TTL: 900 seconds). Check counter at the top of the login handler; only increment on authentication failure. This is a manual Redis counter pattern, separate from slowapi.

---

### Pitfall 5: `UniqueConstraint` on `Certification` without a migration

**What goes wrong:** Adding `UniqueConstraint` to the `Certification` model without a corresponding Alembic migration means the constraint exists in the SQLAlchemy model metadata but not in the actual database schema. `on_conflict_do_update` SQL statements fail silently or raise unexpected errors.

**Why it happens:** `Base.metadata.create_all()` does not modify existing tables — it only creates missing ones. The unique constraint is never applied to the existing `certifications` table.

**How to avoid:** The unique constraint on `Certification` must be included in the Phase 1 Alembic baseline migration. Since D-08 generates a fresh baseline from the current model state, include the constraint in the model *before* running `alembic revision --autogenerate`. The autogenerate will include the constraint in the baseline.

---

### Pitfall 6: `lru_cache` on `get_settings()` caches stale Settings in tests

**What goes wrong:** The startup guard calls `settings.validate_production_secrets()`. Tests that override settings via `create_app(settings)` may still see a cached `get_settings()` instance with production environment values if the cache was populated earlier.

**Why it happens:** `@lru_cache` on `get_settings()` returns the same instance across all calls in the same process.

**How to avoid:** The startup guard should use the `settings` instance already resolved in `lifespan` (passed via `get_settings()` which is already used there). The test pattern already overrides `get_app_settings` dependency — the startup guard in `lifespan` calls `get_settings()` directly. Tests that need to test the guard should call `get_settings.cache_clear()` before each test, or test the `validate_production_secrets()` method directly on a constructed `Settings` instance.

---

## Code Examples

### Generate NATIONAL_ID_ENCRYPTION_KEY

```python
# One-time key generation — run in Python REPL, store in .env
import base64, os
key = base64.b64encode(os.urandom(32)).decode()
print(f"NATIONAL_ID_ENCRYPTION_KEY={key}")
```

### Adding slowapi to create_app()

```python
# backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

def create_limiter(settings: Settings) -> Limiter:
    """Create rate limiter — Redis in production, fallback in dev."""
    if settings.environment == "production":
        return Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    try:
        import redis as _redis
        _redis.from_url(settings.redis_url).ping()
        return Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable — using in-memory rate limiter (dev only)")
        return Limiter(key_func=get_remote_address)

def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(...)
    limiter = create_limiter(resolved_settings)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    ...
```

### Failed-login Redis counter (SEC-02)

```python
# backend/app/api/v1/auth.py
import logging
from fastapi import Request

FAILED_LOGIN_PREFIX = "login_failed:"
FAILED_LOGIN_LIMIT = 10
FAILED_LOGIN_WINDOW = 900  # 15 minutes in seconds

logger = logging.getLogger(__name__)

def _check_and_increment_failed_login(ip: str, settings) -> None:
    """Raise HTTP 429 if too many recent failures. Increment counter on call."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url)
        key = f"{FAILED_LOGIN_PREFIX}{ip}"
        count = r.get(key)
        if count and int(count) >= FAILED_LOGIN_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again in 15 minutes.",
            )
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, FAILED_LOGIN_WINDOW)
        pipe.execute()
    except HTTPException:
        raise
    except Exception:
        logger.warning("Failed login counter unavailable (Redis error) — skipping rate check")

@router.post('/login', response_model=TokenPair)
def login_user(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> TokenPair:
    ip = request.client.host if request.client else "unknown"
    _check_and_increment_failed_login(ip, settings)  # raises 429 if over limit
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        # Counter was already incremented — do not reset on failure
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password.')
    # Success: optionally reset counter
    # (D-06 says no permanent lockout; window self-expires)
    return TokenPair(...)
```

### Role-aware salary response shaping (SEC-04)

```python
# backend/app/api/v1/salary.py
def shape_recommendation_for_role(recommendation, current_user: User):
    if current_user.role in ('admin', 'hrbp'):
        return serialize_recommendation(recommendation)
    if current_user.role == 'manager':
        return SalaryRecommendationManagerRead(
            id=recommendation.id,
            evaluation_id=recommendation.evaluation_id,
            final_adjustment_ratio=recommendation.final_adjustment_ratio,
            recommended_ratio=recommendation.recommended_ratio,
            status=recommendation.status,
            created_at=recommendation.created_at,
        )
    # employee — only adjustment percentage
    return SalaryRecommendationEmployeeRead(
        id=recommendation.id,
        evaluation_id=recommendation.evaluation_id,
        final_adjustment_ratio=recommendation.final_adjustment_ratio,
        status=recommendation.status,
        created_at=recommendation.created_at,
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy `TypeDecorator` with Fernet | `cryptography.hazmat.primitives.ciphers.aead.AESGCM` | AESGCM always preferred for authenticated encryption | GCM provides integrity check; Fernet is slower and uses a different key format |
| `flask-limiter` | `slowapi` for FastAPI | FastAPI ecosystem shift ~2021 | Same `limits` backend, native FastAPI/Starlette integration |
| `batch_alter_table` in Alembic for SQLite | Direct `op.create_unique_constraint()` for PostgreSQL targets | Alembic 1.7+ | Batch mode needed only for SQLite; Postgres migration files should use direct ops |

**Deprecated/outdated:**
- `ensure_schema_compatibility()` pattern: Replaced by Alembic. This was a SQLite-only workaround. Remove entirely in Phase 1.

---

## Open Questions

1. **Existing plaintext `id_card_no` in dev database**
   - What we know: `wage_adjust.db` has rows with plaintext national IDs that will break when `EncryptedString` TypeDecorator tries to decrypt them.
   - What's unclear: Whether the dev team wants a migration script or is comfortable re-seeding dev data.
   - Recommendation: Plan should include a `Wave 0` task — generate the `NATIONAL_ID_ENCRYPTION_KEY`, add it to `.env`, and run a data migration script that reads all `id_card_no` values, encrypts them, and writes back using the new TypeDecorator. Alternatively, clear all national IDs from dev DB (if test data has no real PII, this is fine).

2. **Redis availability in the test environment**
   - What we know: `redis` is in `requirements.txt` but no Redis server is running locally (confirmed: `redis-server not found`).
   - What's unclear: Whether tests should spin up Redis via `fakeredis` or skip rate-limit tests when Redis is unavailable.
   - Recommendation: Use `fakeredis` for tests that exercise rate limiting. Add `fakeredis` to dev/test dependencies. Or test the rate-limit logic against in-memory fallback and document that Redis integration is tested in staging.

3. **`certification_type` uniqueness scope**
   - What we know: DB-03 says "duplicate imports of same employee+cycle+certification". The `Certification` model has no `cycle_id` column — certifications are not cycle-scoped.
   - What's unclear: Should the unique key be `(employee_id, certification_type)` (one cert per type per employee ever) or `(employee_id, certification_type, issued_at)` (multiple certs of same type if re-issued)?
   - Recommendation: Use `(employee_id, certification_type)` with upsert-update semantics. This matches the CONTEXT.md suggestion and aligns with "re-import should update, not duplicate." If the business ever needs to track cert history, that's a separate `certification_history` table.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x | All backend | Assumed available (venv in `.venv/`) | 3.x (exact version not confirmed via CLI) | None |
| `cryptography` | SEC-03 AES-GCM | Installed as transitive dep of `python-jose[cryptography]` | Not pinned directly | Add explicit pin |
| `redis` (client lib) | SEC-02, SEC-05 rate limiting | `redis==5.2.1` in requirements.txt | 5.2.1 | Already installed |
| `slowapi` | SEC-02, SEC-05 | NOT in requirements.txt | — | Must install: `pip install slowapi==0.1.9` |
| Redis server | SEC-02, SEC-05 (production) | NOT running locally (`redis-server not found`) | — | Dev: in-memory fallback (D-05). Tests: `fakeredis` |
| `alembic` | DB-01, DB-02 | 1.14.0 in requirements.txt | 1.14.0 | Already installed |
| SQLite | Dev database | Available (wage_adjust.db exists) | 3.x | — |

**Missing dependencies with no fallback (production):**
- Redis server — must be running in production (D-05 requires hard-fail if unavailable in production). Plan must document that Redis is a required production service.

**Missing dependencies with fallback (dev/test):**
- `slowapi` — must be added to `requirements.txt`. Fallback: none (code won't run without it).
- Redis server — dev falls back to in-memory limiter (D-05 explicitly allows this).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | none — `pytest` run from project root |
| Quick run command | `pytest backend/tests/test_api/test_auth.py -x` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | Startup raises RuntimeError with placeholder JWT secret in production | unit | `pytest backend/tests/test_core/test_config.py::test_startup_guard_blocks_production -x` | ❌ Wave 0 |
| SEC-02 | Login returns 429 after 10 failed attempts from same IP | integration | `pytest backend/tests/test_api/test_auth.py::test_login_rate_limit -x` | ❌ Wave 0 (add to existing file) |
| SEC-03 | national_id encrypted in DB; masked in non-admin responses | unit + integration | `pytest backend/tests/test_core/test_encryption.py -x` | ❌ Wave 0 |
| SEC-04 | Employee role receives only adjustment_percentage in salary response | integration | `pytest backend/tests/test_api/test_salary_api.py::test_salary_response_role_filtering -x` | ❌ Wave 0 (add to existing file) |
| SEC-05 | Public API returns 429 after exceeding rate limit | integration | `pytest backend/tests/test_api/test_public_api.py::test_public_api_rate_limit -x` | ❌ Wave 0 (add to existing file) |
| SEC-06 | .env not tracked by git | manual | `git ls-files .env` returns empty | manual |
| SEC-07 | Traversal path raises ValueError | unit | `pytest backend/tests/test_core/test_storage.py::test_path_traversal_blocked -x` | ❌ Wave 0 |
| SEC-08 | Weak passwords rejected by backend validator | unit | `pytest backend/tests/test_api/test_auth.py::test_password_complexity -x` | ❌ Wave 0 (add to existing file) |
| DB-01 | Alembic baseline migration file exists and applies cleanly | integration | `pytest backend/tests/test_core/test_database.py::test_alembic_baseline -x` | ❌ Wave 0 (add to existing file) |
| DB-02 | ensure_schema_compatibility not called anywhere | static | `grep -r "ensure_schema_compatibility" backend/` returns no results | manual/static |
| DB-03 | Re-importing same certification does not create duplicate | integration | `pytest backend/tests/test_services/test_import_service.py::test_certification_import_idempotent -x` | ❌ Wave 0 (add to existing file) |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/ -x -q` (full suite, fast since SQLite in-memory)
- **Per wave merge:** `pytest backend/tests/ -v`
- **Phase gate:** Full suite green + `git ls-files .env` empty before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_core/test_config.py` — add `test_startup_guard_blocks_production` and `test_startup_guard_allows_development`
- [ ] `backend/tests/test_core/test_encryption.py` — new file; covers AES-256-GCM encrypt/decrypt/mask roundtrip
- [ ] `backend/tests/test_core/test_storage.py` — new file; covers path traversal guard
- [ ] `backend/tests/test_api/test_auth.py` — add rate limit and password complexity tests; needs `fakeredis` or mock
- [ ] `backend/tests/test_api/test_salary_api.py` — add role-filtering assertions
- [ ] `backend/tests/test_api/test_public_api.py` — add rate limit test
- [ ] `backend/tests/test_services/test_import_service.py` — add idempotency test
- [ ] `backend/tests/test_core/test_database.py` — add alembic baseline test (check migration file exists and is parseable)
- [ ] `fakeredis` or mock strategy for rate limit tests — add to test dependencies

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 1 |
|-----------|-------------------|
| Backend: Python + FastAPI | All changes are backend-only. No frontend. |
| All scores/coefficients/rules must be configurable, not hardcoded | `NATIONAL_ID_ENCRYPTION_KEY` must be in `.env` / `Settings`, not hardcoded |
| All key business results must be auditable, explainable, traceable | Rate limit decisions (429 responses) should log the triggering IP and timestamp |
| API versioning: `/api/v1/...` | All rate-limited routes are already under `/api/v1/` |
| No DDL at startup (this phase establishes the rule) | `ensure_schema_compatibility()` removal is the mechanism |
| Must be stable in PyCharm | No new background threads or daemon processes in application startup |
| `task.json` tracks progress; `progress.txt` tracks session notes | Phase 1 implementation must update both |
| Test before marking task complete | All SEC/DB tasks need passing tests before `passes: true` |

---

## Sources

### Primary (HIGH confidence)
- SQLAlchemy 2.0 docs — TypeDecorator pattern, dialect-specific upsert: https://docs.sqlalchemy.org/en/20/core/custom_types.html
- SQLAlchemy 2.0 SQLite INSERT ON CONFLICT: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#insert-on-conflict
- `cryptography` library AESGCM docs: https://cryptography.io/en/latest/hazmat/primitives/aead/
- Alembic 1.14 autogenerate docs: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- Pydantic v2 field_validator docs: https://docs.pydantic.dev/latest/concepts/validators/
- Python 3.9+ `Path.is_relative_to()`: https://docs.python.org/3/library/pathlib.html#pathlib.Path.is_relative_to
- Codebase reading: all canonical ref files (config.py, database.py, storage.py, auth.py, salary.py, public.py, employee.py, user.py, certification.py, import_service.py, alembic/env.py, alembic.ini)

### Secondary (MEDIUM confidence)
- slowapi documentation and README: https://slowapi.readthedocs.io/en/latest/ — rate limiting pattern, limiter attachment to app.state, Redis backend configuration
- slowapi GitHub (version verification): https://github.com/laurentS/slowapi

### Tertiary (LOW confidence)
- slowapi version 0.1.9 as "latest stable" — based on training knowledge and package registry inference; should be verified with `pip index versions slowapi` before pinning

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are in requirements.txt or have well-documented APIs (cryptography, redis, alembic, pydantic v2)
- Architecture: HIGH — all target files confirmed by direct codebase reading; exact line numbers and code patterns verified
- Pitfalls: HIGH — existing plaintext data issue (pitfall 1), slowapi attachment (pitfall 2) verified by direct code inspection; rate limit semantics (pitfall 4) is a known slowapi limitation
- slowapi version: MEDIUM — confirmed library exists and works with FastAPI; specific 0.1.9 version should be verified

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable libraries — cryptography, alembic, pydantic v2 APIs are stable)
