# Domain Pitfalls: v1.1 Feature Integration

**Domain:** Enterprise Salary Adjustment Platform -- v1.1 incremental features
**Researched:** 2026-03-30
**Overall confidence:** HIGH (all findings verified via direct codebase inspection)

> Covers pitfalls specific to 5 new v1.1 features. For foundational pitfalls (LLM pipeline, security, batch import, approval workflow, session management), see v1.0 research archive.

---

## Critical Pitfalls

### Pitfall 1: Eligibility Engine Depends on Data That Does Not Exist

**What goes wrong:** The salary eligibility engine requires 4 business rules from: hire date, salary history, performance data, attendance/leave. Verified schema gaps:
- `Employee` model has **no `hire_date` column** -- grep for `hire_date`, `entry_date`, `join_date` across all backend returns zero results
- **No `SalaryHistory` or `PerformanceRecord` model** -- grep for `performance` and `绩效` in models returns zero
- Attendance exists (`AttendanceRecord`) but `leave_days` added in migration `9d428de0df97` -- older records have NULLs
- Performance data source is undefined (manual? CSV? Feishu?)

**Why it happens:** Feature design assumes data availability without verifying schema.

**Consequences:**
- Engine ships as a facade -- every employee passes because rules cannot be checked
- If NULL treated as "pass": ineligible employees slip through. If NULL = "fail": flood of false negatives overwhelms exceptions
- Adding NOT NULL columns without defaults to existing Employee table fails on both SQLite and PostgreSQL

**Prevention:**
1. Map all 4 rules to data sources BEFORE coding: add `hire_date` (nullable) to Employee, derive salary history from approved `SalaryRecommendation`, create `PerformanceRecord` with import channel or defer rule, use `AttendanceRecord` with NULL handling
2. Treat NULL as distinct reason `data_missing` (not pass, not fail). Yellow "data pending" badge vs red "ineligible"
3. Return structured result: `{ eligible, rules: [{ rule, result: pass|fail|skipped, reason, data_source: available|missing|partial }] }`
4. Add data completeness dashboard before running eligibility checks
5. Eligibility is **advisory, not blocking** -- salary computation proceeds regardless; only HR/admin sees eligibility flags

**Detection:** If eligibility phase produces no Alembic migration, it is a facade. If >30% results are `data_missing`, import pipeline needs attention first.

**Phase:** Must be FIRST in eligibility engine phase. Schema + import channels are prerequisites.

---

### Pitfall 2: File Sharing Breaks the Existing Dedup Hard Block

**What goes wrong:** `FileService._check_duplicate()` (file_service.py lines 45-59) does global dedup on `(file_name, content_hash)`. `upload_files()` (lines 424-434) **raises ValueError to block upload**. The v1.1 requirement: "allow duplicate with warning + sharing request." These are contradictory -- current dedup is a hard block; new feature needs soft warning.

The method is called in at least 4 places: `upload_files()`, `upload_file()`, `import_github_file()`, `replace_file()`.

**Why it happens:** Original dedup was data integrity guard. New sharing reinterprets "duplicate" as collaboration signal.

**Consequences:**
- Modifying `_check_duplicate()` breaks all 4 callers if not all updated
- `ProjectContributor` tracks "co-authored this file" (percentages). File sharing means "reference this in my evaluation." Different semantics, different models.
- Instance-state bug: `self._confirmations` dict (line 209) stores dispute state in process memory -- lost on restart, invisible to other workers

**Prevention:**
1. Do NOT modify `_check_duplicate()`. Create new `_check_duplicate_for_sharing()` or move raise/allow decision to caller
2. Upload endpoint: if duplicate found, return `{ duplicate: true, existing_file_id, can_request_share: true }` instead of raising
3. Create new `FileShareRequest` model (NOT reuse `ProjectContributor`): `id, requester_submission_id, source_file_id, status, requested_at, decided_at`
4. Owner sets contribution percentage on approval, not requester
5. Auto-approve timeout (72h) to prevent indefinite blocking
6. Fix existing `self._confirmations` instance-state bug -- persist to DB

**Detection:** If feature modifies `_check_duplicate()` directly, it conflates concerns. If it reuses `ProjectContributor`, it confuses authorship with reference rights.

**Phase:** File sharing phase. Design data model BEFORE touching FileService.

---

### Pitfall C1: SQLite/PostgreSQL Migration Drift on New Schema

**What goes wrong:** SQLite in dev, PostgreSQL in prod. v1.1 adds columns and tables:
- `init_database()` (database.py line 69-78) calls `Base.metadata.create_all()` which auto-creates tables without migrations -- works in dev, breaks in prod
- SQLite lacks `ALTER TABLE ... ADD CONSTRAINT`, `ALTER COLUMN`
- `CHECK` constraints enforced INSERT-only in SQLite, INSERT+UPDATE in PostgreSQL
- NOT NULL columns without defaults fail on both DBs with existing rows

