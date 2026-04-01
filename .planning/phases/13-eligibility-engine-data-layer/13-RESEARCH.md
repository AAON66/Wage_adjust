# Phase 13: Eligibility Engine & Data Layer - Research

**Researched:** 2026-04-02
**Domain:** Business rule engine, data modeling, Excel/Feishu import
**Confidence:** HIGH

## Summary

Phase 13 introduces an eligibility engine that evaluates four rules against employee data to determine salary adjustment qualification. The core work consists of three layers: (1) new SQLAlchemy models for `PerformanceRecord` and `SalaryAdjustmentRecord` plus two new fields on `Employee`, (2) a pure-computation `EligibilityEngine` following the existing `EvaluationEngine`/`SalaryEngine` pattern, and (3) import pipeline extensions to bring data in via Excel, Feishu, and manual entry.

The existing codebase provides strong precedents for all three layers. Models use UUID+timestamp mixins and Alembic migrations. Engines are stateless dataclass-in/dataclass-out classes with no DB dependency. Import uses pandas DataFrame + per-row SAVEPOINT with localized error messages. Feishu sync uses `FeishuService` with field mapping and upsert. All patterns are well-established and the phase requires zero new libraries.

**Primary recommendation:** Follow existing patterns exactly -- pure-computation engine, Alembic migration for new models/fields, extend `ImportService.SUPPORTED_TYPES` for two new import types, add Feishu sync config for performance data.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `hire_date` and `last_salary_adjustment_date` added directly to Employee model via Alembic migration
- **D-02:** New `PerformanceRecord` model -- one record = one employee's annual grade (A/B/C/D/E), supports multi-year history
- **D-03:** New `SalaryAdjustmentRecord` model -- one record per adjustment (date, type[转正/年度/专项], amount), easy to query most recent
- **D-04:** Rule thresholds configurable -- 6-month tenure, 6-month adjustment interval, C-grade performance, 30-day leave placed in config file or database, HR can adjust without code changes
- **D-05:** Eligibility computed in real-time, not stored -- each query recalculates 4 rules from latest data, avoids snapshot/data inconsistency
- **D-06:** Engine follows existing EvaluationEngine/SalaryEngine pattern -- pure computation, no DB dependency, structured input/output
- **D-07:** All three import channels implemented: Excel batch, Feishu sync, manual entry
- **D-08:** Separate Excel templates for performance (employee_no + year + grade) and salary adjustment history (employee_no + date + type + amount)
- **D-09:** Feishu sync reuses existing feishu_service.py multi-table sync pattern
- **D-10:** Missing data makes overall status "pending" -- existing data rules evaluated normally (pass/fail), missing data shows "data missing"
- **D-11:** No reminder mechanism -- just show "data missing" status in eligibility list, HR imports manually

### Claude's Discretion
- Alembic migration script structure
- EligibilityEngine internal method decomposition
- API endpoint paths and response structure design
- Feishu sync field mapping specifics

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ELIG-01 | Auto-check hire_date >= 6 months | Employee.hire_date field + EligibilityEngine tenure rule |
| ELIG-02 | Auto-check last salary adjustment >= 6 months (including 转正/专项) | SalaryAdjustmentRecord model + engine interval rule |
| ELIG-03 | Auto-check annual performance not C or below (data via Excel/Feishu/manual) | PerformanceRecord model + engine performance rule + import channels |
| ELIG-04 | Auto-check non-statutory leave <= 30 days | AttendanceRecord.leave_days + engine leave rule (clarify statutory vs non-statutory) |
| ELIG-08 | Missing data shows "data missing" not "ineligible" | Three-state rule result: eligible/ineligible/data_missing |
| ELIG-09 | Data supports 3 import channels: Excel, Feishu, manual entry | ImportService extension + FeishuService extension + CRUD API endpoints |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack:** Python + FastAPI backend, React frontend, SQLAlchemy ORM, Alembic migrations
- **Engine pattern:** Pure computation classes, no DB dependency, structured input/output
- **Config:** All thresholds/coefficients must be configurable, not hardcoded in multiple places
- **Audit:** All key business results must be auditable, explainable, traceable
- **Import:** Must handle idempotency, validation error feedback, partial success
- **API:** Versioned under `/api/v1/`
- **Testing:** Unit tests required for scoring/eligibility logic
- **Code style:** `from __future__ import annotations` in all backend modules, PEP 604 unions, Pydantic BaseModel with `ConfigDict(from_attributes=True)`

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36 | ORM for new models | Already in use, DeclarativeBase pattern |
| Alembic | 1.14.0 | Schema migration for Employee fields + new tables | Sole migration path per project decision |
| Pydantic | 2.10.3 | Request/response schemas | Already in use for all API contracts |
| pandas | 2.2.3 | DataFrame operations for Excel import | Already in use by ImportService |
| FastAPI | 0.115.0 | API endpoints | Already in use |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openpyxl | (installed) | XLSX read/write for import templates | Already used by ImportService for xlsx support |
| httpx | 0.28.1 | Feishu API calls | Already used by FeishuService |

