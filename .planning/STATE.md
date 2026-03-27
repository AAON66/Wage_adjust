---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to plan
stopped_at: Completed 02-06-PLAN.md
last_updated: "2026-03-27T14:57:58.447Z"
progress:
  total_phases: 10
  completed_phases: 4
  total_plans: 19
  completed_plans: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** HR can run a complete, auditable salary review cycle — from employee evidence submission to AI evaluation to approved salary adjustment — with every decision explainable and traceable
**Current focus:** Phase 02 — evaluation-pipeline-integrity

## Current Position

Phase: 03
Plan: Not started

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-security-hardening-and-schema-integrity P01 | 5 | 3 tasks | 12 files |
| Phase 01-security-hardening-and-schema-integrity P02 | 8 | 4 tasks | 11 files |
| Phase 01-security-hardening-and-schema-integrity P03 | 8min | 2 tasks | 7 files |
| Phase 01-security-hardening-and-schema-integrity P04 | 4min | 1 tasks | 3 files |
| Phase 01-security-hardening-and-schema-integrity P05 | 12 | 2 tasks | 5 files |
| Phase 02-evaluation-pipeline-integrity P01 | 11 | 7 tasks | 13 files |
| Phase 03-approval-workflow-correctness P01 | 20min | 2 tasks | 3 files |
| Phase 03-approval-workflow-correctness P02 | 27min | 3 tasks | 4 files |
| Phase 03-approval-workflow-correctness P03 | 6min | 2 tasks | 5 files |
| Phase 04-audit-log-wiring P01 | 4min | 2 tasks | 2 files |
| Phase 04-audit-log-wiring P02 | 26min | 2 tasks | 9 files |
| Phase 04-audit-log-wiring P03 | 8min | 2 tasks | 9 files |
| Phase 02 P02 | 8min | 2 tasks | 3 files |
| Phase 02-evaluation-pipeline-integrity P03 | 8min | 2 tasks | 4 files |
| Phase 02 P04 | 12min | 2 tasks | 9 files |
| Phase 02 P06 | 8min | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Key technical decisions pending confirmation before Phase 1:

