# Technology Stack Research

**Project:** Enterprise Salary Adjustment Platform (wage_adjust)
**Researched:** 2026-03-25
**Codebase state:** Brownfield — FastAPI + SQLAlchemy (sync) + React + DeepSeek LLM

---

## 1. FastAPI + SQLAlchemy in a Brownfield Codebase

### Current state (observed in codebase)

The project uses **synchronous SQLAlchemy 2.0** (`create_engine`, `Session`, `sessionmaker`).
The `database.py` module creates a module-level engine and `SessionLocal` at import time.
`get_db_session()` yields a session via `Generator[Session, None, None]` and is wrapped by
`get_db()` in `dependencies.py` for FastAPI injection.

Migration history exists under `alembic/versions/` with four migrations.
The `alembic/env.py` correctly sets `target_metadata = Base.metadata`, loads all model
modules before autogeneration via `load_model_modules()`, and uses `compare_type=True` and
`compare_server_default=True` — which are both required for reliable change detection.

A major code smell exists: `ensure_schema_compatibility()` in `database.py` applies raw
`ALTER TABLE` DDL at startup instead of using migrations. This means schema state is split
across Alembic versions and ad-hoc DDL calls, making it impossible to reproduce schema from
migrations alone.

### Sync vs async: recommendation for this project

**Keep sync SQLAlchemy.** The codebase is already sync. The only async in the stack is
`asyncpg` in `requirements.txt`, which is not yet wired in.

Migrating to `AsyncSession` + `create_async_engine` in a brownfield project is high-effort
and medium-risk. It requires every database call site to be converted (`await db.execute()`
everywhere), every relationship load strategy to be reviewed (lazy loading silently breaks
under asyncio), and new test infrastructure. The benefit — throughput under concurrent I/O —
is only realized if the app handles many simultaneous requests. For an internal HR tool with
tens of concurrent users, sync is appropriate.

If async adoption becomes necessary later, do it as a dedicated migration phase, not
opportunistically during feature work.

### Session management pattern to maintain

The current pattern is correct for sync FastAPI:

```python
# dependencies.py — already implemented correctly
def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()
```

FastAPI runs sync dependencies in a thread pool, so blocking database calls do not block
the event loop. This is the documented sync path for FastAPI + SQLAlchemy.

One gap: the session factory is created at module import time with a module-level engine.
This works but creates implicit global state that makes testing harder. Prefer injecting the
session factory via `app.state` or through the dependency system so tests can swap it without
patching globals. The existing `create_app()` factory in `main.py` already passes settings
down — extending this to carry a test-injectable `SessionFactory` is straightforward.

### Alembic: fixing the split-schema anti-pattern

The `ensure_schema_compatibility()` function in `database.py` must be drained into proper
Alembic migrations. The current state is a correctness risk: if a new developer sets up a
fresh database from Alembic history alone, they will be missing columns that only exist
because of the startup DDL.

**Procedure to drain it:**

1. Identify all columns added by `ensure_schema_compatibility()` that are not yet in any
   migration file.
2. Create a single consolidation migration that adds those columns with `op.add_column()`,
   guarded by inspection: check `inspector.get_columns()` before issuing DDL.
3. Remove the `ensure_schema_compatibility()` function from `database.py` once the migration
   is in place and tested against a clean database.
4. Never add new columns to `ensure_schema_compatibility()` again. Use `alembic revision
   --autogenerate -m "..."` for all future schema changes.

**Autogenerate discipline:**

- Always run `alembic revision --autogenerate` after model changes, never hand-write DDL.
- Review generated migrations before applying — autogenerate misses: server defaults on
  existing columns, column renames (generates drop+add), check constraints, partial indexes.
- Rename in two migrations: first add the new column, backfill data, second drop the old
  one.
- Keep `compare_type=True` in `env.py` (already set) so column type changes are detected.

### Dependency injection: what works, what to watch

The `require_roles(*roles)` factory in `dependencies.py` returns a closure that FastAPI
registers as a dependency. This is the correct pattern for composable authorization.

The `get_current_user` dependency does one `SELECT ... JOIN departments` on every
authenticated request via `selectinload(User.departments)`. For read-heavy endpoints this
is fine; for bulk operations (e.g., importing 200 employees and evaluating each) the
repeated user lookup per request adds up. Consider caching the user in `request.state`
within a middleware for hot paths.

