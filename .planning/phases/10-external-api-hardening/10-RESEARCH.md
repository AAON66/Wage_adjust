# Phase 10: External API Hardening - Research

**Researched:** 2026-03-30
**Domain:** API Security, Pagination, Webhook Delivery, Key Management
**Confidence:** HIGH

## Summary

Phase 10 transforms the existing single-static-key public API into a production-grade integration layer with multi-key management (DB-backed, SHA-256 hashed), per-key rate limiting, cursor-based pagination, webhook push notifications, and comprehensive audit logging. The existing codebase already has a working public API (`public.py` with 4 endpoints), slowapi rate limiting, and an `audit_log` table -- all of which serve as solid foundations.

The primary technical challenges are: (1) replacing the static key check with a DB-backed multi-key lookup that hashes on every request, (2) making slowapi's `key_func` resolve per-API-key instead of per-IP, (3) implementing opaque Base64 cursor pagination over SQLAlchemy queries without the `sqlakeyset` library (to avoid adding dependencies for a straightforward pattern), and (4) building a webhook delivery system with HMAC-SHA256 signing and exponential backoff retries.

**Primary recommendation:** Implement all changes incrementally on top of existing patterns -- new `ApiKey` model + `WebhookEndpoint` model + `WebhookDeliveryLog` model, refactored `require_public_api_key` dependency, custom `key_func` for slowapi, manual cursor encode/decode utility, and a synchronous webhook dispatcher (with background thread for retries).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** DB table `api_keys` for multi-key management with create/rotate/revoke/expire/last_used
- **D-02:** SHA-256 hashed storage, plaintext shown once at creation
- **D-03:** Each key has global read permission on all `/api/v1/public/` endpoints
- **D-04:** Per-key independent rate limiting, default 1000/hour
- **D-05:** Base64 opaque cursors encoding `(sort_field, last_id)`
- **D-06:** Default 20/page, max 100/page
- **D-07:** Only `recommendation.status == 'approved'` records exposed
- **D-08:** Optional `cycle_id` + `department` query filters
- **D-09:** Schema inline examples + responses docs (401/403/404/429)
- **D-10:** Frontend API guide page with auth instructions, pagination tutorial, quick start
- **D-11:** Key management as system settings sub-page
- **D-12:** One-time key display modal with copy button
- **D-13:** Both Pull + Webhook modes
- **D-14:** Webhook: URL registration, HMAC signing, retry, send log
- **D-15:** Full request audit: key ID, name, IP, path, status code, duration, timestamp; reuse audit_log table

### Claude's Discretion
- Webhook signing algorithm (recommend HMAC-SHA256)
- Webhook retry strategy (recommend 3 retries, exponential backoff: 10s, 60s, 300s)
- API guide page layout and styling
- Cursor internal encoding field combination

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-01 | Only approved salary recommendations returned | Filter by `recommendation.status == 'approved'` in SQLAlchemy query; new endpoint replaces current unfiltered `get_cycle_salary_results` |
| API-02 | Cursor-based pagination without missing/duplicating entries | Base64 cursor encoding `(created_at, id)` with keyset WHERE clause; see Cursor Pagination pattern below |
| API-03 | Admin can create/rotate/revoke API keys via UI; shows name, created, last_used, optional expiry | New `api_keys` table + CRUD service + admin-only router + React management page |
| API-04 | Revoked/expired key returns HTTP 401 immediately | Check `is_active` and `expires_at` in `require_public_api_key` dependency |
| API-05 | OpenAPI docs at /docs reflect all /api/v1/public/ endpoints with examples | Pydantic `model_config` with `json_schema_extra` examples + FastAPI `responses` parameter |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | API framework | Already in use |
| SQLAlchemy | 2.0.36 | ORM | Already in use |
| Pydantic | 2.10.3 | Schema validation | Already in use |
| slowapi | 0.1.9 | Rate limiting | Already in use; supports custom `key_func` |
| hashlib (stdlib) | N/A | SHA-256 hashing | Standard library, no dependency |
| hmac (stdlib) | N/A | HMAC-SHA256 signing | Standard library for webhook signatures |
| base64 (stdlib) | N/A | Cursor encoding | Standard library |
| secrets (stdlib) | N/A | Secure key generation | `secrets.token_urlsafe(48)` for API keys |
| httpx | 0.28.1 | Webhook HTTP delivery | Already installed for DeepSeek calls |

### No New Dependencies Required

All required functionality can be implemented with existing installed packages and Python standard library. No new pip dependencies are needed.

