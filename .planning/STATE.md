---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: 体验优化与业务规则完善
status: executing
stopped_at: Completed 16-01 — file sharing backend
last_updated: "2026-04-04T20:02:00Z"
last_activity: 2026-04-04 -- Plan 16-01 completed
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 9
  completed_plans: 9
  percent: 85
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** HR can run a complete, auditable salary review cycle -- from employee evidence submission to AI evaluation to approved salary adjustment -- with every decision explainable and traceable
**Current focus:** Phase 14 — eligibility-visibility-overrides

## Current Position

Phase: 16 (file-sharing-workflow) — EXECUTING
Plan: 2 of 2 (16-01 complete, 16-02 pending)
Status: 16-01 complete
Last activity: 2026-04-04 -- Plan 16-01 completed

Progress: [#########░] 85%

## Performance Metrics

**Velocity:**

- Total plans completed: 2 (v1.1) / 31 (v1.0)
- Average duration: ~7 min (v1.0 baseline)
- Total execution time: 0 hours (v1.1)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 12 P01 | 5min | 2 tasks | 8 files |
| Phase 12 P02 | 4min | 1 task | 8 files |

**Recent Trend (v1.0 tail):**

- Last 5 plans: 3min, 9min, 5min, 4min, 6min
- Trend: Stable

*Updated after each plan completion*
| Phase 13 P02 | 7min | 2 tasks | 7 files |
| Phase 14 P01 | 12min | 2 tasks | 8 files |
| Phase 14 P02 | 8min | 2 tasks | 9 files |
| Phase 15 P01 | 4min | 2 tasks | 7 files |
| Phase 15 P02 | 5min | 2 tasks | 3 files |
| Phase 16 P01 | 8min | 2 tasks | 11 files |

## Accumulated Context

### Decisions

Key decisions carried from v1.0:

- AES-256-GCM for PII encryption (Phase 01)
- Alembic is sole migration path; init_database() only calls create_all (Phase 01)
- Redis rate limiter with in-memory fallback for LLM calls (Phase 02)
- batch_alter_table for SQLite-compatible migrations (Phase 01)

v1.1 pending decisions:

- ELIG data source mapping: performance rating has no model yet -- may need PerformanceRecord model or defer rule
- SHARE dedup refactor: new method vs modify _check_duplicate() across 4 call sites
- NAV: visual-only grouping, no URL path changes (avoid bookmark breakage)
- [Phase 12]: token_version approach for JWT invalidation on unbind — simpler than blacklist, no Redis dependency
- [Phase 12-02]: Added keyword search to employees API for bind modal
- [Phase 13]: Performance grade lookup defaults to previous year; salary adjustment import appends (not upserts); Chinese-to-code mapping for adjustment types
- [Phase 14-01]: UniqueConstraint on (employee_id, year) for overrides; non-rejected filtering at app level (SQLite limitation); filter-before-paginate for batch query; override creation restricted to manager/hrbp per D-03; role-step binding for override approval
- [Phase 14]: Role-conditional action rendering: useAuth() role check hides override button from admin (D-03), step-aware approve/reject matches request status to user role
- [Phase 15-01]: Vision evaluation reuses parsing timeout (120s); compress_image_if_needed in image_parser.py with local import in llm_service; ExtractedImage uses python-pptx native sha1 for dedup
- [Phase 15]: Vision evaluation wired after text parsing in parse_file() to keep text evidence independent of vision success
- [Phase 16-01]: Refactored _check_duplicate to hash-only with deterministic oldest-first ordering (D-01, review #5)
- [Phase 16-01]: check_duplicate_for_sharing uses submission_id for target-employee context (review #4)
- [Phase 16-01]: Atomic upload+SharingRequest creation via skip_duplicate_check flag + single db.commit (review #2)
- [Phase 16-01]: No public POST /sharing-requests — only created via upload endpoint (review #3)
- [Phase 16-01]: Lazy expiry called by BOTH list_requests AND get_pending_count (review #6)
- [Phase 16-01]: ID-list subquery for _expire_stale_requests avoids SQLAlchemy evaluator timezone bug

### Pending Todos

None yet.

### Blockers/Concerns

- ELIG-03/04 depend on data (performance ratings, leave records) not yet in schema -- must add via Alembic migration
- SHARE modifies critical FileService dedup path -- highest risk change in v1.1
- Stale JWT after binding change: must invalidate refresh token on bind/unbind

## Session Continuity

Last session: 2026-04-04T20:02:00Z
Stopped at: Completed 16-01-PLAN.md
Resume file: .planning/phases/16-file-sharing-workflow/16-02-PLAN.md
