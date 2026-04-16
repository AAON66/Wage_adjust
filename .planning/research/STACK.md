# Technology Stack — v1.3 Milestone

**Project:** v1.3 - 飞书登录与登录页重设计 (Feishu OAuth2 Login + Login Page Redesign)
**Researched:** 2026-04-16
**Confidence:** HIGH (Feishu OAuth2 backend), HIGH (tsParticles frontend), MEDIUM (QR SDK embed details)

---

## Scope: What This Research Covers

This document covers only the NEW stack additions for v1.3. The existing stack (FastAPI, SQLAlchemy, Redis, Celery, React, TypeScript, Tailwind) is validated and unchanged.

---

## What Already Exists (Do Not Re-Add)

| Existing Capability | Version | Relevance to v1.3 |
|---------------------|---------|-------------------|
| `httpx` | 0.28.1 | Already used in `FeishuService`; handles all Feishu REST calls |
| `python-jose[cryptography]` | 3.3.0 | JWT creation/validation already wired in `auth.py` |
| `redis` | 5.2.1 | Login rate limiting already uses Redis in `auth.py` |
| `FeishuService` | — | `_ensure_token()`, `FEISHU_BASE_URL`, `httpx` pattern established |
| `feishu_encryption_key` | — | Already in `Settings`; OAuth needs its own `feishu_oauth_app_id/secret` |
| `IdentityBindingService` | — | `auto_bind_user_and_employee()` reusable for post-OAuth binding |
| React 18, TypeScript, Tailwind | — | Full frontend stack live; no framework changes |

---

## New Additions Required

### Backend: Zero New Python Packages

The entire Feishu OAuth2 flow is 2 HTTP calls. `httpx` handles both. No new Python packages.

| Addition | Type | Purpose |
|----------|------|---------|
| `feishu_oauth_app_id` | `Settings` field | App ID for the OAuth app (separate from bitable sync app) |
| `feishu_oauth_app_secret` | `Settings` field | App Secret for the OAuth app |
| `feishu_oauth_redirect_uri` | `Settings` field | Registered callback URL (must match Feishu developer console) |
| `feishu_open_id` column | Alembic migration on `users` | Store `open_id` for re-login without re-doing employee match |
| `FeishuAuthService` | New service class | Encapsulate OAuth code exchange + user info fetch + binding logic |
| `/auth/feishu/authorize-url` | New route in `auth.py` | Return constructed OAuth URL with CSRF state |
| `/auth/feishu/callback` | New route in `auth.py` | Accept `code` + `state`, exchange, bind, issue JWT |

**Why no new package:** `httpx` already calls Feishu REST APIs synchronously throughout this codebase. The official `lark-oapi` Python SDK (latest: 1.5.3 on PyPI) adds 6+ MB of dependencies for exactly 2 HTTP calls. That SDK is appropriate for projects not already using httpx; it is inappropriate here.

### Frontend: Two npm Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `@tsparticles/react` | `^3.0.0` | React 18-compatible component wrapping the tsParticles engine |
| `@tsparticles/slim` | `^3.x` | Slim engine bundle: particles + links + mouse interaction (40 KB gzipped) |

**Why `@tsparticles/slim` and not `@tsparticles/all`:**
The "智慧树风格" particle effect — floating dots connected by lines, mouse attraction/repulsion — uses only particles, links, and movement presets. `slim` covers all of these. `@tsparticles/all` adds confetti, fireworks, and polygon masks that are irrelevant and roughly triple the bundle size.

**Why tsParticles over a pure vanilla canvas component:**
TypeScript-native, fully typed config object. Tuning particle speed, density, colors, and interaction becomes changing JSON values — not rewriting animation loop math. React 18's `useEffect` + `initParticlesEngine(once per lifetime)` pattern is idiomatic and clean. A hand-rolled `requestAnimationFrame` loop would need the same capabilities re-implemented with no advantage.

**Why not particles.js (legacy CDN library):**
Unmaintained since 2018. No TypeScript types. tsParticles is its official TypeScript successor, actively maintained (v3.9.1 published 2025).

### Frontend: Feishu QR Code SDK (CDN, Not npm)

The QR code widget is not an npm package. It is a Feishu-hosted JavaScript file loaded via `<script>` tag.

| Resource | Value |
|----------|-------|
| SDK URL | `https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js` |
| Initialization | `window.QRLogin({ id: 'container', goto: authUrl, width: 300, height: 300 })` |
| Event mechanism | `window.addEventListener('message', handler)` — SDK posts `tmp_code` via postMessage |

