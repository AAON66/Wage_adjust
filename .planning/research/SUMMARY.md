# Project Research Summary

**Project:** 公司综合调薪工具 v1.1 体验优化与业务规则完善
**Domain:** Enterprise HR salary adjustment platform -- incremental feature milestone
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

v1.1 is a 5-feature incremental milestone for an established FastAPI+React salary adjustment platform. The core finding across all research: **zero new libraries are needed**. Every feature -- account binding hardening, file sharing approval, menu restructuring, eligibility engine, display simplification -- fits cleanly into the existing `api/ -> services/ -> engines/ -> models/` layered architecture. The work is new models, new pure-computation engines, service extensions, and frontend component restructuring. This is a well-scoped milestone with no technology risk.

The biggest risk is **data availability for the eligibility engine**. The engine needs hire date, performance rating, and disciplinary data that do not exist in the current schema. The `Employee` model has no `hire_date` column; no performance or disciplinary models exist anywhere in the codebase. The engine must treat missing data as a distinct `data_missing` status (not pass, not fail) and remain advisory rather than blocking. Schema additions via Alembic migration must come before engine logic. The second major risk is **file sharing modifying the dedup hard-block** in `FileService._check_duplicate()`, which is called in 4 places -- this requires a new method rather than modifying the existing one.

The recommended approach: start with navigation restructuring (zero-risk frontend foundation), then account binding (quick win using existing service), then eligibility engine (core business logic with schema prerequisites), then file sharing (most complex, highest risk), and finish with display simplification (polish pass that integrates the eligibility badge).

## Key Findings

### Stack Decisions / 技术栈决策

No new pip or npm packages. The existing stack handles all 5 features. See [STACK.md](./STACK.md) for full analysis.

**Unchanged core:**
- FastAPI 0.115.0 + SQLAlchemy 2.0.36 + Alembic 1.14.0 -- backend
- React 18.3.1 + TypeScript 5.8.3 + Tailwind 3.4.17 + Vite 6.2.6 -- frontend

**Explicitly rejected additions:**
- React Query / TanStack Query -- inconsistent with existing useEffect+useState pattern across 18+ pages
- Ant Design / Headless UI / Radix -- menu grouping is standard HTML/CSS, not worth a component library
- WebSocket / SSE -- file sharing notifications use polling, no real-time infrastructure needed
- State management (Redux/Zustand) -- none of the 5 features add cross-cutting state

**Database changes required (single Alembic migration):**
- 3 new nullable columns on `employees`: `hire_date`, `last_raise_date`, `performance_rating`
- 1 new table: `file_share_requests`
- 1 new table: `eligibility_overrides`

### Feature Priorities / 功能优先级

See [FEATURES.md](./FEATURES.md) for full landscape.

**Must have (table stakes for v1.1):**
- Grouped navigation sidebar -- 13 flat links for admin is unmanageable
- Manual account-employee binding UI -- backend service exists, no UI exposure
- Salary eligibility pre-check engine -- HR needs this before salary computation
- File duplicate warning (soft) instead of hard rejection -- current behavior breaks co-author workflows
- File share request workflow -- co-authors need legitimate access to shared files
- Collapsible salary details -- information overload in current flat display

**Should have (differentiators):**
- Self-service employee binding via id_card_no match
- Batch eligibility check for entire department
- Missing data import link from eligibility UI
- Contribution percentage negotiation in share requests

**Defer to v2+:**
- Real-time notifications (WebSocket) -- no infrastructure, polling sufficient
- SSO/LDAP binding integration -- manual binding covers 90% of cases
- Configurable eligibility rules UI -- hardcode 4 rules, externalize thresholds only
- Drag-and-drop nav reordering -- over-engineering

### Architecture Integration / 架构集成方式

See [ARCHITECTURE.md](./ARCHITECTURE.md) for component map and data flows.

All features integrate into the existing layered architecture. No new layers needed. The principle: **add new components alongside existing ones, modify existing ones minimally.**

**New components (create from scratch):**
1. `EligibilityEngine` (engines/) -- pure computation, no I/O, follows EvaluationEngine/SalaryEngine pattern
2. `EligibilityService` (services/) -- assembles data from DB, calls engine
3. `FileShareService` (services/) -- request/approve/reject lifecycle
4. `FileShareRequest` model (models/) -- separate from ProjectContributor and ApprovalRecord
5. Frontend: `ShareRequestPanel`, `ShareRequestList`, `EligibilityBadge`, `CollapsibleSection`, `SalarySummaryRow`, `SalaryDetailPanel`

