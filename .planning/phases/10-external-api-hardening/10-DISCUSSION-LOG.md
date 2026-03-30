# Phase 10: External API Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 10-external-api-hardening
**Areas discussed:** API Key Management, Cursor Pagination, Data Filtering, OpenAPI Docs, Key Management UI, Webhook Notifications, Audit Logging

---

## API Key Storage

| Option | Description | Selected |
|--------|-------------|----------|
| DB table | New api_keys table, supports multi-key, rotation, revocation, expiry, last_used. SHA-256 hashed storage, plaintext shown only once at creation | ✓ |
| Config file | Continue using .env variable, support multiple keys comma-separated. Simple but no dynamic management | |

**User's choice:** DB table
**Notes:** None

## Key Permission Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Global read | Each key can access all /public/ endpoints. Simple and clear | ✓ |
| Per-endpoint auth | Each key configurable for specific endpoints. Fine-grained but complex | |
| Claude decides | Let Claude determine appropriate granularity | |

**User's choice:** Global read

## Rate Limiting per Key

| Option | Description | Selected |
|--------|-------------|----------|
| Per-key independent | Each key has its own rate limit (default 1000/hr), no interference | ✓ |
| Global shared | All keys share one total limit. Simple but one key can exhaust quota | |

**User's choice:** Per-key independent

## Cursor Encoding

| Option | Description | Selected |
|--------|-------------|----------|
| Base64 encoded ID | Encode (sort_field, last_id) as opaque base64 cursor. Tamper-resistant, internally decodable | ✓ |
| Raw ID cursor | Use last record ID directly. Simple but exposes internal IDs | |
| Claude decides | Let Claude choose | |

**User's choice:** Base64 encoded ID

## Page Size

| Option | Description | Selected |
|--------|-------------|----------|
| 20/100 | Default 20 per page, max 100. Suitable for medium-scale data | ✓ |
| 50/200 | Default 50 per page, max 200. Suitable for bulk pulls | |
| Claude decides | Let Claude determine | |

**User's choice:** 20/100

## Approved Status Filter

| Option | Description | Selected |
|--------|-------------|----------|
| Only approved | Return only recommendation.status == 'approved'. Strictest, matches requirement | ✓ |
| approved + completed | Include both approved and completed records | |
| Claude decides | Let Claude determine | |

**User's choice:** Only approved

## Query Filters

| Option | Description | Selected |
|--------|-------------|----------|
| cycle_id + department | Optional query params for both. No params returns all approved records | ✓ |
| cycle_id only | Only cycle filtering. Department filtering done externally | |
| No filtering | Return all approved, external system filters itself | |

**User's choice:** cycle_id + department

## OpenAPI Documentation Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Inline examples + error codes | Add example fields to schemas, document 401/403/404/429 responses per endpoint | |
| Inline + standalone guide page | Above plus a frontend "API Usage Guide" page with auth instructions, pagination tutorial, quickstart | ✓ |
| Claude decides | Let Claude determine | |

**User's choice:** Inline + standalone guide page

## Key Management UI Location

| Option | Description | Selected |
|--------|-------------|----------|
| System settings sub-page | Add "API Key Management" tab within existing system settings, alongside Feishu config etc. | ✓ |
| Standalone page /api-keys | Separate top-level nav page. More prominent but may seem excessive | |
| Claude decides | Let Claude determine | |

**User's choice:** System settings sub-page

## Key Creation Display

| Option | Description | Selected |
|--------|-------------|----------|
| Modal one-time display | Dialog shows full key after creation, warns "cannot view again after closing", provides copy button | ✓ |
| In-page display | Show new key at top of list page, disappears on refresh | |
| Claude decides | Let Claude determine | |

**User's choice:** Modal one-time display

## Webhook vs Pull

| Option | Description | Selected |
|--------|-------------|----------|
| Pure Pull | External systems poll periodically. Simple, reliable, no webhook infrastructure needed | |
| Webhook notification | Active POST to registered URLs on approval. Real-time but needs retry, signing, logging | |
| Both | Pull + Webhook both available, external systems choose | ✓ |

**User's choice:** Both

## Audit Log Detail

| Option | Description | Selected |
|--------|-------------|----------|
| Full recording | Key ID, key name, request IP, request path, response status code, duration, timestamp. Reuse existing audit_log table | ✓ |
| Simple recording | Only Key ID + timestamp + endpoint. Basic tracking | |
| Claude decides | Let Claude determine | |

**User's choice:** Full recording

## Claude's Discretion

- Webhook signing algorithm (HMAC-SHA256 etc.)
- Webhook retry strategy (count, interval)
- API usage guide page layout and styling
- Cursor internal encoding field combination

## Deferred Ideas

None