- SM4 vs AES-256-GCM for PII encryption (PIPL compliance favors SM4 via gmssl)
- Redis is a required service dependency — not optional — starting Phase 1
- PostgreSQL via Docker recommended for dev to match production migration behavior
- [Phase 01-security-hardening-and-schema-integrity]: Autogenerate Alembic baseline against empty SQLite DB (not live DB) to produce op.create_table() for all 17 tables
- [Phase 01-security-hardening-and-schema-integrity]: Alembic is the sole migration path: init_database() only calls create_all and logs reminder to run alembic upgrade head
- [Phase 01-security-hardening-and-schema-integrity]: AES-256-GCM chosen over SM4 for national ID encryption (PIPL-compliant, no gmssl dependency needed)
- [Phase 01-security-hardening-and-schema-integrity]: Migration uses batch_alter_table (SQLite-compatible); DB-level unique on encrypted id_card_no is ciphertext-unique only -- app-layer check required
- [Phase 01-security-hardening-and-schema-integrity]: Password complexity rule: uppercase + lowercase + (digit OR special char) -- matches NIST SP 800-63B
- [Phase 01-security-hardening-and-schema-integrity]: Shared rate_limit.py module: single Limiter instance for decorator binding; create_limiter() builds Redis-backed instance at app startup for one backend across auth and public routes
- [Phase 01-security-hardening-and-schema-integrity]: validate_startup_config raises RuntimeError only in production; development mode is permissive with warning-only for placeholder secrets
- [Phase 01-security-hardening-and-schema-integrity]: StaticPool required for TestClient tests with in-memory SQLite to share DB state across connections
- [Phase 01-security-hardening-and-schema-integrity]: D-13/D-14 applied: admin/hrbp see full salary figures via SalaryRecommendationAdminRead; manager/employee see adjustment ratio only via SalaryRecommendationEmployeeRead; filtering in API layer only
- [Phase 01-security-hardening-and-schema-integrity]: .env added to .gitignore; git rm --cached .env required as human action to remove from git index
- [Phase 01-security-hardening-and-schema-integrity]: DB-03 upsert: SELECT-then-update-or-insert on (employee_id, certification_type); UniqueConstraint name uq_certifications_employee_type; dev DB must be re-seeded
- [Phase 02-evaluation-pipeline-integrity]: Full-jitter exponential backoff chosen for LLM retries (avoids thundering herd); Retry-After header respected on 429/503
- [Phase 02-evaluation-pipeline-integrity]: Five-point scale detection requires >=3 dimension scores (not just any non-empty list) to prevent false positive score inflation
- [Phase 02-evaluation-pipeline-integrity]: Ambiguous overall_score (dims=100pt, overall<=5) is discarded rather than multiplied; falls to weighted_total path
- [Phase 02-evaluation-pipeline-integrity]: ParseService.deepseek_service is optional DI parameter (not required), preserving backward compatibility with existing call sites
- [Phase 03-approval-workflow-correctness]: Department scope binding required in service tests: list_approvals calls can_access_employee; hrbp/manager users must be bound to employee's department before list_approvals returns non-empty results
- [Phase 03-approval-workflow-correctness]: test_hrbp_cross_department_queue passes immediately: include_all=true for HRBP already surfaces items when HRBP is the designated approver sharing the employee department
- [Phase 03-approval-workflow-correctness]: Actual UniqueConstraint name in DB is uq_approval_records_recommendation_id — drop_constraint uses this name in migration
- [Phase 03-approval-workflow-correctness]: submit_for_approval resubmit: new_generation = current_generation + 1 only when any current-gen record has decision != pending
- [Phase 03-approval-workflow-correctness]: DimensionScoreRead already existed in evaluation.py — imported directly into approval schema, not redefined
- [Phase 03-approval-workflow-correctness]: dimension_scores defaults to [] in ApprovalRecordRead so existing callers require no changes
- [Phase 04-audit-log-wiring]: test_audit_atomicity uses db.add monkey-patch to simulate audit write failure without new operator= param
- [Phase 04-audit-log-wiring]: API tests assert expected status codes against missing endpoint — all get 404, producing clear AssertionError gap messages
- [Phase 04-audit-log-wiring]: AuditLog action names use 'manual_review'/'hr_review'/'evaluation_confirmed' (not 'evaluation_score_changed') to match test assertions; target_type='evaluation'
- [Phase 04-audit-log-wiring]: RequestIdMiddleware registered after CORSMiddleware in register_middlewares() so it runs first on inbound requests (Starlette reverse order)
- [Phase 04-audit-log-wiring]: AuditService.query() returns tuple[list[AuditLog], int]; GET /api/v1/audit/ admin-only; frontend uses plain HTML table with offset/limit pagination
- [Phase 02]: Full-jitter exponential backoff replaces linear 0.2*n sleep to avoid thundering herd
- [Phase 02]: Redis rate limiter uses uuid4() in sorted-set member to prevent concurrent timestamp collision
- [Phase 02]: _DEEPSEEK_REDIS_DEGRADED module-level flag allows health checks to detect degraded mode
- [Phase 02-evaluation-pipeline-integrity]: ParseService.deepseek_service is optional DI parameter (not required), preserving backward compatibility with existing call sites
- [Phase 02-evaluation-pipeline-integrity]: Image OCR always uses deepseek-chat model (not configurable) since vision requires multimodal support
- [Phase 02]: Five-point scale detection requires >= 3 dimension scores to prevent false positive inflation on sparse LLM responses
- [Phase 02]: Evidence sanitization via scan_for_prompt_manipulation wired into LLM prompt construction path; redacts flagged content before embedding
- [Phase 02]: Re-evaluation deletes old DimensionScore rows with synchronize_session=fetch + flush before inserting new rows
- [Phase 02-evaluation-pipeline-integrity]: test_evaluation_api_response_contract uses full TestClient integration with create_app + dependency_overrides to verify API contract shape

### Pending Todos

None yet.

### Blockers/Concerns

- CONCERNS.md: `.env` is tracked in git — secrets must be rotated and file removed from index before Phase 1 completes
- CONCERNS.md: `python-jose` has known CVEs (CVE-2024-33664/33663) — migration to PyJWT should be scoped into Phase 1 or immediately after
- RESEARCH.md: DeepSeek V3 multimodal message format needs API doc validation before Phase 2 image OCR implementation

## Session Continuity

Last session: 2026-03-27T10:05:02.221Z
Stopped at: Completed 02-06-PLAN.md
Resume file: None