## Architecture Patterns

### New Files to Create

```
backend/app/
  models/
    api_key.py           # ApiKey ORM model
    webhook_endpoint.py  # WebhookEndpoint + WebhookDeliveryLog models
  schemas/
    api_key.py           # Create/Read/List schemas
    webhook.py           # Webhook registration/log schemas
  services/
    api_key_service.py   # Key CRUD + hash/verify
    webhook_service.py   # Webhook dispatch + retry
  api/v1/
    api_keys.py          # Admin key management routes
    webhooks.py          # Admin webhook management routes
  utils/
    cursor.py            # Cursor encode/decode utilities

frontend/src/
  pages/
    ApiKeyManagement.tsx # Key management UI
    ApiGuidePage.tsx     # API usage guide (or extend ApiDocs.tsx)
  services/
    apiKeyService.ts     # Key management API calls
    webhookService.ts    # Webhook management API calls
```

### Pattern 1: API Key Model (D-01, D-02)

**What:** DB-backed API key with SHA-256 hashed storage.
**When to use:** Replacing the static `PUBLIC_API_KEY` env var.

```python
# backend/app/models/api_key.py
from __future__ import annotations
import hashlib
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin

class ApiKey(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'api_keys'

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # first 8 chars for identification
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)  # requests per hour
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)  # admin user ID

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
```

**Key generation pattern:**
```python
import secrets
raw_key = secrets.token_urlsafe(48)  # ~64 chars, URL-safe
key_prefix = raw_key[:8]
key_hash = ApiKey.hash_key(raw_key)
# Store key_hash + key_prefix; return raw_key to user ONCE
```

### Pattern 2: Per-Key Rate Limiting with slowapi (D-04)

**What:** Custom `key_func` that extracts the API key from request header and uses it as the rate limit identifier.
**Confidence:** HIGH -- slowapi explicitly supports custom key functions.

```python
# In public.py or a shared dependency
def get_api_key_for_rate_limit(request: Request) -> str:
    """Extract API key from header for per-key rate limiting."""
    api_key = request.headers.get('X-API-Key', '')
    # Hash it so we don't store raw keys in the rate limit backend
    return hashlib.sha256(api_key.encode()).hexdigest()[:16] if api_key else get_remote_address(request)
```

**Important:** The rate limit string can be a callable that reads from the resolved API key model:

```python
def get_dynamic_rate_limit(request: Request) -> str:
    """Return rate limit string based on the resolved API key."""
    api_key_model = getattr(request.state, 'api_key', None)
    if api_key_model:
        return f'{api_key_model.rate_limit}/hour'
    return '100/hour'  # fallback for unauthenticated
```

Then use: `@limiter.limit(get_dynamic_rate_limit, key_func=get_api_key_for_rate_limit)`

**Alternative approach (simpler):** Since all keys share the same 1000/hour default, use a fixed limit string with a per-key key_func. Only implement dynamic limits if the UI allows per-key customization.

### Pattern 3: Cursor-Based Pagination (D-05, D-06)

**What:** Opaque Base64 cursor encoding `(sort_field_value, last_id)` for keyset pagination.
**Confidence:** HIGH -- well-understood pattern, no external library needed.

```python
# backend/app/utils/cursor.py
from __future__ import annotations
import base64
import json
from datetime import datetime

def encode_cursor(sort_value: str | datetime, last_id: str) -> str:
    """Encode pagination cursor as opaque Base64 string."""
    sv = sort_value.isoformat() if isinstance(sort_value, datetime) else str(sort_value)
    payload = json.dumps({'s': sv, 'id': last_id}, separators=(',', ':'))
    return base64.urlsafe_b64encode(payload.encode()).decode()

def decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode cursor into (sort_value, last_id). Raises ValueError on invalid."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return payload['s'], payload['id']
    except Exception as exc:
        raise ValueError('Invalid cursor') from exc
```

**SQLAlchemy keyset WHERE clause:**
```python
# For ascending sort by created_at:
if cursor:
    sort_val, last_id = decode_cursor(cursor)
    query = query.where(
        or_(
            SalaryRecommendation.created_at > sort_val,
            and_(
                SalaryRecommendation.created_at == sort_val,
                SalaryRecommendation.id > last_id,
            ),
        )
    )
query = query.order_by(SalaryRecommendation.created_at.asc(), SalaryRecommendation.id.asc())
query = query.limit(page_size + 1)  # fetch one extra to detect has_next
```

**Response schema:**
```python
class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_next: bool = False
    page_size: int
```