The script is loaded dynamically in the `FeishuQrPanel` React component via `useEffect`. The `tmp_code` from the message event is appended to the `goto` URL and the browser is redirected, which triggers the standard OAuth callback with a `code` parameter.

---

## Recommended Stack Additions Summary

### Core Technologies (New)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `@tsparticles/react` | `^3.0.0` | Particle canvas React component | Official wrapper, React 18 peer dependency, TypeScript-native |
| `@tsparticles/slim` | `^3.x` | Engine bundle | Covers links + movement + mouse at 40 KB; no unused presets |

### Supporting Configuration (No New Libraries)

| Config Field | Location | Notes |
|--------------|----------|-------|
| `feishu_oauth_app_id` | `backend/.env` | OAuth app credentials — separate from bitable sync app |
| `feishu_oauth_app_secret` | `backend/.env` | Must be registered in Feishu developer console |
| `feishu_oauth_redirect_uri` | `backend/.env` | Example: `http://localhost:5174/auth/feishu/callback` |
| `VITE_FEISHU_APP_ID` | `frontend/.env` | Used by frontend to construct QR SDK `goto` URL |
| `VITE_FEISHU_REDIRECT_URI` | `frontend/.env` | Must exactly match `feishu_oauth_redirect_uri` in backend |

---

## Feishu OAuth2 Flow (Verified via Official Docs)

### Web Redirect Flow

```
1. Frontend: GET /api/v1/auth/feishu/authorize-url
   Backend returns redirect URL:
     https://accounts.feishu.cn/open-apis/authen/v1/authorize
       ?client_id={feishu_oauth_app_id}
       &response_type=code
       &redirect_uri={feishu_oauth_redirect_uri}
       &state={random_csrf_token}

2. User authenticates in Feishu (browser redirect or embedded widget)

3. Feishu redirects to:
     {redirect_uri}?code=XXX&state=YYY

4. Frontend /auth/feishu/callback page:
   - Validate state vs. localStorage value (CSRF check)
   - POST /api/v1/auth/feishu/callback { code, state }

5. Backend FeishuAuthService:
   a. POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
      { grant_type: "authorization_code", client_id, client_secret, code, redirect_uri }
      Response: { access_token, expires_in, token_type: "Bearer" }

   b. GET https://open.feishu.cn/open-apis/authen/v1/user_info
      Authorization: Bearer {access_token}
      Response: { open_id, union_id, name, employee_no, mobile, email }
      (employee_no requires scope: contact:user.employee:readonly)

   c. Match employee_no to Employee record
   d. Call IdentityBindingService.auto_bind_user_and_employee() (reuse existing)
   e. Issue platform JWT (access + refresh) via existing _build_auth_response()
   f. Return TokenPair to frontend
```

### QR Code (Scan) Flow

```
1. Frontend dynamically loads LarkSSOSDKWebQRCode-1.0.3.js
2. window.QRLogin({ id: 'qr-container', goto: authUrl }) renders iframe QR widget
3. User scans QR code with Feishu mobile app
4. SDK fires window.message event: { tmp_code: "XXXX" }
5. Frontend handler appends tmp_code to goto URL and browser.location.href redirect
6. Feishu 302 redirects to: {redirect_uri}?code=YYY&state=ZZZ
7. Continue from step 4 of Web Redirect Flow above
```

Both flows share the same backend callback endpoint. No separate code path after the OAuth `code` is obtained.

### Feishu API Endpoints (Verified)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `https://accounts.feishu.cn/open-apis/authen/v1/authorize` | GET (redirect) | Authorization code initiation |
| `https://open.feishu.cn/open-apis/authen/v2/oauth/token` | POST | Exchange `code` for `user_access_token` |
| `https://open.feishu.cn/open-apis/authen/v1/user_info` | GET | Fetch user profile including `employee_no` |

**Required OAuth app scopes:**
- `contact:user.employee:readonly` — access `employee_no` field
- `open_id`, `name` require no explicit scope

---

## DB Schema Addition

One Alembic migration required:

```python
# New column on users table
op.add_column('users', sa.Column(
    'feishu_open_id', sa.String(255), nullable=True, unique=True
))
op.create_index('ix_users_feishu_open_id', 'users', ['feishu_open_id'], unique=True)
```

This allows future logins to find the bound account directly by `open_id` without repeating the employee_no lookup. LOW complexity, HIGH value.

---

## Installation

```bash
# Frontend only — no backend packages needed
cd frontend
npm install @tsparticles/react @tsparticles/slim
```

