# Phase 14: Eligibility Visibility & Overrides - Research

**Researched:** 2026-04-02
**Domain:** Role-based eligibility visibility, batch eligibility listing, two-level override approval workflow
**Confidence:** HIGH

## Summary

Phase 14 extends the Phase 13 eligibility engine with three capabilities: (1) role-based visibility that hides eligibility data from employees, (2) a batch eligibility listing API with multi-dimension filtering and Excel export for HR/managers, and (3) a special override request workflow with two-level approval (HRBP then Admin) for ineligible employees with special circumstances.

The codebase already has all necessary building blocks: `AccessScopeService` for department-scoped filtering, `require_roles()` for endpoint protection, `ProtectedRoute` + `roleAccess.ts` for frontend route/menu gating, `openpyxl` for Excel generation, `StreamingResponse` for file downloads, and the `ApprovalRecord` model for multi-step approval chains. The primary new work is: (a) a new `EligibilityOverride` model for special requests, (b) batch eligibility query methods on `EligibilityService`, (c) new API endpoints with proper access control, and (d) a frontend page with two tabs.

**Primary recommendation:** Create a new `EligibilityOverride` model (not reuse `ApprovalRecord` which is tightly coupled to `SalaryRecommendation`) with its own two-step approval chain, add batch query + export + override endpoints to the eligibility API, and build a single frontend page with "Eligibility List" and "Override Requests" tabs.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Multi-dimension filtering -- support department, eligibility status (eligible/ineligible/pending/all), specific rule (tenure/performance/adjustment interval/leave), job family, job level
- **D-02:** Support Excel export of filtered results
- **D-03:** Manager/HRBP can initiate special override requests for ineligible subordinates
- **D-04:** Two-level approval chain -- HRBP approval then Admin approval; both must approve for override to take effect
- **D-05:** Request fields: reason (text) + select which specific rules to override; no attachments needed
- **D-06:** After approval, overridden rules display as "overridden" status in eligibility result
- **D-07:** Dual protection -- backend returns 403 for employee role + frontend hides menu/route
- **D-08:** Managers see their department employees only, reuse AccessScopeService
- **D-09:** HR/Admin can view all employees' eligibility status
- **D-10:** Eligibility page placed under "operations" menu group, alongside employee evaluations and approval center
- **D-11:** Single page with two tabs: Eligibility List + Override Requests
- **D-12:** Employee role menu does not show this page

### Claude's Discretion
- Data model design for override requests (new table vs reuse ApprovalRecord)
- Pagination strategy and default sort for eligibility list
- Excel export format and field selection
- Frontend component decomposition

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ELIG-05 | Eligibility results visible only to HR/manager/admin; hidden from employee | D-07 pattern: `require_roles('admin','hrbp','manager')` on endpoints + `ProtectedRoute` on frontend route + menu exclusion from employee role in `roleAccess.ts` |
| ELIG-06 | HR can batch-view department/company-wide eligibility status | Batch query method on `EligibilityService` with `AccessScopeService` filtering, multi-dimension filter params, pagination, Excel export via `openpyxl` + `StreamingResponse` |
| ELIG-07 | Department can submit special override request for ineligible employees, approved by HR + management | New `EligibilityOverride` model with two-step approval (HRBP then Admin), override status reflected in eligibility results |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | API endpoints for eligibility list, export, overrides | Already in project |
| SQLAlchemy | 2.0.36 | ORM for new EligibilityOverride model | Already in project |
| Alembic | 1.14.0 | Migration for new table | Already in project |
| Pydantic | 2.10.3 | Request/response schemas | Already in project |
| openpyxl | 3.1.5 | Excel export generation | Already in requirements.txt, used by ImportService |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 2.2.3 | DataFrame assembly for export | Only if complex data aggregation needed; direct openpyxl may suffice |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New EligibilityOverride model | Reuse ApprovalRecord | ApprovalRecord has `recommendation_id` FK (non-nullable) tied to SalaryRecommendation; reusing would require schema changes and violate single responsibility. New model is cleaner. |
| openpyxl direct | pandas to_excel | pandas adds overhead; openpyxl is already the established pattern in ImportService |

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  models/
    eligibility_override.py       # New model
  schemas/
    eligibility.py                # Extend with batch + override schemas
  services/
    eligibility_service.py        # Extend with batch query + override methods
  api/v1/
    eligibility.py                # Extend with new endpoints

