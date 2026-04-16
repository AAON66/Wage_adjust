# Architecture Research

**Domain:** Feishu OAuth2 Login Integration + Login Page Redesign (v1.3)
**Researched:** 2026-04-16
**Confidence:** HIGH — Official Feishu Open Platform docs verified; entire existing auth codebase read directly

---

## Standard Architecture

### System Overview — Feishu OAuth2 Integration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React SPA)                            │
├────────────────────────────────┬────────────────────────────────────────┤
│  LoginPage (redesigned)        │  FeishuOAuthCallback (new route)        │
│  ┌──────────────┐  ┌─────────┐ │  Receives ?code=&state= from Feishu    │
│  │ PasswordForm │  │FeishuQR │ │  Calls POST /auth/feishu/callback       │
│  │ (unchanged)  │  │ Panel   │ │  Stores JWT, redirects to role home     │
│  └──────────────┘  └────┬────┘ │                                         │
│  ParticleCanvas (bg)    │      │                                         │
└─────────────────────────┼───────────────────────────────────────────────┘
                          │ Browser redirect: ?code=AUTH_CODE&state=...
┌─────────────────────────▼───────────────────────────────────────────────┐
│                    FastAPI Backend  /api/v1/auth/                        │
├─────────────────────────────────────────────────────────────────────────┤
│  NEW: POST /auth/feishu/callback                                         │
│    ├── FeishuOAuthService.exchange_code_for_user_token(code)             │
│    │     POST open.feishu.cn/open-apis/authen/v2/oauth/token             │
│    ├── FeishuOAuthService.get_feishu_user_info(user_access_token)        │
│    │     GET  open.feishu.cn/open-apis/authen/v1/user_info               │
│    ├── Resolve Employee by employee_no  (existing Employee model)        │
│    ├── Resolve / create system User bound to employee                    │
│    └── Return TokenPair  (existing create_access_token/refresh_token)   │
│                                                                          │
│  NEW: GET /auth/feishu/web-url                                           │
│    └── Returns { url } for redirect-style (no QR) authorization         │
│                                                                          │
│  EXISTING (unchanged): POST /auth/login, POST /auth/refresh, GET /auth/me│
└─────────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────┐
│                    Feishu Open Platform APIs                              │
│  Auth URL:   https://passport.feishu.cn/suite/passport/oauth/authorize   │
│  Token API:  https://open.feishu.cn/open-apis/authen/v2/oauth/token      │
│  User Info:  https://open.feishu.cn/open-apis/authen/v1/user_info        │
│  QR SDK CDN: https://lf-package-cn.feishucdn.com/obj/feishu-static/...   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Two Login Modes Converge at One Endpoint

**Mode A — QR Code Scan (recommended for enterprise):**
1. Frontend loads Feishu QR SDK via `<script>` CDN tag
2. SDK renders QR iframe inside a `<div>` container using the `goto` URL
3. User scans QR with Feishu mobile app
4. SDK fires `window.postMessage` with `{ tmp_code }`
5. Frontend appends `tmp_code` to `goto` URL and browser redirects to Feishu
6. Feishu validates scan, redirects browser to `redirect_uri?code=AUTH_CODE&state=...`
7. `FeishuOAuthCallback` page sends `code` to backend

**Mode B — Web Authorization (browser already logged into Feishu):**
1. Frontend navigates browser to Feishu authorization URL directly (from `GET /auth/feishu/web-url`)
2. User clicks "Authorize" on Feishu consent page
3. Feishu redirects to `redirect_uri?code=AUTH_CODE&state=...`
4. Same `FeishuOAuthCallback` flow from here

Both modes end at `POST /api/v1/auth/feishu/callback`.

---

## Component Boundaries

### New Backend Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `FeishuOAuthService` | `backend/app/services/feishu_oauth_service.py` | Exchange `code` for `user_access_token`; call `/authen/v1/user_info`; resolve `employee_no` to system `User`; issue JWT |
| Feishu Auth Router | `backend/app/api/v1/feishu_auth.py` | `GET /auth/feishu/web-url` and `POST /auth/feishu/callback` |
| Feishu Auth Schemas | `backend/app/schemas/feishu_auth.py` | `FeishuCallbackRequest`, `FeishuWebUrlResponse` |

