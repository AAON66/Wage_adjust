---
phase: 03-approval-workflow-correctness
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/tests/test_services/test_approval_service.py
  - backend/tests/test_api/test_approval_api.py
  - backend/tests/test_services/test_salary_service.py
autonomous: true
requirements: [APPR-01, APPR-02, APPR-03, APPR-04, APPR-05, APPR-06]

must_haves:
  truths:
    - "Running the approval test suite with no implementation produces named FAILING tests (not errors)"
    - "Each requirement has at least one dedicated test function asserting post-condition behavior"
    - "Test stubs cover: double-decide rejection, history preservation, audit log writes, dimension scores in queue response"
  artifacts:
    - path: "backend/tests/test_services/test_approval_service.py"
      provides: "Unit tests for APPR-01, APPR-03"
      contains: "test_concurrent_decide_rejected, test_audit_log_written_on_decide"
    - path: "backend/tests/test_api/test_approval_api.py"
      provides: "Integration tests for APPR-02, APPR-05, APPR-06"
      contains: "test_resubmit_preserves_history, test_manager_queue_has_dimension_scores, test_hrbp_cross_department_queue"
    - path: "backend/tests/test_services/test_salary_service.py"
      provides: "Unit test for APPR-04"
      contains: "test_audit_log_written_on_salary_change"
  key_links:
    - from: "test_concurrent_decide_rejected"
      to: "approval.decision != 'pending' guard"
      via: "second decide_approval call raises ValueError"
      pattern: "pytest.raises.*ValueError"
    - from: "test_resubmit_preserves_history"
      to: "approval_records table"
      via: "old records still present after resubmit"
      pattern: "generation.*0.*generation.*1|history.*len.*>.*2"
---

<objective>
Create failing test stubs for all Phase 3 approval workflow requirements before any implementation begins.

Purpose: Establish the RED baseline so each implementation task can target a specific green state.
Output: Named test functions that fail deterministically — no `pytest.skip`, no `assert False`, genuine assertions against behavior the implementation has not yet delivered.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/03-approval-workflow-correctness/03-RESEARCH.md
@.planning/phases/03-approval-workflow-correctness/03-VALIDATION.md
</context>

<interfaces>
<!-- Existing test infrastructure — executor MUST follow these patterns exactly. -->

From backend/tests/test_services/test_approval_service.py (existing helpers):
```python
def create_db_context() -> tuple[Settings, sessionmaker]:
    """Creates isolated SQLite DB per test — copy this pattern."""

def seed_workflow_entities(session_factory) -> dict[str, str]:
    """Returns: admin_id, hrbp_id, manager_id, recommendation_id, evaluation_id"""
```

From backend/tests/test_api/test_approval_api.py (existing helpers):
```python
def build_client() -> tuple[TestClient, ApiDatabaseContext]:
def register_user(client, *, email: str, role: str) -> str:
def login_token(client, *, email: str) -> str:
def bind_user_departments(context, *, email: str, department_names: list[str]) -> None:
def seed_recommendation(context) -> tuple[str, str]:  # returns (recommendation_id, evaluation_id)
```

From backend/app/models/approval.py (current — will gain `generation` column in Plan 02):
```python
class ApprovalRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "approval_records"
    __table_args__ = (UniqueConstraint("recommendation_id", "step_name"),)
    recommendation_id: Mapped[str]
    approver_id: Mapped[str]
    step_name: Mapped[str]
    step_order: Mapped[int]
    decision: Mapped[str]  # 'pending' | 'approved' | 'rejected' | 'deferred'
    comment: Mapped[str | None]
    decided_at: Mapped[datetime | None]
```

From backend/app/models/audit_log.py:
```python
class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_logs"
    operator_id: Mapped[str | None]
    action: Mapped[str]   # e.g. 'approval_decided', 'salary_updated'
    target_type: Mapped[str]
    target_id: Mapped[str]
    detail: Mapped[dict]  # JSON: stores operator_role, decision, old_value, new_value
```

From backend/app/services/approval_service.py:
```python
class ApprovalService:
    def decide_approval(self, approval_id, *, current_user, decision, comment, ...) -> ApprovalRecord | None
    def submit_for_approval(self, *, recommendation_id, steps) -> SalaryRecommendation
    def list_approvals(self, *, current_user, include_all=False, decision=None) -> list[ApprovalRecord]
    def list_history(self, recommendation_id, *, current_user=None) -> list[ApprovalRecord]
```

From backend/app/services/salary_service.py:
```python
class SalaryService:
    def update_recommendation(self, recommendation_id, *, final_adjustment_ratio, status) -> SalaryRecommendation | None
```