### No New Dependencies Required
This phase requires zero new library installations. All functionality is built on existing stack.

## Architecture Patterns

### New Files to Create
```
backend/
├── app/
│   ├── models/
│   │   ├── performance_record.py      # New: PerformanceRecord model
│   │   └── salary_adjustment_record.py # New: SalaryAdjustmentRecord model
│   ├── engines/
│   │   └── eligibility_engine.py       # New: Pure computation engine
│   ├── schemas/
│   │   └── eligibility.py              # New: Pydantic schemas
│   ├── services/
│   │   └── eligibility_service.py      # New: DB orchestration layer
│   └── api/v1/
│       └── eligibility.py              # New: API endpoints
├── alembic/versions/
│   └── 013_add_eligibility_models.py   # New: Migration script
```

### Pattern 1: EligibilityEngine (Pure Computation)
**What:** Stateless engine that accepts employee data as dataclasses and returns structured eligibility results per rule
**When to use:** Always -- follows locked decision D-06
**Example:**
```python
# Follows EvaluationEngine/SalaryEngine pattern exactly
from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class EligibilityThresholds:
    min_tenure_months: int = 6
    min_adjustment_interval_months: int = 6
    min_performance_grade: str = 'C'  # C and below = ineligible
    max_non_statutory_leave_days: float = 30.0

@dataclass(frozen=True)
class RuleResult:
    rule_code: str
    rule_label: str
    status: str  # 'eligible' | 'ineligible' | 'data_missing'
    detail: str

@dataclass
class EligibilityResult:
    overall_status: str  # 'eligible' | 'ineligible' | 'pending'
    rules: list[RuleResult]

class EligibilityEngine:
    def __init__(self, thresholds: EligibilityThresholds | None = None):
        self.thresholds = thresholds or EligibilityThresholds()

    def evaluate(self, *, hire_date: date | None, ...) -> EligibilityResult:
        ...
```

### Pattern 2: PerformanceRecord Model
**What:** SQLAlchemy model with UniqueConstraint on (employee_id, year)
**When to use:** Store annual performance grades
**Example:**
```python
from __future__ import annotations
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base
from backend.app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, UpdatedAtMixin

class PerformanceRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'performance_records'
    __table_args__ = (
        UniqueConstraint('employee_id', 'year', name='uq_performance_employee_year'),
    )
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey('employees.id'), nullable=False, index=True)
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(8), nullable=False)  # A/B/C/D/E
    source: Mapped[str] = mapped_column(String(32), nullable=False, default='manual')  # manual/excel/feishu
```

### Pattern 3: SalaryAdjustmentRecord Model
**What:** Historical salary adjustment records with type classification
**When to use:** Track all past adjustments for interval calculation
**Example:**
```python
class SalaryAdjustmentRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'salary_adjustment_records'
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey('employees.id'), nullable=False, index=True)
    employee_no: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    adjustment_type: Mapped[str] = mapped_column(String(32), nullable=False)  # probation/annual/special
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default='manual')
```

### Pattern 4: ImportService Extension
**What:** Add `performance_grades` and `salary_adjustments` to SUPPORTED_TYPES
**When to use:** Reuse existing import pipeline with new dispatch handlers
**Example:**
```python
# In ImportService:
SUPPORTED_TYPES = {'employees', 'certifications', 'performance_grades', 'salary_adjustments'}
REQUIRED_COLUMNS = {
    ...
    'performance_grades': ['employee_no', 'year', 'grade'],
    'salary_adjustments': ['employee_no', 'adjustment_date', 'adjustment_type'],
}
```