**Modified components (extend existing):**
1. `IdentityBindingService` -- add `manual_bind()`, `unbind()`, `get_binding_status()`
2. `FileService` -- change dedup from reject to warn+share (new method, NOT modify `_check_duplicate()`)
3. `roleAccess.ts` -- add `NavGroup` interface, `getRoleNavGroups()` function
4. `AppShell.tsx` -- grouped sidebar rendering
5. `SalaryResultCard.tsx` -- collapsible two-tier display

### Critical Pitfalls / 关键风险

See [PITFALLS.md](./PITFALLS.md) for all 13 pitfalls with prevention strategies.

1. **Eligibility engine depends on non-existent data** -- `Employee` has no `hire_date`; no performance/disciplinary models exist. Prevention: add nullable columns via migration FIRST, treat NULL as `data_missing` (distinct from pass/fail), make engine advisory not blocking.

2. **File sharing breaks existing dedup hard-block** -- `_check_duplicate()` raises ValueError in 4 call sites. Prevention: create NEW method for sharing detection, do NOT modify existing method. Return warning payload instead of 409 error.

3. **SQLite/PostgreSQL migration drift** -- dev uses SQLite, prod uses PostgreSQL. `init_database()` auto-creates tables bypassing Alembic. Prevention: every schema change MUST produce an Alembic migration, new columns nullable first, use `batch_alter_table` for SQLite compatibility.

4. **Stale JWT claims after binding change** -- JWT carries old `employee_id` for up to 30 min. Prevention: invalidate refresh token on bind/unbind, add `binding_updated_at` timestamp, compare vs `token.iat`.

5. **Menu restructuring breaks deep links** -- if route paths change, bookmarks break. Prevention: visual-only grouping, do NOT change route paths, keep `getRoleModules()` for backward compatibility.

## Implications for Roadmap

### Phase 1: Menu/Navigation Restructuring (菜单导航重构)
**Rationale:** Zero backend changes, zero risk, sets up navigation structure for all subsequent features that add new pages/sections. Unblocks Feature 1 and Feature 4 which need nav slots.
**Delivers:** Grouped sidebar navigation for all roles; cleaner workspace page grid.
**Addresses:** Feature 3 (grouped navigation sidebar)
**Avoids:** Pitfall 5 (deep link breakage) -- visual-only grouping, no URL changes.
**Estimated complexity:** Low
**Needs phase research:** No -- standard frontend refactoring pattern.

### Phase 2: Account-Employee Binding Hardening (账号-员工绑定加固)
**Rationale:** Quick win with high user demand. Backend service already exists (`IdentityBindingService`), just needs 3 new methods and UI exposure. Self-contained with no external dependencies.
**Delivers:** Admin manual bind/unbind UI, self-service employee binding, binding status display.
**Addresses:** Feature 1 (account binding) + differentiator (self-service binding)
**Avoids:** Pitfall 4 (stale JWT) -- must invalidate tokens on binding changes.
**Estimated complexity:** Low
**Needs phase research:** No -- extends existing service with established patterns.

### Phase 3: Schema Foundation + Eligibility Engine (调薪资格校验引擎)
**Rationale:** Core business logic that HR needs before salary computation. Requires Alembic migration for Employee model extensions (hire_date, last_raise_date, performance_rating). Should be done before file sharing because it is isolated (new engine, new service, new API) and does not modify existing code. May reveal data import gaps early.
**Delivers:** Eligibility pre-check per employee, batch eligibility view, eligibility badge component, eligibility override mechanism for HR.
**Addresses:** Feature 4 (eligibility engine) + differentiators (batch check, missing data import link)
**Avoids:** Pitfall 1 (missing data) -- nullable columns, `data_missing` status, advisory not blocking. Pitfall 3 (override bypass) -- per-cycle overrides with audit. Pitfall C1 (migration drift) -- proper Alembic migration. Pitfall 8 (Feishu attendance) -- check synced_at, handle NULLs.
**Estimated complexity:** Medium
**Needs phase research:** Yes -- data source mapping for 4 rules, NULL handling strategy, override permission model.