DimensionScoreRecord already defined in frontend/src/types/api.ts:
```typescript
export interface DimensionScoreRecord {
  id: string; dimension_code: string; weight: number;
  ai_raw_score: number; ai_weighted_score: number;
  raw_score: number; weighted_score: number;
  ai_rationale: string; rationale: string; created_at: string;
}
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write failing unit test stubs for APPR-01 and APPR-03</name>
  <files>backend/tests/test_services/test_approval_service.py</files>

  <read_first>
    - backend/tests/test_services/test_approval_service.py — read the FULL file; reuse create_db_context, seed_workflow_entities, and the session pattern exactly
    - backend/app/models/audit_log.py — confirm AuditLog field names (operator_id, action, target_type, target_id, detail)
    - backend/app/services/approval_service.py — confirm decide_approval signature
  </read_first>

  <behavior>
    - test_concurrent_decide_rejected: call decide_approval('approved') on the same approval_id a second time after it has already been decided; assert ValueError is raised (simulates concurrent double-decision)
    - test_audit_log_written_on_decide: call decide_approval for 'approved' decision; query db.scalars(select(AuditLog).where(AuditLog.target_type=='approval_record')) and assert at least one row exists with action=='approval_decided' and target_id matching the approval_id
    - test_audit_log_written_on_reject: call decide_approval for 'rejected' with comment; assert AuditLog row exists with action=='approval_decided' and detail JSON contains 'decision': 'rejected' and 'operator_role' key
  </behavior>

  <action>
Append three new test functions to the EXISTING backend/tests/test_services/test_approval_service.py. DO NOT replace any existing tests.

Import additions at top of file (after existing imports):
```python
from sqlalchemy import select
from backend.app.models.audit_log import AuditLog
```

test_concurrent_decide_rejected:
1. Use create_db_context() and seed_workflow_entities() to get a fresh DB and ids.
2. Submit for approval with two steps: step_name='hr_review' → hrbp_id, step_name='committee' → manager_id.
3. Get the hrbp user and list_approvals(current_user=hrbp) to get the first pending item.
4. Call decide_approval(approval_item.id, current_user=hrbp, decision='approved', comment='OK') — this succeeds.
5. Call decide_approval AGAIN with the same approval_item.id and same args.
6. Wrap the second call in `with pytest.raises(ValueError)`. The current implementation has the guard `if approval.decision != 'pending': raise ValueError(...)` — the test asserts this guard fires.
7. Import pytest at top of file if not already present.

test_audit_log_written_on_decide:
1. Fresh DB from create_db_context(). Seed entities.
2. Submit for approval (one step: step_name='hr_review' → hrbp_id).
3. Get hrbp user. Get the approval item from list_approvals(current_user=hrbp).
4. Call decide_approval(item.id, current_user=hrbp, decision='approved', comment='Looks good').
5. Query: `logs = list(db.scalars(select(AuditLog).where(AuditLog.target_type == 'approval_record')))`.
6. Assert: `assert len(logs) >= 1` — this FAILS until Plan 02 wires the audit write.
7. Assert: `assert any(log.action == 'approval_decided' for log in logs)` — also fails.

test_audit_log_written_on_reject:
1. Fresh DB. Seed. Submit one-step approval to hrbp.
2. Reject: decide_approval(item.id, current_user=hrbp, decision='rejected', comment='Budget mismatch').
3. Query AuditLog for target_type=='approval_record'.
4. Assert at least one log with action=='approval_decided'.
5. Assert the log's detail dict contains key 'decision' with value 'rejected' AND key 'operator_role'.
   — Both assertions fail until Plan 02 implementation.
  </action>

  <verify>
    <automated>.venv/Scripts/python.exe -m pytest backend/tests/test_services/test_approval_service.py::test_concurrent_decide_rejected backend/tests/test_services/test_approval_service.py::test_audit_log_written_on_decide backend/tests/test_services/test_approval_service.py::test_audit_log_written_on_reject -x -q 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - All 3 new test functions exist and are collected by pytest (no ImportError, no SyntaxError)
    - test_concurrent_decide_rejected PASSES (the existing `if approval.decision != 'pending'` guard already handles this)
    - test_audit_log_written_on_decide FAILS with AssertionError (len(logs) >= 1 fails because AuditLog writes not yet wired)
    - test_audit_log_written_on_reject FAILS with AssertionError (same reason)
    - Output shows "1 passed, 2 failed" or similar — NOT "3 errors"
  </acceptance_criteria>

  <done>3 new test functions added; test_concurrent_decide_rejected green; audit log tests red with AssertionError (not import errors)</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write failing integration test stubs for APPR-02, APPR-04, APPR-05, APPR-06</name>
  <files>backend/tests/test_api/test_approval_api.py, backend/tests/test_services/test_salary_service.py</files>

  <read_first>
    - backend/tests/test_api/test_approval_api.py — read the FULL file; reuse build_client, register_user, login_token, bind_user_departments, seed_recommendation helpers
    - backend/tests/test_services/test_salary_service.py — read existing test structure to confirm session pattern
    - backend/app/schemas/approval.py — confirm ApprovalRecordRead fields (currently missing dimension_scores)
    - frontend/src/types/api.ts lines 234-245 — DimensionScoreRecord interface for reference
  </read_first>

  <behavior>
    - test_resubmit_preserves_history (API test): reject a two-step recommendation, then resubmit it; call GET /approvals/history/{recommendation_id}; assert response contains MORE than 2 records (old rejected records are still present alongside the new pending ones)
    - test_manager_queue_has_dimension_scores (API test): list approvals as manager with decision=pending; assert each item in response has a 'dimension_scores' key that is a list (even if empty list for now — key must exist in schema)
    - test_hrbp_cross_department_queue (API test): list approvals as HRBP with include_all=true; assert response contains items from multiple departments (or at minimum includes all items regardless of approver_id filter)
    - test_audit_log_written_on_salary_change (service test): call SalaryService.update_recommendation with a new final_adjustment_ratio; query AuditLog for target_type=='salary_recommendation'; assert at least one row with action=='salary_updated'
  </behavior>

  <action>
Append four new test functions. DO NOT remove or modify existing tests.

**In backend/tests/test_api/test_approval_api.py:**

test_resubmit_preserves_history:
1. build_client(). Register admin, hrbp (hrbp@h.com), manager (mgr@h.com). bind_user_departments for both to 'Engineering'.
2. recommendation_id, _ = seed_recommendation(context).
3. Admin login. Submit two-step approval: hr_review → hrbp_id, committee → manager_id.
4. hrbp_token. GET /api/v1/approvals/ with decision=pending header. Pick the hr_review record id.
5. POST /api/v1/approvals/{id}/decide with decision='rejected', comment='Needs revision'.
6. Admin: POST /api/v1/approvals/submit again with same recommendation_id and same step structure (simulating resubmit after rejection).
7. GET /api/v1/approvals/history/{recommendation_id} (admin token).
8. Assert response status == 200. Parse items list.
9. Assert `len(items) > 2` — this FAILS until Plan 02 adds generation column and preserves old records.

test_manager_queue_has_dimension_scores:
1. build_client(). Register admin, manager (mgr2@h.com). bind_user_departments mgr2 to 'Engineering'.
2. recommendation_id, _ = seed_recommendation(context).
3. Admin: submit one-step approval with manager as approver.
4. manager_token. GET /api/v1/approvals/ with params decision=pending.
5. Assert response status == 200.
6. items = response.json()['items']. Assert len(items) >= 1.
7. first_item = items[0]. Assert 'dimension_scores' in first_item — this FAILS until Plan 03 extends the response schema.

test_hrbp_cross_department_queue:
1. build_client(). Register admin, hrbp1 (hrbp1@h.com). bind_user_departments hrbp1 to 'Engineering'.
2. recommendation_id, _ = seed_recommendation(context) — seeds 'Engineering' department employee.
3. Admin: submit one-step with hrbp1 as approver.
4. GET /api/v1/approvals/ with include_all=true using admin token.
5. Assert response 200. Assert total >= 1.
6. hrbp_token. GET /api/v1/approvals/?include_all=true.
7. Assert response 200. The HRBP should see the item even if it's not assigned to them.
   Assert len(response.json()['items']) >= 1 (FAILS until Plan 02/03 fix include_all scoping).

**In backend/tests/test_services/test_salary_service.py — append:**

Add imports at top if not present:
```python
from sqlalchemy import select
from backend.app.models.audit_log import AuditLog
from backend.app.services.salary_service import SalaryService
```

test_audit_log_written_on_salary_change:
1. Use same create_db_context pattern as test_approval_service.py.
2. Seed minimal data: employee, cycle, submission, evaluation (status='confirmed'), recommendation (status='recommended', final_adjustment_ratio=0.10).
3. Create SalaryService(db) and call update_recommendation(recommendation.id, final_adjustment_ratio=0.15, status='adjusted').
4. Query `logs = list(db.scalars(select(AuditLog).where(AuditLog.target_type == 'salary_recommendation')))`.
5. Assert `len(logs) >= 1` — FAILS until Plan 02 wires salary audit log.
6. Assert `any(log.action == 'salary_updated' for log in logs)` — also fails.
  </action>

  <verify>
    <automated>.venv/Scripts/python.exe -m pytest backend/tests/test_api/test_approval_api.py::test_resubmit_preserves_history backend/tests/test_api/test_approval_api.py::test_manager_queue_has_dimension_scores backend/tests/test_api/test_approval_api.py::test_hrbp_cross_department_queue backend/tests/test_services/test_salary_service.py::test_audit_log_written_on_salary_change -v 2>&1 | tail -25</automated>
  </verify>

  <acceptance_criteria>
    - All 4 new test functions collected without ImportError or SyntaxError
    - test_resubmit_preserves_history FAILS with AssertionError (len(items) <= 2 because history reset not yet fixed)
    - test_manager_queue_has_dimension_scores FAILS with KeyError or AssertionError ('dimension_scores' missing from response)
    - test_hrbp_cross_department_queue: may PASS or FAIL depending on current include_all behavior; either outcome is acceptable as long as it runs without crash
    - test_audit_log_written_on_salary_change FAILS with AssertionError (no AuditLog rows written yet)
    - Output shows no more than 1 PASSED, rest FAILED — not ERROR
  </acceptance_criteria>

  <done>4 new test functions added across two files; all run without import/syntax errors; failures are AssertionError not Exception; test stubs form the RED baseline for Plans 02 and 03</done>
</task>

</tasks>

<verification>
Run full test suite after Wave 1:

```bash
.venv/Scripts/python.exe -m pytest backend/tests/ -x -q 2>&1 | tail -30
```

Expected: all previously-passing tests still pass; the 5 new failing tests (not counting test_concurrent_decide_rejected which passes immediately) are AssertionError failures, not import errors.
</verification>

<success_criteria>
- 3 functions added to test_approval_service.py — collected, run, produce expected pass/fail
- 3 functions added to test_approval_api.py — collected, run, produce expected failures
- 1 function added to test_salary_service.py — collected, runs, fails with AssertionError
- Zero regressions in previously passing tests
- Plan 02 executor can immediately target these test names as their green criteria
</success_criteria>

<output>
After completion, create `.planning/phases/03-approval-workflow-correctness/03-01-SUMMARY.md`
</output>
---
phase: 03-approval-workflow-correctness
plan: 02
type: execute
wave: 2
depends_on: [03-01]
files_modified:
  - alembic/versions/{new_revision}_add_generation_to_approval_records.py
  - backend/app/models/approval.py
  - backend/app/services/approval_service.py
  - backend/app/services/salary_service.py
autonomous: true
requirements: [APPR-01, APPR-02, APPR-03, APPR-04]

must_haves:
  truths:
    - "A second decide_approval on the same already-decided step raises ValueError regardless of concurrency"
    - "After reject + resubmit, GET /approvals/history returns records from BOTH the rejected generation AND the new pending generation"
    - "Every call to decide_approval writes an AuditLog row in the same transaction before db.commit()"
    - "Every call to SalaryService.update_recommendation writes an AuditLog row in the same transaction"
  artifacts:
    - path: "alembic/versions/*_add_generation_to_approval_records.py"
      provides: "Alembic migration adding generation column and updating UniqueConstraint"
      contains: "batch_op.add_column.*generation"
    - path: "backend/app/models/approval.py"
      provides: "ApprovalRecord with generation column"
      contains: "generation: Mapped[int]"
    - path: "backend/app/services/approval_service.py"
      provides: "Pessimistic lock, history-preserving resubmit, audit log writes"
      contains: "with_for_update, AuditLog, generation"
    - path: "backend/app/services/salary_service.py"
      provides: "Audit log write on update_recommendation"
      contains: "AuditLog.*salary_updated"
  key_links:
    - from: "decide_approval"
      to: "AuditLog"
      via: "db.add(AuditLog(...)) before db.commit()"
      pattern: "db\\.add\\(AuditLog"
    - from: "submit_for_approval"
      to: "ApprovalRecord.generation"
      via: "new records get generation = max_generation + 1 on resubmit"
      pattern: "generation.*max_generation"
    - from: "with_for_update"
      to: "ApprovalRecord.id filter"
      via: "select(ApprovalRecord).where(...).with_for_update()"
      pattern: "with_for_update"
---

<objective>
Fix the three backend correctness bugs in the approval workflow: add pessimistic locking, history preservation via a generation column, and same-transaction AuditLog writes for approval and salary changes.

Purpose: Make APPR-01, APPR-02, APPR-03, APPR-04 green — the 5 failing test stubs from Plan 01 become passing.
Output: Alembic migration, updated ApprovalRecord model, rewritten critical paths in ApprovalService and SalaryService.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-approval-workflow-correctness/03-RESEARCH.md
@.planning/phases/03-approval-workflow-correctness/03-01-SUMMARY.md
</context>

<interfaces>
<!-- Existing model and service contracts the executor works against. -->

From backend/app/models/approval.py (CURRENT — this task adds `generation`):
```python
class ApprovalRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "approval_records"
    __table_args__ = (UniqueConstraint("recommendation_id", "step_name"),)
    # ADD: generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # CHANGE constraint to: UniqueConstraint("recommendation_id", "step_name", "generation", name="uq_approval_records_recommendation_step_generation")
    recommendation_id: Mapped[str]
    approver_id: Mapped[str]
    step_name: Mapped[str]
    step_order: Mapped[int]
    decision: Mapped[str]   # 'pending' | 'approved' | 'rejected' | 'deferred'
    comment: Mapped[str | None]
    decided_at: Mapped[datetime | None]
