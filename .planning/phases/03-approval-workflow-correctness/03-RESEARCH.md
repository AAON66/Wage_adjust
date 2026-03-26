# Phase 3: Approval Workflow Correctness - Research

**Researched:** 2026-03-26
**Domain:** SQLAlchemy pessimistic locking, approval history preservation, audit log integration, reviewer UI enrichment
**Confidence:** HIGH

---

## Summary

Phase 3 fixes three concrete bugs in the existing approval service and extends two frontend capabilities. The backend scaffolding is fully present — `ApprovalRecord`, `SalaryRecommendation`, `AuditLog` models exist, `ApprovalService` is wired in, and the `Approvals.tsx` page renders a functional two-panel workflow UI. What is missing is (1) a row-level lock in `decide_approval` to prevent concurrent double-approvals, (2) history preservation when a recommendation is resubmitted after rejection, (3) `AuditLog` writes on every approval/salary-change action, (4) department-scoped pending queue endpoints, and (5) dimension scores displayed alongside the adjustment percentage in the reviewer panel.

The phase is entirely brownfield — no new tables are required. One Alembic migration is needed only if the `AuditLog.operator_role` column is added (it currently stores role only in `detail` JSON). All changes are surgical edits to `approval_service.py`, `approvals.py` router, `approval.py` schema, and `Approvals.tsx`.

**Primary recommendation:** Add `with_for_update()` to the `decide_approval` query path, archive rather than delete approval records on resubmission, wire `AuditLog` writes inside the same `db.commit()` transactions, add a `/approvals/queue` endpoint that returns pending items with embedded dimension scores, and extend the frontend panel to render those scores.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APPR-01 | `decide_approval` uses `SELECT ... FOR UPDATE` pessimistic lock | SQLAlchemy 2.0 `with_for_update()` on synchronous Session; SQLite uses serialized writes as fallback |
| APPR-02 | Rejected-and-resubmitted evaluations preserve full rejection history | Replace `decision='pending'` reset in `submit_for_approval` with archival via a new `generation` column or by never resetting decided records — create new rows instead |
| APPR-03 | Every approval action writes to `AuditLog` in same transaction | `AuditLog` model exists; `db.add(AuditLog(...))` before `db.commit()` inside `decide_approval` and `submit_for_approval` |
| APPR-04 | Every salary recommendation change writes to `AuditLog` | Wire into `SalaryService` and the `PATCH /salary/{id}` endpoint; same-transaction pattern |
| APPR-05 | Manager approval queue filtered by department with dimension scores | New or extended endpoint; `selectinload(AIEvaluation.dimension_scores)` already supported by model |
| APPR-06 | HR/HRBP cross-department view with adjustment comparison | `include_all=True` path already exists; needs dimension scores in response schema |
| APPR-07 | Approval UI shows 5 dimension scores + rationale alongside salary recommendation | Frontend schema extension + panel render; data already available via dimension_scores relationship |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Backend: Python + FastAPI; frontend: React + TypeScript
- All scoring rules/coefficients must be configurable, not hardcoded
- All evaluation results must be auditable, explainable, traceable
- API must be versioned under `/api/v1/`
- `from __future__ import annotations` required at top of every Python file
- Pydantic 2 `BaseModel` with `ConfigDict(from_attributes=True)` for ORM-mapped responses
- SQLAlchemy 2.0 with `Mapped[T]` column declarations and synchronous `Session`
- `snake_case` for Python identifiers; `PascalCase` for React component files
- Alembic is the sole migration path — no DDL at startup

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36 (confirmed) | ORM + query builder; `with_for_update()` for locking | Already in use; 2.0 style required |
| FastAPI | 0.115.0 (confirmed) | HTTP routing + dependency injection | Project standard |
| Pydantic | 2.10.3 | Request/response validation and serialization | Project standard |
| React | 18.3.1 | Frontend UI | Project standard |
| TypeScript | 5.8.3 | Frontend type safety | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Alembic | 1.14.0 | Schema migrations | Only if new columns are added |
| pytest | 8.3.5 | Backend test runner | New test cases for locking, history, audit |

### No New Dependencies Required
All capabilities needed for this phase are already installed. No `pip install` or `npm install` additions needed.

---

## Architecture Patterns

### Pessimistic Locking Pattern (APPR-01)

**What:** `SELECT ... FOR UPDATE` prevents two concurrent requests from both reading `decision='pending'` and both proceeding to write.

