# Project Research Summary

**Project:** 公司综合调薪工具 (Enterprise Salary Adjustment Platform)
**Domain:** HR Compensation Intelligence — AI-assisted evaluation and salary adjustment
**Researched:** 2026-03-25
**Confidence:** HIGH (all findings based on direct codebase inspection + verified against official docs)

---

## Executive Summary

This is a brownfield FastAPI + React platform for AI-assisted employee salary adjustment. The architecture is sound — layered monolith with strict dependency direction, role-based access at both layers, and an evaluation engine that is structurally separate from I/O. Most core features exist in some form. The primary problem is not missing features but unreliable or insecure implementations of existing ones: the AI evaluation pipeline has silent score corruption bugs, the approval workflow has race conditions and audit gaps, security vulnerabilities are production-blocking, and the batch import pipeline has data integrity issues.

The recommended approach is to fix and harden the existing system rather than rebuild. The evaluation and approval engines are architecturally correct but have specific implementation bugs that must be patched before any production use. Security issues — particularly the default JWT secret, missing login rate limiting, and plaintext national ID storage — are the highest-priority fixes because they represent unacceptable risk on any production deployment. After security, the focus should be on making the evaluation pipeline trustworthy (score integrity, fallback visibility, audit log wiring) and then completing the dashboard and bulk import surfaces.

The key risks are: (1) silent data corruption in the LLM scoring pipeline that produces incorrect salary recommendations without any error signal, (2) a production-blocking set of security vulnerabilities that are simple to fix but catastrophic if shipped, (3) an audit log model that exists in the schema but is never written by any service — meaning the system cannot defend salary decisions in a dispute context. All three are fixable with targeted work. The external API and real-time dashboard features are stable to defer; the evaluation and approval cores must be solid first.

---

## Top 10 Actionable Findings (Ranked by Impact)

### 1. The audit log is never written — all evaluation and approval decisions are untracked

**File:** `backend/app/models/audit_log.py` (model defined), `evaluation_service.py`, `approval_service.py` (model never used)
**Impact:** CRITICAL — cannot defend salary decisions in disputes; regulatory non-compliance
**Action:** Wire `AuditLog` writes into every service mutation: `EvaluationService.manual_review`, `ApprovalService.decide_approval`, `ImportService.run_import`, all salary status transitions. Commit audit log in the same transaction as the mutation.

### 2. Default JWT secret `"change_me"` accepted at runtime — tokens can be forged

**File:** `backend/app/core/config.py` line 25
**Impact:** CRITICAL — any attacker with repo read access can forge admin tokens; all endpoints are compromised
**Action:** Add startup guard in `lifespan`: reject if `jwt_secret_key` is `"change_me"` or shorter than 32 characters in non-test environments. Rotate immediately. Minimum key length Pydantic validator should be raised from 8 to 32.

### 3. National ID numbers stored and transmitted in plaintext — PIPL violation

**File:** `backend/app/models/employee.py` (`Employee.id_card_no` is plain VARCHAR)
**Impact:** CRITICAL — China PIPL + GB/T 45574-2025 require sensitive PII to be encrypted at rest; fines up to 5% of annual revenue
**Action:** Apply `EncryptedString` SQLAlchemy TypeDecorator using SM4 (preferred under China commercial cryptography regulations) or AES-256-GCM. Mask national IDs in all API responses by default; expose full value only to `admin`/`hr_admin` roles with role-scoped Pydantic schemas.

### 4. LLM score scale ambiguity silently corrupts salary recommendations

**File:** `backend/app/services/evaluation_service.py` (`_normalize_llm_evaluation_payload`)
**Impact:** HIGH — the `use_five_point_scale = max(raw_scores) <= 5.0` heuristic produces 20x inflation for low-scoring employees; error is silent and propagates to salary calculation
**Action:** Enforce a 0-100 integer contract in every system prompt. Add server-side validator after parsing: reject responses where all scores are ≤ 10 and flag for fallback. Log all scale-detection decisions as warnings with raw LLM response attached.

### 5. LLM fallback silently passes as authoritative AI evaluation

**File:** `backend/app/services/evaluation_service.py`, `llm_service.py`
**Impact:** HIGH — when DeepSeek is unavailable/rate-limited, rule-engine results are stored as `status='generated'` with no indicator that LLM was never called; HR staff assume AI analysis was performed
**Action:** Add `used_llm: bool` and `llm_fallback_reason: str | None` columns to `AIEvaluation`. Set from `DeepSeekCallResult.used_fallback` at write time. Display a visible "基于规则引擎估算，未调用AI" indicator in the review UI.