### Pattern 4: Webhook Delivery with HMAC-SHA256 (D-13, D-14)

**What:** Push notifications on approval events with signature verification and retry.
**Recommendation (Claude's discretion):**
- Signing: HMAC-SHA256 with per-endpoint shared secret
- Retry: 3 attempts with exponential backoff (10s, 60s, 300s)
- Timeout: 10 seconds per delivery attempt
- Headers: `X-Webhook-Signature`, `X-Webhook-Timestamp`, `X-Webhook-ID`

```python
# backend/app/services/webhook_service.py
import hmac
import hashlib
import time
import json
from datetime import datetime, UTC

def sign_payload(secret: str, timestamp: int, body: bytes) -> str:
    """Compute HMAC-SHA256 signature: sign(secret, timestamp.body)."""
    message = f'{timestamp}.'.encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

def deliver_webhook(endpoint_url: str, secret: str, payload: dict) -> tuple[int, str]:
    """Deliver webhook with signature headers. Returns (status_code, response_body)."""
    body = json.dumps(payload, default=str).encode()
    timestamp = int(time.time())
    signature = sign_payload(secret, timestamp, body)
    webhook_id = generate_uuid()

    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-ID': webhook_id,
        'X-Webhook-Timestamp': str(timestamp),
        'X-Webhook-Signature': f'sha256={signature}',
    }
    response = httpx.post(endpoint_url, content=body, headers=headers, timeout=10.0)
    return response.status_code, response.text
```

**Webhook Endpoint Model:**
```python
class WebhookEndpoint(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'webhook_endpoints'

    url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(128), nullable=False)  # HMAC shared secret
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    events: Mapped[str] = mapped_column(String(256), nullable=False, default='recommendation.approved')
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

class WebhookDeliveryLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = 'webhook_delivery_logs'

    endpoint_id: Mapped[str] = mapped_column(ForeignKey('webhook_endpoints.id'), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Retry strategy (Claude's discretion decision):**
- 3 retry attempts max
- Backoff intervals: 10 seconds, 60 seconds, 300 seconds
- Use a background thread or scheduled task (project already has APScheduler via feishu_scheduler)
- Log every attempt to `webhook_delivery_logs`

### Pattern 5: Refactored Public API Key Dependency (D-01 through D-04)

**What:** Replace static key comparison with DB lookup.

```python
# backend/app/dependencies.py (updated)
def require_public_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    db: Session = Depends(get_db),
) -> ApiKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail='X-API-Key header is required.')

    key_hash = ApiKey.hash_key(x_api_key)
    api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))

    if api_key is None:
        raise HTTPException(status_code=401, detail='Invalid API key.')
    if not api_key.is_active:
        raise HTTPException(status_code=401, detail='API key has been revoked.')
    if api_key.expires_at and api_key.expires_at < utc_now():
        raise HTTPException(status_code=401, detail='API key has expired.')

    # Update last_used_at
    api_key.last_used_at = utc_now()
    db.commit()

    # Store on request.state for rate limiting and audit
    request.state.api_key = api_key
    return api_key