No `pip install` additions. All backend OAuth logic uses `httpx` (already present at 0.28.1).

---

## Integration Points with Existing Code

| Existing Module | How v1.3 Touches It |
|-----------------|---------------------|
| `backend/app/api/v1/auth.py` | Add `GET /feishu/authorize-url` and `POST /feishu/callback` routes |
| `backend/app/core/config.py` | Add `feishu_oauth_app_id`, `feishu_oauth_app_secret`, `feishu_oauth_redirect_uri` |
| `backend/app/models/user.py` | Add `feishu_open_id: Mapped[str \| None]` column |
| `backend/app/services/feishu_service.py` | DO NOT MODIFY — handles bitable/attendance only |
| `backend/app/services/identity_binding_service.py` | Reuse `auto_bind_user_and_employee()` after `employee_no` obtained |
| `frontend/src/pages/Login.tsx` | Redesign to left/right split layout |
| `frontend/src/services/api.ts` | Add `getFeishuAuthorizeUrl()` and `feishuCallback()` |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Raw `httpx` for OAuth | `lark-oapi` (PyPI, 1.5.3) | Adds 6 MB+ for 2 HTTP calls; `httpx` already proven in this codebase |
| Raw `httpx` for OAuth | `authlib` | General OAuth library adds session management complexity; single-provider flow doesn't justify it |
| `@tsparticles/slim` | `@tsparticles/all` | 3x larger bundle; confetti/fireworks presets irrelevant |
| `@tsparticles/slim` | Custom `requestAnimationFrame` canvas loop | More code to maintain; tsParticles JSON config is simpler to tune |
| `@tsparticles/slim` | `particles.js` (CDN legacy) | Unmaintained since 2018; no TypeScript types |
| Separate OAuth app credentials | Reuse bitable sync app credentials | Bitable sync uses `tenant_access_token`; OAuth2 login needs user-scoped token from a separate app registration |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `lark-oapi` Python package | 6 MB for 2 HTTP calls already handled by `httpx` | Raw `httpx` calls in `FeishuAuthService` |
| `react-tsparticles` (v2 legacy npm) | API completely changed in v3; package no longer maintained | `@tsparticles/react` v3 |
| `particles.js` CDN | Unmaintained since 2018, no TypeScript support | `@tsparticles/slim` |
| Feishu H5 JSAPI / `window.h5sdk` | Only works inside Feishu client app; not for standalone web | QR SDK for scan; standard OAuth redirect for web |
| `python-social-auth` / `allauth` | Django-centric; incompatible with FastAPI's DI pattern | Custom `FeishuAuthService` |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `@tsparticles/react@^3.0.0` | React `^18.3.1` | React 18 is an explicit peer dependency; confirmed compatible |
| `@tsparticles/slim@^3.x` | `@tsparticles/react@^3.x` | Engine and React wrapper must share the same major version |
| Feishu QR SDK 1.0.3 | All modern browsers | CDN-loaded; no npm conflict |
| `httpx==0.28.1` | Feishu OAuth2 REST endpoints | No version change; same client used by `FeishuService` |
| Python 3.9 | All above additions | No new Python packages; existing Python 3.9 constraint unaffected |

---

## Sources

- [Feishu OAuth2 authorize URL](https://open.feishu.cn/document/common-capabilities/sso/api/obtain-oauth-code) — endpoint and parameter structure verified
- [Feishu token exchange endpoint](https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token) — `POST /authen/v2/oauth/token` verified; request/response fields confirmed
- [Feishu user info endpoint](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get) — `employee_no` field confirmed; scope `contact:user.employee:readonly` required
- [Feishu QR SDK documentation](https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/qr-sdk-documentation) — SDK URL 1.0.3 confirmed; `window.QRLogin` API verified; `tmp_code` mechanism verified
- [@tsparticles/react npm](https://www.npmjs.com/package/@tsparticles/react) — v3.0.0; React 18 peer dependency confirmed
- [tsParticles GitHub](https://github.com/tsparticles/tsparticles) — active development confirmed; latest v3.9.1 (2025); MIT license
- [tsParticles v3 breaking changes](https://dev.to/tsparticles/tsparticles-300-is-out-breaking-changes-ahead-3hl1) — v3 API changes documented; confirms `react-tsparticles` (v2) is legacy
- [lark-oapi PyPI](https://pypi.org/project/lark-oapi/) — v1.5.3 confirmed available; evaluated and rejected for this use case

---

*Stack research for: 飞书 OAuth2 login + canvas particle background (v1.3 milestone)*
*Researched: 2026-04-16*