**SQLAlchemy 2.0 synchronous Session syntax:**
```python
# Source: SQLAlchemy 2.0 docs — ORM Querying, with_for_update
from sqlalchemy import select

stmt = (
    select(ApprovalRecord)
    .where(ApprovalRecord.id == approval_id)
    .with_for_update()
)
approval = db.scalar(stmt)
```

**SQLite caveat (HIGH confidence):** SQLite does not support `SELECT FOR UPDATE` — the clause is silently ignored by pysqlite. However, SQLite's default journal mode serializes writes at the file level, so concurrent write contention still resolves without corruption. The lock is primarily meaningful for PostgreSQL (production target per v2 notes). The code must use `with_for_update()` so that when the DB is PostgreSQL, it works correctly — SQLite tests will still pass.

**Pattern:** Move the approval fetch inside `decide_approval` from `self.get_approval(approval_id)` (which uses a plain SELECT via `_approval_query()`) to a direct `db.scalar(select(ApprovalRecord).where(...).with_for_update())`. The post-lock guard `if approval.decision != 'pending': raise ValueError(...)` then correctly rejects the second concurrent request.

### History Preservation Pattern (APPR-02)

**What's broken now:** `submit_for_approval` resets existing `ApprovalRecord` rows in-place — `record.decision = 'pending'`, `record.decided_at = None`. This destroys the rejection history.

**Fix approach — new `generation` column:**

Add an integer `generation` column to `approval_records` (default 0). On resubmission after rejection:
- Do NOT mutate existing decided records.
- Insert new `ApprovalRecord` rows with `generation = max_generation + 1`.
- The unique constraint `(recommendation_id, step_name)` must be changed to `(recommendation_id, step_name, generation)`.

**Alternative approach — status gate instead of reset:**
Only allow resubmission to create new records if the current recommendation was `rejected` or `deferred`. Never update `decision` or `decided_at` on a record that is not still `pending`. The existing `existing_by_step` dict in `submit_for_approval` reuses step rows — this is the bug. Replace it with always-insert when resubmitting a rejected/deferred recommendation.

**Recommended approach (simpler, fewer schema changes):**
Add `generation: Mapped[int]` column with default `0`. Change UniqueConstraint to `(recommendation_id, step_name, generation)`. On resubmission, detect `recommendation.status in {'rejected', 'deferred'}` and increment generation — all new `ApprovalRecord` objects get the new generation number. Old records are preserved. `_is_current_step` and `list_history` query by `max(generation)` to find actionable steps.

**Alembic migration required:** Yes — add `generation` column and replace the unique constraint.

### AuditLog Write Pattern (APPR-03, APPR-04)

**What exists:** `AuditLog` model is defined at `backend/app/models/audit_log.py` with fields: `operator_id`, `action`, `target_type`, `target_id`, `detail` (JSON). There is no `AuditLogService` — writes have never been wired.

**Pattern for same-transaction writes:**
```python
# Inside decide_approval, before db.commit()
audit = AuditLog(
    operator_id=current_user.id,
    action='approval_decided',
    target_type='approval_record',
    target_id=approval.id,
    detail={
        'decision': normalized_decision,
        'recommendation_id': approval.recommendation_id,
        'step_name': approval.step_name,
        'comment': approval.comment,
        'operator_role': current_user.role,
    },
)
db.add(audit)
# db.commit() follows — audit and decision land atomically
```

**Key rule:** `db.add(audit)` MUST happen before `db.commit()`. Never commit the business change first and then audit second — that creates a window where the change exists without a log entry. The existing `decide_approval` already calls `db.flush()` before `db.commit()`, so audit writes can be inserted between flush and commit.

**AuditLog field gap:** The existing `AuditLog` model lacks `operator_role` and `old_value`/`new_value` columns. APPR-03 only requires writing to `AuditLog` — the full schema enrichment (with old/new value, request_id) is AUDIT-01 in Phase 4. For Phase 3: write to existing `AuditLog` fields only, storing role and values in the `detail` JSON dict. No migration needed for Phase 3 audit writes.

### Pending Queue with Dimension Scores (APPR-05, APPR-06)

**What's missing:** The existing `list_approvals` returns `ApprovalRecord` items. The `ApprovalRecordRead` schema does not include dimension scores. The frontend `Approvals.tsx` currently shows only `final_adjustment_ratio` for the selected approval, not the 5-dimension breakdown.

**Backend change:** Extend `_approval_query()` to include `selectinload` of the evaluation's `dimension_scores`:
```python
selectinload(ApprovalRecord.recommendation)
    .selectinload(SalaryRecommendation.evaluation)
    .selectinload(AIEvaluation.dimension_scores)
```

