---
phase: 01-security-hardening-and-schema-integrity
plan: 03
subsystem: auth
tags: [slowapi, redis, rate-limiting, startup-guard, fastapi, jwt]

requires:
  - phase: 01-01
    provides: Alembic baseline, schema stubs, migration foundation
  - phase: 01-02
    provides: Encryption, path guard, password complexity

provides:
  - Startup guard (validate_startup_config) blocking production launch with placeholder secrets or unreachable Redis
  - Shared rate_limit.py module with create_limiter() and module-level limiter instance
  - Login failed-attempt counter via Redis INCR (10 attempts / 15 min) with graceful dev fallback
  - slowapi @limiter.limit decorator on all 4 public API routes

affects:
  - Phase 01-04 (PII filtering/role-aware salary responses — same main.py)
  - Phase 01-05 (any remaining security hardening)

tech-stack:
  added:
    - slowapi 0.1.9 (already in requirements.txt; installed but not previously wired)
    - limits (transitive dependency of slowapi)
  patterns:
    - Shared Limiter module pattern: single rate_limit.py creates the module-level limiter for decorator use; create_limiter() builds Redis-backed instance at app startup
    - Module-level redis_lib import alias in main.py for clean mock-patching in tests
    - StaticPool SQLAlchemy pattern for in-memory DB sharing across connections in TestClient tests

key-files:
  created:
    - backend/app/core/rate_limit.py
    - (test) backend/tests/test_core/test_startup_guard.py (replaced xfail stubs with 5 real tests)
    - (test) backend/tests/test_api/test_rate_limit.py (replaced xfail stubs with 2 real tests)
    - (test) backend/tests/test_api/test_public_rate_limit.py (replaced xfail stub with 2 real tests)
  modified:
    - backend/app/main.py (validate_startup_config, create_limiter wiring, redis_lib import)
    - backend/app/api/v1/auth.py (request: Request param, Redis failed-attempt counter helpers)
    - backend/app/api/v1/public.py (limiter import from rate_limit, @limiter.limit decorators, request: Request on 4 routes)

key-decisions:
  - "Shared Limiter in rate_limit.py: module-level instance used for @limiter.limit decoration; create_limiter() builds Redis-backed instance and attaches to app.state.limiter at app creation time — single backend for both auth and public routes"
  - "validate_startup_config raises RuntimeError only in production; development is permissive (log warning for placeholder secrets, no Redis check)"
  - "Login rate limiting is counter-only (not slowapi decorator): Redis INCR key=login_failed:{ip} with 15-min TTL; graceful fallback to no-op when Redis unavailable in dev"
  - "StaticPool required for TestClient tests using in-memory SQLite: ensures all connections share same DB, fixing 'no such table' errors from per-connection in-memory isolation"

patterns-established:
  - "Startup guard pattern: validate_startup_config(settings) in lifespan, before any DB/LLM init, raises RuntimeError on bad production config"
  - "Redis graceful degradation: try ping in dev, warn + use in-memory fallback; production requires Redis (enforced by startup guard)"
  - "slowapi route decoration order: @router.get/post FIRST, @limiter.limit SECOND (inner decorator applied first)"

requirements-completed: [SEC-01, SEC-02, SEC-05]

duration: 8min
completed: 2026-03-26
---

# Phase 01 Plan 03: Startup Guard + slowapi Rate Limiting Summary

**slowapi rate limiter wired on public API routes and Redis failed-attempt counter on login; production startup guard blocks launch with placeholder secrets or unreachable Redis**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-26T00:53:34Z
- **Completed:** 2026-03-26T01:01:29Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 7 (3 new, 4 modified)

## Accomplishments

- Created `backend/app/core/rate_limit.py` with shared `Limiter` instance and `create_limiter()` that uses Redis in production, falls back to in-memory in dev
- Added `validate_startup_config()` to `main.py`: hard-fails in production for placeholder `jwt_secret_key`, `public_api_key`, or unreachable Redis
- Wired Redis INCR failed-attempt counter on login endpoint (10 failures / 15 min = HTTP 429; success resets counter)
- Applied `@limiter.limit(_RATE_LIMIT)` decorator to all 4 `/api/v1/public/` route functions using shared limiter
- 9 total tests passing (5 startup guard + 2 rate limit + 2 public rate limit)