**Prevention:**
1. Every schema change MUST produce Alembic migration (9 already exist in `alembic/versions/`)
2. New columns on existing tables: nullable first, backfill, then tighten
3. Use Alembic `batch_alter_table` for SQLite-incompatible operations
4. Test `alembic upgrade head` on PostgreSQL before merging

**Detection:** New models in `backend/app/models/` without corresponding `alembic/versions/` file.

**Phase:** ALL phases. Every phase touching schema needs a migration.

---

## Moderate Pitfalls

### Pitfall 3: Eligibility Override Becomes Blanket Bypass

**What goes wrong:** Exception mechanism used too liberally. HR grants overrides for entire departments, disabling engine.

**Prevention:**
1. Overrides **per-cycle** (tied to `cycle_id`), not permanent
2. Structured reason enum: `data_not_imported` (temporary, auto-clears), `rule_not_applicable` (permanent), `executive_decision` (escalated approval)
3. Time-bound: `data_not_imported` has `expires_at`, re-checks when data arrives
4. Dashboard metric: alert if override rate >15%
5. Separate permission for "create exception" vs "approve salary"
6. All overrides create `AuditLog` entry

**Phase:** Eligibility engine phase. Design WITH core rules.

---

### Pitfall 4: Account Binding Changes Leave Stale JWT Claims

**What goes wrong:** `IdentityBindingService` binds `User.employee_id` via `id_card_no`. After unbinding/rebinding:
- JWT still carries old `employee_id` for up to 30 min (access) or 7 days (refresh)
- `get_current_user` reads from JWT, not DB -- stale claims grant wrong access
- Multiple binding paths (auto-bind via id_card_no, manual bind by admin) can race
- FK has no cascade -- deleting Employee leaves dangling `User.employee_id`

Additionally, manual bind can conflict with auto-bind: admin binds User A to Employee X, but Employee X's `id_card_no` matches User B. Both paths write to `User.employee_id`.

**Prevention:**
1. After any binding change, **invalidate refresh token** and force re-login
2. Add `binding_updated_at` to User; compare vs `token.iat` in `get_current_user`
3. Manual bind takes priority; auto-bind skips already-bound employees (check `Employee.bound_user`)
4. Add `binding_source` field to distinguish manual vs auto
5. Log all bind/unbind via AuditLog with `previous_employee_id`
6. Add ON DELETE SET NULL on `User.employee_id` FK

**Phase:** Account binding phase. Token lifecycle MUST ship with binding CRUD.

---

### Pitfall 5: Menu Restructuring Breaks Deep Links

**What goes wrong:** Flat routes (`/employees`, `/approvals`, etc.) in `App.tsx` lines 417-459. Changing paths breaks bookmarks, browser history, documentation.

**Prevention:**
1. **Do NOT change route paths.** Visual grouping only:
   ```typescript
   interface ModuleGroup { label: string; modules: WorkspaceModuleLink[] }
   const ROLE_MODULE_GROUPS: Record<string, ModuleGroup[]>
   ```
2. Keep `getRoleModules()` functional (flatten groups) for backward compat
3. Add `getRoleNavGroups()` as new function; update sidebar and workspace separately
4. If URLs must change, add redirect routes for ALL old paths
5. Extract nav config to single source of truth (`navigationConfig.ts`)

**Detection:** If `App.tsx` route `path` attributes change without redirects, breakage is guaranteed.

**Phase:** Menu restructuring. Decide visual-only (safe) vs URL change (risky) upfront.

---

### Pitfall 6: Collapsible Salary Display Hides Approver-Critical Info

**What goes wrong:** Simplification hides information approvers need. Rubber-stamping without reviewing scores.

**Prevention:**
1. For **approvers on current record**, auto-expand detail sections. Collapse for read-only viewers.
2. Collapsed MUST include: employee/dept/level, AI level, recommended ratio, eligibility status, override indicator
3. Do NOT remove API response fields -- change rendering only. Schema backward-compatible for `/api/v1/public/`
4. Consider "I have reviewed details" checkbox before approve activates
5. Define clear `SalaryDisplayProps` interface; pass single object, not individual props

**Phase:** Salary display. Frontend-only if done correctly.

---

### Pitfall 7: File Share Notifications Have No Delivery Channel

**What goes wrong:** No notification infrastructure (no table, no email, no WebSocket). Share requests sit pending indefinitely.

**Prevention:**
1. Create `Notification` table (`user_id, type, title, message, read_at, created_at`)
2. Badge count in sidebar (poll on page load)
3. "Pending Actions" section at top of MyReview
4. Auto-approve timeout (72h) prevents indefinite blocking
5. HR/admin can approve on behalf if owner unresponsive
6. Do NOT build email/push for v1.1 -- badge + page sufficient

**Phase:** File sharing phase.

---

### Pitfall 8: Feishu Attendance Assumed Complete

