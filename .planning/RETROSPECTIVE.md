# Project Retrospective

## Milestone: v1.1 — 体验优化与业务规则完善

**Shipped:** 2026-04-07
**Phases:** 7 | **Plans:** 13 | **Tasks:** 17
**Duration:** 7 days (2026-03-31 → 2026-04-07)
**Commits:** 343 | **Files changed:** 571

### What Was Built

- Account-employee binding with token_version JWT invalidation and admin + self-bind flows
- Salary eligibility engine: 4 three-state rules (tenure/interval/performance/leave) with 28 unit tests and configurable thresholds
- Eligibility service + API + ImportService extensions for 3 data import channels (Excel, Feishu, manual)
- Batch eligibility query with filter-before-paginate, two-level override approval (HRBP → admin), Excel export
- Multimodal vision evaluation: PPT image extraction with SHA1 dedup, DeepSeek vision scoring, >5MB compression
- File sharing workflow: hash-only dedup, atomic upload+request, 72h lazy expiry, approve/reject/revoke
- Salary display simplification: SalarySummaryPanel + SalaryDetailPanel extraction, EligibilityBadge with 4-rule drill-down

### What Worked

- **Phase-gated plan execution** prevented scope creep; each plan had clear provides/requires boundaries
- **Pure-computation engine layer** (EligibilityEngine, SalaryEngine) made unit tests trivial to write — 28 tests passed without mocking DB
- **Atomic transaction pattern** for upload+SharingRequest eliminated an entire class of orphan-record bugs identified in review
- **hash-only dedup with oldest-first ordering** resolved determinism issues that arose from the v1.0 content_hash approach
- **Vision evaluation after text parsing** (sequential, not parallel) kept text evidence reliable when vision failed

### What Was Inefficient

- Phase 11 (menu/navigation) was executed but SUMMARY.md was never written — left a documentation gap carried into v1.2
- filter-before-paginate workaround for SQLite was necessary but created a known scaling debt — should have been flagged earlier
- Several `fix()` commits in Phase 16 suggest the frontend integration needed more upfront API contract definition
- REQUIREMENTS.md traceability table was not updated as phases completed — arrived at milestone completion with 6 "Pending" rows that were actually done

### Patterns Established

- `token_version` column on User for forced JWT invalidation — simpler than Redis blacklist, reusable pattern for any credential change
- `check_duplicate_for_sharing` uses `submission_id` for target-employee context — prevents cross-employee data leaks in dedup path
- Lazy expiry called by both list and pending-count endpoints — avoids a background job for 72h timeout
- ID-list subquery for bulk status updates avoids SQLAlchemy evaluator timezone bug on SQLite

### Key Lessons

- Plan SUMMARY.md should be created immediately after each plan executes, not deferred — gaps are hard to backfill
- Traceability table in REQUIREMENTS.md should be updated at phase completion, not milestone completion
- For phases touching critical shared paths (FileService dedup), a review checklist before execution reduces fix commits
- filter-before-paginate is fine for dev but must be flagged as a scaling concern in PLAN.md when used

---

## Milestone: v1.2 — 生产就绪与数据管理完善

**Shipped:** 2026-04-16
**Phases:** 7 | **Plans:** 18 | **Tasks:** 34
**Duration:** 9 days (2026-04-07 → 2026-04-16)
**Commits:** 144 | **Files changed:** 227 (+22,544 / -2,096)

### What Was Built

- Python 3.9 full compatibility: 440+ PEP 604/585 annotation downgrades across 37 files, numpy/Pillow version pins, SQLite FK pragma
- Celery+Redis async infrastructure: app module, worker DB lifecycle fix, health endpoint, Docker compose, runtime proof
- AI evaluation and bulk import async migration: Celery tasks, polling endpoint, useTaskPolling hook, frontend progress display
- Unified eligibility data import: 6-tab management page, 4 new data types, Excel drag-drop upload + Feishu bitable field mapper with SVG connection lines
- File sharing rejection/timeout cleanup: atomic copy deletion, history-safe FK with snapshots, pending badge, no-revoke terminal state
- Employee company field: model + migration + import semantics + admin form + detail-only visibility
- Production deployment: gunicorn+uvicorn Dockerfile, Nginx frontend multi-stage build, docker-compose.prod.yml 4-service orchestration