**Confidence: HIGH** — verified against FastAPI official docs and existing codebase.

---

## 2. DeepSeek API Integration Patterns

### Current state (observed in codebase)

`llm_service.py` implements:
- `InMemoryRateLimiter` (sliding window, in-process, per-worker)
- `DeepSeekPromptLibrary` with four task-specific prompt builders
- `DeepSeekService._invoke_json()` with linear retry (configurable via
  `deepseek_max_retries`, defaulting to 2), linear backoff (`0.2 * (attempt + 1)` seconds),
  `response_format: {"type": "json_object"}`, and a JSON extraction fallback via regex when
  the model returns prose with embedded JSON
- `used_fallback: bool` tracking via `DeepSeekCallResult` so callers know whether a real LLM
  call succeeded
- Model routing by task type (`evidence_extraction` → `deepseek-chat`; `evaluation_generation`
  → `deepseek-chat`; default → `deepseek-reasoner`)
- Prompt injection protection: all system prompts explicitly instruct the model to ignore
  manipulation attempts in evidence text

### DeepSeek JSON mode: verified constraints

**Source: DeepSeek official API docs (api-docs.deepseek.com/guides/json_mode)**

The word "json" must appear in the system or user prompt when using
`response_format: {"type": "json_object"}`. The API returns an error if it does not.
All current system prompts in the codebase satisfy this — "Return JSON with keys: ..." is
present in every prompt.

Known issue acknowledged in DeepSeek's own documentation: the API may occasionally return
empty content. DeepSeek states they are actively working on it. The current codebase handles
this via the fallback chain in `_parse_response_payload()`.

### What the current implementation does well

- Separate timeout values per task type (`parsing_timeout`, `evaluation_timeout`) — correct,
  since `deepseek-reasoner` has much higher latency than `deepseek-chat`.
- `_is_configured()` guard prevents silent no-op calls when the API key is a placeholder.
- `fallback_payload` pattern ensures callers always receive a usable dict even on failure,
  with `used_fallback: True` so the service layer can decide whether to surface a warning.
- JSON regex fallback (`JSON_BLOCK_PATTERN`) handles the case where the model wraps the JSON
  in markdown code fences or prose.

### Gaps and recommended improvements

**1. Linear backoff should become exponential with jitter.**

The current `0.2 * (attempt + 1)` scheme produces delays of 0.2s and 0.4s on two retries.
DeepSeek's own documentation and industry best practice recommend exponential backoff with
jitter to avoid thundering herd when the API is under load:

```python
import random
delay = (2 ** attempt) * 0.5 + random.uniform(0, 0.3)
self.sleeper(delay)
```

This produces roughly 0.5s, 1.3s, 2.7s for attempts 0–2 — much more effective against 503
and 429 transient errors.

**2. 429 (rate limit) responses should not count against the retry budget.**

A 429 from DeepSeek means the API-side rate limit was hit, not an application error.
The current code catches all `httpx.HTTPError` the same way. Split handling:

```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", "5"))
    self.sleeper(retry_after)
    continue  # retry without consuming the budget
elif response.status_code >= 500:
    # consume budget, apply backoff
    ...
else:
    response.raise_for_status()  # 4xx other than 429 → do not retry
```

**3. The in-memory rate limiter is per-worker, not per-deployment.**

`InMemoryRateLimiter` with a 20 req/min limit works correctly for a single Uvicorn worker.
If the application is run with `--workers 4` (or under Gunicorn with multiple processes),
each worker has its own limiter and the combined rate can be 80 req/min. This will cause
429s from DeepSeek.

For multi-worker deployments, the rate limiter must be Redis-backed. Use a Redis sorted-set
sliding window or `redis-py` with a Lua script. The Redis connection is already present in
`requirements.txt` and `config.py`. This is a critical fix before production deployment with
multiple workers.

**4. Schema validation on LLM output is absent.**

The current code parses JSON and returns it to callers without validating that all expected
keys are present. A Pydantic model for each task's output (`EvidenceOutput`,
`EvaluationOutput`, `SalaryExplanationOutput`) should be used to validate the parsed dict
immediately after `_parse_response_payload()`. If validation fails, treat it like a parse
failure and fall back. This prevents subtle bugs where missing keys cause downstream
`KeyError` exceptions deep in the evaluation engine.

**5. `deepseek-reasoner` is not appropriate for evidence extraction.**