## Task Commits

Each task was committed atomically:

1. **Task 1: Startup guard and rate_limit.py** - `e5ffa54` (feat)
2. **Task 2: Login rate limiting + public API decorators** - `70987cd` (feat)

_Note: TDD tasks — both followed RED (failing tests) → GREEN (passing) cycle_

## Files Created/Modified

- `backend/app/core/rate_limit.py` - Shared Limiter module; `create_limiter()` with Redis/in-memory fallback; module-level `limiter` for decorator binding
- `backend/app/main.py` - Added `validate_startup_config()`, `import redis as redis_lib`, `create_limiter()` wiring in `create_app()`, `RateLimitExceeded` handler
- `backend/app/api/v1/auth.py` - Added `request: Request` to `login_user`, Redis failed-attempt counter helpers (`_get_redis_client`, `_check_and_increment_failed_login`, `_reset_failed_login`)
- `backend/app/api/v1/public.py` - Import shared `limiter` from `rate_limit.py`; `@limiter.limit(_RATE_LIMIT)` and `request: Request` on all 4 route functions
- `backend/tests/test_core/test_startup_guard.py` - 5 tests replacing xfail stubs; mock Redis via `patch('backend.app.main.redis_lib')`
- `backend/tests/test_api/test_rate_limit.py` - 2 tests replacing xfail stubs; MagicMock Redis injection; StaticPool for in-memory DB sharing
- `backend/tests/test_api/test_public_rate_limit.py` - 2 tests replacing xfail stub; inspects route signatures and source file

## Decisions Made

- Used shared `rate_limit.py` module (one Limiter = one Redis backend) to avoid two independent rate limit stores
- Login rate limiting uses manual Redis INCR (not slowapi decorator) to control the condition: only increment on authentication failure, not on every request
- Production startup requires Redis reachability (D-05): enforced via `validate_startup_config`, not just a runtime warning
- StaticPool pattern established for all future TestClient tests requiring in-memory SQLite with session-sharing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed slowapi (module not importable)**
- **Found during:** Task 1 (creating rate_limit.py)
- **Issue:** `slowapi` was in `requirements.txt` but not installed in the virtualenv
- **Fix:** Ran `python -m pip install slowapi` in the project venv
- **Files modified:** None (runtime install only; requirements.txt already correct)
- **Verification:** `python -c "import slowapi"` succeeded
- **Committed in:** e5ffa54 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test using wrong SessionLocal sharing pattern**
- **Found during:** Task 2 (test_successful_login_does_not_count_against_limit)
- **Issue:** `create_session_factory(settings)` creates its own engine internally; the `Base.metadata.create_all(engine)` and the session factory pointed at different in-memory SQLite connections (each connection = empty DB)
- **Fix:** Use SQLAlchemy `StaticPool` with a single engine shared between `create_all()` and `sessionmaker(bind=engine)`, and override `get_db` with a proper generator yielding from that engine
- **Files modified:** backend/tests/test_api/test_rate_limit.py
- **Verification:** Test passes — login succeeds, `_reset_failed_login` called once
- **Committed in:** 70987cd (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both were blocking correctness. No scope creep.

## Issues Encountered

- SQLite in-memory DB per-connection isolation: each `create_engine('sqlite:///:memory:')` call without `StaticPool` creates a separate empty database. Tests that write data in one connection and read in another need `StaticPool` to share state. Established as a project test pattern going forward.

## Next Phase Readiness

- Phase 01-04 (role-aware salary response filtering / PII masking) can proceed — main.py is stable
- All SEC-01, SEC-02, SEC-05 requirements satisfied
- No blockers for Wave 3 plans

## Self-Check: PASSED

- FOUND: backend/app/core/rate_limit.py
- FOUND: backend/app/main.py (validate_startup_config, create_limiter, redis_lib import)
- FOUND: backend/app/api/v1/auth.py (login rate limiting)
- FOUND: backend/app/api/v1/public.py (@limiter.limit on 4 routes)
- FOUND: .planning/phases/01-security-hardening-and-schema-integrity/01-03-SUMMARY.md
- FOUND commit: e5ffa54 (Task 1)
- FOUND commit: 70987cd (Task 2)

---
*Phase: 01-security-hardening-and-schema-integrity*
*Completed: 2026-03-26*
