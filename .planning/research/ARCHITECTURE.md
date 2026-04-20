# Architecture Research — v1.4 Integration Design

**Domain:** Enterprise salary adjustment platform (existing layered monorepo)
**Researched:** 2026-04-20
**Confidence:** HIGH (read of all current integration surfaces; no new architectural layers introduced)

## Scope and Guiding Principle

v1.4 does NOT change the backend layering (`api/` → `services/` → `engines/` → `models/`) nor the frontend layering (`pages/` → `services/` → `types/api.ts`). Every new feature is either (a) a new vertical slice that follows the existing convention, or (b) a method added to an existing service/engine. No shared abstractions are rewritten.

Quality constraints preserved from existing architecture:
- AccessScopeService remains the single permission gate for employee resources
- EligibilityEngine, SalaryEngine, EvaluationEngine stay pure (no DB, no I/O)
- Alembic stays the sole migration path; batch_alter_table for SQLite compatibility
- Celery + Redis async tasks remain opt-in; no new hard Redis dependency

---

## Standard Architecture (Unchanged)

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                       React SPA (frontend/)                          │
│  pages/        components/       services/        types/api.ts       │
│       └────────┬─────────┘              │              │             │
│                ↓                        ↓              │             │
│          AppShell + ROLE_MODULES        api.ts (Axios) │             │
└────────────────────────────┬────────────────────────────┬───────────┘
                             │ HTTP /api/v1/*             │
                             ↓                            ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  FastAPI backend (backend/app/)                      │
│ api/v1/ (routers) → services/ (business logic) → engines/ (compute) │
│              ↓                    ↓                                  │
│       dependencies.py       AccessScopeService                       │
│       require_roles()        ensure_*_access()                       │
│              ↓                    ↓                                  │
│                     models/ (SQLAlchemy ORM)                         │
│                            ↓                                         │
│              core/database.py (Base, SessionLocal)                   │
└─────────────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
          SQLite/PG      Redis(opt)    Celery workers
          (primary)     (rate limit,   (imports + feishu sync)
                         task broker)
```

### Component Responsibilities (v1.4 additions in **bold**)

| Layer | Component | Responsibility | v1.4 Change |
|-------|-----------|---------------|-------------|
| api/v1 | `eligibility.py` | Eligibility query + override workflow | **Add `GET /eligibility/me`** (employee self-read) |
| api/v1 | `eligibility_import.py` | Feishu + Excel eligibility data imports | **Unchanged; bug fixes only** |
| api/v1 | `employees.py` | Employee CRUD | No change — tier is NOT on this response |
| api/v1 | `imports.py` | General batch imports | **Unchanged router; add `hire_info` + `non_statutory_leave` types at service layer** |
| api/v1 | **`performance.py`** *(new)* | Dedicated performance grade management | **New** — thin wrapper listing PerformanceRecord + tier distribution |
| services | `EligibilityService` | Eligibility computation orchestration | **Add `check_self(user)` method** (resolves user.employee_id, calls `check_employee`) |
| services | `FeishuService` | Feishu bitable sync | **Extend `sync_performance_records` + `sync_salary_adjustments` + `sync_hire_info` + `sync_non_statutory_leave` to write `FeishuSyncLog` entries** (currently only `sync_attendance` writes sync_log) |
| services | `ImportService` | Excel/CSV import + templates | **Fix `_map_fields` + verify xlsx dtype preservation + add `hire_info` + `non_statutory_leave` types** |
| services | **`PerformanceService`** *(new)* | Performance record query + tier distribution | **New** — owns list/filter/summary queries; tier classification delegated to engine |
| engines | `EligibilityEngine` | 4-rule eligibility computation (pure) | **Unchanged** |
| engines | **`PerformanceTierEngine`** *(new)* | Rank → 1/2/3 tier with 20/70/10 distribution + <50 sample gate | **New pure engine** — input: sorted list of `(employee_id, grade)`, output: `{employee_id: tier}` or `{}` when sample < threshold |
| models | `PerformanceRecord` | Annual performance grade A/B/C/D/E | **Unchanged schema** (tier is derived, not stored) |
| models | `FeishuSyncLog` | Feishu sync run metadata | **Extend:** add `mode` values `performance_grades`, `salary_adjustments`, `hire_info`, `non_statutory_leave` — no schema change, just new valid string values |

---

## Integration-Point Map (v1.4 Feature-by-Feature)

### 1. 员工端调薪资格自助可见

**Backend**

| File | Change | Detail |
|------|--------|--------|
| `backend/app/api/v1/eligibility.py` | **Add endpoint** `GET /eligibility/me` | Uses `get_current_user` only (no `require_roles` — any authenticated user including `employee`). Resolves `current_user.employee_id`; returns 404 if user is not bound to any employee. Delegates to `EligibilityService.check_employee(employee_id)`. |
| `backend/app/services/eligibility_service.py` | **Add method** `check_self(user: User)` | Guards: user must have `employee_id` set (via account-binding). Reuses `check_employee()` — zero duplication of rule logic. Reuses `_apply_overrides()` so an approved override is transparent to the employee. |
| `backend/app/schemas/eligibility.py` | **Reuse `EligibilityResultSchema`** | Same schema as HR/manager view. Internal field `detail` for each rule is already human-readable (e.g. "入职仅 3 个月，需满 6 个月"). No new schema needed. |

**Permission model:** NOT routed through `AccessScopeService` — self-access is fundamentally different (no cross-employee lookup). The existing `AccessScopeService.ensure_employee_access()` is for admin/hrbp/manager accessing OTHER employees. For self-access we use `user.employee_id` directly, which is the same pattern used by `/api/v1/submissions/me` (existing).

**Frontend**

| File | Change | Detail |
|------|--------|--------|
| `frontend/src/pages/MyReview.tsx` | **Extend existing page** | Do NOT create `/my-eligibility`. Add a new section/tab "调薪资格" to MyReview — employee self-service is unified on one route. Matches `ROLE_HOME_PATHS['employee'] = '/my-review'` convention. |
| `frontend/src/components/eligibility/MyEligibilityPanel.tsx` | **New component** | Renders 4 rules with pass/fail badges; failed rules show `detail` and a short "如何补齐" hint. Reuses `RULE_STATUS_BADGE` constants from `EligibilityListTab.tsx` (extract to `eligibility/badgeConfig.ts`). |
| `frontend/src/services/eligibilityService.ts` | **Add function** `fetchMyEligibility()` | Returns same `EligibilityBatchItem['rules']` shape. |

**Rejected alternatives:**
- ~~New `/my-eligibility` route~~ — fragments the employee home surface; MyReview already aggregates personal evaluation state
- ~~Make `EligibilityListTab` role-aware~~ — conflates HR-batch-view and employee-self-view, each has different actions (HR: export, override-request; employee: none)

---

### 2. 绩效档次 + 独立绩效管理页 + 历史绩效展示

**Tier calculation placement decision:** **NEW pure engine `PerformanceTierEngine`**.

Rationale:
- `EligibilityEngine` stays focused on the 4 salary eligibility rules; tier computation is a separate concern (distribution, not pass/fail)
- Lives alongside other engines at `backend/app/engines/performance_tier_engine.py`, inherits the "no I/O, no DB" convention
- Accepts a sorted list of `(employee_id, grade)` and returns `{employee_id: tier (1|2|3) | None}`; `None` when sample < threshold

**Pseudocode:**

```python
# backend/app/engines/performance_tier_engine.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class TierThresholds:
    min_sample_size: int = 50
    top_pct: float = 0.20   # tier 1
    mid_pct: float = 0.70   # tier 2
    # tier 3 = remainder (0.10)

class PerformanceTierEngine:
    def __init__(self, thresholds: TierThresholds | None = None) -> None:
        self.t = thresholds or TierThresholds()

    def assign(self, ranked: list[tuple[str, str]]) -> dict[str, int | None]:
        """Input already sorted best→worst. Returns {employee_id: tier|None}.
        Returns {eid: None} for every id when len < min_sample_size."""
        if len(ranked) < self.t.min_sample_size:
            return {eid: None for eid, _ in ranked}
        n = len(ranked)
        t1_cut = int(round(n * self.t.top_pct))
        t2_cut = t1_cut + int(round(n * self.t.mid_pct))
        return {
            eid: (1 if idx < t1_cut else 2 if idx < t2_cut else 3)
            for idx, (eid, _grade) in enumerate(ranked)
        }
```

**Caching strategy:** **NO Redis dependency for v1.4**. Justification:
- Tier values change only when a new performance import completes — low write frequency
- Full-company tier map for ~10k employees is a ~200 KB Python dict, computed in <50 ms from indexed `(year, grade)` query
- Use `functools.lru_cache` at service layer keyed by `year` with a manual `invalidate()` call after performance import finishes
- If latency becomes a problem later, drop in `cache_service.py` (existing Redis wrapper with in-memory fallback) without changing the engine

**Independent 绩效管理 page — routing, nav, permission:**

| Aspect | Decision |
|--------|----------|
| Backend prefix | `/api/v1/performance` (new router `backend/app/api/v1/performance.py`) |
| Frontend route | `/performance` |
| Nav group | `系统管理` (same group as `导入中心` + `飞书配置`) — it's a data-ops surface, not an operational workflow |
| Roles | admin + hrbp only (matches attendance/feishu-config pattern) |
| Existing nav overlap | `调薪资格` page already handles performance_grades import via ELIGIBILITY_IMPORT_TYPES — keep that as the *import path* unchanged; new page is a *read/list* surface |

**Endpoints on `/api/v1/performance`:**
- `GET /performance/records` — list with filters (year, department, grade), paginated
- `GET /performance/tier-summary?year=2025` — returns `{year, sample_size, tier_1_count, tier_2_count, tier_3_count, insufficient_sample: bool}`
- `GET /performance/me/tier?year=2025` — employee self-read (returns `{tier: 1|2|3|null, year, sample_size, insufficient_sample}`)

**Rejected: embed `/me/tier` into `GET /employees/me`** — employee identity endpoint should not expand with derived per-year data; year is a query parameter.

**Evaluation detail / salary recommendation history display:**

| Frontend file | Change |
|---------------|--------|
| `frontend/src/pages/EvaluationDetail.tsx` | Insert new `PerformanceHistoryPanel` component between evidence and dimension score sections |
| `frontend/src/components/salary/` (existing salary recommendation detail component) | Insert same panel above/adjacent to multiplier explanation |
| `frontend/src/components/performance/PerformanceHistoryPanel.tsx` *(new)* | Fetches `GET /eligibility/{employee_id}/performance-records` (already exists) and renders a 3-year-max table with grade and source |

The backend endpoint `GET /eligibility/{employee_id}/performance-records` **already exists** (`eligibility.py:315`). No new API needed for the history view — only a new frontend component.

**Employee-end tier display:** surfaces inside `MyReview.tsx` next to the eligibility panel — single round-trip via `/api/v1/performance/me/tier?year={currentCycleYear}`.

---

### 3. 工号前导零保留

**Root cause:** `employee_no` is already `String(64)` in the DB model. Leading zeros are lost at three upstream points:

| Location | Current behavior | Fix |
|----------|-----------------|-----|
| `ImportService._load_table` (CSV) | `dtype=str` already set on `pd.read_csv(..., dtype=str)` — correct | ✓ No change |
| `ImportService._load_table` (xlsx) | `dtype=str` already set on `pd.read_excel(..., engine='openpyxl', dtype=str)` — but openpyxl reads cells by cell-type; numeric cells become float before dtype coercion | **Verify** with test case; if lost, read with `keep_default_na=False` + iterate cells as strings via `str(cell.value)` when cell.data_type == 'n' |
| `FeishuService._map_fields` (line 240-245) | `if isinstance(value, float) and value == int(value): value = str(int(value))` — **THIS STRIPS LEADING ZEROS** because Feishu number fields are always float (e.g. `02615.0` → `"2615"`) | **Fix:** when the field_mapping target is `employee_no`, always treat the raw cell as text; prefer the Feishu field's `text` sub-property from `_extract_cell_value` over the numeric coercion |
| Manual create (`EmployeeCreate` schema + `EmployeeService.create_employee`) | Pydantic string field; no coercion issue | ✓ No change, but add Pydantic `field_validator` to **reject** implicit int-to-str |

**Storage-side guarantees (already in place):**
- `Employee.employee_no` is `String(64)` with unique index — preserves zeros
- `FeishuService._build_employee_map()` already tolerates leading-zero mismatch by indexing both `"02615"` and `"2615"` — a defensive layer that masks upstream bugs but does NOT fix the storage problem

**Existing-data repair:** Two-step:
1. **Alembic data migration** `v14_01_restore_employee_no_leading_zeros.py`:
   - For each `Employee` row where `employee_no` is all-digits and a corresponding Feishu employee row exists with a longer zero-prefixed form, update
   - Safe because `employee_no` has unique constraint; conflicts are expected to be zero (prod data shouldn't have both forms)
2. **One-off script** `scripts/repair_employee_no_zeros.py` that dry-runs the migration first, prints diff, requires `--commit` flag to apply

**Prevention (new Pydantic validator):**

```python
# backend/app/schemas/employee.py (add to EmployeeCreate + EmployeeUpdate)
from pydantic import field_validator

class EmployeeBase(BaseModel):
    employee_no: str
    @field_validator('employee_no', mode='before')
    @classmethod
    def _preserve_leading_zeros(cls, v):
        if isinstance(v, (int, float)):
            raise ValueError('employee_no must be provided as a string to preserve leading zeros.')
        return str(v).strip()
```

**FeishuService._map_fields fix (load-bearing):**

```python
if system_name == 'employee_no':
    has_employee_no = True
    # Always treat as text — NEVER int-coerce.
    # Raw Feishu number fields come as float (e.g. 2615.0); but Feishu rich-text
    # fields preserve string form in .text property (handled in _extract_cell_value
    # when first dict element has 'text' key). For pure numeric bitable cells,
    # we still need to format without losing zeros.
    if isinstance(raw_value, (int, float)) or (
        isinstance(value, float) and value == int(value)
    ):
        # FIX: don't use int(value); prefer Feishu "text" subfield if present
        raw_text = _prefer_text_over_numeric(raw_value)
        value = raw_text if raw_text is not None else str(value).rstrip('0').rstrip('.') or '0'
    else:
        value = str(value).strip()
```

The helper `_prefer_text_over_numeric` inspects Feishu's raw cell for a text subfield before falling back to the numeric form. This is the cleanest fix at the mapping layer; no downstream change needed.

---

### 4. 调薪资格导入修复（飞书同步根因 + Excel 模板 + 覆盖更新）

**Root cause of "飞书同步成功但未落库":** `sync_performance_records`, `sync_salary_adjustments`, `sync_hire_info`, `sync_non_statutory_leave` do NOT create `FeishuSyncLog` rows (only `sync_attendance` does — see `feishu_service.py:288-437`). They also do NOT track `unmatched_count`; employees whose `employee_no` doesn't match are silently `skipped` with only a `logger.warning`.

**Integration fix:**

| Change | Location | Detail |
|--------|----------|--------|
| **Wrap all 4 eligibility sync methods with sync-log scaffolding** | `feishu_service.py:461-862` | Extract a private `_with_sync_log(mode, triggered_by, fn)` helper that: (a) creates FeishuSyncLog at start; (b) runs fn which returns counts; (c) updates sync_log + commits in final block; (d) on exception, writes failure log in a fresh session (matching existing `sync_attendance` pattern). Apply to all 4 eligibility sync methods. |
| **Track unmatched employee_nos** | Same 4 methods | Mirror the `unmatched_nos` list in `sync_attendance` — write top-20 to `sync_log.unmatched_employee_nos`. This is the *primary diagnostic* HR needs when "sync succeeded but data missing." |
| **Expose sync logs in UI** | `frontend/src/pages/EligibilityManagementPage.tsx` | Add a "同步日志" tab that calls existing `FeishuService.get_sync_logs(limit=20)` — already exists, currently only rendered on attendance page. |

**Upsert semantics decision — (employee_id, cycle_id) vs (employee_no, cycle_id):**

`PerformanceRecord` and `SalaryAdjustmentRecord` do NOT have `cycle_id`. They have:
- `PerformanceRecord`: UNIQUE `(employee_id, year)` — correct; `year` is the natural performance period key
- `SalaryAdjustmentRecord`: NO unique constraint — multiple adjustments per year are legitimate (probation + annual + special)

**Decision:** Keep employee_id as upsert key (via the existing `emp_map` leading-zero-tolerant lookup). Do NOT introduce `cycle_id` on these tables — salary cycles and performance years are separate concepts. When the UI reports conflict, return:

```json
{
  "conflict": {
    "employee_no": "02615",
    "year": 2025,
    "existing_grade": "B",
    "incoming_grade": "A",
    "action": "overwrite"
  }
}
```

Current code already does silent overwrite; the v1.4 fix is to **log** each overwrite to the result_summary so HR sees what changed. No schema change needed.

**Excel 模板下载修复:** Both `GET /api/v1/imports/templates/{import_type}` (`imports.py:96`) and `GET /api/v1/eligibility-import/templates/{import_type}` (`eligibility_import.py:127`) already exist and call `ImportService.build_template_xlsx`.

**Likely root cause of "模板下载返回非真实文件":** `ELIGIBILITY_IMPORT_TYPES = {'performance_grades', 'salary_adjustments', 'hire_info', 'non_statutory_leave'}` (`eligibility_import.py:6` / `schemas/eligibility_import.py`) but `ImportService.SUPPORTED_TYPES = {'employees', 'certifications', 'performance_grades', 'salary_adjustments'}`. **`hire_info` and `non_statutory_leave` are missing from `ImportService.SUPPORTED_TYPES`**, so the template endpoint at `eligibility_import.py:143-146` would raise `ValueError('Unsupported import type.')` for those two types. Fix: add these to `SUPPORTED_TYPES` + `REQUIRED_COLUMNS` + `COLUMN_ALIASES` + new `_import_hire_info` / `_import_non_statutory_leave` methods in `ImportService` + branch coverage in `build_template_xlsx`.

**Task status feedback:** Existing `Celery taskPolling` mechanism via `taskService.ts` + `TaskTriggerResponse` is reused as-is. No change.

---

### 5. Phase 11 导航菜单验证补齐

**Inputs:**
- Current state (per PROJECT.md Known Issues): code in repo, no SUMMARY.md, UAT not run
- v1.4 introduces new menu entries: `我的资格` (under employee `personal` group — as a tab in /my-review, not a new href) and `绩效管理` (under admin/hrbp `系统管理` group)

**SUMMARY.md补齐 content checklist (targeted at `.planning/milestones/v1.1/phases/phase-11/SUMMARY.md` if that milestone folder still exists, otherwise under v1.4's phase for navigation-restructuring):**
- Problem statement: what Phase 11 changed in nav structure (ROLE_MODULES restructuring)
- Before/After: ROLE_MODULES diff
- UAT checklist: one row per role (admin/hrbp/manager/employee) with click-through evidence

**Nav entries for v1.4:**

| Entry | Role(s) | Path | Group | Icon |
|-------|---------|------|-------|------|
| 绩效管理 | admin, hrbp | `/performance` | 系统管理 | `trending-up` |
| 调薪资格（我的） | employee | (tab within `/my-review`) | personal (no new href) | N/A |

Employee "我的资格" is not a new top-level menu — it is a tab inside MyReview page. Keeps the `employee` role's menu concise (3 items maximum).

---

## Integration Matrix

Files/surfaces touched in v1.4, sorted by risk:

| File | Type | Risk | Change |
|------|------|------|--------|
| `backend/app/services/feishu_service.py` | Modified | **HIGH** | `_map_fields` employee_no fix (fragile path); extend 4 sync methods with sync_log scaffolding |
| `backend/app/services/import_service.py` | Modified | MEDIUM | Add `hire_info` + `non_statutory_leave` to SUPPORTED_TYPES + handlers; dtype verification |
| `backend/app/services/eligibility_service.py` | Modified | LOW | Add `check_self(user)` — thin wrapper |
| `backend/app/api/v1/eligibility.py` | Modified | LOW | Add `/me` endpoint |
| `backend/app/api/v1/performance.py` | **New** | LOW | Thin router delegating to new service |
| `backend/app/services/performance_service.py` | **New** | LOW | Query + tier assembly, delegates to engine |
| `backend/app/engines/performance_tier_engine.py` | **New** | LOW | Pure function; fully unit-testable |
| `backend/app/schemas/employee.py` | Modified | LOW | Add `field_validator` for employee_no |
| `backend/app/schemas/performance.py` | **New** | LOW | `PerformanceRead`, `TierSummary`, `MyTier` |
| `alembic/versions/v14_01_restore_employee_no_leading_zeros.py` | **New** | **HIGH** | Data migration; irreversible without backup. Required `--dry-run` first |
| `frontend/src/pages/MyReview.tsx` | Modified | LOW | Add eligibility + tier panels |
| `frontend/src/pages/PerformanceManagement.tsx` | **New** | LOW | List + tier summary |
| `frontend/src/components/performance/PerformanceHistoryPanel.tsx` | **New** | LOW | Reused by EvaluationDetail and SalaryDetail |
| `frontend/src/components/eligibility/MyEligibilityPanel.tsx` | **New** | LOW | Standalone rendering of 4-rule result |
| `frontend/src/services/performanceService.ts` | **New** | LOW | API client wrapper |
| `frontend/src/services/eligibilityService.ts` | Modified | LOW | Add `fetchMyEligibility` |
| `frontend/src/types/api.ts` | Modified | LOW | New interfaces: `PerformanceTierSummary`, `MyTierResult` |
| `frontend/src/utils/roleAccess.ts` | Modified | LOW | Add `绩效管理` entry for admin + hrbp |
| `frontend/src/App.tsx` | Modified | LOW | Add `/performance` route with `allowedRoles=["admin","hrbp"]` |

**No conflicts with existing v1.3 work:** the touchpoints are additive (new files) or on well-bounded methods that have had no churn in the current git working tree (observed: eligibility service last modified during v1.1).

---

## New vs Modified

**All-new files (10):**
1. `backend/app/api/v1/performance.py`
2. `backend/app/services/performance_service.py`
3. `backend/app/engines/performance_tier_engine.py`
4. `backend/app/schemas/performance.py`
5. `alembic/versions/v14_01_restore_employee_no_leading_zeros.py`
6. `scripts/repair_employee_no_zeros.py`
7. `frontend/src/pages/PerformanceManagement.tsx`
8. `frontend/src/components/performance/PerformanceHistoryPanel.tsx`
9. `frontend/src/components/eligibility/MyEligibilityPanel.tsx`
10. `frontend/src/services/performanceService.ts`

**Modified files (existing methods extended, not redesigned — 12):**
1. `backend/app/services/feishu_service.py` — sync_log scaffolding + `_map_fields` fix
2. `backend/app/services/import_service.py` — add 2 import types + dtype verification
3. `backend/app/services/eligibility_service.py` — `check_self` method
4. `backend/app/api/v1/eligibility.py` — `/me` endpoint
5. `backend/app/schemas/employee.py` — validator
6. `backend/app/schemas/eligibility_import.py` — (verify ELIGIBILITY_IMPORT_TYPES still in sync)
7. `frontend/src/pages/MyReview.tsx` — add tab / section
8. `frontend/src/pages/EvaluationDetail.tsx` — insert history panel
9. `frontend/src/utils/roleAccess.ts` — add menu entry
10. `frontend/src/App.tsx` — add route
11. `frontend/src/services/eligibilityService.ts` — add `fetchMyEligibility`
12. `frontend/src/types/api.ts` — new interfaces

---

## Suggested Build Order

**Rationale:** Data-foundation first, then pure-compute, then read-side features. Put the highest-risk (production data) work first with time to revert.

### Phase A — Data Integrity Foundation (HIGH risk, must ship first)

1. **A1 工号前导零修复 (schema validators + FeishuService._map_fields fix + repair script dry-run)**
   - Deliverables: Pydantic validator, `_map_fields` fix, dry-run output
   - Gate: Dry-run shows N employees would be updated; HR confirms list before commit
2. **A2 Alembic data migration execution**
   - Gate: Prod DB backup taken; migration runs; verification query confirms no duplicate `employee_no`

**Why first:** Every downstream feature (tier assignment, eligibility query, feishu re-sync) depends on stable employee_no values. Fixing later means re-running all imports.

### Phase B — Import Chain Fixes (MEDIUM risk, unblocks HR)

3. **B1 FeishuSyncLog scaffolding for 4 eligibility sync methods**
   - Deliverables: `_with_sync_log` helper, 4 methods wrapped, unmatched tracking
   - Gate: Test sync that intentionally has 3 unmatched employee_nos; verify sync_log shows 3 + employee_nos
4. **B2 ImportService: add hire_info + non_statutory_leave + template endpoint verification**
   - Deliverables: SUPPORTED_TYPES expanded, templates download correctly, xlsx dtype verified
5. **B3 Import result diagnostic (overwrite logging)**
   - Deliverables: result_summary rows include `action: overwrite` with old/new values for HR to review

**Why before performance features:** B1 diagnoses why v1.3 imports failed silently — without this, product is stuck re-diagnosing every import failure manually.

### Phase C — Performance Tier Foundation (MEDIUM risk, pure compute)

6. **C1 `PerformanceTierEngine` with tests (<50 sample, boundary rounding, tie handling)**
7. **C2 `PerformanceService` + `/api/v1/performance` router + schemas**
8. **C3 Alembic migration: none required** — tier is derived, not stored

**Why before employee-end:** tier API must be stable before wiring into MyReview.

### Phase D — Read-Side Features (LOW risk, employee-facing)

9. **D1 `EligibilityService.check_self` + `GET /eligibility/me`**
10. **D2 `PerformanceService.get_my_tier` + `GET /performance/me/tier`**
11. **D3 `MyEligibilityPanel` + `PerformanceTierBadge` inside MyReview**
12. **D4 `PerformanceHistoryPanel` inside EvaluationDetail + SalaryDetail**

### Phase E — Independent Performance Page (LOW risk)

13. **E1 `PerformanceManagement.tsx` + `/performance` route + nav entry**
14. **E2 Tier summary chart + filters**

### Phase F — Phase 11 Nav Closure (DOCS, no code change)

15. **F1 SUMMARY.md补齐 (phase 11 retrospective)**
16. **F2 UAT checklist for 4 roles × new + existing menu entries — include v1.4 新增的两个条目**

---

## Data Flow (v1.4 additions)

### Employee Self-Service Read (new)

```
employee opens /my-review
  ↓
MyReview.tsx useEffect fires 3 parallel requests:
  GET /api/v1/submissions/me           (existing)
  GET /api/v1/eligibility/me           (new — eligibility.py)
  GET /api/v1/performance/me/tier?year (new — performance.py)
  ↓
Backend: eligibility.py → EligibilityService.check_self(user)
         → resolves user.employee_id
         → delegates to check_employee() (SAME logic as HR batch view)
         → applies override (SAME as HR view — approved overrides are visible to employee too)
  ↓
MyEligibilityPanel renders 4 rules; MyTierBadge renders "您本年度处于档次 2/3 (前 70%)"
```

### Performance Tier Computation (new, full-company)

```
HR imports performance_grades (Excel or Feishu)
  ↓
PerformanceRecord rows inserted (existing flow)
  ↓
PerformanceService.invalidate_tier_cache(year=2025) called post-import
  ↓
Next request to /performance/me/tier or /performance/tier-summary:
  PerformanceService._ranked_employees(year=2025)   # SQL: ORDER BY grade
    → PerformanceTierEngine.assign(ranked)           # pure
    → {employee_id: 1|2|3} cached in LRU by year
  ↓
Response: {tier: 2, sample_size: 1247, insufficient_sample: false}
```

### Feishu Sync with Observability (fixed)

```
HR triggers feishu sync for performance_grades
  ↓
eligibility_import.py → feishu_sync_eligibility_task.delay(...)
  ↓
Celery worker → FeishuService.sync_performance_records(...)
  ↓ NEW: _with_sync_log wrapper
  FeishuSyncLog row created (status='running', mode='performance_grades')
  ↓
  Bitable records fetched
  ↓
  For each record:
    _lookup_employee(emp_map, emp_no)
    if unmatched: increment unmatched_count, append to unmatched_nos (top 20)
    else: upsert PerformanceRecord
  ↓ NEW:
  FeishuSyncLog updated: synced/updated/skipped/unmatched/failed counts, unmatched_employee_nos
  ↓
HR visits /eligibility?tab=sync-logs → sees 1247 fetched, 1243 synced, 4 unmatched (工号 "12345", "67890", ...)
```

---

## Architectural Patterns Reused (No New Patterns Introduced)

### Pattern: Service method with self-access specialization

**What:** Add `check_self(user)` sibling to `check_employee(employee_id)`. Self-methods resolve identity from `user` then delegate to the canonical method.

**When to use:** Employee-facing read endpoints where the subject is always the caller.

**Precedent in codebase:** `SubmissionService.get_for_employee_id` is already called from both batch and self-service paths; same shape.

### Pattern: Pure engine + service orchestrator

**What:** Put rules-and-math in `engines/*.py` with no DB/I/O; service layer queries data and calls the engine.

**Precedent:** `EligibilityEngine` + `EligibilityService`. New `PerformanceTierEngine` + `PerformanceService` follow identical shape.

### Pattern: Upsert by natural key with leading-zero tolerance

**What:** `FeishuService._build_employee_map()` indexes both zero-prefixed and stripped forms — masks upstream data quality but ensures no lost records.

**When to use:** Any integration layer that cannot guarantee upstream data cleanliness.

**Limitation:** Hides root cause (v1.4 fix addresses the actual cause, keeping the tolerance as defense-in-depth).

---

## Anti-Patterns to Avoid (v1.4-specific)

### Anti-Pattern 1: Storing tier on PerformanceRecord

**What people want to do:** Add `tier: Mapped[int]` to PerformanceRecord so it's denormalized and fast.

**Why wrong:** Tier depends on the *distribution* of all records in a year. Adding/removing one record shifts boundaries. A stored tier becomes stale the moment another import runs. Would need invalidation logic everywhere.

**Instead:** Always derive tier from `PerformanceTierEngine`. Cache at service layer keyed by year with explicit `invalidate(year)` after imports.

### Anti-Pattern 2: Creating `/my-eligibility` as a separate route

**What people want to do:** New route for discoverability.

**Why wrong:** Fragments the employee self-service experience; every new employee-facing feature would become its own route; menu sprawl.

**Instead:** MyReview is the single employee home. Add tabs/sections.

### Anti-Pattern 3: Piping employee tier through `/api/v1/employees/me`

**What people want to do:** Stick `tier` on the employee-me response payload so it ships with every auth check.

**Why wrong:** `GET /employees/me` is identity data (name, department, role). Tier is derived per-year analytics. Coupling them means every login roundtrip runs a tier computation.

**Instead:** Dedicated `GET /performance/me/tier?year=X` — called only when a UI component needs it.

### Anti-Pattern 4: Adding Redis as a hard dependency for tier cache

**What people want to do:** Use Redis to cache tier map across workers.

**Why wrong:** `cache_service.py` already has a Redis-with-in-memory-fallback design. Adding a required Redis path violates v1.2's no-hard-Redis-in-dev guarantee.

**Instead:** Start with `@lru_cache` on the service method; upgrade to `cache_service` later only if a multi-worker cache coherence problem appears.

### Anti-Pattern 5: Silently skipping unmatched Feishu records

**What the current code does:** `logger.warning` only; no persistent record of which employee_nos failed to match.

**Why wrong:** HR sees "sync successful" but some employees' data is missing; no way to diagnose without shell access.

**Instead:** Always record unmatched employee_nos in FeishuSyncLog + expose in UI.

---

## Scaling Considerations

| Scale | Tier engine | Sync log observability | Import throughput |
|-------|-------------|------------------------|-------------------|
| 0–1k employees | In-process dict, <10 ms per call | 20 log rows fits easily | Synchronous OK |
| 1k–10k employees | `@lru_cache` by year; ~200 KB dict | Already paginated; no change | Celery async already in place |
| 10k–100k | Move cache to Redis via `cache_service`; tier recomputation still <500 ms | Truncate `unmatched_employee_nos` to top 100 + link to paginated endpoint | Split by cycle or department chunks |

**First bottleneck at real scale:** `_build_employee_map()` in FeishuService loads ALL employees every sync. At 10k+, move to chunked lookup or DB-side JOIN. Out-of-scope for v1.4.

---

## Integration Points — External + Internal

### External Services

| Service | Integration Pattern | v1.4 Changes |
|---------|---------------------|--------------|
| Feishu Bitable | HTTP polling via `FeishuService._fetch_all_records` | Sync log scaffolding makes failures visible; no protocol change |
| DeepSeek LLM | Unchanged | — |
| Celery + Redis broker | Unchanged | — |

### Internal Boundaries

| Boundary | Communication | v1.4 Considerations |
|----------|---------------|---------------------|
| `MyReview` page ↔ `/eligibility/me` | HTTPS + JWT | Employee-scoped; no AccessScopeService (identity via user.employee_id) |
| `PerformanceService` ↔ `PerformanceTierEngine` | Direct function call | Engine is pure, fully unit-testable |
| `FeishuService._map_fields` ↔ `employee_no` validator | No runtime coupling (validator is Pydantic-layer) | Defense in depth: any `employee_no` leaving the API boundary now passes through validator |
| Alembic data migration ↔ runtime | One-shot at deploy | Dry-run + HR review before commit |

---

## Open Questions for Requirements/Roadmapping

Forwarded to downstream Requirements phase:

1. **Tier visibility for employees with `null` tier (sample < 50):** Show "样本不足 (需 ≥50 人)" or hide? — UX decision.
2. **Does tier refresh automatically after import, or require HR trigger?** — product decision; pure-engine supports both.
3. **Should `/eligibility/me` return 404 for unbound users or 200 with a "not linked to an employee record" message?** — consistency decision.
4. **Repair script gating: run once globally or per-department?** — ops decision; both are supported by the proposed script.
5. **Sync log UI: merge with existing attendance sync log page or create a unified log center?** — scope decision.

---

## Sources

- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/api/v1/eligibility.py` (existing `/batch` + `/{employee_id}` endpoints)
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/services/eligibility_service.py` (`check_employee`, `_apply_overrides`, `check_employees_batch`)
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/services/import_service.py` (SUPPORTED_TYPES gap; dtype handling)
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/services/feishu_service.py` (`_map_fields:240-245` leading-zero bug; `sync_attendance:288-437` sync_log pattern; missing sync_log on 4 eligibility methods)
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/engines/eligibility_engine.py` (pure-engine precedent for `PerformanceTierEngine`)
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/api/v1/eligibility_import.py` (ELIGIBILITY_IMPORT_TYPES includes `hire_info`, `non_statutory_leave` not in ImportService.SUPPORTED_TYPES)
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/models/performance_record.py` (UNIQUE(employee_id, year))
- `/Users/mac/PycharmProjects/Wage_adjust/backend/app/models/feishu_sync_log.py` (existing schema supports any `mode` string)
- `/Users/mac/PycharmProjects/Wage_adjust/frontend/src/utils/roleAccess.ts` (`ROLE_MODULES['employee']` personal group; `ROLE_HOME_PATHS['employee'] = '/my-review'`)
- `/Users/mac/PycharmProjects/Wage_adjust/frontend/src/App.tsx:432-433` (`<Route element={<MyReviewPage />} path="/my-review" />`)
- `/Users/mac/PycharmProjects/Wage_adjust/frontend/src/components/eligibility/EligibilityListTab.tsx` (shared `RULE_STATUS_BADGE` to be extracted)
- `/Users/mac/PycharmProjects/Wage_adjust/.planning/PROJECT.md` (v1.4 target features, layering constraints, Phase 11 known issue)
- `/Users/mac/PycharmProjects/Wage_adjust/.planning/codebase/ARCHITECTURE.md` (layering invariants: api → services → engines → models)

---
*Architecture research for: v1.4 employee-end eligibility visibility, performance tier, employee_no integrity, import chain stability*
*Researched: 2026-04-20*
