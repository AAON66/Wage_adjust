# Requirements: 公司综合调薪工具 v1

**Created:** 2026-03-25
**Scope:** Complete and harden the existing brownfield platform for production use.

---

## Scope Summary

The existing codebase has a sound architecture but unreliable or incomplete implementations in 6 areas: security, AI evaluation pipeline, approval workflow + audit, batch import, dashboard analytics, and external API. v1 is complete when HR can run a full salary review cycle end-to-end, all evaluations are explainable and auditable, and the system is safe to deploy to production.

---

## v1 Requirements

### Security Hardening

- [ ] **SEC-01**: Application refuses to start in production if `jwt_secret_key` equals the default `"change_me"` value — startup validation raises an error with clear instructions
- [ ] **SEC-02**: Login endpoint (`POST /api/v1/auth/login`) is rate-limited to max 10 failed attempts per IP per 15 minutes using `slowapi`; returns `429` when exceeded
- [ ] **SEC-03**: National ID numbers are encrypted at rest using SM4 (or AES-256-GCM if SM4 is not production-validated) before being stored in the database; API responses show masked format (e.g., `330104********1234`) to non-admin roles
- [ ] **SEC-04**: Salary recommendation endpoints return full salary figures only to `admin` and `hrbp` roles; `manager` role sees adjustment percentage only; `employee` role sees only their own adjustment percentage
- [ ] **SEC-05**: Public API rate limit config is wired to actual middleware — the `/api/v1/public/` endpoints enforce the configured `public_api_rate_limit` value
- [ ] **SEC-06**: `.env` is removed from git tracking (`git rm --cached .env`), `.gitignore` excludes all `.env*` files, and all default placeholder secrets are documented as required configuration
- [ ] **SEC-07**: `LocalStorageService.resolve_path()` asserts that the resolved path stays within `base_dir` before any read or delete — path traversal attacks are prevented
- [ ] **SEC-08**: Password complexity is validated on the backend (minimum 8 chars, requires mixed case + digit or symbol) — not only in the frontend

### Database & Schema Integrity

- [ ] **DB-01**: Alembic is configured and a baseline migration is generated from the current schema — `ensure_schema_compatibility()` startup DDL is drained into proper migrations
- [ ] **DB-02**: All future schema changes use Alembic migrations following expand-contract pattern — no direct DDL at startup in production
- [ ] **DB-03**: `Certification` import is idempotent — re-importing the same certification file for the same employee and period does not create duplicate rows or inflate `certification_bonus`

### AI Evaluation Pipeline

- [ ] **EVAL-01**: DeepSeek LLM calls use exponential backoff with jitter for retries — the current linear 0.2s/0.4s backoff is replaced with a strategy that handles 429/503 responses safely
- [ ] **EVAL-02**: The LLM rate limiter is backed by Redis (or a Redis-compatible store) so it works correctly under multi-worker deployment — per-process in-memory counting is eliminated
- [ ] **EVAL-03**: Image file parsing extracts real text/content for LLM evaluation — the current placeholder (dimensions only) is replaced with OCR (pytesseract) or DeepSeek multimodal vision API
- [ ] **EVAL-04**: The score normalization heuristic (`_normalize_llm_evaluation_payload`) correctly distinguishes 5-point scale scores from 100-point scale scores — the 20× inflation bug for low scores is fixed
- [ ] **EVAL-05**: Each dimension score returned by the LLM is stored with its prompt hash (SHA-256) so the evaluation can be reproduced and audited
- [ ] **EVAL-06**: The stub/fallback evaluation path is clearly visible to the user — when DeepSeek is not configured or returns an error, the UI shows a clear indicator that the result is a stub, not a real AI evaluation
- [ ] **EVAL-07**: Evaluation results display each of the 5 dimensions with its score, weight, and a human-readable explanation from the LLM — not just the final AI level
- [ ] **EVAL-08**: Prompt injection is blocked — user-uploaded document content is sanitized before being included in LLM prompts (existing `prompt_safety.py` is validated and extended as needed)

### Approval Workflow

- [ ] **APPR-01**: `decide_approval` uses `SELECT ... FOR UPDATE` (or equivalent pessimistic lock) to prevent race conditions when two reviewers act simultaneously
- [ ] **APPR-02**: Re-submitting a previously-approved evaluation for revision does not erase prior approval step decisions — revision history is preserved
- [ ] **APPR-03**: Every approval decision (approve, reject, request revision, override) writes an `AuditLog` row — the existing `AuditLog` model is wired into `ApprovalService`
- [ ] **APPR-04**: Every salary recommendation change (system suggestion vs approved value) writes an `AuditLog` row
- [ ] **APPR-05**: Managers can view a list of pending evaluations in their scope with filtering by status, employee, and department
- [ ] **APPR-06**: HR/HRBP can view all evaluations across departments with the same filtering capabilities plus cross-department comparison
- [ ] **APPR-07**: The approval UI shows the full evaluation breakdown (5 dimensions + scores + explanations) alongside the salary recommendation so reviewers have context to decide