### New Frontend Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `FeishuQRPanel` | `frontend/src/components/auth/FeishuQRPanel.tsx` | Loads QR SDK script, renders QR container, listens to `postMessage`, triggers redirect to Feishu authorize URL |
| `FeishuOAuthCallback` | `frontend/src/pages/FeishuOAuthCallback.tsx` | Route at `/auth/feishu/callback`; parses `?code=&state=`; validates state; calls backend; stores JWT; navigates to role home |
| `ParticleCanvas` | `frontend/src/components/auth/ParticleCanvas.tsx` | `<canvas>` with animated particle system; absolute-positioned behind login layout; self-contained animation loop with cleanup |
| `feishuAuthService.ts` | `frontend/src/services/feishuAuthService.ts` | `getFeishuWebUrl()`, `exchangeFeishuCode(code, state)` — wraps backend calls |

### Existing Components Modified

| Component | What Changes | What Does Not Change |
|-----------|-------------|----------------------|
| `frontend/src/pages/Login.tsx` | Layout → left/right split; right panel gets `FeishuQRPanel`; `ParticleCanvas` added as background | `handleLogin`, `LoginForm`, error handling, navigation logic — all untouched |
| `frontend/src/App.tsx` | Add route `/auth/feishu/callback` → `FeishuOAuthCallback` | All other routes unchanged |
| `backend/app/core/config.py` | Add `feishu_app_id`, `feishu_app_secret`, `feishu_redirect_uri` settings | All existing settings unchanged |
| `backend/app/api/v1/__init__.py` | Include `feishu_auth` router under `/auth` prefix | All existing routers unchanged |

### Existing Components Untouched

- `backend/app/core/security.py` — `create_access_token`, `create_refresh_token`, `decode_token` used as-is
- `backend/app/api/v1/auth.py` — password login unchanged; `_build_auth_response` helper reusable
- `backend/app/services/feishu_service.py` — bitable sync service; different concern; not modified
- `backend/app/models/user.py` — existing `User` model sufficient (see optional migration note below)
- `backend/app/models/employee.py` — `employee_no` field already exists
- `frontend/src/hooks/useAuth.tsx` — `AuthContext`, `login`, `logout`, bootstrap unchanged
- `frontend/src/services/auth.ts` — `storeAuthSession`, `clearAuthStorage`, `AUTH_SESSION_EVENT` reused
- `frontend/src/components/auth/LoginForm.tsx` — unchanged

---

## Data Flow

### Feishu OAuth2 Callback (Happy Path)

```
User scans QR code
    → Feishu redirects browser to: /auth/feishu/callback?code=AUTH_CODE&state=STATE
        ↓
FeishuOAuthCallback.tsx
    ├── Read state from sessionStorage('feishu_oauth_state')
    ├── Validate: URL state === sessionStorage state  (CSRF guard — abort if mismatch)
    ├── Clear sessionStorage('feishu_oauth_state')
    └── POST /api/v1/auth/feishu/callback { code }
              ↓
    feishu_auth.py  →  FeishuOAuthService.handle_callback(code)
              ├── POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
              │     { grant_type, client_id, client_secret, code, redirect_uri }
              │     Response: { access_token: user_access_token, expires_in }
              │
              ├── GET https://open.feishu.cn/open-apis/authen/v1/user_info
              │     Authorization: Bearer <user_access_token>
              │     Response: { employee_no, open_id, name, email, ... }
              │
              ├── employee = db.scalar(Employee).where(employee_no == feishu_employee_no)
              │     NO MATCH → HTTP 404 "员工工号未在系统中找到，请联系HR"
              │
              ├── user = employee.bound_user
              │     BOUND   → reuse existing User
              │     UNBOUND → auto-create User with random password, auto-bind to employee
              │               (token_version=0, must_change_password=False)
              │
              └── return TokenPair (create_access_token + create_refresh_token)
                        ↓
    FeishuOAuthCallback.tsx
              ├── GET /api/v1/auth/me  (fetch full UserProfile)
              ├── storeAuthSession({ user: profile, tokens })  (localStorage + event)
              └── navigate(getRoleHomePath(profile.role), { replace: true })
```