```

From backend/app/models/audit_log.py:
```python
class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_logs"
    operator_id: Mapped[str | None]  # ForeignKey users.id, nullable
    action: Mapped[str]              # max 128 chars
    target_type: Mapped[str]         # max 64 chars
    target_id: Mapped[str]           # max 36 chars (UUID)
    detail: Mapped[dict]             # JSON column
```

From backend/app/services/approval_service.py (CURRENT decide_approval):
```python
def decide_approval(self, approval_id, *, current_user, decision, comment, defer_until=None, defer_target_score=None):
    approval = self.get_approval(approval_id)      # plain SELECT — REPLACE with with_for_update()
    # ... validation ...
    if approval.decision != 'pending':
        raise ValueError('This approval step has already been processed.')
    # ... mutate approval ...
    self.db.flush()
    # ... update recommendation status ...
    self.db.add(recommendation)
    self.db.commit()      # ADD: db.add(AuditLog(...)) BEFORE this commit
```

From backend/app/services/approval_service.py (CURRENT submit_for_approval — BUG):
```python
# BUG: existing_by_step reuses decided records, resetting decision='pending' and decided_at=None
existing_by_step = {record.step_name: record for record in recommendation.approval_records}
# ... loop mutates existing records: record.decision = 'pending'; record.decided_at = None
```

From backend/app/services/salary_service.py (CURRENT update_recommendation):
```python
def update_recommendation(self, recommendation_id, *, final_adjustment_ratio, status) -> SalaryRecommendation | None:
    recommendation = self._query_recommendation(recommendation_id)
    if recommendation is None:
        return None
    recommendation.final_adjustment_ratio = round(final_adjustment_ratio, 4)
    recommendation.recommended_salary = ...
    if status is not None:
        recommendation.status = status
    self.db.add(recommendation)
    self.db.commit()     # ADD: db.add(AuditLog(...)) BEFORE this commit
    return recommendation