### 6. Approval workflow has two correctness bugs that corrupt decision history

**Files:** `backend/app/services/approval_service.py`
**Impact:** HIGH — (a) no `SELECT FOR UPDATE` on `decide_approval` allows concurrent approvals to produce duplicate decisions; (b) `submit_for_approval` resets approved step records on re-submission, erasing rejection history
**Action:** (a) Add `.with_for_update()` to the approval record query. (b) Preserve historical `ApprovalRecord` rows by creating new records with a `parent_record_id` FK instead of resetting existing ones.

### 7. No login rate limiting — brute-force attacks on `/auth/login` are unrestricted

**File:** `backend/app/api/v1/auth.py`
**Impact:** HIGH — employee numbers are predictable (`EMP-1001` to `EMP-9999`); PBKDF2 is slow but the endpoint has no throttle
**Action:** Add `slowapi` with `@limiter.limit("5/minute")` on the login endpoint using client IP as key. Use Redis as the storage backend (already configured) so limits work correctly across multiple workers.

### 8. `ensure_schema_compatibility` runs raw DDL at startup — Alembic cannot reproduce schema from migrations alone

**File:** `backend/app/core/database.py` lines 73-115
**Impact:** HIGH — split schema state between Alembic versions and ad-hoc DDL calls; fresh database setup from migrations will miss columns; `NOT NULL` columns will crash startup on PostgreSQL with existing data
**Action:** Drain all `ensure_schema_compatibility` columns into a consolidation Alembic migration. Remove the function. Never add columns outside of `alembic revision --autogenerate` going forward.

### 9. Certification import creates duplicates on re-import, inflating salary calculations

**File:** `backend/app/services/import_service.py` (`_import_certifications`)
**Impact:** HIGH — no unique constraint on `(employee_id, certification_type, certification_stage, issued_at)`; re-importing the same file doubles certification bonuses; arithmetic corruption propagates silently to salary recommendations
**Action:** Add `UniqueConstraint` on those four fields. Use upsert pattern in `_import_certifications`.

### 10. In-memory rate limiter breaks under multi-worker deployment

**File:** `backend/app/services/llm_service.py` (`InMemoryRateLimiter`)
**Impact:** MEDIUM (production-blocking at scale) — each worker has its own 20 req/min limit; 4 workers = 80 req/min combined, causing 429s from DeepSeek
**Action:** Replace with Redis-backed sliding window rate limiter for the DeepSeek limiter and the planned `slowapi` auth limiter. Redis connection is already in `requirements.txt`.

---

## Critical Blockers

Things that must be fixed before any production deployment:

| Blocker | Severity | File | Fix Complexity |
|---------|----------|------|----------------|
| Default JWT secret `"change_me"` accepted at runtime | CRITICAL | `config.py` | Low — add startup guard |
| National ID plaintext storage | CRITICAL | `employee.py` | Medium — TypeDecorator + migration |
| Audit log never written | CRITICAL | All services | Medium — add AuditLog calls per service |
| No login rate limiting | HIGH | `auth.py` | Low — add `slowapi` |
| LLM fallback invisible to reviewers | HIGH | `evaluation_service.py` | Low — add `used_llm` column + UI flag |
| Score scale corruption (silent 20x inflation) | HIGH | `evaluation_service.py` | Low — prompt contract + server validator |
| Approval race condition | HIGH | `approval_service.py` | Low — add `with_for_update()` |
| Approval reset erases rejection history | HIGH | `approval_service.py` | Medium — immutable record chain |
| `ensure_schema_compatibility` raw DDL | HIGH | `database.py` | Medium — Alembic consolidation migration |
| Certification duplicate on re-import | HIGH | `import_service.py` | Low — unique constraint + upsert |

---

## Key Technical Decisions

These decisions need to be made (or confirmed) before implementation begins:

### Decision 1: SM4 vs AES-256 for PII encryption
- **Context:** FEATURES.md recommends SM4 (`gmssl`) as required under China's commercial cryptography regulations for PIPL compliance. PITFALLS.md notes AES-256-GCM as acceptable but less compliant. PROJECT.md confirms this is a China-hosted internal tool.
- **Recommendation:** Use SM4 via `gmssl`. Implement as `EncryptedString` SQLAlchemy TypeDecorator so the choice is isolated to one place and switchable.
- **Risk if deferred:** Legal exposure under PIPL if audited before encryption is in place.

### Decision 2: Redis — required now, not optional
- **Context:** Three separate research areas all require Redis: (a) DeepSeek rate limiter must be cross-worker, (b) `slowapi` auth rate limiter for multi-worker safety, (c) dashboard cache via `fastapi-cache2`. Redis is already in `requirements.txt` and `config.py`.
- **Recommendation:** Treat Redis as a required service dependency, not an optional cache. Add to Docker Compose / deployment config in Phase 1.
- **Risk if deferred:** Rate limiting and caching will silently misbehave under load.