### State Parameter (CSRF Protection) Lifetime

```
FeishuQRPanel mounts
    → state = crypto.randomUUID()
    → sessionStorage.setItem('feishu_oauth_state', state)
    → goto URL includes &state=<state>

User scans → Feishu sends browser to /auth/feishu/callback?code=...&state=<state>

FeishuOAuthCallback mounts
    → stored = sessionStorage.getItem('feishu_oauth_state')
    → if url.state !== stored: show error, stop
    → sessionStorage.removeItem('feishu_oauth_state')
    → proceed with backend call
```

---

## Recommended Project Structure Changes

```
backend/app/
├── api/v1/
│   ├── auth.py                      EXISTING — untouched
│   └── feishu_auth.py               NEW — 2 endpoints
├── services/
│   ├── feishu_service.py            EXISTING — bitable sync, untouched
│   └── feishu_oauth_service.py      NEW — OAuth2 user login only
├── schemas/
│   ├── user.py                      EXISTING — reuse AuthResponse, TokenPair
│   └── feishu_auth.py               NEW — FeishuCallbackRequest, FeishuWebUrlResponse
└── core/
    └── config.py                    MODIFIED — add feishu_app_id, feishu_app_secret, feishu_redirect_uri

frontend/src/
├── pages/
│   ├── Login.tsx                    MODIFIED — layout + canvas + right Feishu panel
│   └── FeishuOAuthCallback.tsx      NEW — ?code= handler route
├── components/auth/
│   ├── LoginForm.tsx                EXISTING — untouched
│   ├── FeishuQRPanel.tsx            NEW — QR SDK embed
│   └── ParticleCanvas.tsx           NEW — canvas animation
├── services/
│   └── feishuAuthService.ts         NEW — feishu backend calls
└── App.tsx                          MODIFIED — add /auth/feishu/callback route
```

### Structure Rationale

- `feishu_oauth_service.py` is a separate file from `feishu_service.py`. The existing service manages bitable data sync using `tenant_access_token`; OAuth login uses `user_access_token` for a fundamentally different purpose. Merging them would create a ~1200-line god class with two unrelated concerns.
- `FeishuOAuthCallback.tsx` is a page (not a component) because it handles a browser redirect — it needs its own route entry in `App.tsx`.
- `ParticleCanvas.tsx` is isolated to encapsulate the animation loop's `requestAnimationFrame` + `useEffect` cleanup without polluting the login page component.

---

## Architectural Patterns

### Pattern 1: Client Secret Never Leaves the Backend

**What:** `client_id` appears in the frontend (embedded in the `goto` URL and QR `goto` parameter — this is public). `client_secret` never appears in frontend code. The code-for-token exchange (`POST /authen/v2/oauth/token`) is always a server-to-server call.

**Why:** Standard OAuth2 security. The existing `FeishuService._ensure_token()` follows this pattern for `tenant_access_token`. OAuth login must follow the same discipline.

```python
# feishu_oauth_service.py — server-to-server only
def exchange_code_for_user_token(self, code: str) -> str:
    settings = get_settings()
    resp = httpx.post(
        'https://open.feishu.cn/open-apis/authen/v2/oauth/token',
        json={
            'grant_type': 'authorization_code',
            'client_id': settings.feishu_app_id,
            'client_secret': settings.feishu_app_secret,
            'code': code,
            'redirect_uri': settings.feishu_redirect_uri,
        },
        timeout=10,
    )
    data = resp.json()
    if data.get('code') != 0:
        raise HTTPException(status_code=400, detail=f'飞书授权失败: {data.get("msg")}')
    return data['access_token']
```

### Pattern 2: Reuse Existing JWT Infrastructure Unchanged

**What:** After resolving the Feishu user to a system `User`, call `create_access_token` and `create_refresh_token` from `security.py` with identical arguments as the password login endpoint. Return `TokenPair` — same schema.

**Why:** `token_version` invalidation, `decode_token` validation in `get_current_user`, and all downstream RBAC work without modification. The frontend `storeAuthSession` function accepts any `TokenPair` — it does not know or care how the user authenticated.

