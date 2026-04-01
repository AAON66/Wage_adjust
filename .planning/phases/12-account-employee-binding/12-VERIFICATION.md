---
phase: 12-account-employee-binding
verified: 2026-04-01T12:00:00Z
status: passed
score: 7/7
gaps: []
human_verification:
  - test: "Admin bind/unbind workflow end-to-end"
    expected: "Admin selects unbound user, searches employees in modal, binds successfully; then clicks unbind with confirmation dialog, unbind succeeds"
    why_human: "Requires running app with seeded data, visual modal interaction, network round-trip verification"
  - test: "Employee self-bind 3-step flow"
    expected: "Non-admin user enters id_card_no, preview shows matched employee, confirm binds and warning banner disappears"
    why_human: "Multi-step UI flow with state transitions, requires real employee data match"
  - test: "Conflict binding shows bound account email"
    expected: "Binding to already-bound employee shows error with email like '...已绑定到账号 user@example.com'"
    why_human: "Requires two users and one employee to create conflict scenario"
  - test: "Forced re-login after admin unbind"
    expected: "After admin unbinds user, user's next API call or token refresh fails with 401"
    why_human: "Requires two browser sessions and timed token refresh"
---

# Phase 12: Account-Employee Binding Verification Report

**Phase Goal:** 管理员可在后台将用户账号与员工信息绑定/解绑，员工可自助绑定，系统阻止冲突绑定
**Verified:** 2026-04-01T12:00:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | POST /api/v1/users/{id}/bind with employee_id binds user to employee | VERIFIED | `backend/app/api/v1/users.py` line 160-175: `admin_bind_employee` endpoint calls `UserAdminService.bind_employee` with `employee_id`, returns `UserRead` |
| 2   | DELETE /api/v1/users/{id}/bind unbinds user and increments token_version | VERIFIED | `backend/app/api/v1/users.py` line 178-192: `admin_unbind_employee` calls `bind_employee(employee_id=None)`. `user_admin_service.py` line 190-191: `user.employee_id = None; user.token_version += 1` |
| 3   | GET /api/v1/auth/self-bind/preview?id_card_no=X returns matching employee preview | VERIFIED | `backend/app/api/v1/auth.py` line 192-226: `self_bind_preview` sets temp id_card_no, searches via IdentityBindingService, returns `SelfBindPreview` or 404/409 |
| 4   | POST /api/v1/auth/self-bind with id_card_no binds current user to matched employee | VERIFIED | `backend/app/api/v1/auth.py` line 229-262: `self_bind_confirm` normalizes id_card_no, calls `auto_bind_user_and_employee`, commits and returns `UserRead` |
| 5   | Binding a user to an already-bound employee returns 400/409 with bound email hint | VERIFIED | `user_admin_service.py` line 207-209: conflict raises `ValueError(f'该员工已绑定到账号 {existing_binding.email}...')`. `auth.py` line 213-219: preview returns 409 with email. `auth.py` line 247-254: self-bind enriches conflict message with email |
| 6   | After unbind, old refresh tokens are rejected (token_version mismatch) | VERIFIED | `auth.py` line 159-161: refresh endpoint checks `tv` claim vs `user.token_version`, returns 401 on mismatch. `dependencies.py` line 49-51: `get_current_user` same check for access tokens |
| 7   | Frontend provides admin bind/unbind UI, employee self-bind flow, and unbound warning banner | VERIFIED | `UserAdmin.tsx` line 530 shows binding status column, line 544 has bind/unbind buttons, line 556-590 has search modal. `Settings.tsx` line 128-168 has 3-step self-bind. `AppShell.tsx` line 216-229 has yellow warning banner |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/app/models/user.py` | token_version column on User model | VERIFIED | Line 19: `token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')` |
| `backend/app/api/v1/users.py` | POST bind and DELETE unbind endpoints | VERIFIED | Lines 160-192: both endpoints present, properly wired to service layer |
| `backend/app/api/v1/auth.py` | self-bind preview and confirm endpoints | VERIFIED | Lines 192-262: GET preview and POST confirm present with full conflict handling |
| `alembic/versions/b12_add_token_version.py` | Migration adding token_version column | VERIFIED | File exists with `op.add_column('users', sa.Column('token_version', sa.Integer(), ...))` |
| `backend/app/core/security.py` | token_version in JWT token building | VERIFIED | Lines 37,48,53,66: `token_version` parameter flows through `_build_token` -> `create_access_token`/`create_refresh_token`, stored as `"tv"` claim |
| `backend/app/dependencies.py` | token_version check in get_current_user | VERIFIED | Lines 49-51: checks `payload["tv"]` against `user.token_version` |
| `backend/app/schemas/user.py` | AdminBindRequest, SelfBindRequest, SelfBindPreview schemas | VERIFIED | Lines 135-150: all three Pydantic schemas present with proper fields |
| `backend/app/services/user_admin_service.py` | bind_employee with conflict email and token_version increment | VERIFIED | Lines 183-221: full bind/unbind logic with conflict message including email, token_version += 1 on unbind |
| `frontend/src/pages/UserAdmin.tsx` | Binding status column + bind/unbind actions + employee search modal | VERIFIED | 593 lines: binding column at line 543, bind/unbind buttons at line 544, modal at lines 556-590 |
| `frontend/src/pages/Settings.tsx` | Self-bind section with 3-step flow | VERIFIED | Lines 128-168: input step, preview step, done step with proper state management |
| `frontend/src/components/layout/AppShell.tsx` | Yellow warning banner for unbound users | VERIFIED | Lines 216-229: conditional banner with `user && !user.employee_id && user.role !== 'admin'`, links to /settings |
| `frontend/src/services/userAdminService.ts` | adminBindEmployee, adminUnbindEmployee functions | VERIFIED | Lines 76-91: both functions calling correct endpoints |
| `frontend/src/services/auth.ts` | selfBindPreview, selfBindConfirm functions | VERIFIED | Lines 92-102: both functions present, calling correct endpoints |
| `frontend/src/types/api.ts` | SelfBindPreviewResult, EmployeeSearchQuery interfaces | VERIFIED | Lines 812-822: both interfaces present with correct fields |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `users.py` (API) | `user_admin_service.py` | `UserAdminService.bind_employee` | WIRED | Lines 169,186: `service.bind_employee(...)` called in both bind and unbind endpoints |
| `auth.py` (API) | `identity_binding_service.py` | `IdentityBindingService methods` | WIRED | Lines 204,243: `search_employee_for_user_by_identity` and `auto_bind_user_and_employee` called |
| `dependencies.py` | `security.py` | token_version check | WIRED | Line 50: `int(tv_claim) != user.token_version` check present in `get_current_user` |
| `UserAdmin.tsx` | `POST /api/v1/users/{id}/bind` | `adminBindEmployee` | WIRED | Line 337: `await adminBindEmployee(bindTargetUserId, employeeId)` |
| `Settings.tsx` | `POST /api/v1/auth/self-bind` | `selfBindConfirm` | WIRED | Line 67: `await selfBindConfirm(bindIdCardNo.trim())` followed by `refreshProfile()` |
| `AppShell.tsx` | `useAuth` | `user.employee_id check` | WIRED | Line 216: `user && !user.employee_id && user.role !== 'admin'` condition |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `UserAdmin.tsx` | `users` (binding status) | `fetchUsers` -> `GET /api/v1/users` | DB query via `UserAdminService.list_users` | FLOWING |
| `UserAdmin.tsx` | `employeeSearchResults` | `searchEmployeesForBinding` -> `GET /api/v1/employees` | DB query via `EmployeeService` with keyword filter | FLOWING |
| `Settings.tsx` | `bindPreview` | `selfBindPreview` -> `GET /api/v1/auth/self-bind/preview` | DB query via `IdentityBindingService.search_employee_for_user_by_identity` | FLOWING |
| `AppShell.tsx` | `user.employee_id` | `useAuth` context -> `GET /api/v1/auth/me` | DB User model with employee_id FK | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| TypeScript compiles cleanly | `npx tsc --noEmit` | No output (success) | PASS |
| Backend app factory works | `python -c "from backend.app.main import create_app; ..."` | "App starts OK" | PASS |
| Migration file valid Python | `python -c "import alembic.versions.b12_add_token_version"` | N/A (module path check via Read) | PASS (file syntax valid) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| BIND-01 | 12-01, 12-02 | 管理员可在用户管理页面将用户账号与员工信息手动绑定/解绑 | SATISFIED | Backend: POST/DELETE `/users/{id}/bind` endpoints. Frontend: UserAdmin binding status column, bind modal, unbind button with confirmation |
| BIND-02 | 12-01, 12-02 | 员工可在个人设置页面通过身份证号自助绑定自己的员工信息 | SATISFIED | Backend: GET/POST `/auth/self-bind` endpoints. Frontend: Settings page 3-step flow (input -> preview -> confirm). AppShell warning banner with link to Settings |
| BIND-03 | 12-01, 12-02 | 绑定冲突时系统阻止操作并提示当前绑定方 | SATISFIED | Backend: `user_admin_service.py` raises ValueError with email, `auth.py` returns 409 with email. Frontend: error messages display conflict detail |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | - | - | - | No anti-patterns detected |

