---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to plan
stopped_at: Phase 10 context gathered
last_updated: "2026-03-30T10:39:43.032Z"
progress:
  total_phases: 10
  completed_phases: 9
  total_plans: 30
  completed_plans: 32
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-25)

**Core value:** HR can run a complete, auditable salary review cycle — from employee evidence submission to AI evaluation to approved salary adjustment — with every decision explainable and traceable
**Current focus:** Phase 10 — external-api-hardening

## Current Position

Phase: 10
Plan: 02 (next)

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
| Phase 05 P01 | 5min | 2 tasks | 12 files |
| Phase 05 P03 | 15min | 2 tasks | 5 files |
| Phase 05 P04 | 4min | 2 tasks | 6 files |
| Phase 06 P01 | 4min | 2 tasks | 3 files |
| Phase 06 P02 | 5min | 2 tasks | 9 files |
| Phase 06 P03 | 2min | 2 tasks | 6 files |
| Phase 07 P01 | 6min | 2 tasks | 8 files |
| Phase 07 P02 | 3min | 2 tasks | 11 files |
| Phase 08 P01 | 2min | 2 tasks | 6 files |
| Phase 09 P01 | 4min | 2 tasks | 16 files |
| Phase 09 P02 | 5min | 2 tasks | 8 files |
| Phase 09 P03 | 6min | 2 tasks | 11 files |
| Phase 10 P01 | 3min | 2 tasks | 10 files |

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
- [Phase 05]: Global dedup scope (D-02): content_hash uniqueness checked across all employees, not per-employee
- [Phase 05]: Evidence scaling uses in-memory copy with make_transient to avoid DB persistence of scaled items
- [Phase 05]: ContributorPicker loads full employee list (page_size=200) for dropdown simplicity
- [Phase 05]: ContributorTags groups by file_name and uses filled vs outline badges for owner distinction
- [Phase 06]: AuditLog 的 operator_role 存储在 detail JSON 中（模型无 operator_role 列）
- [Phase 06]: SAVEPOINT 失败后调用 expire_all() 清理会话状态防止连锁失败
- [Phase 06]: 部分成功时使用 HTTP 207 Multi-Status 而非 201
- [Phase 06]: Tests follow existing standalone test DB pattern (uuid SQLite per test) for isolation
- [Phase 06]: RED tests define expected behaviors (207, error_column, xlsx templates, audit logging) for Plan 01/03 implementation
- [Phase 06]: ImportRowResult 类型添加到 api.ts 保持类型集中管理；ImportJobRecord.status 添加 partial；模板下载改为双格式 chip-button
- [Phase 07]: 缓存 key 使用 user_id 而非 role，防止 manager 跨部门数据泄漏
- [Phase 07]: KPI 摘要端点不走 Redis 缓存，直接查库支持 30 秒轮询
- [Phase 07]: Redis 不可用时缓存端点返回 503，不静默降级
- [Phase 07]: 所有看板端点统一使用 require_roles 鉴权，employee 角色返回 403
- [Phase 07]: ServiceUnavailableBanner exported from AILevelChart and reused across chart components
- [Phase 07]: KpiCards uses inline style tag for responsive grid (4/2/1 columns at breakpoints)
- [Phase 08]: 维度常量集中管理在 dimensionConstants.ts，组件通过 import 引用避免重复定义
- [Phase 08]: 雷达图按 DIMENSION_ORDER 固定顺序排列，缺失维度默认 0 分
- [Phase 09]: AES-256-GCM encryption module created for feishu app_secret (no pre-existing encrypt_national_id found)
- [Phase 09]: Startup validation for feishu_encryption_key: warning in dev, RuntimeError in production
- [Phase 09]: Background thread for manual sync trigger (not blocking request)
- [Phase 09]: EncryptedString TypeDecorator restored to encryption.py (lost during 09-01 merge)
- [Phase 09]: AttendanceKpiCard embedded in EvaluationDetail (not SalarySimulator) per Review #1 fix
- [Phase 09]: AbortController used in AttendanceKpiCard to prevent stale request races on employee switch
- [Phase 10]: Feishu migration down_revision fixed from missing 9a7b6c5d4e3f to actual head a5b6c7d8e9f0
- [Phase 10]: Autogenerated migration manually cleaned to only include 3 new tables (api_keys, webhook_endpoints, webhook_delivery_logs)

### Pending Todos

None yet.

### Blockers/Concerns

- CONCERNS.md: `.env` is tracked in git — secrets must be rotated and file removed from index before Phase 1 completes
- CONCERNS.md: `python-jose` has known CVEs (CVE-2024-33664/33663) — migration to PyJWT should be scoped into Phase 1 or immediately after
- RESEARCH.md: DeepSeek V3 multimodal message format needs API doc validation before Phase 2 image OCR implementation

## Session Continuity

Last session: 2026-03-30T10:39:43.025Z
Stopped at: Completed 10-01-PLAN.md
Resume file: .planning/phases/10-external-api-hardening/10-02-PLAN.md