```

### Pattern 6: Audit Logging Enhancement (D-15)

**What:** Extend existing `log_public_access` to include key ID, name, IP, path, status code, duration.

The existing `AuditLog` model has a `detail` JSON column. API access logging can store structured data:

```python
detail = {
    'api_key_id': api_key.id,
    'api_key_name': api_key.name,
    'client_ip': request.client.host if request.client else 'unknown',
    'path': request.url.path,
    'method': request.method,
    'status_code': 200,
    'duration_ms': elapsed_ms,
}
```

**Implementation approach:** Use a middleware or FastAPI dependency that wraps the response to capture status code and timing. A lightweight approach is an `after_request` pattern using `request.state` to store start time, then logging in the dependency cleanup.

### Anti-Patterns to Avoid

- **Storing raw API keys in the database:** Always hash with SHA-256 before storage. The plaintext is only returned once at creation time.
- **Using offset pagination for public APIs:** Offset skips rows and breaks with concurrent inserts/deletes. Always use cursor/keyset pagination.
- **Synchronous webhook delivery in the request path:** Never block the API response waiting for webhook delivery. Queue webhooks for async delivery.
- **Using `==` for HMAC comparison:** Always use `hmac.compare_digest()` for constant-time comparison to prevent timing attacks.
- **Hardcoding rate limits:** Store per-key rate limits in the `api_keys` table. The slowapi `limit_value` parameter accepts a callable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting backend | Custom counter + Redis logic | slowapi (already installed) | Handles sliding windows, Redis/memory backends, exception handling |
| UUID generation | Custom ID logic | `secrets.token_urlsafe()` for keys, existing `generate_uuid()` for models | Cryptographically secure randomness |
| HMAC signing | Custom signature scheme | `hmac.new()` + `hashlib.sha256` from stdlib | Standard, auditable, well-understood |
| HTTP webhook delivery | `urllib3` or raw sockets | `httpx` (already installed) | Timeout handling, connection pooling |

## Common Pitfalls

### Pitfall 1: Race condition on `last_used_at` updates
**What goes wrong:** Updating `last_used_at` on every request creates write contention on the api_keys row.
**Why it happens:** High-frequency API calls from the same key all try to UPDATE the same row.
**How to avoid:** Use a debounced update -- only update `last_used_at` if the existing value is more than 60 seconds old, or batch updates in a background task.
**Warning signs:** Slow response times under load, database lock contention.

### Pitfall 2: Cursor pagination with NULL sort values
**What goes wrong:** If `created_at` or the sort field can be NULL, the keyset WHERE clause produces unexpected results.
**Why it happens:** SQL NULL comparison semantics (`NULL > X` is UNKNOWN, not TRUE/FALSE).
**How to avoid:** Ensure the sort column is NOT NULL (the existing `CreatedAtMixin` already enforces this). Always include the UUID PK as tie-breaker.
**Warning signs:** Missing or duplicated rows in paginated results.

### Pitfall 3: slowapi key_func not receiving Request object
**What goes wrong:** slowapi silently falls back to IP-based limiting if the endpoint signature doesn't include `request: Request`.
**Why it happens:** slowapi inspects the function signature to inject the Request.
**How to avoid:** Always include `request: Request` as a parameter in rate-limited endpoints (already done in existing code).
**Warning signs:** All API keys sharing the same rate limit bucket.

### Pitfall 4: Webhook retry flooding
**What goes wrong:** Failed webhook endpoints accumulate retries, consuming resources.
**Why it happens:** Dead endpoints never respond, but retries keep firing.
**How to avoid:** After 3 consecutive failures, auto-disable the webhook endpoint and mark it for manual review. Log all delivery attempts.
**Warning signs:** Growing `webhook_delivery_logs` table, background thread starvation.

### Pitfall 5: Static key migration
**What goes wrong:** Existing external integrations using the old `PUBLIC_API_KEY` env var break after migration to DB-backed keys.
**Why it happens:** The old static key is no longer checked after refactoring.
**How to avoid:** During migration, create a DB entry for the existing `PUBLIC_API_KEY` value (hash it and insert). Optionally support a fallback check for the env var during a transition period.
**Warning signs:** 401 errors from previously-working integrations.

## Code Examples

### Backward-Compatible Key Migration
```python
# In lifespan or init_database, seed the old static key as a DB record
def migrate_static_api_key(db: Session, settings: Settings) -> None:
    if settings.public_api_key and settings.public_api_key != 'your_public_api_key':
        existing = db.scalar(
            select(ApiKey).where(ApiKey.key_hash == ApiKey.hash_key(settings.public_api_key))
        )
        if not existing:
            db.add(ApiKey(
                name='Legacy Static Key (migrated)',
                key_hash=ApiKey.hash_key(settings.public_api_key),
                key_prefix=settings.public_api_key[:8],
                is_active=True,
                rate_limit=1000,
                created_by='system',
            ))
            db.commit()
```

### Paginated Approved Recommendations Endpoint
```python
@router.get('/recommendations', response_model=CursorPageResponse)
@limiter.limit(get_dynamic_rate_limit, key_func=get_api_key_for_rate_limit)
def list_approved_recommendations(
    request: Request,
    cursor: str | None = Query(None, description='Opaque pagination cursor'),
    page_size: int = Query(20, ge=1, le=100, description='Items per page'),
    cycle_id: str | None = Query(None, description='Filter by evaluation cycle'),
    department: str | None = Query(None, description='Filter by department'),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(require_public_api_key),
) -> CursorPageResponse:
    ...
```

### Frontend Key Creation with One-Time Display
```typescript
// Modal pattern for API key creation
const [newKeyValue, setNewKeyValue] = useState<string | null>(null);

async function handleCreateKey(name: string, expiresAt?: string) {
  const result = await createApiKey({ name, expires_at: expiresAt });
  setNewKeyValue(result.raw_key);  // Only returned once from server
  // Show modal with key + copy button
}