**What goes wrong:** Attendance from Feishu is periodic, field mapping configurable, `leave_days` may be NULL on older records. Engine may not check freshness.

**Prevention:**
1. Check `AttendanceRecord.synced_at` is within current cycle
2. `leave_days IS NULL` = "not synced," NOT "zero leave" -- return `skipped` not `pass`
3. Show freshness: "Attendance as of: 2026-03-15"
4. "Sync Now" button in eligibility UI

**Phase:** Eligibility engine, rule 4.

---

## Minor Pitfalls

### Pitfall 9: Eligibility Hardcoded Thresholds

**What goes wrong:** Attendance threshold (95%), tenure threshold (3 months) hardcoded. Different departments/cycles need different values.

**Prevention:** Define thresholds as engine constructor parameters with defaults.

### Pitfall 10: Share Request Without Active Cycle

**What goes wrong:** User tries to share but has no active submission (no cycle). No submission to attach shared file to.

**Prevention:** Share request creation verifies requester has active submission. Show "请先确认当前评估周期" if not.

### Pitfall 11: Timezone in Date Comparisons

**What goes wrong:** `hire_date` as Date column compared to "today." Server UTC vs business CST shifts threshold by a day.

**Prevention:** Use `Asia/Shanghai` for all date comparisons in eligibility engine.

### Pitfall 12: N+1 Queries in Eligibility Batch Check

**What goes wrong:** 4 rules x 200 employees = 800 queries with lazy loading.

**Prevention:** Batch-load with `selectinload`, in-memory evaluation, paginate (50/page).

### Pitfall 13: Collapsible State Not Persisted

**What goes wrong:** User expands details, navigates away, returns -- collapsed again.

**Prevention:** `localStorage` for expand/collapse state, or accept as designed behavior.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | Severity |
|-------------|---------------|------------|----------|
| **Eligibility: data** | Schema does not exist (P1) | Columns + models + migrations FIRST | CRITICAL |
| **Eligibility: data** | NOT NULL on existing rows (P1/C1) | Nullable first, backfill, then tighten | HIGH |
| **Eligibility: engine** | NULL = silent pass or failure flood (P1) | Distinct `data_missing` reason code | CRITICAL |
| **Eligibility: engine** | Override bypass (P3) | Per-cycle, structured reasons, audit | HIGH |
| **Eligibility: engine** | Feishu data incomplete (P8) | Check synced_at, handle NULLs | HIGH |
| **Eligibility: engine** | N+1 queries (P12) | Batch-load, pagination | MEDIUM |
| **File sharing** | Dedup hard-block conflict (P2) | New method, separate model | CRITICAL |
| **File sharing** | Instance-state bug (P2) | Persist to DB, not dict | HIGH |
| **File sharing** | No notifications (P7) | Badge + pending page | HIGH |
| **Account binding** | Stale JWT claims (P4) | Invalidate tokens, binding_updated_at | HIGH |
| **Account binding** | Auto vs manual bind conflict (P4) | Manual priority, binding_source flag | MEDIUM |
| **Menu restructuring** | Breaking deep links (P5) | Visual-only grouping | MEDIUM |
| **Salary display** | Hiding approver info (P6) | Progressive disclosure, stable API | MEDIUM |
| **All phases** | SQLite/PG drift (C1) | Alembic migration per change | HIGH |

---

## Recommended Phase Ordering

1. **Schema & Data Foundation** -- `hire_date` on Employee, missing models, Alembic migrations. Unblocks eligibility.
2. **Account-Employee Binding** -- Self-contained, token invalidation required. No external dependencies.
3. **Menu/Navigation** -- Frontend-only if visual. Low risk. Parallelizable.
4. **Salary Display Simplification** -- Frontend-only. No dependencies. Parallelizable.
5. **File Sharing/Approval** -- Most complex: new models, dedup refactor, instance-state fix, notifications.
6. **Eligibility Engine** -- Depends on schema foundation (1). Requires careful NULL/missing-data handling.

---

## Sources

Direct code inspection at `D:/wage_adjust/`:
- `backend/app/models/employee.py` -- No hire_date column
- `backend/app/models/user.py` -- employee_id FK without cascade
- `backend/app/models/project_contributor.py` -- Contribution model (not for sharing)
- `backend/app/models/attendance_record.py` -- leave_days nullable, synced_at
- `backend/app/services/file_service.py` -- Dedup block (lines 424-434), instance-state (lines 207-221), 4 call sites
- `backend/app/services/identity_binding_service.py` -- Auto-bind via id_card_no
- `backend/app/core/database.py` -- init_database auto-create (line 69-78)
- `frontend/src/utils/roleAccess.ts` -- Flat ROLE_MODULES
- `frontend/src/App.tsx` -- Route definitions (lines 417-459)
- `alembic/versions/` -- 9 existing migration files
- Codebase grep: zero results for hire_date, performance, 绩效 in models