frontend/src/
  pages/
    EligibilityManagementPage.tsx # Main page with two tabs
  components/
    eligibility/
      EligibilityListTab.tsx      # Tab 1: batch list with filters
      OverrideRequestsTab.tsx     # Tab 2: override request list
      EligibilityFilters.tsx      # Filter controls component
  services/
    eligibilityService.ts         # API client functions
```

### Pattern 1: EligibilityOverride Model Design

**What:** A new SQLAlchemy model to track special override requests with two-step approval.

**When to use:** For all override request lifecycle management.

**Example:**
```python
# Source: project pattern from approval.py + context decisions D-03 through D-06
class EligibilityOverride(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = 'eligibility_overrides'

    employee_id: Mapped[str] = mapped_column(ForeignKey('employees.id'), nullable=False, index=True)
    requester_id: Mapped[str] = mapped_column(ForeignKey('users.id'), nullable=False, index=True)
    override_rules: Mapped[list] = mapped_column(JSON, nullable=False)  # e.g. ['TENURE', 'PERFORMANCE']
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='pending_hrbp')
    # status flow: pending_hrbp -> pending_admin -> approved / rejected
    hrbp_approver_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    hrbp_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hrbp_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    hrbp_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    admin_approver_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    admin_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

**Rationale for inline approval fields (not a separate join table):** The approval chain is fixed at exactly two steps (D-04). A separate step table would over-engineer a two-step process. If the chain becomes dynamic in the future, refactoring to a step table is straightforward.

### Pattern 2: Batch Eligibility Query with N+1 Prevention

**What:** Batch eligibility check that pre-loads all needed data in bulk queries, then runs the pure engine per employee.

**When to use:** For the eligibility list API.

**Example:**
```python
# Source: existing EligibilityService.check_employee() pattern, adapted for batch
def check_employees_batch(
    self,
    employee_ids: list[str],
    *,
    reference_date: date | None = None,
    year: int | None = None,
) -> dict[str, EligibilityResult]:
    # 1. Bulk load all employees
    # 2. Bulk load performance records for the year
    # 3. Bulk load max adjustment dates
    # 4. Bulk load leave totals
    # 5. Run engine.evaluate() per employee using pre-loaded data
    # This avoids N+1: 4 bulk queries instead of 4*N individual queries
```

### Pattern 3: Access Control Dual Protection (D-07)

**What:** Backend `require_roles` + `AccessScopeService` filtering + frontend `ProtectedRoute` + menu exclusion.

**When to use:** For all eligibility visibility endpoints and pages.

**Example:**
```python
# Backend: employee role gets 403
@router.get('/batch', response_model=EligibilityBatchResponse)
def list_eligibility_batch(
    ...,
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
):
    # AccessScopeService filters by department for manager role
```

```typescript
// Frontend: route protected + menu excluded
// In App.tsx:
<Route element={<ProtectedRoute allowedRoles={['admin', 'hrbp', 'manager']} />}>
  <Route element={<EligibilityManagementPage />} path="/eligibility" />
</Route>

// In roleAccess.ts: add to admin, hrbp, manager operations groups
// employee role has NO entry for this page
```

### Pattern 4: Excel Export via StreamingResponse

**What:** Generate Excel in memory with openpyxl, return via StreamingResponse.

**When to use:** For the eligibility list export endpoint.

**Example:**
```python
# Source: existing pattern in backend/app/api/v1/imports.py lines 94-106
from fastapi.responses import StreamingResponse
from openpyxl import Workbook

@router.get('/batch/export')
def export_eligibility(
    ...,
    current_user: User = Depends(require_roles('admin', 'hrbp', 'manager')),
):
    # Build workbook with openpyxl
    wb = Workbook()
    ws = wb.active
    # ... populate rows ...
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=eligibility_export.xlsx'},
    )
```