### Audit Log & Traceability

- [ ] **AUDIT-01**: Every evaluation score change, approval decision, and salary override writes an `AuditLog` row with: entity type, entity ID, action, actor (user ID + role), old value, new value, timestamp, and request ID
- [ ] **AUDIT-02**: Admin users can query the audit log by entity, actor, action type, and date range via `GET /api/v1/audit/`
- [ ] **AUDIT-03**: Audit log writes commit atomically with the business mutation in the same database transaction — there is no window where a mutation succeeds but the audit log does not

### Batch Import

- [ ] **IMP-01**: Batch import collects all row-level validation errors before failing — uses lazy validation so the full error list is returned in one response, not just the first error
- [ ] **IMP-02**: Batch import uses per-row savepoints so valid rows are committed even when some rows fail — returns HTTP 207 with per-row status
- [ ] **IMP-03**: The import response includes a clear summary: total rows, rows succeeded, rows failed, and a list of failed rows with specific error messages
- [ ] **IMP-04**: Batch import handles Chinese character encoding correctly — supports both UTF-8 and GBK/GB2312 Excel files without data corruption
- [ ] **IMP-05**: Employee import is idempotent — re-importing the same employee data upserts on `employee_id` rather than creating duplicates
- [ ] **IMP-06**: Import template files (Excel format with required columns and example data) are downloadable from the UI

### Dashboard & Analytics

- [ ] **DASH-01**: Dashboard queries use SQL-side aggregation (`GROUP BY`, `func.count`, `func.sum`) — the full-table-scan pattern in `DashboardService` is eliminated
- [ ] **DASH-02**: Dashboard data is cached in Redis with a TTL of 5-15 minutes per chart; cache keys include `cycle_id` and the requesting user's role to prevent cross-role data leakage
- [ ] **DASH-03**: Dashboard displays talent distribution by AI level (count and percentage per level) as a chart
- [ ] **DASH-04**: Dashboard displays salary adjustment distribution (histogram or band chart) showing the spread of recommended adjustment percentages
- [ ] **DASH-05**: Dashboard displays approval pipeline status — how many evaluations are in each workflow state (draft, submitted, manager review, HR review, approved, rejected)
- [ ] **DASH-06**: Dashboard displays department-level breakdown — HR/HRBP can drill down by department to see level distribution and adjustment averages
- [ ] **DASH-07**: KPI cards for "pending approvals" refresh every 30 seconds — other chart data uses TTL-based cache

### External API

- [ ] **API-01**: Public API endpoints (`/api/v1/public/`) return only approved salary recommendations — draft and in-review records are excluded
- [ ] **API-02**: Public API supports cursor-based pagination so external systems can reliably paginate through large result sets
- [ ] **API-03**: Public API key management: admin can create, rotate, and revoke API keys via the UI; each key has a name, creation date, last-used date, and optional expiry
- [ ] **API-04**: API key authentication validates the key is not expired and not revoked on every request
- [ ] **API-05**: Public API response schema is documented (OpenAPI spec is accurate and includes all `/api/v1/public/` endpoints with example responses)

### Employee Self-Service

- [ ] **EMP-01**: Employees can view their own evaluation status and the current stage in the approval workflow
- [ ] **EMP-02**: Employees can view their own evaluation result with dimension breakdown (scores per dimension) once the evaluation is complete
- [ ] **EMP-03**: Employees can view their own salary recommendation (adjustment percentage only — not absolute figures) once the recommendation is approved

---

## v2 Backlog (Out of Scope for v1)

- Webhook notifications to external HR systems on approval events
- Multiple concurrent salary review cycles
- Mobile-responsive UI
- LDAP/SSO authentication
- Performance review integration (pull data from external performance systems)
- Automated certification recognition from uploaded certificates (OCR → auto-populate certification fields)
- Historical salary trend visualization per employee
- PostgreSQL migration (dev environment can stay on SQLite for v1)

---

## Traceability Index

*(Populated by roadmapper — maps each REQ-ID to a Phase)*

| REQ-ID | Phase |
|--------|-------|
| TBD | TBD |
