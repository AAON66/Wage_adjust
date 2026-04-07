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

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 |
|--------|------|------|
| Phases | 10 | 7 |
| Plans | 35 | 13 |
| Duration | ~5 days | 7 days |
| Avg plans/phase | 3.5 | 1.9 |
| Fix commits (estimate) | ~20 | ~15 |
| Python LOC (cumulative) | ~22,000 | ~30,800 |
| TypeScript LOC (cumulative) | ~14,000 | ~20,000 |

**Trends:**
- Phase count decreasing, plan depth per phase stabilizing around 2
- Fix commit ratio improving — better upfront design in v1.1
- Codebase growing at ~8k Python + ~6k TS per milestone