Then extend `ApprovalRecordRead` schema to include `dimension_scores: list[DimensionScoreRead]`.

**Department filter:** `list_approvals` already enforces department scoping via `AccessScopeService.can_access_employee`. The manager sees only their department because their user has `departments` linked. The `include_all` flag for admin/hrbp already bypasses this. No new endpoint is strictly required — extend the existing list endpoint's response schema.

**New endpoint option:** A dedicated `/approvals/queue` endpoint could return a cleaner pending-only view optimized for the approval worklist. The plan should decide whether to extend the existing list or add a new endpoint. Either works; extending the existing is less disruptive.

### Frontend Dimension Panel (APPR-07)

**What exists:** `Approvals.tsx` right panel shows employee name, department, step name, approver email, recommendation status, and adjustment ratio. It has no dimension score rendering.

**Pattern:** Add a `DimensionScoreBreakdown` section in the selected-approval detail panel. The `ApprovalRecord` TypeScript interface needs `dimension_scores` added. A simple grid renders `dimension_code`, `weight`, `weighted_score`, and `ai_rationale` per row — same pattern as `EvaluationDetail.tsx`.

**DimensionScore interface already exists?** Check `api.ts` — if not, add:
```typescript
export interface DimensionScoreRecord {
  dimension_code: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  ai_rationale: string;
}
```

### Anti-Patterns to Avoid

- **Reset-in-place on resubmit:** Mutating `decision='pending'` on a decided record destroys history. Never do this.
- **Commit-then-audit:** Writing the business change to DB and committing, then writing audit in a second commit, creates an audit-gap window. Always same-transaction.
- **Separate session for locking:** `with_for_update()` only works within the same transaction/session that fetches the row. Don't fetch in one session and lock in another.
- **`selectinload` after lock:** Load all necessary relationships after the locked fetch — avoid additional queries that could deadlock.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Row-level locking | Custom application mutex / Redis lock | `SQLAlchemy .with_for_update()` | DB-level locks are atomic and release on transaction end automatically |
| History versioning | Soft-delete + copy pattern | `generation` integer column on `approval_records` | Minimal schema change, preserves unique constraint semantics |
| Audit log helper | A separate audit microservice | Direct `db.add(AuditLog(...))` before commit | Same-session write guarantees atomicity; no IPC needed |
| Dimension score join | Multiple separate API calls from frontend | `selectinload` eager load on existing relationship | One query round-trip, already wired in SQLAlchemy model |

---

## Common Pitfalls

### Pitfall 1: SQLite Ignores FOR UPDATE
**What goes wrong:** Tests pass on SQLite but the race condition reappears on PostgreSQL.
**Why it happens:** pysqlite silently drops `FOR UPDATE` — no error is raised.
**How to avoid:** Rely on the `if approval.decision != 'pending': raise ValueError(...)` guard as the correctness check in tests. The lock becomes effective when DB is PostgreSQL. Document this clearly in code comments.
**Warning signs:** Tests pass but there is no evidence of a real lock being acquired.

### Pitfall 2: UniqueConstraint Violation on Resubmission
**What goes wrong:** `submit_for_approval` inserts a new `ApprovalRecord` with the same `(recommendation_id, step_name)` and hits the existing `UniqueConstraint`.
**Why it happens:** The current constraint is `(recommendation_id, step_name)` without generation.
**How to avoid:** The Alembic migration that adds `generation` MUST also drop the old constraint and create the new one `(recommendation_id, step_name, generation)`. In SQLite, this requires `batch_alter_table` (already established pattern in Phase 1).
**Warning signs:** `IntegrityError` on second submission of a rejected recommendation.

### Pitfall 3: Orphaned Approval Records on Route Update
**What goes wrong:** `submit_for_approval` currently deletes records for step names not in the new route. With `generation`, this deletion must be scoped to the current generation only — do not delete records from previous generations.
**Why it happens:** The `existing_by_step` logic and the delete loop do not distinguish generations.
**How to avoid:** Add `generation` filter: `{record.step_name: record for record in recommendation.approval_records if record.generation == current_generation}`.

### Pitfall 4: AuditLog Missing on Salary Service Path (APPR-04)
**What goes wrong:** Approval audit log is added, but `SalaryRecommendation` value changes (system → final) go unlogged.
**Why it happens:** `SalaryService` is a separate service from `ApprovalService`.
**How to avoid:** Find all `PATCH /salary/` paths that mutate `recommended_salary`, `final_adjustment_ratio`, or `status` and add `AuditLog` writes there in the same transaction.
**Warning signs:** Approval history shows approval decisions but no record of the salary value that was approved.