### Decision 3: PostgreSQL in development (not just production)
- **Context:** ARCHITECTURE.md notes that SQLite does not support `ALTER TABLE ... ALTER COLUMN`, `CONCURRENTLY`, or most constraint operations. Migration behavior differs between dev and prod, creating a class of bugs that only appear in production.
- **Recommendation:** Use PostgreSQL via Docker in development. SQLite is acceptable only for in-memory unit tests.
- **Risk if deferred:** Alembic migrations developed against SQLite may fail on PostgreSQL in production.

### Decision 4: `python-statemachine` vs current manual state transitions
- **Context:** FEATURES.md recommends `python-statemachine` 3.x bound to SQLAlchemy model via `MachineMixin`. The current codebase uses manual `record.status = "..."` updates. The current approach has the race condition and history-reset bugs documented in PITFALLS.md.
- **Recommendation:** Adopt `python-statemachine` when fixing the approval workflow. The refactor scope is contained to `approval_service.py`.
- **Risk if deferred:** Manual state transitions will accumulate more edge-case bugs as the state graph grows.

### Decision 5: `pypdf` vs `pymupdf4llm` for PDF extraction
- **Context:** STACK.md notes that `pypdf` returns empty or fragmented text for layout-heavy PDFs (PowerPoint exports, scanned docs). `pymupdf4llm` is a drop-in replacement producing clean markdown output.
- **Recommendation:** Replace `pypdf` with `pymupdf4llm` in `DocumentParser`. One-line change, no interface changes.
- **Risk if deferred:** Employees submitting PDF evidence from PowerPoint exports will receive incomplete evaluations with no error signal.