```python
# feishu_auth.py
@router.post('/feishu/callback', response_model=TokenPair)
def feishu_callback(
    payload: FeishuCallbackRequest,
    db: Session = Depends(get_db),
    settings=Depends(get_app_settings),
) -> TokenPair:
    service = FeishuOAuthService(db)
    user = service.handle_callback(payload.code)  # raises HTTP 4xx on failure
    return TokenPair(
        access_token=create_access_token(
            user.id, role=user.role, settings=settings, token_version=user.token_version
        ),
        refresh_token=create_refresh_token(
            user.id, role=user.role, settings=settings, token_version=user.token_version
        ),
    )
```

### Pattern 3: Employee Resolution by employee_no

**What:** After Feishu returns user info, look up `Employee` by `employee_no`. Traverse to `employee.bound_user`. Issue JWT for that `User`.

**Why:** `employee_no` is the canonical cross-system identifier. Feishu's `/authen/v1/user_info` returns `employee_no` when the app has the "获取用户受雇信息" scope. No new model fields required — this mirrors how `FeishuService._build_employee_map()` already resolves employees in bitable sync. The leading-zero handling pattern from `FeishuService._lookup_employee()` should be reused.

**Auto-create policy:** If `employee.bound_user is None`, auto-create a `User` with `role='employee'`, random UUID password hash, and bind to the employee. This allows any Feishu user who has an employee record to log in immediately without admin pre-provisioning. Emit an audit log entry for traceability.

### Pattern 4: FeishuOAuthCallback Does Not Use useAuth.login()

**What:** `FeishuOAuthCallback` calls `feishuAuthService.exchangeFeishuCode(code)` directly, gets a `TokenPair`, calls `fetchCurrentUser` to get `UserProfile`, then calls `storeAuthSession({user, tokens})` and dispatches `AUTH_SESSION_EVENT`.

**Why:** `useAuth.login()` accepts email+password and calls `/auth/login`. The callback page is a one-shot redirect handler. Adding an OAuth path to `AuthContext` would make it asymmetric. The `storeAuthSession` + `AUTH_SESSION_EVENT` pattern already exists and is the correct integration point — the `AuthContext` bootstrap will pick up the session without any changes.

```typescript
// FeishuOAuthCallback.tsx — correct approach
const code = searchParams.get('code');
const state = searchParams.get('state');
const stored = sessionStorage.getItem('feishu_oauth_state');
if (!code || !state || state !== stored) { setError('授权失败'); return; }
sessionStorage.removeItem('feishu_oauth_state');

const tokens = await feishuAuthService.exchangeFeishuCode(code);
const profile = await fetchCurrentUser(tokens.access_token);
storeAuthSession({ user: profile, tokens });        // fires AUTH_SESSION_EVENT
navigate(getRoleHomePath(profile.role), { replace: true });
```

---

## Integration Points

### Feishu Open Platform (External)

| Step | Method | URL | Auth | Notes |
|------|--------|-----|------|-------|
| Authorize (browser redirect) | GET | `https://passport.feishu.cn/suite/passport/oauth/authorize` | None | `client_id`, `response_type=code`, `redirect_uri`, `state` as query params |
| Exchange code for user token | POST | `https://open.feishu.cn/open-apis/authen/v2/oauth/token` | `client_id` + `client_secret` in body | Returns `access_token` (user_access_token); valid ~6900s |
| Get user info | GET | `https://open.feishu.cn/open-apis/authen/v1/user_info` | Bearer user_access_token | Returns `employee_no`, `open_id`, `name`, `email`. Requires "获取用户受雇信息" scope |
| QR SDK (frontend) | `<script>` | `https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js` | None | `QRLogin({id, goto, width, height})` → `window.postMessage` with `{tmp_code}` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `feishu_auth.py` → `FeishuOAuthService` | Direct call, same process | Service raises `HTTPException` directly on failures (matching existing service pattern) |
| `FeishuOAuthService` → `Employee` model | SQLAlchemy `select` via injected `Session` | Reuse leading-zero tolerance from `FeishuService._lookup_employee()` |
| `FeishuOAuthService` → `User` model | SQLAlchemy query + optional insert via `Session` | Traverse `employee.bound_user`; auto-create if None |
| `FeishuOAuthService` → `security.py` | Import `create_access_token`, `create_refresh_token` | No change to these functions |
| `FeishuOAuthService` → Feishu APIs | `httpx.post` / `httpx.get` | Same client as existing `FeishuService._ensure_token()` |
| `FeishuQRPanel.tsx` → Feishu QR SDK | `window.postMessage` listener | SDK loaded via dynamic `<script>` append in `useEffect`; `removeEventListener` in cleanup |
| `FeishuOAuthCallback.tsx` → `auth.ts` | Import `storeAuthSession`, `fetchCurrentUser` | Reuse existing storage helpers directly |

