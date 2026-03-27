# Roadmap: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

## Overview

This is a brownfield hardening roadmap. The architecture is sound — FastAPI + React layered monolith
with evaluation engine, salary engine, approval workflow, and role-based access all structurally
present. The work is fixing, completing, and securing what exists so HR can run a full salary review
cycle end-to-end: employee evidence submission → AI evaluation → approval → export. Phases are ordered
by production risk first (security, schema integrity), then evaluation correctness (the core value),
then workflow completion (approval, audit, import), then new feature delivery (deduplication,
attendance, external API). Nothing is built from scratch — everything lands on existing scaffolding.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, ...): Planned milestone work
- Decimal phases (1.1, 2.1, ...): Urgent insertions (marked INSERTED)

- [x] **Phase 1: Security Hardening and Schema Integrity** - Fix production-blocking security vulnerabilities and establish Alembic as the sole migration path (completed 2026-03-26)
- [ ] **Phase 2: Evaluation Pipeline Integrity** - Make AI evaluations trustworthy, explainable, and auditable end-to-end
- [ ] **Phase 3: Approval Workflow Correctness** - Fix race conditions and history-reset bugs; complete reviewer UI
- [ ] **Phase 4: Audit Log Wiring** - Wire AuditLog into every service mutation so every decision is traceable
- [ ] **Phase 5: Document Deduplication and Multi-Author** - Prevent duplicate uploads and support shared project attribution
- [ ] **Phase 6: Batch Import Reliability** - Make bulk employee import idempotent with clear per-row error reporting
- [ ] **Phase 7: Dashboard and Cache Layer** - Complete all dashboard charts with SQL aggregation and Redis caching
- [ ] **Phase 8: Employee Self-Service UI** - Give employees visibility into their evaluation status and results
- [ ] **Phase 9: Feishu Attendance Integration** - Sync attendance data from Feishu for use during salary review
- [ ] **Phase 10: External API Hardening** - Validate and harden the public REST API for external HR system integration

## Phase Details

### Phase 1: Security Hardening and Schema Integrity
**Goal**: The system can be safely deployed to a production environment without cryptographic, PII, or schema integrity risks
**Depends on**: Nothing (first phase)
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-07, SEC-08, DB-01, DB-02, DB-03
**Success Criteria** (what must be TRUE):
  1. The backend refuses to start in production when JWT secret is the default "change_me" value, printing a clear error
  2. The login endpoint returns HTTP 429 after 10 failed attempts from the same IP within 15 minutes
  3. National ID numbers are stored encrypted in the database and masked in API responses for non-admin roles
  4. Salary adjustment percentages (not absolute figures) are all an employee role can see in their own recommendation responses
  5. All database schema changes execute exclusively via Alembic migrations — no DDL runs at application startup
**Plans**: 5 plans
Plans:
- [x] 01-01-PLAN.md — Wave 0 test stubs + Alembic migration reset + retire ensure_schema_compatibility()
- [x] 01-02-PLAN.md — AES-256-GCM national ID encryption, path traversal guard, password complexity
- [x] 01-03-PLAN.md — slowapi rate limiting (login + public API) and startup configuration guard
- [x] 01-04-PLAN.md — Role-aware salary response filtering (admin/hrbp vs manager/employee)
- [x] 01-05-PLAN.md — .env git hygiene, .env.example REQUIRED markers, certification import idempotency
**UI hint**: no

### Phase 2: Evaluation Pipeline Integrity
**Goal**: Every AI evaluation result is trustworthy, correctly scored, and clearly labeled as AI-backed or rule-engine fallback
**Depends on**: Phase 1
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05, EVAL-06, EVAL-07, EVAL-08
**Success Criteria** (what must be TRUE):
  1. The evaluation detail page shows all 5 dimension scores with weights and LLM-provided text explanations — not just the final AI level
  2. When DeepSeek is unavailable or unconfigured, the UI displays a visible "rule-engine estimate, AI not used" indicator — no silent fallback
  3. Image files uploaded as evidence produce real extracted text content for LLM evaluation (not the current "OCR reserved" stub)
  4. Re-running an evaluation on the same submission does not silently inflate scores due to 5-point vs 100-point scale ambiguity
  5. Each stored dimension score carries the SHA-256 hash of the prompt that produced it, enabling reproducibility audits