### Pitfall 5: Dimension Score N+1 Query
**What goes wrong:** Each `ApprovalRecord` in the list response triggers a separate query to load dimension scores.
**Why it happens:** Lazy loading is the default for SQLAlchemy relationships.
**How to avoid:** Add `selectinload(AIEvaluation.dimension_scores)` to `_approval_query()` — one additional JOIN per list call, no N+1.

---

## Code Examples

### SQLAlchemy 2.0 `with_for_update` in synchronous Session
```python
# Source: SQLAlchemy 2.0 official docs
from sqlalchemy import select

# Replaces self.get_approval(approval_id) in decide_approval
stmt = (
    select(ApprovalRecord)
    .options(
        selectinload(ApprovalRecord.approver),
        selectinload(ApprovalRecord.recommendation)
        .selectinload(SalaryRecommendation.approval_records),
    )
    .where(ApprovalRecord.id == approval_id)
    .with_for_update()
)
approval = db.scalar(stmt)
if approval is None:
    return None
if approval.decision != 'pending':
    raise ValueError('This approval step has already been processed.')
```

### Adding `generation` column via Alembic batch_alter_table (SQLite-compatible)
```python
# In new Alembic migration
def upgrade() -> None:
    with op.batch_alter_table('approval_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('generation', sa.Integer(), nullable=False, server_default='0'))
        batch_op.drop_constraint('uq_approval_records_recommendation_id_step_name', type_='unique')
        batch_op.create_unique_constraint(
            'uq_approval_records_recommendation_step_generation',
            ['recommendation_id', 'step_name', 'generation'],
        )
```

### Same-transaction AuditLog write
```python
# Before db.commit() in decide_approval
from backend.app.models.audit_log import AuditLog

audit_entry = AuditLog(
    operator_id=current_user.id,
    action='approval_decided',
    target_type='approval_record',
    target_id=approval.id,
    detail={
        'decision': normalized_decision,
        'recommendation_id': approval.recommendation_id,
        'step_name': approval.step_name,
        'step_order': approval.step_order,
        'comment': approval.comment,
        'operator_role': current_user.role,
    },
)
db.add(audit_entry)
db.add(recommendation)
db.commit()  # audit + business change in same transaction
```

### DimensionScore eager load in approval query
```python
# In _approval_query(), add to selectinload chain:
selectinload(ApprovalRecord.recommendation)
    .selectinload(SalaryRecommendation.evaluation)
    .selectinload(AIEvaluation.dimension_scores)
```