```

Phase 1 established pattern for SQLite-compatible batch_alter_table migrations:
```python
def upgrade() -> None:
    with op.batch_alter_table('approval_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('generation', sa.Integer(), nullable=False, server_default='0'))
        batch_op.drop_constraint('uq_approval_records_recommendation_id_step_name', type_='unique')
        batch_op.create_unique_constraint(
            'uq_approval_records_recommendation_step_generation',
            ['recommendation_id', 'step_name', 'generation'],
        )
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Alembic migration — add generation column and update UniqueConstraint</name>
  <files>alembic/versions/{new_revision}_add_generation_to_approval_records.py, backend/app/models/approval.py</files>

  <read_first>
    - backend/app/models/approval.py — full file; read current __table_args__ UniqueConstraint name exactly
    - alembic/versions/4f2eeacd62c3_add_prompt_hash_dimension_scores_used_.py — read for pattern reference on how Phase 2 migrations are structured (batch_alter_table pattern)
    - alembic/env.py — confirm target_metadata setup
  </read_first>

  <action>
Step 1 — Generate the migration file:
```bash
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "add_generation_to_approval_records"
```
The autogenerated file will be in `alembic/versions/`. Open it and REPLACE the upgrade/downgrade bodies.

Step 2 — Write the upgrade body (SQLite-compatible, must use batch_alter_table):
```python
def upgrade() -> None:
    with op.batch_alter_table('approval_records', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('generation', sa.Integer(), nullable=False, server_default='0')
        )
        # Drop the old two-column unique constraint.
        # The constraint name in the model is auto-generated by SQLAlchemy as:
        # uq_approval_records_recommendation_id_step_name
        # Confirm the actual name by reading the existing migration baseline or inspecting the DB.
        batch_op.drop_constraint('uq_approval_records_recommendation_id_step_name', type_='unique')
        batch_op.create_unique_constraint(
            'uq_approval_records_recommendation_step_generation',
            ['recommendation_id', 'step_name', 'generation'],
        )

def downgrade() -> None:
    with op.batch_alter_table('approval_records', schema=None) as batch_op:
        batch_op.drop_constraint('uq_approval_records_recommendation_step_generation', type_='unique')
        batch_op.create_unique_constraint(
            'uq_approval_records_recommendation_id_step_name',
            ['recommendation_id', 'step_name'],
        )
        batch_op.drop_column('generation')
```

Step 3 — Update backend/app/models/approval.py:
- Add `from sqlalchemy import ..., Integer` to the imports (Integer already imported, confirm).
- Change `__table_args__` to:
  ```python
  __table_args__ = (
      UniqueConstraint('recommendation_id', 'step_name', 'generation',
                       name='uq_approval_records_recommendation_step_generation'),
  )
  ```
- Add the new column after `step_order`:
  ```python
  generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  ```

Step 4 — Run the migration:
```bash
.venv/Scripts/python.exe -m alembic upgrade head
```

IMPORTANT: If `alembic upgrade head` fails because the old UniqueConstraint name does not match exactly, inspect the actual constraint name in the SQLite DB:
```bash
.venv/Scripts/python.exe -c "
import sqlite3; conn = sqlite3.connect('wage_adjust.db')
print(conn.execute(\"SELECT sql FROM sqlite_master WHERE type='table' AND name='approval_records'\").fetchone())
"
```
Use whatever name appears in the CREATE TABLE statement for the drop_constraint call.
  </action>

  <verify>
    <automated>.venv/Scripts/python.exe -m alembic current 2>&1 && .venv/Scripts/python.exe -c "from backend.app.models.approval import ApprovalRecord; print(ApprovalRecord.__table__.columns.keys())" 2>&1</automated>
  </verify>

  <acceptance_criteria>
    - `alembic current` shows the new revision as head (no "(head)" mismatch)
    - `ApprovalRecord.__table__.columns.keys()` output includes 'generation'
    - `alembic upgrade head` exits with code 0 (no migration errors)
    - The backend server still starts: `.venv/Scripts/python.exe -c "from backend.app.main import create_app; print('OK')"` prints OK
  </acceptance_criteria>

  <done>generation column present in approval_records; UniqueConstraint updated to 3-column form; migration runs to head without error</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Fix ApprovalService — pessimistic lock, history preservation, audit log writes</name>
  <files>backend/app/services/approval_service.py</files>

  <read_first>
    - backend/app/services/approval_service.py — read the FULL file (critical: understand decide_approval, submit_for_approval, _is_current_step, list_history)
    - backend/app/models/approval.py — confirm generation column now exists (from Task 1 above)
    - backend/app/models/audit_log.py — confirm AuditLog fields (operator_id, action, target_type, target_id, detail)
    - backend/tests/test_services/test_approval_service.py — read the 3 new test stubs from Plan 01 to understand exact assertions you must satisfy
  </read_first>

  <behavior>
    - APPR-01 (pessimistic lock): decide_approval fetches ApprovalRecord with .with_for_update() before any mutation; the `if approval.decision != 'pending'` guard remains as the application-level safety net
    - APPR-02 (history preservation): submit_for_approval on a rejected/deferred recommendation must NOT mutate existing decided records; instead compute max_generation across existing records and insert new ApprovalRecord rows with generation = max_generation + 1; existing records are untouched
    - APPR-03 (audit on decide): before db.commit() in decide_approval, db.add(AuditLog(operator_id=current_user.id, action='approval_decided', target_type='approval_record', target_id=approval.id, detail={...}))
    - _is_current_step and list_history must filter by current generation (max generation for the recommendation)
  </behavior>

  <action>
Make the following surgical changes to backend/app/services/approval_service.py:

**1. Add import at top:**
```python
from backend.app.models.audit_log import AuditLog
```

**2. Change decide_approval fetch to use WITH FOR UPDATE:**
Replace:
```python
approval = self.get_approval(approval_id)
```
With a direct locked fetch (at the TOP of decide_approval, before any validation):
```python
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
approval = self.db.scalar(stmt)
```
The remaining validation (approval is None check, role check, _is_current_step check, decision != 'pending' check) stays exactly as-is.

**3. Wire AuditLog in decide_approval before db.commit():**
Insert AFTER `self.db.add(recommendation)` and BEFORE `self.db.commit()`:
```python
audit_entry = AuditLog(
    operator_id=current_user.id,
    action='approval_decided',
    target_type='approval_record',
    target_id=approval.id,
    detail={
        'decision': normalized_decision,
        'recommendation_id': str(approval.recommendation_id),
        'step_name': approval.step_name,
        'step_order': approval.step_order,
        'comment': approval.comment,
        'operator_role': current_user.role,
    },
)
self.db.add(audit_entry)
# db.commit() follows immediately after
```

**4. Fix submit_for_approval to preserve history on resubmit:**

The bug is in this block (around line 184-210):
```python
existing_by_step = {record.step_name: record for record in recommendation.approval_records}
```

Replace the ENTIRE "existing_by_step / incoming_step_names / delete loop / for index, step in enumerate loop" block with generation-aware logic:

```python
# Determine current generation and whether this is a resubmission after decision
existing_records = list(recommendation.approval_records)
if existing_records:
    current_generation = max(r.generation for r in existing_records)
    any_decided = any(
        r.generation == current_generation and r.decision != 'pending'
        for r in existing_records
    )
    new_generation = current_generation + 1 if any_decided else current_generation
else:
    current_generation = 0
    new_generation = 0

# If resubmitting (new_generation > current_generation), do NOT touch old records.
# If updating a never-decided route (new_generation == current_generation), delete only
# current-generation pending records whose step_name is not in the new steps list.
if new_generation == current_generation:
    # Route update on an un-decided submission — safe to delete current-gen pending records
    incoming_step_names = {str(step['step_name']).strip() for step in steps}
    for record in existing_records:
        if record.generation == current_generation and record.step_name not in incoming_step_names:
            self.db.delete(record)
    existing_by_step_current = {
        r.step_name: r
        for r in existing_records
        if r.generation == current_generation
    }
else:
    # Resubmission — preserve ALL existing records, start fresh with new generation
    existing_by_step_current = {}

for index, step in enumerate(steps, start=1):
    step_name = str(step['step_name']).strip()
    approver_id = str(step['approver_id']).strip()
    comment = str(step['comment']).strip() if step.get('comment') else None
    record = existing_by_step_current.get(step_name)
    if record is None:
        record = ApprovalRecord(
            recommendation_id=recommendation_id,
            approver_id=approver_id,
            step_name=step_name,
            step_order=index,
            decision='pending',
            comment=comment,
            generation=new_generation,
        )
    else:
        record.approver_id = approver_id
        record.step_order = index
        record.decision = 'pending'
        record.comment = comment
        record.decided_at = None
    self.db.add(record)
```

**5. Update _is_current_step to filter by current generation:**

Replace the `for item in self._ordered_records(recommendation):` logic with generation-aware ordering:
```python
def _is_current_step(self, record: ApprovalRecord, *, current_user: User | None = None) -> bool:
    recommendation = record.recommendation
    if recommendation is None or recommendation.status != 'pending_approval' or record.decision != 'pending':
        return False
    if current_user is not None and current_user.role != 'admin' and record.approver_id != current_user.id:
        return False
    # Only consider the current generation
    all_records = recommendation.approval_records
    if not all_records:
        return False
    current_gen = max(r.generation for r in all_records)
    current_gen_records = sorted(
        [r for r in all_records if r.generation == current_gen],
        key=lambda item: (item.step_order, item.created_at),
    )
    for item in current_gen_records:
        if item.id == record.id:
            return True
        if item.decision != 'approved':
            return False
    return False
```

**6. Update list_history to return all generations in order:**
```python
def list_history(self, recommendation_id: str, *, current_user: User | None = None) -> list[ApprovalRecord]:
    query = (
        self._approval_query()
        .where(ApprovalRecord.recommendation_id == recommendation_id)
        .order_by(ApprovalRecord.generation.asc(), ApprovalRecord.step_order.asc(), ApprovalRecord.created_at.asc())
    )
    records = list(self.db.scalars(query))
    if current_user is None:
        return records
    scope_service = AccessScopeService(self.db)
    return [
        record
        for record in records
        if scope_service.can_access_employee(current_user, record.recommendation.evaluation.submission.employee)
    ]
```

**NOTE on SQLite and WITH FOR UPDATE:** SQLite silently ignores FOR UPDATE — pysqlite does not raise an error. The `if approval.decision != 'pending': raise ValueError` guard provides the application-level protection that the tests validate. On PostgreSQL (production), the DB-level lock activates. Add a comment above the with_for_update() call:
```python
# SQLite silently ignores FOR UPDATE; the decision != 'pending' guard below
# provides application-level idempotency. On PostgreSQL this lock is effective.
```
  </action>

  <verify>
    <automated>.venv/Scripts/python.exe -m pytest backend/tests/test_services/test_approval_service.py -x -q 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - `test_concurrent_decide_rejected` still passes (was already passing)
    - `test_audit_log_written_on_decide` now PASSES (AuditLog row written with action='approval_decided')
    - `test_audit_log_written_on_reject` now PASSES (AuditLog row in detail has 'decision': 'rejected' and 'operator_role' key)
    - `test_submit_decide_and_list_workflow` (existing test) still passes — no regression
    - `.venv/Scripts/python.exe -c "from backend.app.services.approval_service import ApprovalService; print('OK')"` prints OK
  </acceptance_criteria>

  <done>APPR-01 guard enforced; APPR-02 generation-based history preserved; APPR-03 AuditLog written in same transaction — all 3 service tests green</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire AuditLog in SalaryService.update_recommendation (APPR-04)</name>
  <files>backend/app/services/salary_service.py</files>

  <read_first>
    - backend/app/services/salary_service.py — read the FULL file; locate update_recommendation (around line 343)
    - backend/app/models/audit_log.py — confirm field names (no old_value/new_value columns yet — store in detail JSON)
    - backend/tests/test_services/test_salary_service.py::test_audit_log_written_on_salary_change — read the exact assertions to satisfy
  </read_first>

  <behavior>
    - update_recommendation captures old_ratio = recommendation.final_adjustment_ratio BEFORE mutation
    - After mutation, before db.commit(), writes AuditLog(operator_id=None, action='salary_updated', target_type='salary_recommendation', target_id=recommendation_id, detail={'old_final_adjustment_ratio': float(old_ratio), 'new_final_adjustment_ratio': round(final_adjustment_ratio,4), 'old_status': old_status, 'new_status': status or old_status})
    - The AuditLog.operator_id is nullable — salary service has no current_user context; pass None
  </behavior>

  <action>
Make the following targeted edit to backend/app/services/salary_service.py:

**1. Add import at top (with other model imports):**
```python
from backend.app.models.audit_log import AuditLog
```

**2. Edit update_recommendation:**
Find the existing implementation. Replace/update it as follows:

```python
def update_recommendation(
    self,
    recommendation_id: str,
    *,
    final_adjustment_ratio: float,
    status: str | None,
) -> SalaryRecommendation | None:
    recommendation = self._query_recommendation(recommendation_id)
    if recommendation is None:
        return None

    # Capture old values before mutation for audit
    old_ratio = float(recommendation.final_adjustment_ratio)
    old_status = recommendation.status

    recommendation.final_adjustment_ratio = round(final_adjustment_ratio, 4)
    recommendation.recommended_salary = (
        recommendation.current_salary * Decimal(str(1 + recommendation.final_adjustment_ratio))
    ).quantize(Decimal('0.01'))
    if status is not None:
        recommendation.status = status

    self.db.add(recommendation)

    # Write audit log in same transaction (APPR-04)
    # operator_id is None — salary service has no auth context; Phase 4 will enrich this
    audit_entry = AuditLog(
        operator_id=None,
        action='salary_updated',
        target_type='salary_recommendation',
        target_id=recommendation_id,
        detail={
            'old_final_adjustment_ratio': old_ratio,
            'new_final_adjustment_ratio': round(final_adjustment_ratio, 4),
            'old_status': old_status,
            'new_status': status if status is not None else old_status,
        },
    )
    self.db.add(audit_entry)
    self.db.commit()

    self.db.refresh(recommendation)
    return recommendation
```

NOTE: The original update_recommendation does not call `self.db.refresh(recommendation)` — check whether it does. If it does not, add it for consistency. Do NOT change any other method signatures or behavior.
  </action>

  <verify>
    <automated>.venv/Scripts/python.exe -m pytest backend/tests/test_services/test_salary_service.py::test_audit_log_written_on_salary_change -x -q 2>&1 | tail -15</automated>
  </verify>

  <acceptance_criteria>
    - `test_audit_log_written_on_salary_change` PASSES
    - Existing salary service tests still pass: `.venv/Scripts/python.exe -m pytest backend/tests/test_services/test_salary_service.py -x -q 2>&1 | tail -10`
    - `.venv/Scripts/python.exe -c "from backend.app.services.salary_service import SalaryService; print('OK')"` prints OK
  </acceptance_criteria>

  <done>APPR-04 satisfied — salary recommendation changes write AuditLog in same transaction; test_audit_log_written_on_salary_change green; no salary service regressions</done>
</task>

</tasks>

<verification>
Run the full approval + salary test suite:

```bash
.venv/Scripts/python.exe -m pytest backend/tests/test_services/test_approval_service.py backend/tests/test_api/test_approval_api.py backend/tests/test_services/test_salary_service.py -v 2>&1 | tail -35
```

Expected:
- test_concurrent_decide_rejected: PASSED
- test_audit_log_written_on_decide: PASSED
- test_audit_log_written_on_reject: PASSED
- test_audit_log_written_on_salary_change: PASSED
- test_resubmit_preserves_history: PASSED (after this plan's submit_for_approval fix)
- All existing approval and salary tests: PASSED
- test_manager_queue_has_dimension_scores: still FAILING (dimension_scores not yet in schema — addressed in Plan 03)
</verification>

<success_criteria>
- Alembic migration runs to head; approval_records table has `generation` column
- ApprovalRecord model reflects the new column and UniqueConstraint
- decide_approval uses with_for_update() fetch
- submit_for_approval preserves old records when resubmitting a rejected recommendation
- Both AuditLog write targets (approval, salary) pass their test stubs
- Zero regressions in existing test suite
</success_criteria>

<output>
After completion, create `.planning/phases/03-approval-workflow-correctness/03-02-SUMMARY.md`
</output>
---
phase: 03-approval-workflow-correctness
plan: 03
type: execute
wave: 3
depends_on: [03-02]
files_modified:
  - backend/app/schemas/approval.py
  - backend/app/api/v1/approvals.py
  - frontend/src/types/api.ts
  - frontend/src/pages/Approvals.tsx
autonomous: false
requirements: [APPR-05, APPR-06, APPR-07]

must_haves:
  truths:
    - "GET /api/v1/approvals/ response items include a dimension_scores list (may be empty if evaluation has none)"
    - "Manager sees only approvals scoped to their department (approval queue filter works)"
    - "HR/HRBP with include_all=true sees approvals across all departments"
    - "The approval detail panel in Approvals.tsx renders a 5-row dimension score table next to the salary recommendation"
  artifacts:
    - path: "backend/app/schemas/approval.py"
      provides: "ApprovalRecordRead with dimension_scores field"
      contains: "dimension_scores.*list.*DimensionScoreRead"
    - path: "backend/app/api/v1/approvals.py"
      provides: "serialize_approval_with_service populates dimension_scores"
      contains: "dimension_scores"
    - path: "frontend/src/types/api.ts"
      provides: "ApprovalRecord interface with dimension_scores"
      contains: "dimension_scores: DimensionScoreRecord"
    - path: "frontend/src/pages/Approvals.tsx"
      provides: "Dimension score breakdown panel in approval detail view"
      contains: "dimension_scores"
  key_links:
    - from: "backend/app/schemas/approval.py ApprovalRecordRead"
      to: "DimensionScoreRead schema"
      via: "from backend.app.schemas.evaluation import DimensionScoreRead"
      pattern: "DimensionScoreRead"
    - from: "_approval_query()"
      to: "AIEvaluation.dimension_scores"
      via: "selectinload chain: recommendation → evaluation → dimension_scores"
      pattern: "selectinload.*dimension_scores"
    - from: "Approvals.tsx"
      to: "ApprovalRecord.dimension_scores"
      via: "selectedApproval?.dimension_scores?.map(...)"
      pattern: "dimension_scores.*map"
---

<objective>
Extend the approval list API to include dimension scores in each response item, and update the Approvals.tsx panel to render those scores alongside the salary recommendation.

Purpose: Give managers and HR reviewers the evaluation breakdown they need to make informed decisions (APPR-05, APPR-06, APPR-07).
Output: Updated schema, API serializer, TypeScript types, and approval detail panel. Verified by test stubs from Plan 01 going green and a human smoke test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/03-approval-workflow-correctness/03-RESEARCH.md
@.planning/phases/03-approval-workflow-correctness/03-02-SUMMARY.md
</context>

<interfaces>
<!-- Contracts the executor must implement against. Read these before touching files. -->

From frontend/src/types/api.ts — DimensionScoreRecord (already exists, do NOT redefine):
```typescript
export interface DimensionScoreRecord {
  id: string;
  dimension_code: string;
  weight: number;
  ai_raw_score: number;
  ai_weighted_score: number;
  raw_score: number;
  weighted_score: number;
  ai_rationale: string;
  rationale: string;
  created_at: string;
}
```

From frontend/src/types/api.ts — ApprovalRecord (current — needs dimension_scores added):
```typescript
export interface ApprovalRecord {
  // ... existing 20 fields ...
  // ADD: dimension_scores: DimensionScoreRecord[];
}
```

From backend/app/schemas/approval.py — ApprovalRecordRead (current — needs dimension_scores):
```python
class ApprovalRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    # ... 24 existing fields ...
    # ADD: dimension_scores: list[DimensionScoreRead] = []
```

From backend/app/schemas/evaluation.py — DimensionScoreRead (check if it exists; if not, define it):
```python
# Expected location: backend/app/schemas/evaluation.py
class DimensionScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    dimension_code: str
    weight: float
    ai_raw_score: float
    ai_weighted_score: float
    raw_score: float
    weighted_score: float
    ai_rationale: str
    rationale: str
    created_at: datetime
```

From backend/app/services/approval_service.py — _approval_query (needs dimension_scores selectinload):
```python
def _approval_query(self):
    return (
        select(ApprovalRecord)
        .options(
            selectinload(ApprovalRecord.approver),
            selectinload(ApprovalRecord.recommendation)
            .selectinload(SalaryRecommendation.evaluation)
            .selectinload(AIEvaluation.submission)
            .selectinload(EmployeeSubmission.employee),
            selectinload(ApprovalRecord.recommendation)
            .selectinload(SalaryRecommendation.evaluation)
            .selectinload(AIEvaluation.submission)
            .selectinload(EmployeeSubmission.cycle),
            # ADD: selectinload chain for dimension_scores (see action below)
        )
    )
```

From backend/app/api/v1/approvals.py — serialize_approval_with_service (needs dimension_scores):
```python
def serialize_approval_with_service(record, service) -> ApprovalRecordRead:
    # ... existing fields ...
    # ADD: dimension_scores = [DimensionScoreRead.model_validate(ds) for ds in evaluation.dimension_scores]
    return ApprovalRecordRead(
        # ... existing kwargs ...
        # ADD: dimension_scores=dimension_scores,
    )
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add dimension_scores to approval backend response (APPR-05, APPR-06)</name>
  <files>backend/app/schemas/approval.py, backend/app/api/v1/approvals.py, backend/app/services/approval_service.py</files>

  <read_first>
    - backend/app/schemas/evaluation.py — check whether DimensionScoreRead already exists; if it does, note the exact class name and fields
    - backend/app/models/evaluation.py — confirm DimensionScore model and relationship name on AIEvaluation
    - backend/app/services/approval_service.py — read _approval_query() in full to understand current selectinload chain
    - backend/app/api/v1/approvals.py — read serialize_approval_with_service in full
    - backend/tests/test_api/test_approval_api.py::test_manager_queue_has_dimension_scores — confirm the exact assertion ('dimension_scores' in first_item)
  </read_first>

  <behavior>
    - ApprovalRecordRead gains field: `dimension_scores: list[DimensionScoreRead] = []`
    - _approval_query adds a selectinload chain for AIEvaluation.dimension_scores
    - serialize_approval_with_service populates dimension_scores from evaluation.dimension_scores
    - test_manager_queue_has_dimension_scores PASSES (key 'dimension_scores' present in each item)
    - test_hrbp_cross_department_queue PASSES (include_all=true returns items regardless of approver filter)
  </behavior>

  <action>
**Step 1 — Confirm or create DimensionScoreRead in backend/app/schemas/evaluation.py:**

Read backend/app/schemas/evaluation.py. If DimensionScoreRead exists, note its import path. If it does NOT exist, append it:
```python
class DimensionScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dimension_code: str
    weight: float
    ai_raw_score: float
    ai_weighted_score: float
    raw_score: float
    weighted_score: float
    ai_rationale: str
    rationale: str
    created_at: datetime
```

**Step 2 — Update backend/app/schemas/approval.py:**

Add import:
```python
from backend.app.schemas.evaluation import DimensionScoreRead
```

Add field to ApprovalRecordRead at the end of the class (after `defer_reason`):
```python
dimension_scores: list[DimensionScoreRead] = []
```

**Step 3 — Extend _approval_query in approval_service.py to eager-load dimension_scores:**

Find the options() block in _approval_query. Add a new selectinload chain:
```python
selectinload(ApprovalRecord.recommendation)
    .selectinload(SalaryRecommendation.evaluation)
    .selectinload(AIEvaluation.dimension_scores),
```
This should be added as an additional option alongside the existing employee and cycle chains.

Important: confirm the attribute name on AIEvaluation for dimension_scores is `dimension_scores` by reading backend/app/models/evaluation.py.

**Step 4 — Update serialize_approval_with_service in approvals.py router:**

Add import:
```python
from backend.app.schemas.evaluation import DimensionScoreRead
```

Inside serialize_approval_with_service, add before the return:
```python
dimension_scores = [
    DimensionScoreRead.model_validate(ds)
    for ds in (evaluation.dimension_scores or [])
]
```

Add `dimension_scores=dimension_scores` to the ApprovalRecordRead(...) constructor call.

**Step 5 — Verify include_all scoping for APPR-06:**

Read list_approvals in approval_service.py. The existing logic is:
```python
if not include_all or current_user.role not in {'admin', 'hrbp'}:
    query = query.where(ApprovalRecord.approver_id == current_user.id)
```
This already correctly gives admin/hrbp the full list when include_all=True. No change needed for APPR-06 functionality.

If test_hrbp_cross_department_queue is still failing after schema change, check whether the HRBP user has department scope that blocks `can_access_employee`. The AccessScopeService check at the end of list_approvals may filter out records if HRBP's departments list doesn't include the employee's department. If so, bind the test HRBP user to the same department as the seeded employee in the test fixture.
  </action>

  <verify>
    <automated>.venv/Scripts/python.exe -m pytest backend/tests/test_api/test_approval_api.py::test_manager_queue_has_dimension_scores backend/tests/test_api/test_approval_api.py::test_hrbp_cross_department_queue -x -q 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - `test_manager_queue_has_dimension_scores` PASSES ('dimension_scores' key present in response items)
    - `test_hrbp_cross_department_queue` PASSES (HRBP with include_all sees cross-department items)
    - `cd frontend && npm run lint` exits 0 (TypeScript changes in next task may cause failures — run after Task 2)
    - `.venv/Scripts/python.exe -c "from backend.app.schemas.approval import ApprovalRecordRead; print(ApprovalRecordRead.model_fields.keys())"` shows 'dimension_scores' in output
  </acceptance_criteria>

  <done>ApprovalRecordRead includes dimension_scores; eager load wired; APPR-05 and APPR-06 backend tests green</done>
</task>

<task type="auto">
  <name>Task 2: Add dimension score panel to Approvals.tsx (APPR-07)</name>
  <files>frontend/src/types/api.ts, frontend/src/pages/Approvals.tsx</files>

  <read_first>
    - frontend/src/types/api.ts — read the FULL ApprovalRecord interface (lines 328-355); read DimensionScoreRecord (lines 234-245)
    - frontend/src/pages/Approvals.tsx — read the FULL file; locate the right-panel detail section that renders employee name, department, step_name, approver_email, recommendation_status, adjustment ratio
    - frontend/src/pages/EvaluationDetail.tsx — read the dimension score rendering section as a pattern reference (same grid pattern to use)
  </read_first>

  <action>
**Step 1 — Update frontend/src/types/api.ts:**

Find the `export interface ApprovalRecord {` block (lines ~328-355). Add one field at the end of the interface (before the closing brace):
```typescript
dimension_scores: DimensionScoreRecord[];
```
DimensionScoreRecord already exists in this file — do NOT redefine it.

**Step 2 — Update frontend/src/pages/Approvals.tsx:**

Find the right-panel detail section. It currently renders: employee name, department, step name, approver email, recommendation_status, final_adjustment_ratio, defer fields.

ADD a dimension score breakdown section BELOW the adjustment ratio display and ABOVE any action buttons (approve/reject/defer).

The UI spec:
- Section heading: "评估维度明细" (Assessment Dimension Breakdown)
- Only render if `selectedApproval.dimension_scores && selectedApproval.dimension_scores.length > 0`
- If no dimension_scores (empty list), render: `<p className="text-sm text-gray-400">暂无维度评分数据</p>`
- Grid: 5 rows, columns: 维度代码 | 权重 | 原始得分 | 加权得分 | AI说明
- Use `dimension_code`, `weight` (format as percentage: `(weight * 100).toFixed(0)%`), `raw_score` (toFixed(1)), `weighted_score` (toFixed(2)), `ai_rationale` (truncate at 60 chars with ellipsis if longer)

Follow the Tailwind patterns from Approvals.tsx:
- Table container: `<div className="mt-4 overflow-x-auto">`
- Table: `<table className="min-w-full text-sm">`
- Header row: `<th className="text-left text-xs font-medium text-gray-500 uppercase pb-2 pr-4">`
- Data rows: `<td className="py-1 pr-4 text-gray-700">` or `<td className="py-1 pr-4 text-gray-500 text-xs">`
- AI rationale cell: allow text wrap, `max-w-xs` class, truncation via JS: `ds.ai_rationale.length > 60 ? ds.ai_rationale.slice(0, 60) + '…' : ds.ai_rationale`

**Variable name to use:** `selectedApproval` (the currently selected ApprovalRecord in the right panel — check the exact variable name by reading the Approvals.tsx state).

TypeScript strict mode: ensure all accesses are null-safe. The `dimension_scores` field defaults to `[]` from the backend so it will always be an array, but use optional chaining `selectedApproval?.dimension_scores` to be safe.

**Step 3 — Verify build:**
```bash
cd frontend && npm run lint
```
Fix any TypeScript errors before marking done.
  </action>

  <verify>
    <automated>cd D:/wage_adjust/frontend && npm run lint 2>&1 | tail -15</automated>
  </verify>

  <acceptance_criteria>
    - `npm run lint` exits 0 (TypeScript strict mode passes — no `tsc --noEmit` errors)
    - `ApprovalRecord` interface in api.ts includes `dimension_scores: DimensionScoreRecord[]`
    - `Approvals.tsx` contains the string "评估维度明细" (section heading)
    - `Approvals.tsx` contains `dimension_scores.map` or `dimension_scores?.map` (renders the list)
    - `npm run build` succeeds (run after lint to confirm production bundle)
  </acceptance_criteria>

  <done>ApprovalRecord TypeScript type includes dimension_scores; Approvals.tsx renders dimension score table in detail panel; lint and build pass</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Complete Phase 3 approval workflow fixes:
    - Pessimistic lock in decide_approval (APPR-01)
    - Generation-based approval history preservation on resubmit (APPR-02)
    - AuditLog writes on every approval decision and salary change (APPR-03, APPR-04)
    - Dimension scores in approval list response for manager and HRBP queues (APPR-05, APPR-06)
    - Dimension score breakdown panel in the Approvals.tsx detail view (APPR-07)
  </what-built>

  <how-to-verify>
    Run the full backend test suite first:
    ```
    .venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short 2>&1 | tail -20
    ```
    Confirm all tests pass (no failures).

    Then start the application and perform the following smoke tests:

    1. Start backend: `uvicorn backend.app.main:app --reload`
    2. Start frontend: `cd frontend && npm run dev`
    3. Open http://127.0.0.1:5174 in browser.

    Smoke test A — Dimension scores visible in approval queue:
    - Log in as a manager or admin
    - Navigate to the "审批中心" (Approval Center) page
    - Select a pending approval from the left panel
    - In the right detail panel, confirm "评估维度明细" section appears below the adjustment ratio
    - If no dimension scores exist for a test evaluation, confirm "暂无维度评分数据" message shows instead of a crash

    Smoke test B — HR/HRBP cross-department view:
    - Log in as an HRBP or admin account
    - Enable the "查看全部" (include all) toggle if it exists, or verify the approval list shows items across multiple departments

    Smoke test C — Rejection history preserved (requires data):
    - If test data is available: reject an existing pending approval, then resubmit it for approval
    - Open the history view for that recommendation
    - Confirm the rejection record from the first round is still visible
  </how-to-verify>

  <resume-signal>Type "approved" if all smoke tests pass. Describe any issues found if they fail.</resume-signal>
</task>

</tasks>

<verification>
Final automated gate before human checkpoint:

```bash
.venv/Scripts/python.exe -m pytest backend/tests/test_services/test_approval_service.py backend/tests/test_api/test_approval_api.py backend/tests/test_services/test_salary_service.py -v 2>&1 | tail -35
```

All 7 Phase 3 requirement tests must be green:
- test_concurrent_decide_rejected: PASSED (APPR-01)
- test_audit_log_written_on_decide: PASSED (APPR-03)
- test_audit_log_written_on_reject: PASSED (APPR-03)
- test_resubmit_preserves_history: PASSED (APPR-02)
- test_audit_log_written_on_salary_change: PASSED (APPR-04)
- test_manager_queue_has_dimension_scores: PASSED (APPR-05)
- test_hrbp_cross_department_queue: PASSED (APPR-06)

Frontend build:
```bash
cd frontend && npm run build 2>&1 | tail -10
```
Must exit 0.
</verification>

<success_criteria>
- All 7 Phase 3 backend tests pass
- frontend build succeeds
- Human smoke test passes (checkpoint task approved)
- No regressions in the broader test suite (.venv/Scripts/python.exe -m pytest backend/tests/ -q)
</success_criteria>

<output>
After completion, create `.planning/phases/03-approval-workflow-correctness/03-03-SUMMARY.md`
</output>