### Pattern 5: Override Status Integration with Eligibility Results

**What:** When returning eligibility results, check for approved overrides and mark overridden rules.

**When to use:** Whenever eligibility results are returned for an employee with approved overrides.

**Example:**
```python
# After engine.evaluate(), check for approved overrides
overrides = self._get_approved_overrides(employee_id, year=year)
if overrides:
    overridden_codes = set()
    for override in overrides:
        overridden_codes.update(override.override_rules)
    # Patch rule results
    for rule in result.rules:
        if rule.rule_code in overridden_codes and rule.status == 'ineligible':
            # Replace with overridden status
            rule = RuleResult(
                rule_code=rule.rule_code,
                rule_label=rule.rule_label,
                status='overridden',
                detail=f'{rule.detail}（已通过特殊审批覆盖）',
            )
    # Recalculate overall: treat 'overridden' as 'eligible' for overall determination
```

**Note:** This requires adding `'overridden'` to the `RuleResultSchema.status` Literal type and updating the overall status logic.

### Anti-Patterns to Avoid
- **N+1 query in batch eligibility:** Do NOT call `check_employee()` in a loop for batch listing. Pre-load all data in bulk, then run the engine per employee.
- **Reusing ApprovalRecord for overrides:** ApprovalRecord has a non-nullable `recommendation_id` FK. Forcing it to serve override requests would require schema hacks.
- **Client-side filtering only:** All filtering must happen server-side. Do not load all employees and filter in the browser.
- **Hardcoding approval chain logic in the API layer:** Keep override approval logic in the service layer, not in the router.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Excel generation | Custom CSV-to-XLSX converter | openpyxl `Workbook` directly | Already used in ImportService; handles formatting, column widths, etc. |
| Role-based access control | Custom middleware or decorators | `require_roles()` + `AccessScopeService` | Established project pattern; consistent security model |
| Department scoping | Manual department filtering queries | `AccessScopeService.can_access_employee()` | Already handles admin/hrbp/manager/employee role logic |
| Pagination | Manual OFFSET/LIMIT arithmetic | SQLAlchemy `.offset()/.limit()` with standard page/page_size params | Simple and consistent |
| Frontend route protection | Custom auth checks in components | `ProtectedRoute` component | Established pattern in App.tsx |

## Common Pitfalls

### Pitfall 1: N+1 Queries in Batch Eligibility
**What goes wrong:** Calling `check_employee()` for each employee in a loop results in 4 DB queries per employee (tenure, adjustment, performance, leave).
**Why it happens:** The existing single-employee method makes 4 separate queries.
**How to avoid:** Create a batch method that loads all data for all employees in 4 bulk queries, then runs the pure engine per employee.
**Warning signs:** Response time grows linearly with employee count; SQLAlchemy debug logs show hundreds of queries.

### Pitfall 2: Inconsistent Override Status Across Endpoints
**What goes wrong:** The single-employee eligibility endpoint and batch endpoint return different results for overridden employees.
**Why it happens:** Override integration logic is duplicated or only applied in one code path.
**How to avoid:** Extract override application into a shared method (e.g., `_apply_overrides()`) called by both single and batch endpoints.
**Warning signs:** Same employee shows different status in batch list vs individual check.

### Pitfall 3: RuleResult is Frozen Dataclass
**What goes wrong:** Attempting to mutate `RuleResult` objects to apply override status raises `FrozenInstanceError`.
**Why it happens:** `RuleResult` is `@dataclass(frozen=True)`.
**How to avoid:** Create new `RuleResult` instances with overridden values rather than mutating existing ones. Build a new list of rules.
**Warning signs:** `FrozenInstanceError` at runtime.

### Pitfall 4: Missing Year/Reference Date Scoping for Overrides
**What goes wrong:** An override approved for 2025 evaluation year incorrectly affects 2026 eligibility checks.
**Why it happens:** Override lookup doesn't filter by year.
**How to avoid:** Store `year` (and optionally `reference_date`) on the override record; filter by year when applying overrides.
**Warning signs:** Override applied to wrong evaluation period.