---

## New Settings Required

Add to `backend/app/core/config.py`:

```python
feishu_app_id: str = ''
feishu_app_secret: str = ''
feishu_redirect_uri: str = 'http://localhost:5174/auth/feishu/callback'
```

Add to `.env.example`:

```
FEISHU_APP_ID=cli_your_app_id
FEISHU_APP_SECRET=your_app_secret_here
FEISHU_REDIRECT_URI=https://yourdomain.com/auth/feishu/callback
```

The `feishu_app_secret` lives in `.env` settings (not encrypted in the DB). This matches how `jwt_secret_key` and other auth secrets are stored — environment-level secrets. The existing `FeishuConfig.encrypted_app_secret` column is for bitable sync and may belong to a different app configuration.

Note: `feishu_app_id` and `feishu_app_secret` may point to the same Feishu app as the bitable sync config, or a separate app — depending on how the admin configures Feishu permissions. They are independent settings in our system regardless.

---

## Optional Alembic Migration

If `feishu_open_id` should be stored on the User model for audit and future reference:

```python
# backend/app/models/user.py addition
feishu_open_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True, index=True)
```

Migration: `alembic revision --autogenerate -m "add_feishu_open_id_to_users"`

This is optional. The core flow works without it — `open_id` only needs to be stored if we want to support "find existing user by open_id to skip employee_no lookup on repeat logins" as a future optimization.

---

## Build Order (Phase Dependencies)

```
Phase 1 — Backend service + endpoint (no frontend dependency, testable with curl)
    1a. config.py: add feishu_app_id, feishu_app_secret, feishu_redirect_uri
    1b. schemas/feishu_auth.py: FeishuCallbackRequest, FeishuWebUrlResponse
    1c. services/feishu_oauth_service.py: exchange_code, get_user_info, resolve_user
    1d. api/v1/feishu_auth.py: POST /auth/feishu/callback + GET /auth/feishu/web-url
    1e. api/v1/__init__.py: include feishu_auth router
    1f. (optional) alembic migration for feishu_open_id

Phase 2 — Frontend callback route (depends on Phase 1 endpoint)
    2a. FeishuOAuthCallback.tsx: parse ?code=&state=, validate, call backend, store JWT
    2b. App.tsx: add /auth/feishu/callback route
    2c. feishuAuthService.ts: exchangeFeishuCode(), getFeishuWebUrl()

Phase 3 — Frontend QR panel (depends on Phase 1 config for goto URL)
    3a. FeishuQRPanel.tsx: load SDK, build goto, postMessage handler

Phase 4 — Login page redesign (depends on Phase 3 panel; canvas can start in parallel)
    4a. ParticleCanvas.tsx: canvas animation (can build in parallel with Phase 3)
    4b. Login.tsx: left/right layout, embed FeishuQRPanel + ParticleCanvas
```

Phase 1 alone enables complete end-to-end testing via browser redirect (Mode B). Phase 2 + 3 together enable QR code login. Phase 4 is purely visual and does not affect functionality.

---

## Anti-Patterns

### Anti-Pattern 1: Storing user_access_token in Frontend

**What people do:** Return `user_access_token` from backend and store in localStorage.

**Why it's wrong:** Feishu `user_access_token` grants access to the user's documents, calendar, and Feishu data — a far larger attack surface than needed. It expires independently of the system's JWT lifecycle.

