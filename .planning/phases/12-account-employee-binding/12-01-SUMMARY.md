---
phase: 12-account-employee-binding
plan: 01
subsystem: auth
tags: [jwt, token-version, binding, fastapi, sqlalchemy, alembic]

requires:
  - phase: 01-security-hardening
    provides: JWT auth infrastructure, User model with employee_id FK
provides:
  - token_version column on User model for JWT invalidation
  - POST /api/v1/users/{id}/bind admin binding endpoint
  - DELETE /api/v1/users/{id}/bind admin unbinding endpoint with token invalidation
  - GET /api/v1/auth/self-bind/preview employee self-bind preview
  - POST /api/v1/auth/self-bind employee self-bind confirmation
  - Alembic migration b12a00000001 for token_version column
affects: [12-account-employee-binding]

tech-stack:
  added: []
  patterns: [token-version-based JWT invalidation]

key-files:
  created:
    - alembic/versions/b12_add_token_version.py
  modified:
    - backend/app/models/user.py
    - backend/app/core/security.py
    - backend/app/dependencies.py
    - backend/app/api/v1/auth.py
    - backend/app/api/v1/users.py
    - backend/app/schemas/user.py
    - backend/app/services/user_admin_service.py

key-decisions:
  - "token_version approach for JWT invalidation: increment on unbind, include in JWT 'tv' claim, validate on each request"
  - "Backward compatible: old tokens without 'tv' claim still pass validation (skip check)"
  - "Conflict messages include bound account email per D-05 decision"

patterns-established:
  - "Token version pattern: user.token_version stored in JWT as 'tv', checked in get_current_user and refresh_tokens"

requirements-completed: [BIND-01, BIND-02, BIND-03]

duration: 5min
completed: 2026-04-01
---

# Phase 12 Plan 01: Account-Employee Binding API Summary

**4 binding API endpoints with token_version-based JWT invalidation for forced re-login on unbind**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-01T06:35:02Z
- **Completed:** 2026-04-01T06:39:37Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added token_version column to User model with Alembic migration, enabling per-user JWT invalidation
- Implemented 4 new API endpoints: admin bind, admin unbind, self-bind preview, and self-bind confirm
- Conflict detection returns bound account email in error messages per D-05 design decision
- Unbind operation increments token_version, causing old tokens to be rejected on next request or refresh

## Task Commits

Each task was committed atomically:

1. **Task 1: Add token_version column + token invalidation logic + migration** - `c7bb94f` (feat)
2. **Task 2: Create 4 binding API endpoints with conflict email hint** - `1ad750c` (feat)

## Files Created/Modified
- `backend/app/models/user.py` - Added token_version column (Integer, default 0)
- `backend/app/core/security.py` - Added token_version parameter to _build_token, create_access_token, create_refresh_token
- `backend/app/dependencies.py` - Added token_version validation in get_current_user
- `backend/app/api/v1/auth.py` - Added self-bind preview/confirm endpoints, token_version in all token generation
- `backend/app/api/v1/users.py` - Added admin bind/unbind endpoints
- `backend/app/schemas/user.py` - Added AdminBindRequest, SelfBindRequest, SelfBindPreview schemas
- `backend/app/services/user_admin_service.py` - Increment token_version on unbind, email in conflict message
- `alembic/versions/b12_add_token_version.py` - Migration adding token_version column

## Decisions Made
- Used token_version integer increment approach (not token blacklist) for JWT invalidation -- simpler, no Redis dependency
- Backward compatible: tokens without "tv" claim skip validation, so existing sessions are unaffected
- Conflict messages include bound account email directly in the error detail string

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 4 API endpoints ready for frontend integration in plan 12-02
- token_version mechanism ready for use by any future unbind/role-change scenarios

## Self-Check: PASSED

- All 9 key files verified present
- Commit c7bb94f (Task 1) verified in git log
- Commit 1ad750c (Task 2) verified in git log

---
*Phase: 12-account-employee-binding*
*Completed: 2026-04-01*