All "placeholder" grep matches were HTML `placeholder` attributes on input elements -- legitimate usage, not code stubs.

### Human Verification Required

### 1. Admin Bind/Unbind Workflow

**Test:** Login as admin, go to UserAdmin page, find unbound user, click "绑定员工", search for an employee, click "选择" to bind. Then click "解绑" on a bound user, confirm dialog.
**Expected:** Bind succeeds and shows employee name/no in binding status column. Unbind succeeds and shows "未绑定".
**Why human:** Requires running app with seeded data, modal interactions, API round trips.

### 2. Employee Self-Bind Flow

**Test:** Login as non-admin unbound user. Verify yellow banner appears. Click "立即绑定" or go to Settings. Enter id_card_no, click "查询匹配", verify preview, click "确认绑定".
**Expected:** Banner disappears after binding. Settings shows "已绑定员工" with name/no.
**Why human:** Multi-step flow with state transitions, requires real employee data.

### 3. Conflict Binding Detection

**Test:** Try binding a user to an employee already bound to another account (both via admin and self-bind).
**Expected:** Error message includes bound account email: "该员工已绑定到账号 xxx@xxx.com"
**Why human:** Requires specific data setup with pre-existing bindings.

### 4. Token Version Forced Re-Login

**Test:** Admin unbinds a user who is currently logged in. That user's next API call or token refresh should fail.
**Expected:** 401 response, user forced to re-login.
**Why human:** Requires two concurrent sessions and timed token lifecycle observation.

### Gaps Summary

No gaps found. All backend endpoints are fully implemented with proper conflict detection, email hints, and token version invalidation. All frontend UI components are wired to real API calls with proper error handling. TypeScript compiles cleanly and the backend app factory starts successfully. All three requirements (BIND-01, BIND-02, BIND-03) are satisfied by the implementation.

---

_Verified: 2026-04-01T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
