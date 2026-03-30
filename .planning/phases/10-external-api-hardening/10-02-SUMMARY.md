---
phase: 10-external-api-hardening
plan: 02
subsystem: backend/services, backend/api, backend/utils, backend/core
tags: [api-key, webhook, cursor-pagination, rate-limiting, audit, openapi]
dependency_graph:
  requires: [ApiKey-model, WebhookEndpoint-model, WebhookDeliveryLog-model, ApiKey-schemas, Webhook-schemas, CursorPaginatedResponse]
  provides: [ApiKeyService, WebhookService, cursor-pagination-util, multi-key-auth, per-key-rate-limiting, approved-only-filter, api-key-admin-crud, webhook-admin-crud]
  affects: [backend/app/services, backend/app/api/v1, backend/app/utils, backend/app/dependencies.py, backend/app/core/rate_limit.py]
tech_stack:
  added: []
  patterns: [cursor-pagination, hmac-sha256-webhook-signing, per-key-rate-limiting, audit-enrichment]
key_files:
  created:
    - backend/app/services/api_key_service.py
    - backend/app/services/webhook_service.py
    - backend/app/utils/cursor_pagination.py
    - backend/app/api/v1/api_keys.py
    - backend/app/api/v1/webhooks.py
  modified:
    - backend/app/services/integration_service.py
    - backend/app/dependencies.py
    - backend/app/core/rate_limit.py
    - backend/app/api/v1/public.py
    - backend/app/api/v1/router.py
    - backend/app/schemas/public.py
decisions:
  - "from __future__ import annotations causes -> None to be string-typed, breaking FastAPI 204 status_code; removed return annotation on DELETE endpoint"
  - "Audit logging done at endpoint level (not middleware) to access typed api_key object directly"
  - "Webhook delivery uses synchronous httpx with exponential backoff (1s/5s/30s), max 3 attempts"
metrics:
  duration: 9min
  completed: "2026-03-30T11:50:23Z"
---

# Phase 10 Plan 02: Service Layer + API Hardening Summary

ApiKeyService with SHA-256 create/validate/rotate/revoke, WebhookService with HMAC-SHA256 signed delivery and retry, cursor pagination utility, approved-only salary results filter, per-key rate limiting, admin CRUD endpoints for Key and Webhook management, and enriched audit logging on all public API endpoints.

## What Was Done

### Task 1: Service Layer + Tool Modules
- Created `ApiKeyService` with full CRUD: `create_key` (secrets.token_urlsafe + SHA-256 hash), `validate_key` (hash lookup + expiry check + last_used update), `rotate_key` (revoke old + create new with same config), `revoke_key`, `list_keys`, `get_key`
- Created `WebhookService` with `register` (auto-generates HMAC secret), `unregister`, `list_endpoints`, `get_endpoint`, `deliver` (HMAC-SHA256 signing, 3 retries with exponential backoff, delivery log per attempt), `get_delivery_logs`
- Created `cursor_pagination` utility: `encode_cursor` (base64 JSON), `decode_cursor`, `apply_cursor_pagination` (page_size capped 1-100, fetch N+1 for has_more detection)
- Modified `IntegrationService.get_cycle_salary_results` to join and filter `SalaryRecommendation.status == 'approved'` (per D-07, API-01)
- Added `IntegrationService.get_approved_salary_results_paginated` with cursor pagination support (per D-05, D-06, D-08)
- Replaced `dependencies.py` `get_public_api_key` (kept as deprecated) with `require_public_api_key` returning `ApiKey` ORM model via DB lookup
- Added `get_api_key_identifier` to `rate_limit.py` for per-key rate limiting (per D-04)

### Task 2: API Endpoints
- Created `api_keys.py` router: POST create, GET list, GET by ID, POST rotate, POST revoke -- all admin-only with `require_roles('admin')`
- Created `webhooks.py` router: POST register, GET list, GET by ID, DELETE unregister, GET logs -- all admin-only
- Overhauled `public.py`: replaced static key auth with multi-key DB auth, added cursor pagination params to salary-results endpoint, added per-key rate limiting via `get_api_key_identifier`, enriched audit logging with key_id/key_name/client_ip/path/duration_ms (per D-15)
- Registered `api_keys_router` and `webhooks_router` in `router.py`
- Added OpenAPI examples and error response documentation (401/403/404/429) to public schemas and endpoints (per D-09, API-05)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FastAPI 204 + from __future__ annotations incompatibility**
- **Found during:** Task 2
- **Issue:** `from __future__ import annotations` makes `-> None` a string annotation, which FastAPI 0.115.0 doesn't recognize as NoneType for 204 no-body validation
- **Fix:** Removed `-> None` return type annotation from the DELETE webhook endpoint
- **Files modified:** `backend/app/api/v1/webhooks.py`
- **Commit:** b3af0a7

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | eb9a652 | Service layer + tools (ApiKeyService, WebhookService, cursor_pagination, approved-only filter) |
| 2 | b3af0a7 | API endpoints (Key CRUD, Webhook CRUD, public API hardening, OpenAPI docs) |

## Known Stubs

None -- all files are complete implementations with full business logic wired.

## Self-Check: PASSED