### Pattern 5: Three-State Rule Result (ELIG-08)
**What:** Each rule returns one of three states, overall status derived from combination
**When to use:** Always -- core requirement
**Logic:**
- If ANY rule is `ineligible` -> overall = `ineligible`
- If ALL rules are `eligible` -> overall = `eligible`
- If no rule is `ineligible` but some are `data_missing` -> overall = `pending`

### Anti-Patterns to Avoid
- **Storing eligibility snapshots:** D-05 explicitly says real-time computation. Do NOT create an eligibility result table.
- **Hardcoding thresholds:** D-04 requires configurable thresholds. Do NOT put `6` or `30` as magic numbers in engine logic.
- **Mixing DB access into engine:** D-06 requires pure computation. The service layer queries DB and passes data to the engine.
- **Treating data_missing as ineligible:** ELIG-08 explicitly separates these states.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Excel import parsing | Custom file reader | Existing ImportService + pandas | Already handles CSV/XLSX, encoding, error reporting |
| Feishu data sync | New sync infrastructure | Existing FeishuService pattern | Token management, pagination, field mapping, retry all built |
| Date interval calculation | Manual day counting | Python `dateutil.relativedelta` or manual month diff | Edge cases around month boundaries; but stdlib is sufficient since we only need month-level granularity |
| Migration | Manual SQL | Alembic `op.add_column` / `op.create_table` | Sole migration path per project decision |

**Key insight:** This phase adds zero new libraries. Every infrastructure need is already solved in the codebase.

## Common Pitfalls

### Pitfall 1: AttendanceRecord leave_days Does Not Distinguish Statutory vs Non-Statutory
**What goes wrong:** ELIG-04 requires checking "non-statutory leave" (excluding maternity leave etc.), but AttendanceRecord.leave_days is a single float with no type distinction.
**Why it happens:** Original attendance model was designed for general tracking, not eligibility rules.
**How to avoid:** Two options: (a) add a `non_statutory_leave_days` field to AttendanceRecord via migration, or (b) treat the existing `leave_days` as non-statutory by convention and document this assumption. Option (b) is simpler and aligns with D-11 (minimal scope). The CONTEXT.md notes this as a specific idea to clarify.
**Warning signs:** Leave data imported from Feishu may or may not have statutory/non-statutory breakdown.