// Modal: "This key will only be shown once. Copy it now."
// After close: setNewKeyValue(null) -- cannot retrieve again
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | No pytest.ini; tests run via `pytest` from project root |
| Quick run command | `pytest backend/tests/test_api/test_public_api.py -x` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | Only approved recommendations returned | unit | `pytest backend/tests/test_api/test_public_api.py::test_only_approved -x` | Wave 0 |
| API-02 | Cursor pagination no gaps/duplication | unit | `pytest backend/tests/test_api/test_public_api.py::test_cursor_pagination -x` | Wave 0 |
| API-03 | Admin CRUD for API keys | unit | `pytest backend/tests/test_api/test_api_keys.py -x` | Wave 0 |
| API-04 | Revoked/expired key returns 401 | unit | `pytest backend/tests/test_api/test_public_api.py::test_revoked_key_401 -x` | Wave 0 |
| API-05 | OpenAPI docs include examples | unit | `pytest backend/tests/test_api/test_public_api.py::test_openapi_schema -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_api/test_public_api.py -x`
- **Per wave merge:** `pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_api/test_api_keys.py` -- covers API-03, API-04
- [ ] `backend/tests/test_services/test_api_key_service.py` -- covers key hash/verify/CRUD
- [ ] `backend/tests/test_services/test_webhook_service.py` -- covers HMAC signing, delivery
- [ ] `backend/tests/test_utils/test_cursor.py` -- covers cursor encode/decode roundtrip
- [ ] Existing `test_public_api.py` needs new test cases for pagination, approved-only filter

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static API key in env var | DB-backed multi-key with hash | This phase | Enables key rotation without restarts |
| IP-based rate limiting | Per-key rate limiting | This phase | Fair rate allocation per consumer |
| Offset pagination (none currently) | Cursor/keyset pagination | This phase | Stable pagination under concurrent writes |
| No push notifications | Webhook with HMAC signing | This phase | Reduces polling load, faster integration |

## Open Questions

1. **Webhook delivery mechanism**
   - What we know: Project uses APScheduler for feishu sync. httpx is available.
   - What's unclear: Whether to reuse APScheduler for webhook retries or use a simpler threading approach.
   - Recommendation: Use `threading.Timer` for retry scheduling in dev. It is simpler and does not require Redis. For production, consider Celery tasks (already in requirements.txt but not actively wired).

2. **Static key deprecation timeline**
   - What we know: The `PUBLIC_API_KEY` env var is currently the only authentication method.
   - What's unclear: Whether any external systems are already using this key.
   - Recommendation: Auto-migrate the static key to DB on first startup (see migration pattern above). Keep the env var for backward compatibility but log a deprecation warning.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python hashlib/hmac | Key hashing, HMAC signing | Yes | stdlib | -- |
| SQLite | Dev database | Yes | bundled | -- |
| slowapi | Rate limiting | Yes | 0.1.9 | -- |
| httpx | Webhook delivery | Yes | 0.28.1 | -- |
| Redis | Rate limit backend (prod) | Optional | -- | In-memory (dev) |

**Missing dependencies with no fallback:** None
**Missing dependencies with fallback:** Redis -- dev mode uses in-memory rate limiting (already handled by `create_limiter`)

## Sources

### Primary (HIGH confidence)
- Project source code: `public.py`, `dependencies.py`, `config.py`, `rate_limit.py`, `integration_service.py`, `audit_log.py`
- [slowapi GitHub](https://github.com/laurentS/slowapi) -- custom key_func, dynamic limit_value
- [slowapi docs](https://slowapi.readthedocs.io/) -- API reference for Limiter class
- Python stdlib docs: `hashlib`, `hmac`, `base64`, `secrets`

### Secondary (MEDIUM confidence)
- [Sling Academy: FastAPI + SQLAlchemy cursor pagination](https://www.slingacademy.com/article/fastapi-sqlalchemy-using-cursor-based-pagination/) -- implementation pattern
- [Hookdeck: SHA256 webhook signature verification](https://hookdeck.com/webhooks/guides/how-to-implement-sha256-webhook-signature-verification) -- signing best practices
- [Webhook security best practices](https://hooque.io/guides/webhook-security/) -- replay protection, secret rotation

### Tertiary (LOW confidence)
- None -- all findings verified against source code or official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and verified in requirements.txt
- Architecture: HIGH -- patterns directly extend existing codebase conventions
- Pitfalls: HIGH -- derived from code review of existing implementation + well-known API security patterns
- Webhooks: MEDIUM -- retry mechanism design is discretionary; implementation details may evolve during development

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)