### Pitfall 5: HRBP Rejection Should Short-Circuit
**What goes wrong:** After HRBP rejects, the system still expects admin approval.
**Why it happens:** Status machine doesn't handle the rejection path.
**How to avoid:** Per CONTEXT.md specifics: first-level rejection terminates immediately; status goes to `rejected` without proceeding to admin step.
**Warning signs:** Rejected overrides stuck in `pending_admin` state.

### Pitfall 6: Literal Type Not Updated for 'overridden' Status
**What goes wrong:** Pydantic validation rejects responses containing `status: 'overridden'` because the Literal type only allows `'eligible' | 'ineligible' | 'data_missing'`.
**Why it happens:** Schema not updated when adding the override feature.
**How to avoid:** Add `'overridden'` to `RuleResultSchema.status` Literal type.
**Warning signs:** 500 errors on eligibility endpoints for employees with approved overrides.

## Code Examples

### Batch Employee Query with Bulk Loading
```python
# Source: project pattern from EligibilityService + SQLAlchemy bulk query
from sqlalchemy import func, select

def _bulk_load_eligibility_data(
    self,
    employee_ids: list[str],
    year: int,
) -> tuple[dict, dict, dict]:
    """Load performance, adjustment, and leave data in 3 bulk queries."""
    # Performance grades by employee_id
    perf_rows = self.db.execute(
        select(PerformanceRecord.employee_id, PerformanceRecord.grade)
        .where(
            PerformanceRecord.employee_id.in_(employee_ids),
            PerformanceRecord.year == year,
        )
    ).all()
    perf_map = {r[0]: r[1] for r in perf_rows}

    # Max adjustment dates by employee_id
    adj_rows = self.db.execute(
        select(
            SalaryAdjustmentRecord.employee_id,
            func.max(SalaryAdjustmentRecord.adjustment_date),
        )
        .where(SalaryAdjustmentRecord.employee_id.in_(employee_ids))
        .group_by(SalaryAdjustmentRecord.employee_id)
    ).all()
    adj_map = {r[0]: r[1] for r in adj_rows}

    # Leave totals by employee_id
    leave_rows = self.db.execute(
        select(
            AttendanceRecord.employee_id,
            func.sum(AttendanceRecord.non_statutory_leave_days),
        )
        .where(
            AttendanceRecord.employee_id.in_(employee_ids),
            AttendanceRecord.period.like(f'{year}%'),
        )
        .group_by(AttendanceRecord.employee_id)
    ).all()
    leave_map = {r[0]: r[1] for r in leave_rows}

    return perf_map, adj_map, leave_map
```

### Override Request Creation
```python
# Source: project pattern from ApprovalService + CONTEXT.md D-03/D-05
def create_override_request(
    self,
    *,
    employee_id: str,
    requester: User,
    override_rules: list[str],
    reason: str,
    reference_date: date | None = None,
    year: int | None = None,
) -> EligibilityOverride:
    # Validate employee exists and requester has access
    employee = self.db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail='Employee not found')
    # Validate rule codes
    valid_codes = {'TENURE', 'ADJUSTMENT_INTERVAL', 'PERFORMANCE', 'LEAVE'}
    if not set(override_rules).issubset(valid_codes):
        raise HTTPException(status_code=400, detail='Invalid rule codes')
    # Create override record
    override = EligibilityOverride(
        employee_id=employee_id,
        requester_id=requester.id,
        override_rules=override_rules,
        reason=reason,
        status='pending_hrbp',
        reference_date=reference_date,
        year=year or (reference_date.year - 1 if reference_date else date.today().year - 1),
    )
    self.db.add(override)
    self.db.flush()
    return override
```