### Pitfall 2: Alembic Migration Order with SQLite batch_alter_table
**What goes wrong:** Adding columns to existing Employee table on SQLite requires `batch_alter_table` context manager.
**Why it happens:** SQLite does not support `ALTER TABLE ADD COLUMN` with constraints in all cases.
**How to avoid:** Use `with op.batch_alter_table('employees') as batch_op:` pattern. See existing migration `b12_add_token_version.py` which uses simple `op.add_column` -- this works for nullable columns or columns with server_default on SQLite. For `hire_date` and `last_salary_adjustment_date` which should be nullable (existing employees won't have these), simple `op.add_column` is fine.
**Warning signs:** Migration fails on SQLite but works on PostgreSQL.

### Pitfall 3: Real-Time Computation Performance at Scale
**What goes wrong:** Eligibility check for all employees requires joining multiple tables per employee.
**Why it happens:** D-05 says no snapshots -- compute on every request.
**How to avoid:** For list views, the service should batch-load attendance/performance/adjustment data for the requested page of employees in one query each, then feed to engine per employee. Avoid N+1 queries.
**Warning signs:** `/api/v1/eligibility` endpoint takes > 2 seconds for 100 employees.

### Pitfall 4: Import Upsert Key Design
**What goes wrong:** Duplicate imports create duplicate records instead of updating.
**Why it happens:** No unique constraint on the import key.
**How to avoid:** PerformanceRecord has `UniqueConstraint('employee_id', 'year')`. SalaryAdjustmentRecord should upsert on `(employee_id, adjustment_date, adjustment_type)` or just append (since multiple adjustments of same type on same date are unlikely). Use SAVEPOINT pattern from existing ImportService.
**Warning signs:** Duplicate rows after re-importing same file.

### Pitfall 5: Grade Comparison Logic
**What goes wrong:** String comparison of grades (A > B > C > D > E) may not work correctly with simple string operators.
**Why it happens:** Alphabetical order happens to work for A/B/C/D/E but this is fragile.
**How to avoid:** Map grades to numeric values in the engine: `{'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}`. Check if grade value <= threshold value.
**Warning signs:** Grade 'B+' or 'C-' breaks the comparison.

## Code Examples

### EligibilityEngine Core Logic
```python
# Source: Derived from existing EvaluationEngine/SalaryEngine pattern
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from dateutil.relativedelta import relativedelta

GRADE_ORDER = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}

@dataclass(frozen=True)
class EligibilityThresholds:
    min_tenure_months: int = 6
    min_adjustment_interval_months: int = 6
    performance_fail_grades: tuple[str, ...] = ('C', 'D', 'E')
    max_non_statutory_leave_days: float = 30.0

class EligibilityEngine:
    def __init__(self, thresholds: EligibilityThresholds | None = None):
        self.thresholds = thresholds or EligibilityThresholds()

    def check_tenure(self, hire_date: date | None, reference_date: date) -> RuleResult:
        if hire_date is None:
            return RuleResult(rule_code='TENURE', rule_label='入职时长', status='data_missing', detail='入职日期未录入')
        months = (reference_date.year - hire_date.year) * 12 + (reference_date.month - hire_date.month)
        if months >= self.thresholds.min_tenure_months:
            return RuleResult(rule_code='TENURE', rule_label='入职时长', status='eligible', detail=f'已入职 {months} 个月')
        return RuleResult(rule_code='TENURE', rule_label='入职时长', status='ineligible', detail=f'入职仅 {months} 个月，需满 {self.thresholds.min_tenure_months} 个月')
```

### Alembic Migration Pattern
```python
# Source: Existing b12_add_token_version.py pattern
def upgrade() -> None:
    # Employee fields -- nullable for existing rows
    op.add_column('employees', sa.Column('hire_date', sa.Date(), nullable=True))
    op.add_column('employees', sa.Column('last_salary_adjustment_date', sa.Date(), nullable=True))

    # New tables
    op.create_table(
        'performance_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('employee_no', sa.String(64), nullable=False, index=True),
        sa.Column('year', sa.Integer(), nullable=False, index=True),
        sa.Column('grade', sa.String(8), nullable=False),
        sa.Column('source', sa.String(32), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('employee_id', 'year', name='uq_performance_employee_year'),
    )
    op.create_table(
        'salary_adjustment_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False, index=True),
        sa.Column('employee_no', sa.String(64), nullable=False, index=True),
        sa.Column('adjustment_date', sa.Date(), nullable=False, index=True),
        sa.Column('adjustment_type', sa.String(32), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('source', sa.String(32), nullable=False, server_default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
```

### Import Extension Pattern
```python
# Source: Existing ImportService._import_certifications pattern
def _import_performance_grades(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for index, row in dataframe.iterrows():
        try:
            with self.db.begin_nested():
                employee_no = str(row['employee_no']).strip()
                employee = self.db.scalar(select(Employee).where(Employee.employee_no == employee_no))
                if employee is None:
                    raise ValueError(f'未找到员工工号"{employee_no}"')
                year = int(row['year'])
                grade = str(row['grade']).strip().upper()
                if grade not in ('A', 'B', 'C', 'D', 'E'):
                    raise ValueError(f'绩效等级"{grade}"不合法，请填写 A/B/C/D/E')
                # Upsert on (employee_id, year)
                existing = self.db.scalar(
                    select(PerformanceRecord).where(
                        PerformanceRecord.employee_id == employee.id,
                        PerformanceRecord.year == year,
                    )
                )
                if existing:
                    existing.grade = grade
                    existing.source = 'excel'
                else:
                    record = PerformanceRecord(
                        employee_id=employee.id, employee_no=employee_no,
                        year=year, grade=grade, source='excel',
                    )
                    self.db.add(record)
                self.db.flush()
            results.append({'row_index': int(index) + 1, 'status': 'success', 'message': '绩效导入成功。'})
        except Exception as exc:
            self.db.expire_all()
            results.append({'row_index': int(index) + 1, 'status': 'failed', 'message': str(exc)})
    self.db.commit()
    return results
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No eligibility check | Real-time 4-rule engine | Phase 13 | Automated qualification filtering |
| No performance data model | PerformanceRecord table | Phase 13 | Enables ELIG-03 rule |
| No adjustment history | SalaryAdjustmentRecord table | Phase 13 | Enables ELIG-02 rule |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | pytest section not explicit; tests under `backend/tests/` |
| Quick run command | `python -m pytest backend/tests/test_engines/ -x -q` |
| Full suite command | `python -m pytest backend/tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ELIG-01 | Tenure >= 6 months check | unit | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py::test_tenure_rule -x` | Wave 0 |
| ELIG-02 | Adjustment interval >= 6 months | unit | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py::test_adjustment_interval_rule -x` | Wave 0 |
| ELIG-03 | Performance grade C or below = ineligible | unit | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py::test_performance_rule -x` | Wave 0 |
| ELIG-04 | Non-statutory leave > 30 days = ineligible | unit | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py::test_leave_rule -x` | Wave 0 |
| ELIG-08 | Missing data -> data_missing status | unit | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py::test_missing_data_status -x` | Wave 0 |
| ELIG-09 | Import channels work | unit | `python -m pytest backend/tests/test_services/test_import_eligibility.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_engines/test_eligibility_engine.py -x -q`
- **Per wave merge:** `python -m pytest backend/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_engines/test_eligibility_engine.py` -- covers ELIG-01 through ELIG-04, ELIG-08
- [ ] `backend/tests/test_services/test_import_eligibility.py` -- covers ELIG-09 import channels
- [ ] `backend/tests/test_models/test_eligibility_models.py` -- basic model instantiation tests

## Open Questions

1. **AttendanceRecord leave_days: statutory vs non-statutory**
   - What we know: `leave_days` is a single float field. ELIG-04 needs non-statutory leave only.
   - What's unclear: Whether Feishu source data distinguishes leave types. Whether to add a new column or use convention.
   - Recommendation: Add `non_statutory_leave_days` field to AttendanceRecord in the same migration. Default to `leave_days` value when distinction is unavailable. This preserves backward compatibility and enables future refinement.

2. **Configurable thresholds storage**
   - What we know: D-04 says thresholds must be configurable. Options: (a) Settings/env vars, (b) database table, (c) JSON config file.
   - What's unclear: Whether HR needs a UI to change thresholds (deferred per Out of Scope) or env vars suffice.
   - Recommendation: Use `Settings` (pydantic-settings) for now -- add `eligibility_min_tenure_months`, `eligibility_min_adjustment_interval_months`, etc. to `config.py`. This follows existing pattern and is easy to override via `.env`. A future phase can add a UI config table.

3. **Employee.last_salary_adjustment_date vs SalaryAdjustmentRecord**
   - What we know: D-01 adds the field to Employee, D-03 creates SalaryAdjustmentRecord. Both exist.
   - What's unclear: Whether `last_salary_adjustment_date` is denormalized from SalaryAdjustmentRecord or independent.
   - Recommendation: The engine should query `SalaryAdjustmentRecord` for the most recent record and use that date. `Employee.last_salary_adjustment_date` serves as a fallback/seed value for employees whose history predates the system. The service layer should prefer SalaryAdjustmentRecord data when available.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/engines/evaluation_engine.py`, `backend/app/engines/salary_engine.py` -- engine pattern
- Existing codebase: `backend/app/services/import_service.py` -- import pipeline pattern
- Existing codebase: `backend/app/services/feishu_service.py` -- Feishu sync pattern
- Existing codebase: `backend/app/models/attendance_record.py` -- model + migration pattern
- Existing codebase: `backend/app/models/mixins.py` -- UUID/timestamp mixins
- Phase 13 CONTEXT.md -- all locked decisions

### Secondary (MEDIUM confidence)
- None needed -- all patterns are well-established in the codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - zero new dependencies, all existing libraries
- Architecture: HIGH - follows established engine/model/import patterns exactly
- Pitfalls: HIGH - based on direct codebase analysis of AttendanceRecord limitations and SQLite migration constraints

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable -- internal patterns, no external dependency changes)