**Plans**: 6 plans
Plans:
- [x] 02-01-PLAN.md — Wave 1: Schema migration — prompt_hash on dimension_scores, used_fallback on ai_evaluations (EVAL-05, EVAL-06)
- [x] 02-02-PLAN.md — Wave 2: LLM service hardening — exponential backoff retry, Redis rate limiter, prompt_hash in DeepSeekCallResult (EVAL-01, EVAL-02, EVAL-05)
- [x] 02-03-PLAN.md — Wave 2: Image OCR via DeepSeek vision API — clear stub, add extract_image_text, wire through ParseService (EVAL-03)
- [x] 02-04-PLAN.md — Wave 2: Scale normalization fix, used_fallback + prompt_hash storage wiring, prompt safety extension (EVAL-04, EVAL-07, EVAL-08)
- [x] 02-05-PLAN.md — Wave 3: Frontend — fallback banner + read-only dimension summary panel in EvaluationDetail (EVAL-06, EVAL-07)
- [x] 02-06-PLAN.md — Wave 3: Unit tests — 22 tests covering all 8 EVAL requirements, no live API required (EVAL-01 through EVAL-08)
**UI hint**: yes

### Phase 3: Approval Workflow Correctness
**Goal**: The approval workflow correctly tracks multi-step decisions without race conditions or lost history, and gives reviewers all the information they need
**Depends on**: Phase 2
**Requirements**: APPR-01, APPR-02, APPR-03, APPR-04, APPR-05, APPR-06, APPR-07
**Success Criteria** (what must be TRUE):
  1. Two managers approving the same evaluation simultaneously produce exactly one approved decision — concurrent requests do not create duplicates
  2. When an evaluation is rejected and resubmitted, the full rejection history is preserved and visible alongside the new submission
  3. The manager approval queue shows pending evaluations filtered by their department, with evaluation dimension scores visible on the same screen
  4. HR/HRBP can view pending evaluations across all departments and compare adjustment percentages side by side
  5. Every approval action (approve, reject, return for revision, override) writes an audit log entry in the same transaction
**Plans**: 3 plans
Plans:
- [x] 03-01-PLAN.md — Wave 0 test stubs for APPR-01 through APPR-06 (RED baseline)
- [x] 03-02-PLAN.md — Alembic migration (generation column), pessimistic lock, history preservation, audit log wiring
- [x] 03-03-PLAN.md — Dimension scores in approval response schema + Approvals.tsx panel + human smoke test
**UI hint**: yes

### Phase 4: Audit Log Wiring
**Goal**: Every score change, salary override, and approval decision produces an immutable audit log entry that administrators can query and export
**Depends on**: Phase 3
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03
**Success Criteria** (what must be TRUE):
  1. An administrator can query audit logs by entity, operator, operation type, and date range via the admin UI or API
  2. When an evaluation score is changed or a salary value is overridden, the audit log entry appears in the same database transaction — there is no window where the change exists without a log entry
  3. Each audit log entry contains entity type, entity ID, operation type, operator user ID and role, old value, new value, timestamp, and request ID
**Plans**: 3 plans
Plans:
- [x] 04-01-PLAN.md — Wave 0 test stubs for AUDIT-01, AUDIT-02, AUDIT-03 (RED baseline)
- [x] 04-02-PLAN.md — Alembic migration, RequestIdMiddleware, evaluation/salary service audit wiring
- [x] 04-03-PLAN.md — AuditService query layer, GET /api/v1/audit/ endpoint, admin AuditLog UI page
**UI hint**: yes

### Phase 5: Document Deduplication and Multi-Author
**Goal**: Employees cannot accidentally submit duplicate evidence, and collaborative projects correctly distribute evaluation credit across co-contributors
**Depends on**: Phase 2
**Requirements**: SUB-01, SUB-02, SUB-03, SUB-04, SUB-05
**Success Criteria** (what must be TRUE):
  1. Uploading a project file that matches an already-uploaded project (same name + file content hash) shows a rejection message referencing the existing record
  2. An employee can assign co-contributors from the employee list when uploading a project, entering contribution percentages that must sum to 100%
  3. A co-contributor can see the shared project in their own materials list and upload supplementary files to it
  4. When AI evaluates a shared project worth 80 points, a contributor with 60% share receives a 48-point effective score for that project
  5. The approval review screen shows all co-contributors and their contribution percentages for any shared project
**Plans**: 4 plans
Plans:
- [ ] 05-01-PLAN.md — Schema migration + ProjectContributor model + UploadedFile extension + RED test stubs (SUB-01..SUB-05)
- [ ] 05-02-PLAN.md — FileService dedup logic + contributor management + API endpoint update (SUB-01, SUB-02, SUB-03)
- [ ] 05-03-PLAN.md — EvaluationService score scaling + ApprovalService contributor display (SUB-04, SUB-05)
- [ ] 05-04-PLAN.md — Frontend: ContributorPicker, dedup UX, approval ContributorTags (SUB-01, SUB-02, SUB-03, SUB-05)
**UI hint**: yes