`deepseek-reasoner` (DeepSeek-R1) is a reasoning model with higher latency and cost,
designed for complex multi-step problems. Evidence extraction and salary explanation are
structured output tasks that benefit from `deepseek-chat` (DeepSeek-V3). The codebase
already routes `evidence_extraction` and `handbook_parsing` to `deepseek-chat`, which is
correct. Confirm `deepseek_model` (the default) is not left as `deepseek-reasoner` in
production `.env` unless evaluation tasks genuinely require it.

**Confidence: HIGH for JSON mode constraints (official docs). MEDIUM for retry patterns
(DeepSeek docs + industry practice). MEDIUM for multi-worker limiter gap (confirmed by
code analysis).**

---

## 3. React Patterns for Multi-Role HR Workflows

### Current state (observed in codebase)

The frontend has a four-role model: `admin`, `hrbp`, `manager`, `employee`. Role enforcement
is layered:

- **Route level:** `ProtectedRoute` with `allowedRoles` prop. Unauthorized roles are
  redirected to their role home via `getRoleHomePath()`. A `must_change_password` guard
  forces a redirect to `/settings` before any other page loads.
- **UI level:** `getRoleModules()` in `roleAccess.ts` returns role-specific workspace module
  links; the workspace page renders only what that role should see.
- **Auth state:** `useAuth()` context provides `user.role`, `isAuthenticated`,
  `isBootstrapping`. The bootstrapping state is handled correctly — a loading splash is shown
  while the session is validated on mount, preventing a flash of the login page.
- **Token refresh:** The Axios interceptor in `api.ts` implements a single-flight token
  refresh using `refreshInFlight ??= ...`. This prevents multiple concurrent 401 responses
  from each triggering a separate refresh call — a common race condition bug that this
  codebase correctly avoids.

### What the current implementation does well

The `refreshInFlight ??= refreshAccessToken().finally(() => { refreshInFlight = null; })`
pattern is the correct single-flight refresh guard. Many implementations miss this and allow
two simultaneous 401 responses to each try to refresh, causing one to invalidate the other's
new token.

The approval state machine in `approval_service.py` (step ordering, `_is_current_step()`
check, `decision: pending/approved/rejected`) is well-designed. The frontend's
`ApprovalTable` reads this state and should conditionally render action buttons based on
whether the current user is the active approver for the current step.

### Gaps and recommended improvements

**1. Role checks are not composable at the component level.**

Route-level `allowedRoles` prevents navigation to the wrong page. But within a page,
individual UI elements (buttons, fields, action menus) need their own role checks. Currently
these are scattered as inline `user.role === 'admin'` conditionals.

Introduce a small `usePermission` hook or `<CanDo>` component so permissions are declared
rather than scattered:

```typescript
// hooks/usePermission.ts
export function usePermission(allowedRoles: string[]): boolean {
  const { user } = useAuth();
  return isAllowedRole(user, allowedRoles);
}

// usage
const canApprove = usePermission(['admin', 'hrbp', 'manager']);
```

This makes role logic grep-able and testable. `isAllowedRole` is already in `roleAccess.ts`
so this is a thin wrapper.

**2. Approval state machine is implemented only on the backend.**

The `ApprovalRecord` step ordering logic (`_is_current_step`, `step_order` comparison) lives
entirely in Python. The frontend fetches the approval records and must re-derive whether the
current user can act. This can desync if the derivation logic differs.

Two options:
- Have the API response include a computed `can_act: bool` field per record (server is the
  single source of truth — preferred for audit integrity).
- Or have the frontend derive it from `decision === 'pending'` and `approver_id === user.id`
  and `step_order` ordering. This is fragile if step semantics change.

Prefer the server-computed approach. Add `can_act: bool` to the approval record response
schema and compute it in `ApprovalService`.

**3. Optimistic updates are not used for approval actions.**

When a manager approves or rejects, the UI waits for the server round-trip before updating
the approval list. For a simple status toggle (pending → approved), optimistic update is
appropriate: update the local state immediately, then confirm with the server, roll back on
error.

Use a local `useState` or TanStack Query's `useMutation` with `onMutate`/`onError` for this.
TanStack Query is not currently in the codebase (plain `axios` + manual `useState` is used).
Adding TanStack Query is recommended as a targeted improvement for data-heavy pages like the
approval list and evaluation list.

**4. The `useAuth` bootstrap sequence has a silent failure mode.**