### Frontend Tab Component Structure
```typescript
// Source: project pattern from existing page components
function EligibilityManagementPage() {
  const [activeTab, setActiveTab] = useState<'list' | 'overrides'>('list');

  return (
    <div>
      <div className="flex border-b mb-4">
        <button
          className={`px-4 py-2 ${activeTab === 'list' ? 'border-b-2 border-blue-500' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          Eligibility List
        </button>
        <button
          className={`px-4 py-2 ${activeTab === 'overrides' ? 'border-b-2 border-blue-500' : ''}`}
          onClick={() => setActiveTab('overrides')}
        >
          Override Requests
        </button>
      </div>
      {activeTab === 'list' ? <EligibilityListTab /> : <OverrideRequestsTab />}
    </div>
  );
}
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | backend/tests/ (implicit discovery) |
| Quick run command | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py -x` |
| Full suite command | `python -m pytest backend/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ELIG-05 | Employee role gets 403 on eligibility batch endpoint | unit | `python -m pytest backend/tests/test_api/test_eligibility_visibility.py -x` | Wave 0 |
| ELIG-06 | Batch eligibility list returns filtered results with pagination | unit | `python -m pytest backend/tests/test_services/test_eligibility_batch.py -x` | Wave 0 |
| ELIG-06 | Excel export contains correct columns and data | unit | `python -m pytest backend/tests/test_services/test_eligibility_export.py -x` | Wave 0 |
| ELIG-07 | Override request creation, HRBP approval, admin approval flow | unit | `python -m pytest backend/tests/test_services/test_eligibility_override.py -x` | Wave 0 |
| ELIG-07 | HRBP rejection short-circuits; no admin step needed | unit | `python -m pytest backend/tests/test_services/test_eligibility_override.py::test_hrbp_rejection_terminates -x` | Wave 0 |
| ELIG-07 | Approved override changes rule status to 'overridden' | unit | `python -m pytest backend/tests/test_engines/test_eligibility_engine.py -x` | Extend existing |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_engines/test_eligibility_engine.py backend/tests/test_services/test_eligibility_batch.py backend/tests/test_services/test_eligibility_override.py -x`
- **Per wave merge:** `python -m pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_api/test_eligibility_visibility.py` -- covers ELIG-05 (403 for employee role)
- [ ] `backend/tests/test_services/test_eligibility_batch.py` -- covers ELIG-06 (batch query + filtering)
- [ ] `backend/tests/test_services/test_eligibility_export.py` -- covers ELIG-06 (Excel export)
- [ ] `backend/tests/test_services/test_eligibility_override.py` -- covers ELIG-07 (full override lifecycle)

## Open Questions

1. **Override uniqueness constraint**
   - What we know: An employee can be ineligible on multiple rules in a given year
   - What's unclear: Should there be one override request per employee per year, or can multiple override requests exist (one per rule set)?
   - Recommendation: Allow one active (non-rejected) override per employee per year. Add a unique constraint on `(employee_id, year)` filtered to non-rejected status, enforced at application level.

2. **Override expiry**
   - What we know: Overrides are scoped to a year/reference_date
   - What's unclear: Should overrides from previous years affect current year checks?
   - Recommendation: No. Filter overrides by year when applying; previous-year overrides do not carry forward.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/engines/eligibility_engine.py` -- EligibilityEngine architecture
- Existing codebase: `backend/app/services/eligibility_service.py` -- service pattern
- Existing codebase: `backend/app/services/approval_service.py` -- multi-step approval pattern
- Existing codebase: `backend/app/models/approval.py` -- ApprovalRecord model structure
- Existing codebase: `backend/app/services/access_scope_service.py` -- department scope filtering
- Existing codebase: `backend/app/dependencies.py` -- `require_roles()` pattern
- Existing codebase: `frontend/src/utils/roleAccess.ts` -- menu/route role configuration
- Existing codebase: `backend/app/api/v1/imports.py` -- StreamingResponse + openpyxl export pattern
- CONTEXT.md decisions D-01 through D-12

### Secondary (MEDIUM confidence)
- None needed; all patterns are established in the codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use in the project
- Architecture: HIGH -- all patterns directly map to existing codebase patterns
- Pitfalls: HIGH -- identified from direct code inspection (frozen dataclasses, N+1 query structure, Literal types)

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable; no external dependency changes expected)