**Do this instead:** Backend exchanges the code, calls `/user_info`, then discards `user_access_token`. Only the system's JWT `TokenPair` leaves the backend.

### Anti-Pattern 2: Validating state Parameter in Backend

**What people do:** Send `state` to backend via `POST /auth/feishu/callback` and validate it server-side.

**Why it's wrong:** `state` is a browser-session CSRF token. The backend has no way to know what value the specific browser tab generated. Backend state validation is security theater.

**Do this instead:** Frontend validates `state` against `sessionStorage` before calling the backend. Backend ignores `state` entirely (or logs it for debugging, but does not validate it).

### Anti-Pattern 3: Reusing feishu_service.py for OAuth Login

**What people do:** Add `exchange_oauth_code()` methods to the existing `FeishuService`.

**Why it's wrong:** `FeishuService` is a 1000-line bitable sync service using `tenant_access_token`. OAuth login uses `user_access_token` for an entirely different API surface. Mixing them violates single responsibility and makes the class harder to test and maintain.

**Do this instead:** `feishu_oauth_service.py` as a separate, focused service — 100-150 lines covering only the OAuth2 login flow.

### Anti-Pattern 4: Adding feishu Login to useAuth Context

**What people do:** Add `loginWithFeishu(code)` to `AuthContextValue` and handle the callback inside `AuthProvider`.

**Why it's wrong:** `FeishuOAuthCallback` is a one-time redirect handler. `AuthContext` is for ongoing session management. The callback page does not need to be in the global context — it just needs to call `storeAuthSession` and `notifyAuthSessionChanged`, which are already exported from `services/auth.ts`.

**Do this instead:** `FeishuOAuthCallback.tsx` calls backend directly via `feishuAuthService`, gets tokens and profile, then calls `storeAuthSession({user, tokens})`. The `AuthContext` bootstrap picks up the new session automatically via `AUTH_SESSION_EVENT`.

### Anti-Pattern 5: Loading QR SDK from a `<script>` Tag in public/index.html

**What people do:** Add the Feishu QR SDK CDN URL to `public/index.html` globally.

**Why it's wrong:** The SDK is only needed on the login page. Loading it globally adds unnecessary payload to every page load. It also makes it harder to conditionally render the QR panel based on whether Feishu OAuth is configured.

**Do this instead:** Dynamically append the `<script>` tag in `FeishuQRPanel`'s `useEffect`, check if `window.QRLogin` already exists before loading to avoid double-loading, and clean up the event listener on unmount.

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|-------------------------|
| 0–500 users | Synchronous `httpx` calls for token exchange are fine; Feishu API responds in <200ms |
| 500–5000 users | No OAuth-specific scaling concern; Feishu rate limits are per-tenant, not per-user |
| 5000+ users | General PostgreSQL + Redis scaling applies; OAuth adds no new bottlenecks |

---

## Sources

- [Feishu Open Platform — Get Authorization Code](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code) — HIGH confidence
- [Feishu Open Platform — Get user_access_token v2](https://open.feishu.cn/open-apis/authen/v2/oauth/token) — HIGH confidence
- [Feishu Open Platform — Get User Info (authen/v1/user_info)](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get) — HIGH confidence; `employee_no` confirmed in response; requires "获取用户受雇信息" permission
- [Feishu QR SDK Documentation](https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/qr-sdk-documentation) — HIGH confidence
- QR SDK CDN version 1.0.3: `https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js` — MEDIUM confidence (from community articles; verify CDN URL against official docs before production deploy)
- Existing codebase (read directly): `backend/app/core/security.py`, `backend/app/api/v1/auth.py`, `backend/app/services/feishu_service.py`, `backend/app/models/user.py`, `backend/app/models/employee.py`, `backend/app/models/feishu_config.py`, `backend/app/core/config.py`, `backend/app/dependencies.py`, `frontend/src/hooks/useAuth.tsx`, `frontend/src/services/auth.ts`, `frontend/src/pages/Login.tsx`

---

*Architecture research for: Feishu OAuth2 Login Integration + Login Page Redesign (v1.3)*
*Researched: 2026-04-16*