On app mount, if both the `fetchCurrentUser` call and the `refreshRequest` call fail, the
user is silently logged out via `clearAuthStorage()`. The user sees nothing — they are just
redirected to `/login`. This is acceptable UX but should log the failure reason for debugging
(e.g., network down vs. expired refresh token). Consider adding a brief error toast before
redirecting in the catch-all fallback.

**5. Token storage in `localStorage` is an XSS risk.**

Access and refresh tokens in `localStorage` are readable by any JavaScript on the page. For
an internal HR tool handling salary data, consider `httpOnly` cookie storage for refresh
tokens (the backend sets the cookie; the frontend never touches it). The access token can
remain in memory (React state) since it is short-lived. This is a security hardening concern,
not a blocking issue.

**Confidence: HIGH for observed patterns (code inspection). MEDIUM for optimistic update
and permission hook recommendations (industry practice, not verified against a specific lib
version).**

---

## 4. File Parsing Pipeline Patterns

### Current state (observed in codebase)

Four parsers exist:

| Parser | Extensions | Extraction method |
|--------|-----------|-------------------|
| `DocumentParser` | `.pdf`, `.md`, `.txt`, `.docx` | `pypdf` for PDF; ZIP+ElementTree for DOCX; raw read for text |
| `PPTParser` | `.pptx` | `python-pptx` shape text iteration |
| `ImageParser` | `.png`, `.jpg`, `.jpeg` | Pillow metadata only — no OCR |
| `CodeParser` | (inferred from glob) | Raw text read |

All parsers return a `ParsedDocument(text, title, metadata)` dataclass and derive from
`BaseParser`. The dispatch pattern (check `can_parse(path)` → call `parse()`) is clean and
extensible.

`parse_service.py` and `evidence_service.py` sit between the parsers and the LLM service.
The LLM receives the first 3500 characters of `parsed.text` for evidence extraction, and
up to 8000 for handbook parsing.

### What works well

The `BaseParser` interface is minimal and correct. Adding a new file type means one new
class and no changes to the dispatch layer. The character-limit truncation before LLM
submission is important for cost and latency control.

The metadata dict is thread-safe since all parsers create new dicts per call. No shared
mutable state exists in the parser layer.

### Gaps and recommended improvements

**1. Image parsing has no content extraction (placeholder only).**

`ImageParser.parse()` returns a placeholder string: "OCR is reserved for a later task."
Any image evidence (screenshots of dashboards, certificates, code output) is submitted to
the LLM with only dimensions and color mode, which provides no evaluable content.

For production image parsing, two approaches:

Option A — Embed images in the LLM call directly (multimodal). DeepSeek-V3 supports vision
via base64-encoded images in message content. This is the most direct path and avoids adding
an OCR dependency. The `ImageParser` would encode the image to base64 and return it in
`metadata['base64']`; the prompt builder in `llm_service.py` would include it as an image
message part.

Option B — Add a lightweight OCR library. `pytesseract` (wraps Tesseract) or
`easyocr` (pure Python, no system deps) can extract text from images without a separate
service. Tesseract requires a system binary; EasyOCR is pip-installable but ~1GB of model
weights. For a self-hosted enterprise tool, Tesseract is the more practical choice.

Neither option is installed in `requirements.txt` yet. This is a gap in the evaluation
quality for image-heavy submissions.

**2. PDF extraction with `pypdf` misses layout-heavy PDFs.**

`pypdf` (formerly PyPDF2) does simple text layer extraction. PDFs generated from PowerPoint
exports or scanned documents often have no extractable text layer, or the text is fragmented
by the PDF layout engine. `pypdf.PdfReader.extract_text()` will return empty or
garbage-structured text for these.

For better PDF extraction, `pymupdf4llm` (open source, published by Artifex) produces clean
markdown output from PDFs including layout, headers, and tables. It applies OCR selectively
only on pages without a text layer. This is the highest-quality freely available PDF
extraction library as of 2025.

Add: `pip install pymupdf4llm`

The `DocumentParser.parse()` for `.pdf` can be replaced with:
```python
import pymupdf4llm
text = pymupdf4llm.to_markdown(str(path))
```
This is a drop-in replacement at the parser level with no interface changes.

**3. PPT parser does not extract notes or image alt text.**

`PPTParser` iterates `slide.shapes` and extracts `shape.text`. Speaker notes
(`slide.notes_slide.notes_text_frame.text`) and image alt text (`shape.name`,
`shape.title`) are skipped. Speaker notes often contain the most substantive content
in employee achievement presentations. Add notes extraction:

```python
for slide in presentation.slides:
    if slide.has_notes_slide:
        notes_text = slide.notes_slide.notes_text_frame.text
        if notes_text.strip():
            chunks.append(f"[Notes] {notes_text.strip()}")
```

**4. DOCX parser uses raw XML tag matching, not the `python-docx` library.**

The current DOCX implementation reads `word/document.xml` directly and finds elements
ending in `}t` (the Word XML `<w:t>` tag). This is fragile against OOXML schema variations
and misses: table cell text, text boxes, and headers/footers. `python-docx` (already a
transitive dependency of `python-pptx`) handles all these correctly.

Replace with:
```python
from docx import Document
doc = Document(str(path))
text = '\n'.join(para.text for para in doc.paragraphs if para.text.strip())
```

**5. Text truncation at 3500 chars may lose critical content for long documents.**

The current LLM call uses `parsed.text[:3500]`. For a 40-slide PPTX with 2000 chars per
slide, only the first 1-2 slides are evaluated. A better approach: extract top-N text
chunks by density (number of non-whitespace characters per shape/paragraph), then
concatenate the highest-density chunks up to the token budget.

For PPT: rank slides by text density and take the top 5-8 rather than the first 3500 chars.

**Confidence: HIGH for observed gaps (code inspection). MEDIUM for pymupdf4llm
recommendation (official docs + 2025 community consensus). MEDIUM for DeepSeek vision
approach (official docs confirm multimodal support for V3 but exact API shape should be
verified before implementing).**

---

## 5. JWT Security Hardening

### Current state (observed in codebase)

- Algorithm: `HS256` with a shared secret from `Settings.jwt_secret_key`.
- Access token expiry: 30 minutes (configurable via `jwt_access_token_expire_minutes`).
- Refresh token expiry: 7 days (configurable via `jwt_refresh_token_expire_days`).
- Password hashing: `pbkdf2_sha256` via `passlib` — correct, bcrypt would also be
  acceptable.
- Token types (`type: "access"` / `type: "refresh"`) are checked in `decode_token()` via
  `expected_type` parameter — prevents access tokens from being used as refresh tokens.
- `jwt_secret_key` has a minimum length of 8 characters enforced by Pydantic `Field(min_length=8)`.
  This is too short. A 256-bit (32-byte) random secret is the minimum for HS256 security.
- `python-jose` is used for JWT encoding/decoding.
- No rate limiting on `/auth/login` or `/auth/refresh`.
- Refresh tokens are not stored server-side; there is no revocation mechanism.
- The default `jwt_secret_key` is `"change_me"` — the `_is_configured()` check in
  `llm_service.py` rejects placeholder keys, but no equivalent check exists for the JWT
  secret. A deployment with the default key will silently issue valid tokens.

### Hardening recommendations (priority order)

**1. Enforce a strong JWT secret at startup (CRITICAL).**

Add a startup validation in `create_app()` or the `lifespan` handler:

```python
import secrets
if len(settings.jwt_secret_key) < 32 or settings.jwt_secret_key == "change_me":
    raise RuntimeError(
        "jwt_secret_key must be at least 32 characters and not the default value. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
```

**2. Add rate limiting to auth endpoints.**

`slowapi` (0.1.x) is the standard rate limiting library for FastAPI/Starlette. It mirrors
`flask-limiter`'s API and supports Redis for distributed state.

Install: `pip install slowapi`

Apply limits:
- `POST /auth/login`: 10 requests per minute per IP
- `POST /auth/refresh`: 20 requests per minute per IP
- `POST /auth/register`: 5 requests per minute per IP (if enabled)

With Redis already in `requirements.txt`, use Redis as the storage backend for rate
limiting so limits work correctly under multiple Uvicorn workers. In-memory storage
(the slowapi default) has the same multi-worker problem as the in-memory DeepSeek
rate limiter.

**3. Implement refresh token rotation.**

Currently `/auth/refresh` issues a new access token and a new refresh token but does not
invalidate the old refresh token. If a refresh token is stolen, an attacker can use it
indefinitely until it expires (7 days).

Refresh token rotation with a short-lived token jti (JWT ID) and a server-side blocklist
(Redis set of revoked jtis with TTL equal to the refresh token expiry) is the standard
approach. When `/auth/refresh` is called:

1. Decode the incoming refresh token, verify its `jti` is not in the revoked set.
2. Add the incoming `jti` to the revoked set with a TTL of 7 days.
3. Issue a new access token and a new refresh token with a new `jti`.
4. If the revoked set already contains the incoming `jti`, treat it as a replay attack:
   revoke all tokens for that user (set a per-user revocation timestamp in Redis).

**4. Add a per-user token revocation timestamp for logout.**

Stateless JWTs cannot be immediately revoked on logout because they are valid until
expiry. A Redis key of `token_revoked_before:{user_id}` set to `now()` on logout means
`decode_token()` can check whether the token's `iat` (issued-at) claim predates the
revocation timestamp. If it does, reject the token. This makes logout effective within
the access token TTL.

**5. Increase minimum secret key length validation.**

Change the Pydantic field validator from `min_length=8` to `min_length=32`. Enforce
this separately from the startup check so it catches misconfiguration at settings load
time rather than only at application start.

**6. Consider switching from HS256 to RS256 for the public API key path.**

The `/api/v1/public/` endpoints use a static `X-API-Key` header compared against
`settings.public_api_key`. This is a shared secret approach with no expiry. For the
external API surface, issue short-lived signed tokens with RS256 so the public key can
be distributed without exposing the signing key. This is a longer-term improvement;
the current `X-API-Key` approach is acceptable for internal enterprise deployment.

**7. `python-jose` vs `PyJWT` note.**

`python-jose` is in maintenance mode as of 2024 (the primary maintainer has reduced
activity). `PyJWT` (maintained by jpadilla) is the more actively maintained alternative.
Both support HS256 and RS256. Migration is straightforward since both libraries share
similar encode/decode API shapes. This is a low-priority improvement but worth tracking.

**Confidence: HIGH for secret length and startup validation (security first principles,
verified in config code). HIGH for slowapi recommendation (official GitHub, actively
maintained). MEDIUM for refresh token rotation pattern (industry standard, not yet
verified against this exact version of jose). LOW for RS256 migration (training data only,
verify PyJWT docs before implementing).**

---

## Recommended Stack Additions

| Library | Purpose | Priority | Install |
|---------|---------|----------|---------|
| `slowapi` | Rate limiting on auth and public API endpoints | HIGH | `pip install slowapi` |
| `pymupdf4llm` | High-quality PDF to markdown extraction | HIGH | `pip install pymupdf4llm` |
| `python-docx` | Robust DOCX parsing (replace raw XML approach) | MEDIUM | `pip install python-docx` |
| `pytesseract` | Image OCR for PNG/JPG evidence files | MEDIUM | `pip install pytesseract` (+ Tesseract binary) |
| `PyJWT` | Replace `python-jose` (maintenance concern) | LOW | `pip install PyJWT[cryptography]` |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| DB session mode | Keep sync SQLAlchemy | Migrate to AsyncSession | High migration cost, marginal benefit for internal HR tool scale |
| PDF extraction | `pymupdf4llm` | `pdfplumber`, `pdfminer.six` | `pymupdf4llm` produces markdown output tuned for LLM input; others return fragmented text |
| Image OCR | `pytesseract` | `easyocr` | Tesseract is lighter; EasyOCR downloads ~1GB of model weights at install |
| Rate limiting | `slowapi` + Redis | In-memory custom limiter | Existing in-memory rate limiter breaks under multi-worker deployment |
| JWT secret storage | Environment variable via `.env` | AWS Secrets Manager / Vault | Vault integration is out of scope for current maturity; `.env` + strong secret length is sufficient |

## Sources

- DeepSeek JSON mode documentation: https://api-docs.deepseek.com/guides/json_mode
- SlowAPI GitHub (laurentS/slowapi): https://github.com/laurentS/slowapi
- Alembic autogenerate docs: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- PyMuPDF4LLM documentation: https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/
- FastAPI SQL Databases tutorial: https://fastapi.tiangolo.com/tutorial/sql-databases/
- FastAPI JWT auth 2025 guide: https://craftyourstartup.com/cys-docs/jwt-authentication-in-fastapi-guide/
- React RBAC with react-admin: https://marmelab.com/react-admin/AuthRBAC.html
- Alembic brownfield migrations: https://medium.com/@megablazikenabhishek/initialize-alembic-migrations-on-existing-database-for-auto-generated-migrations-zero-state-31ee93632ed1