### Decision 6: Image OCR approach — multimodal vs Tesseract
- **Context:** `ImageParser` currently returns a placeholder for all image files. STACK.md offers two options: (A) DeepSeek V3 multimodal (base64 in message content — direct, no extra dependency), (B) `pytesseract` (system binary required, ~50MB, lighter than EasyOCR's 1GB).
- **Recommendation:** Option A (multimodal) for images attached to evaluations; Option B (Tesseract) for any offline/batch processing needs. Confirm DeepSeek V3 vision API shape before implementing.
- **Validation needed:** Verify exact DeepSeek V3 multimodal message format against official docs before implementing.

---

## Phase Recommendations

### Phase 1: Security Hardening and Schema Integrity
**Rationale:** These are production blockers. Nothing else matters if tokens can be forged and PII is exposed. Schema integrity must be fixed before any new features add migrations.
**Delivers:** Production-safe authentication, encrypted PII, stable migration baseline
**Key work:**
- Add startup JWT secret validation guard
- Raise `jwt_secret_key` Pydantic min_length from 8 to 32
- Encrypt `id_card_no` via `EncryptedString` TypeDecorator (SM4)
- Add Pydantic response masking for national ID / phone / name
- Add `slowapi` rate limiting to `/auth/login`, `/auth/refresh`
- Drain `ensure_schema_compatibility()` into a consolidation Alembic migration; remove the function
- Fix `get_db_session` to rollback on exception
- Make engine/SessionLocal lazy-initialized
**Avoids:** Pitfalls 2.1, 2.2, 2.5, 5.2, 5.4, 5.5
**Research flag:** Standard patterns — no research phase needed

### Phase 2: Evaluation Pipeline Integrity
**Rationale:** The evaluation pipeline is the core value proposition of this system. Silent score corruption and invisible fallbacks make every salary recommendation untrustworthy. Must be fixed before dashboard or approval work can be validated.
**Delivers:** Trustworthy, explainable, auditable AI evaluations
**Key work:**
- Enforce 0-100 integer scoring contract in all system prompts
- Add server-side scale validator; reject ≤10-all-scores responses
- Add `used_llm: bool` + `llm_fallback_reason` columns to `AIEvaluation`
- Display fallback indicator in manager review UI
- Add `used_fallback` check before persisting evaluation in `EvaluationService`
- Add `DimensionScore` snapshot on re-evaluation (`previous_snapshot` column)
- Require justification when re-evaluation delta > 5 points
- Implement evidence cross-reference check for hallucinated citations (`rationale_verified` flag)
- Apply `scan_for_prompt_manipulation` to all file metadata fields (not just user-typed text)
- Upgrade `pypdf` to `pymupdf4llm` for PDF parsing
- Fix DOCX parser to use `python-docx` instead of raw XML tag matching
- Add PPT speaker notes extraction to `PPTParser`
- Switch DeepSeek retry from linear to exponential backoff with jitter
- Separate 429 handling from 5xx handling in retry logic
**Avoids:** Pitfalls 1.1, 1.2, 1.3, 1.4, 1.5
**Research flag:** DeepSeek V3 multimodal API shape needs validation before implementing image support

### Phase 3: Audit Log Wiring and Approval Workflow Fixes
**Rationale:** The audit log model exists but is dead code. The approval workflow has correctness bugs that corrupt decision history. Both are required for regulatory defensibility and HR user trust. These depend on Phase 2 being stable (evaluations need to be correct before approvals are trustworthy).
**Delivers:** Complete, immutable audit trail; correct multi-step approval workflow
**Key work:**
- Wire `AuditLog` writes into all service mutations (create `AuditService` or context manager)
- `AuditContext` middleware collects operator/IP/request_id per request
- Add `with_for_update()` to `ApprovalService.decide_approval` (race condition fix)
- Preserve approval history on re-submission (immutable record chain with `parent_record_id`)
- Deferral history: persist deferral reason before clearing `defer_until`
- Separation of duty: block self-approval (approver != record creator)
- Add `can_act: bool` computed field to approval record API response (server as source of truth)
- Adopt `python-statemachine` 3.x for state graph clarity; bind via `get_machine()` pattern
- Fix `include_all=True` scope bypass in `list_approvals` for HRBP role
**Avoids:** Pitfalls 2.3, 2.4, 4.1, 4.2, 4.3, 4.4
**Research flag:** Standard patterns — no research phase needed

### Phase 4: Batch Import Reliability
**Rationale:** Import is a frequent HR operation; data corruption in import propagates silently to salary calculations. Depends on Phase 2 evaluation correctness and Phase 3 audit log (import runs should be logged).
**Delivers:** Reliable, idempotent bulk import with clear per-row error reporting
**Key work:**
- Enable `.xlsx` direct import via `pd.read_excel(engine='openpyxl')`; add `openpyxl` to requirements.txt
- Add Unicode replacement character (U+FFFD) validation for Chinese-expected string columns
- Pass `encoding_errors='strict'` explicitly to `pd.read_csv`
- Add `UniqueConstraint` on `(employee_id, certification_type, certification_stage, issued_at)`
- Use upsert in `_import_certifications` (return `status='updated'` vs `'created'`)
- Separate import data transaction from import job metadata transaction (batch savepoints)
- Per-row result tracking with HTTP 207 Multi-Status response
- Add `pandera` lazy validation for schema errors (return all row errors before failing)
- Add import `AuditLog` entries (file name, row counts, operator)
**Avoids:** Pitfalls 3.1, 3.2, 3.3, 3.4
**Research flag:** Standard patterns — no research phase needed

### Phase 5: Dashboard Completeness and Cache Layer
**Rationale:** Dashboard depends on correct evaluations (Phase 2) and a trustworthy audit trail (Phase 3). Redis cache layer requires Redis to be a declared dependency (Phase 1). N+1 query bugs cause multi-second load times at moderate scale.
**Delivers:** Fast, accurate dashboard with complete chart coverage and Redis caching
**Key work:**
- Complete `selectinload` chains in `DashboardService._submissions` and `_evaluations` to cover all accessed relationships
- Replace Python-side aggregation with SQL `GROUP BY` + `func.count()` for all chart data
- Add `fastapi-cache2[redis]` decorator caching to all dashboard endpoints (TTL per endpoint type)
- Cache key must include `cycle_id` and `user.role` to prevent data leakage
- Cache invalidation on evaluation confirm / salary approval
- Add development-mode query counter middleware (warn when single request > 20 DB queries)
- Implement all dashboard chart types with Recharts (level distribution, salary band, department heatmap, certification completion, ROI)
- Wrap all charts in `ResponsiveContainer`; memoize chart data with `useMemo`
- Poll pending approvals count every 30 seconds (no WebSocket needed)
- Replace per-request `httpx.Client` creation with app-level singleton via `lifespan`
**Avoids:** Pitfalls 5.1, 5.3
**Research flag:** Standard patterns — no research phase needed

### Phase 6: External API and Integration Hardening
**Rationale:** Public API exists but has not been validated against real external systems. Deferred until internal workflows (Phases 1-5) are stable, because the API contract should reflect the final internal data model.
**Delivers:** Validated external API with webhook support, API key management, and deprecation headers
**Key work:**
- Add cursor-based pagination to external endpoints (for incremental sync use case)
- Add `Deprecation` / `Sunset` headers to v1 routes
- Implement `WebhookSubscription` table and HMAC-SHA256 signed delivery
- API key rotation: overlap window support, `last_used_at` tracking
- Add `slowapi` rate limiting to public API endpoints (per API key)
- Validate with a real HR system integration (even a mock HRIS)
- Switch from Redis-based multi-worker rate limiter to Redis-backed `slowapi` for consistency
**Avoids:** Security concerns from STACK.md §5, ARCHITECTURE.md §1
**Research flag:** Webhook delivery reliability patterns may need research if high delivery guarantees are required

---

## Phase Ordering Rationale

- **Security first (Phase 1):** JWT forgery is an unconditional production blocker. PII encryption requires a migration that creates the baseline for all subsequent migrations. No phase is safe to ship before Phase 1.
- **Evaluation before approval (Phase 2 before Phase 3):** Approval decisions are only meaningful if the underlying evaluations are correct. Auditing wrong evaluations is worse than not auditing at all.
- **Audit log before import (Phase 3 before Phase 4):** Import runs should be audited. Wiring the audit log in Phase 3 means Phase 4 import gets audit coverage for free.
- **Dashboard after evaluation (Phase 5 after Phase 2):** Dashboard data integrity depends on evaluation correctness. A dashboard over corrupt evaluation data gives HR false confidence.
- **External API last (Phase 6):** The public API schema should reflect the final internal data model. Publishing an API before internal workflows are stable creates a migration burden.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings from direct codebase inspection + official docs (FastAPI, SQLAlchemy, DeepSeek API) |
| Features | HIGH | Evaluation, approval, and import patterns verified against official library docs and PIPL legal sources |
| Architecture | HIGH | All patterns verified against official FastAPI and SQLAlchemy 2.0 documentation |
| Pitfalls | HIGH | All pitfalls from direct code inspection with specific file/line references; not theoretical |

**Overall confidence:** HIGH

### Gaps to Address

- **DeepSeek V3 multimodal API shape:** Official docs confirm vision support but exact message format (base64 encoding, content array structure) should be verified against `api-docs.deepseek.com` before implementing image evaluation. Risk: low, but wasted implementation effort if the API shape differs.
- **`python-jose` maintenance status:** STACK.md notes it is in maintenance mode as of 2024. Migration to `PyJWT` is low priority but should be planned before the project reaches high traffic. No urgency for v1.
- **SM4 key rotation strategy:** `gmssl` supports SM4 but key rotation (rolling re-encryption of existing records) requires a key version column on encrypted tables and a background migration job. This is not needed for v1 but must be planned before any SM4 key rotation event.
- **HRBP scope definition in matrix orgs:** The `AccessScopeService` scope check uses `department` membership. For matrix organizations where HRBP responsibilities don't map cleanly to department boundaries, this may need a more flexible scope model. Validate the org structure assumption before finalizing the data model.

---

## Sources

### Primary (HIGH confidence — official docs or direct code inspection)
- DeepSeek JSON mode: https://api-docs.deepseek.com/guides/json_mode
- FastAPI official docs: https://fastapi.tiangolo.com/
- SQLAlchemy 2.0 relationship loading: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
- Alembic autogenerate: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- `python-statemachine` 3.0: https://python-statemachine.readthedocs.io/en/latest/
- Pandera error report: https://pandera.readthedocs.io/en/latest/error_report.html
- SlowAPI: https://github.com/laurentS/slowapi
- PyMuPDF4LLM: https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/
- fastapi-cache2: https://pypi.org/project/fastapi-cache2/
- Direct codebase inspection (V3.0.0, commit `6e769bf`)

### Secondary (MEDIUM confidence — community consensus, multiple sources agree)
- China PIPL compliance: https://www.china-briefing.com/doing-business-guide/china/company-establishment/pipl-personal-information-protection-law
- GB/T 45574-2025 sensitive PII standard: https://www.morganlewis.com/pubs/2025/06/china-issues-new-national-standard-on-security-requirements-for-sensitive-personal-information
- gmssl SM4 implementation: https://github.com/knitmesh/gmssl
- LLM-as-a-Judge patterns: https://www.evidentlyai.com/llm-guide/llm-as-a-judge
- Zero-downtime Alembic migrations: https://that.guru/blog/zero-downtime-upgrades-with-alembic-and-sqlalchemy/

### Tertiary (LOW confidence — needs validation before implementing)
- DeepSeek V3 multimodal message format — confirm exact API shape at api-docs.deepseek.com before implementing image evaluation
- RS256 for public API key path — referenced in STACK.md but needs PyJWT doc verification before implementing

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