### Phase 6: Batch Import Reliability
**Goal**: HR can reliably import large batches of employee and certification records with clear feedback on exactly which rows succeeded and which failed
**Depends on**: Phase 4
**Requirements**: IMP-01, IMP-02, IMP-03, IMP-04, IMP-05, IMP-06
**Success Criteria** (what must be TRUE):
  1. A CSV with 10 invalid rows and 90 valid rows results in HTTP 207 with all 10 errors reported and 90 rows committed — the import does not stop at the first error
  2. Re-importing the same employee file a second time updates existing records rather than creating duplicates
  3. The import response includes total rows, success count, failure count, and a per-row error message for every failed row
  4. A GBK-encoded Chinese Excel file imports without garbled characters
  5. The frontend provides a downloadable Excel template with correct column headers and example rows
**Plans**: TBD
**UI hint**: yes

### Phase 7: Dashboard and Cache Layer
**Goal**: The dashboard loads quickly with accurate data across all chart types, with role-appropriate data scoping and live pending-approval counts
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07
**Success Criteria** (what must be TRUE):
  1. The dashboard AI level distribution chart shows headcount and percentage for each of the 5 AI levels
  2. The salary adjustment histogram shows the distribution of recommended adjustment percentages across all evaluated employees
  3. The approval pipeline status card shows live counts in each workflow state (draft, submitted, manager review, HR review, approved, rejected)
  4. HR can click a department name to drill down and see that department's level distribution and average adjustment percentage
  5. The pending-approvals count refreshes every 30 seconds without a full page reload; other charts use Redis cache with TTL-based refresh
**Plans**: TBD
**UI hint**: yes

### Phase 8: Employee Self-Service UI
**Goal**: Employees can independently track where their evaluation stands and view their results once the process completes, without needing to contact HR
**Depends on**: Phase 2, Phase 3
**Requirements**: EMP-01, EMP-02, EMP-03
**Success Criteria** (what must be TRUE):
  1. An employee logging in sees their current evaluation status and which approval stage it is in (submitted, manager review, HR review, etc.)
  2. After evaluation is confirmed, the employee can view all 5 dimension scores and the dimension-level explanations for their evaluation
  3. After approval, the employee sees their salary adjustment percentage — not an absolute salary figure
**Plans**: TBD
**UI hint**: yes

### Phase 9: Feishu Attendance Integration
**Goal**: HR reviewers can see an employee's attendance summary alongside salary adjustment decisions, with data synced from Feishu on demand and on schedule
**Depends on**: Phase 3
**Requirements**: ATT-01, ATT-02, ATT-03, ATT-04, ATT-05, ATT-06, ATT-07
**Success Criteria** (what must be TRUE):
  1. Clicking "Sync Attendance" in the HR admin panel immediately pulls the latest data from the configured Feishu multi-dimensional table
  2. The Feishu connection settings (App ID, App Secret, table ID, field mappings) are editable in the admin UI without code changes
  3. The manual salary adjustment screen shows an attendance summary panel for the employee (attendance rate, absences, overtime, late/early departures) labeled with the data-as-of timestamp
  4. A scheduled daily sync runs at a configurable time and updates attendance records automatically
  5. If Feishu sync fails, the admin panel shows the last sync status and error message — the salary adjustment workflow continues unaffected
**Plans**: TBD
**UI hint**: yes

### Phase 10: External API Hardening
**Goal**: External HR systems can reliably and securely pull approved salary recommendations via a documented, rate-limited, cursor-paginated public API with per-key management
**Depends on**: Phase 3, Phase 4
**Requirements**: API-01, API-02, API-03, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. The public API returns only approved salary recommendations — draft and in-review records are never returned
  2. An external system can page through all records using cursor-based pagination without missing or duplicating entries across pages
  3. An admin can create, rotate, and revoke API keys through the admin UI; each key shows name, created date, last used date, and optional expiry
  4. A revoked or expired API key immediately returns HTTP 401 on the next request
  5. The OpenAPI documentation at `/docs` accurately reflects all `/api/v1/public/` endpoints with example request and response bodies
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Security Hardening and Schema Integrity | 5/5 | Complete   | 2026-03-26 |
| 2. Evaluation Pipeline Integrity | 4/6 | In Progress|  |
| 3. Approval Workflow Correctness | 0/3 | Not started | - |
| 4. Audit Log Wiring | 1/3 | In Progress|  |
| 5. Document Deduplication and Multi-Author | 0/4 | Not started | - |
| 6. Batch Import Reliability | 0/TBD | Not started | - |
| 7. Dashboard and Cache Layer | 0/TBD | Not started | - |
| 8. Employee Self-Service UI | 0/TBD | Not started | - |
| 9. Feishu Attendance Integration | 0/TBD | Not started | - |
| 10. External API Hardening | 0/TBD | Not started | - |