### Phase 4: File Upload Sharing/Approval (文件上传共享申请机制)
**Rationale:** Most complex feature: new model, new service, new API, frontend components, AND modifies existing FileService dedup logic. Placed after eligibility because it touches critical upload path and needs the most careful implementation. Navigation and binding should be stable before this.
**Delivers:** Duplicate warning (soft) instead of hard rejection, share request workflow, approval/rejection flow, file cloning on approval, pending request notifications (polling-based).
**Addresses:** Feature 2 (file sharing) + differentiator (contribution negotiation)
**Avoids:** Pitfall 2 (dedup hard-block) -- new method, separate model. Pitfall 7 (no notifications) -- badge + pending actions page, 72h auto-approve timeout.
**Estimated complexity:** Medium-High
**Needs phase research:** Yes -- dedup refactor strategy across 4 call sites, notification UX pattern, share-vs-contributor semantic boundary.

### Phase 5: Salary Display Simplification (调薪建议展示精简)
**Rationale:** Pure frontend polish pass. Depends on Phase 3's EligibilityBadge component for integration. Best done last as it improves presentation of existing data plus new eligibility data.
**Delivers:** Collapsible salary details with summary-first layout, eligibility badge integration, reusable CollapsibleSection component.
**Addresses:** Feature 5 (display simplification)
**Avoids:** Pitfall 6 (hiding approver info) -- auto-expand for approvers, collapsed summary includes all critical metrics.
**Estimated complexity:** Low
**Needs phase research:** No -- standard React component refactoring.

### Phase Ordering Rationale

- **Dependency chain:** Feature 3 (nav) provides slots for Features 1 and 4. Feature 4 (eligibility) provides the badge used in Feature 5 (display).
- **Risk escalation:** Phases go from lowest risk (pure frontend) to highest risk (FileService modification). Stable foundation before risky changes.
- **Schema first:** Phase 3 includes the Alembic migration that adds Employee columns AND creates new tables. All schema changes in one migration prevents drift.
- **Independent parallelism:** Phases 1+2 could potentially run in parallel (different layers, no conflicts). Phases 3+5 are sequential (badge dependency).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Eligibility Engine):** Data source mapping for 4 rules is partially undefined -- performance rating has no source, disciplinary records have no model. Needs decision on whether to add models or defer rules.
- **Phase 4 (File Sharing):** Dedup refactor touches 4 call sites in FileService. Needs careful plan for which callers get warning behavior vs hard-block. Instance-state bug (`self._confirmations` dict) should be fixed as part of this phase.

Phases with standard patterns (skip phase research):
- **Phase 1 (Navigation):** Well-documented React pattern, pure frontend refactoring.
- **Phase 2 (Binding):** Extends existing IdentityBindingService with 3 methods. Pattern established.
- **Phase 5 (Display):** Standard collapsible component pattern, no API changes.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct codebase inspection of requirements.txt and package.json; all features verified implementable with existing libraries |
| Features | HIGH | All 5 features directly specified in PROJECT.md; dependency graph verified against codebase |
| Architecture | HIGH | Component map verified against existing models, services, engines; patterns match established codebase conventions |
| Pitfalls | HIGH | All pitfalls verified via direct code inspection with specific file/line references; grep results confirm schema gaps |

**Overall confidence:** HIGH -- all research based on direct codebase analysis, not external documentation.

### Gaps to Address

- **Performance rating data source:** No model, no import channel, no Feishu mapping. Decision needed: add `PerformanceRecord` model with CSV import, or defer the performance eligibility rule to v1.2. Recommendation: defer rule, mark as `data_missing`.
- **Disciplinary record data source:** Same gap as performance. No model exists. Recommendation: defer rule, mark as `data_missing`.
- **File share notification UX:** No notification infrastructure exists. Polling-based badge is the recommendation, but exact placement (sidebar badge? page header? MyReview section?) needs design decision.
- **Eligibility engine thresholds:** Tenure >= 6 months? >= 3 months? Attendance <= 30 days or >= 95% rate? Exact thresholds need business confirmation. Recommendation: make thresholds engine constructor parameters with reasonable defaults.
- **Auto-approve timeout for share requests:** 72h recommended but needs business confirmation. Could be per-cycle configurable.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection at `D:/wage_adjust/` -- all models, services, engines, frontend components, migrations, configuration files
- `.planning/PROJECT.md` -- milestone scope and feature definitions
- `requirements.txt` + `frontend/package.json` -- dependency inventory
- `alembic/versions/` -- 9 existing migrations confirming migration patterns

### Secondary (MEDIUM confidence)
- Existing engine patterns (`EvaluationEngine`, `SalaryEngine`) -- used as templates for eligibility engine design
- Existing `IdentityBindingService` + `ProjectContributor` -- used as templates for binding and sharing designs

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