### Frontend DimensionScoreRecord type (api.ts)
```typescript
export interface DimensionScoreRecord {
  dimension_code: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  ai_rationale: string;
}
// Add to ApprovalRecord:
// dimension_scores: DimensionScoreRecord[];
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `select(Model).where(...)` plain read | `.with_for_update()` locking select | SQLAlchemy 2.0+ | Prevents concurrent double-approvals on PostgreSQL |
| `decision='pending'` reset in-place | New `generation` column + insert-new | This phase | Preserves full rejection history for auditors |
| `AuditLog` model defined but never written to | `db.add(AuditLog(...))` before commit | This phase | Enables Phase 4 full audit query without data backfill |

**Deprecated patterns to avoid:**
- `db.query(Model).with_for_update()` — SQLAlchemy 1.x style; use `select(Model).with_for_update()` in 2.0
- Audit writes after `db.commit()` in a second transaction — creates data integrity gap

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python .venv | All backend | ✓ | 3.13.7 | — |
| SQLAlchemy | Locking | ✓ | 2.0.36 | — |
| FastAPI | API endpoints | ✓ | 0.115.0 | — |
| Alembic | Schema migration | ✓ | 1.14.0 | — |
| pytest | Tests | ✓ | 8.3.5 | — |
| Node.js | Frontend | ✓ | v24.14.0 | — |
| SQLite | Dev DB | ✓ | bundled | FOR UPDATE silently ignored (documented) |

No missing dependencies. Phase executes entirely with existing toolchain.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | none (pytest auto-discovers `backend/tests/`) |
| Quick run command | `.venv/Scripts/python.exe -m pytest backend/tests/test_api/test_approval_api.py backend/tests/test_services/test_approval_service.py -x -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest backend/tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APPR-01 | Second concurrent decision on already-decided step is rejected | unit | `pytest backend/tests/test_services/test_approval_service.py::test_concurrent_decide_rejected -x` | ❌ Wave 0 |
| APPR-02 | Rejected-then-resubmitted recommendation preserves old approval records | integration | `pytest backend/tests/test_api/test_approval_api.py::test_resubmit_preserves_history -x` | ❌ Wave 0 |
| APPR-03 | AuditLog row exists after approve/reject/defer/override action | unit | `pytest backend/tests/test_services/test_approval_service.py::test_audit_log_written_on_decide -x` | ❌ Wave 0 |
| APPR-04 | AuditLog row exists after salary recommendation value change | unit | `pytest backend/tests/test_services/test_salary_service.py::test_audit_log_written_on_salary_change -x` | ❌ Wave 0 |
| APPR-05 | Manager list returns pending evaluations filtered to department with dimension scores | integration | `pytest backend/tests/test_api/test_approval_api.py::test_manager_queue_has_dimension_scores -x` | ❌ Wave 0 |
| APPR-06 | Admin/HRBP include_all returns cross-department evaluations with adjustment percentages | integration | `pytest backend/tests/test_api/test_approval_api.py::test_hrbp_cross_department_queue -x` | ❌ Wave 0 |
| APPR-07 | Frontend approval panel renders dimension score table (manual smoke) | manual | — | N/A |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python.exe -m pytest backend/tests/test_api/test_approval_api.py backend/tests/test_services/test_approval_service.py -x -q`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest backend/tests/ -x -q`
- **Phase gate:** Full suite green + frontend `npm run build` passes before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test functions in `backend/tests/test_services/test_approval_service.py` — APPR-01, APPR-03
- [ ] New test functions in `backend/tests/test_api/test_approval_api.py` — APPR-02, APPR-05, APPR-06
- [ ] New test function in `backend/tests/test_services/test_salary_service.py` — APPR-04

---

## Open Questions

1. **Generation vs. soft-delete for history preservation**
   - What we know: Adding `generation` preserves history cleanly and allows queries to target "current generation" vs "all history"
   - What's unclear: Whether the planner prefers simpler approach (status gate: only allow resubmission creating new records without reusing step names) vs `generation` column
   - Recommendation: Use `generation` column — it cleanly separates current-round steps from historical ones without ambiguity in `_is_current_step` logic

2. **Where to wire APPR-04 salary audit log**
   - What we know: `SalaryService` handles salary mutations; the relevant method is the `adjust_salary` or `update_recommendation` call path
   - What's unclear: Phase 4 (AUDIT-01) will fully standardize audit fields — Phase 3's APPR-04 only requires wiring the existing `AuditLog` model, not the full Phase 4 schema
   - Recommendation: Add minimal `AuditLog` writes in `SalaryService` for `final_adjustment_ratio` changes using the existing `detail` JSON field; Phase 4 will enrich the schema

3. **New endpoint vs. extending existing list for APPR-05/06**
   - What we know: `/approvals` already supports `include_all` and `decision` filters; response schema would need `dimension_scores` added
   - What's unclear: Whether a dedicated `/approvals/queue` endpoint would be cleaner than extending `ApprovalRecordRead`
   - Recommendation: Extend the existing list endpoint's response schema — fewer API surface changes, and the frontend already calls `/approvals`

---

## Sources

### Primary (HIGH confidence)
- SQLAlchemy 2.0 ORM source code (installed, version 2.0.36) — `with_for_update()` in `select()` builder
- Project source: `backend/app/services/approval_service.py` — full current implementation read
- Project source: `backend/app/models/approval.py` — UniqueConstraint on `(recommendation_id, step_name)` confirmed
- Project source: `backend/app/models/audit_log.py` — AuditLog model fields confirmed (no `operator_role` column, no `old_value`)
- Project source: `backend/tests/test_api/test_approval_api.py` — existing test coverage catalogued
- Project source: `frontend/src/pages/Approvals.tsx` — current UI capabilities confirmed
- Project source: `frontend/src/types/api.ts` — `ApprovalRecord` interface missing `dimension_scores`

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 docs pattern for `with_for_update()` — consistent with installed library behavior
- Alembic `batch_alter_table` for SQLite — established pattern from Phase 1 migrations in this project

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed installed and version-verified
- Architecture: HIGH — all proposed patterns derived from reading actual project code
- Pitfalls: HIGH — derived from reading the actual `submit_for_approval` implementation and identifying the reset-in-place bug directly

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (stable libraries, no external services)