### What Worked

- **Celery DB lifecycle fix in Phase 19** (worker_process_init disposing shared engine) prevented a subtle bug that would have caused stale connections in all async tasks — catching this early in infrastructure phase saved significant debugging later
- **Reusing run_import_task for Phase 23 Excel imports** — the Phase 22 Celery task infrastructure was well-abstracted enough that Phase 23 needed zero new Celery code for Excel imports
- **Phase verification reports** caught real gaps: Phase 23 initially had gaps_found (ImportService missing 2 new types), closed before milestone completion
- **Separate docker-compose.prod.yml** kept dev workflow untouched while adding full production orchestration
- **History-safe FK migration** (Phase 21) with requester snapshot fields preserved audit trail even after copy deletion

### What Was Inefficient

- **REQUIREMENTS.md traceability not updated during phases** — same v1.1 problem repeated; 15/19 requirements still marked "Pending" despite being satisfied
- **Phase 23 ROADMAP not updated** — ROADMAP showed 1/3 plans despite all 3 SUMMARYs existing on disk, causing confusion in pre-flight check
- **FeishuSyncPanel custom polling** — diverged from the shared useTaskPolling pattern established in Phase 22; should have been caught during Phase 23 plan review
- **llm_service.py InMemoryRateLimiter duplication** — Plan 23-01 claimed it would add a re-export for backwards compatibility, but never did

### Patterns Established

- `useTaskPolling` hook as the standard frontend async pattern — 3 out of 4 async operations use it consistently
- `docker-compose.prod.yml` separate from dev compose — clean production/development separation
- `core/rate_limiter.py` as shared rate limiting module — available for any service needing RPM control
- Celery task pattern: `SessionLocal()` + `try/finally: db.close()` for independent DB sessions
- `.env.production.example` as comprehensive production config template with Chinese section comments

### Key Lessons

- REQUIREMENTS.md traceability MUST be updated at phase completion, not deferred — this is the third milestone with the same gap
- When establishing a shared hook/pattern (useTaskPolling), plan review should explicitly check that all consumers use it
- Phase 23's ROADMAP discrepancy (1/3 vs 3/3) suggests the SUMMARY creation step isn't always updating ROADMAP checkboxes — needs workflow enforcement
- Runtime verification items (Python 3.9 env, Docker builds) should be scheduled early in milestone, not left as human_needed items at completion

### Cost Observations
- Sessions: ~15-20 across milestone
- Notable: Phase 18 (type annotations) was high-volume mechanical work; Phase 19 (Celery) required the most debugging iterations

---

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 | v1.2 |
|--------|------|------|------|
| Phases | 10 | 7 | 7 |
| Plans | 35 | 13 | 18 |
| Duration | ~5 days | 7 days | 9 days |
| Avg plans/phase | 3.5 | 1.9 | 2.6 |
| Commits | — | 343 | 144 |
| Python LOC (cumulative) | ~22,000 | ~30,800 | ~33,164 |
| TypeScript LOC (cumulative) | ~14,000 | ~20,000 | ~21,398 |
| Requirements | — | — | 19/19 satisfied |

**Trends:**
- Phase count stable at 7; plan depth rebounded to 2.6 (infrastructure phases needed more plans)
- Commit count dropped sharply (343 → 144) — less rework, more deliberate execution
- LOC growth slowing (~2.3k Python + ~1.4k TS) — more infrastructure/config work, less feature code
- REQUIREMENTS.md traceability gap persists across all 3 milestones — systemic issue needing workflow fix
- Phase verification catching real gaps (Phase 23 re-verified after ImportService fix) — validates the verify step
