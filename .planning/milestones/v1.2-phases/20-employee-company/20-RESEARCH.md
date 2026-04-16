# Phase 20: 员工所属公司字段 - Research

**Researched:** 2026-04-09
**Domain:** Employee profile schema extension + import upsert semantics + admin/detail UI visibility
**Confidence:** HIGH

## Summary

Phase 20 is a narrow employee-profile extension, not a new business module. The existing code already centralizes employee reads and writes through `backend/app/models/employee.py`, `backend/app/schemas/employee.py`, `backend/app/services/employee_service.py`, `backend/app/api/v1/employees.py`, and a shared frontend `EmployeeRecord` contract in `frontend/src/types/api.ts`. That means the safest implementation path is to add `company` once to the shared employee contract, then constrain visibility at the UI layer rather than splitting the API into separate list/detail schemas.

The import path is the only place where a shallow implementation would likely regress. `ImportService._import_employees()` currently updates optional fields like `sub_department` only when the column exists in the uploaded table. The user locked a more specific rule for `company`: when the column is present, blank values must clear the field; when the column is absent, existing values must remain untouched. That requires explicit `column in dataframe.columns` handling instead of mirroring the current unconditional optional-field pattern.

**Primary recommendation:** split execution into two plans:
- Plan 01: backend schema/migration/import behavior/tests
- Plan 02: frontend form/detail visibility + shared type alignment + list-page non-display regression

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `company` is optional free text, not required
- **D-02:** all write paths trim leading/trailing whitespace before saving
- **D-03:** no company master-data table, dropdown, or separate company management in this phase
- **D-04:** manual maintenance happens only in the existing `EmployeeArchiveManager` create/edit form
- **D-05:** the employee archive list on the right side of EmployeeAdmin must not show `company`
- **D-06:** manual create and update must both support `company`
- **D-07:** detail display lives on the existing `/employees/:employeeId` route
- **D-08:** `company` belongs in the top profile-card grid beside department/job_family/job_level
- **D-09:** the `/employees` list page must not display `company`
- **D-10:** import `company` column is optional
- **D-11:** if import file includes `company`, non-empty value overwrites and blank clears
- **D-12:** if import file omits `company`, preserve existing value
- **D-13:** import still uses `employee_no` as the upsert key

### the agent's Discretion
- exact Alembic revision id / filename
- exact field ordering within the detail-card grid and admin form
- whether the shared employee API contract includes `company` for list responses, as long as list UI still hides it

### Deferred Ideas (OUT OF SCOPE)
- company master data management
- company-based filters or search
- a new standalone employee profile page
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EMP-01 | Employee 模型新增 company，支持批量导入和管理端手动设置 | Model/schema/service/import patterns below cover the full write path |
| EMP-02 | company 仅在员工档案详情页展示，不出现在员工列表等页面 | Frontend surface analysis below identifies where to render and where to keep omission |
</phase_requirements>

## Existing Integration Map

### Backend source of truth

| File | Role | Phase 20 Impact |
|------|------|-----------------|
| `backend/app/models/employee.py` | ORM entity | Add nullable indexed `company` column |
| `backend/app/schemas/employee.py` | shared create/update/read contract | Add `company` to request/response models |
| `backend/app/services/employee_service.py` | manual create/update normalization | Trim `company` and persist on create/update |
| `backend/app/api/v1/employees.py` | CRUD endpoints | No route changes; responses inherit schema change |
| `backend/app/services/import_service.py` | employee import upsert + templates | Add alias/label/template columns and presence-aware overwrite logic |
| `alembic/versions/` | schema migration path | Add nullable column using SQLite-safe Alembic pattern |

### Frontend surfaces

| File | Role | Phase 20 Impact |
|------|------|-----------------|
| `frontend/src/types/api.ts` | typed employee contract | Add `company` to `EmployeeRecord`, create, and update payloads |
| `frontend/src/components/employee/EmployeeArchiveManager.tsx` | admin create/edit form + archive list | Add editable field on form only; keep right-side list unchanged |
| `frontend/src/pages/EvaluationDetail.tsx` | `/employees/:employeeId` detail page | Render `company` in the top employee info card area |
| `frontend/src/pages/Employees.tsx` | employee list page | Must remain company-free; likely no code change required |
| `frontend/src/pages/MyReview.tsx` and binding/search consumers | shared employee contract readers | Type changes should remain backward compatible if the field is optional |

## Architecture Patterns

### Pattern 1: Shared employee schema with UI-level visibility control

`EmployeeRead` currently powers both list and detail endpoints. Splitting into separate list/detail schemas would create broader API churn without a requirement benefit. The simpler and safer pattern is:

1. add `company: Optional[str] = None` to backend create/update/read schemas
2. add `company: string | null` to frontend employee types
3. keep `/employees` list UI unchanged so the field exists in data but is not rendered there

This matches the user’s requirement, which is about display scope rather than transport prohibition.

### Pattern 2: Trim-on-write in service layer

Manual employee writes already normalize some optional fields in `EmployeeService`, for example `sub_department`. `company` should follow the same pattern:

```python
employee_data['company'] = payload.company.strip() if payload.company else None
```

and for update:

```python
if 'company' in update_data:
    update_data['company'] = update_data['company'].strip() if update_data['company'] else None
```

This keeps normalization centralized instead of relying on frontend hygiene.

### Pattern 3: Presence-aware import updates

The import service currently computes optional values like:

```python
sub_department = str(row['sub_department']).strip() if 'sub_department' in dataframe.columns else ''
...
employee.sub_department = sub_department or None
```

That behavior works for `sub_department`, but it is insufficient for the locked `company` rule because it would clear the field when the column is absent. The correct Phase 20 pattern is:

```python
has_company_column = 'company' in dataframe.columns
company = str(row['company']).strip() if has_company_column else None
...
if employee is None:
    employee.company = company or None
elif has_company_column:
    employee.company = company or None
# else: preserve existing company
```

### Pattern 4: Template parity across CSV and XLSX

Employee import has both CSV and XLSX template generation paths:
- `build_template()`
- `build_template_xlsx()`

Both must add the new `所属公司` column and example value, otherwise one template path will silently drift from the other.

### Pattern 5: Detail-only UI extension

The existing employee detail route already renders a four-cell top grid:
- 部门
- 岗位族
- 岗位级别
- 当前周期

The lowest-risk UI change is to turn this into a five-item grid or move the current-cycle selector after adding `公司` as another profile fact. No new section or route is required.

## Testing Strategy

### Backend regression surface

| Area | Existing tests to extend |
|------|--------------------------|
| manual employee create/update | `backend/tests/test_services/test_employee_service.py` |
| employee CRUD API | `backend/tests/test_api/test_employee_cycle_api.py` |
| employee import CSV/API | `backend/tests/test_services/test_import_service.py`, `backend/tests/test_api/test_import_api.py` |
| employee import XLSX/template parity | `backend/tests/test_services/test_import_xlsx.py` |

### Frontend regression surface

No dedicated frontend test harness exists in this repo. The practical automated gate is `npm --prefix frontend run lint`, combined with file-level assertions that:
- `EvaluationDetail.tsx` renders `employee.company`
- `Employees.tsx` still does not render `employee.company`
- `EmployeeArchiveManager.tsx` form state includes `company`

## Validation Architecture

Wave 0 already exists for backend pytest and frontend type-checking, so Phase 20 does not need new test infrastructure. Validation should sample quickly on:
- targeted backend employee/import pytest files
- frontend TypeScript strict checking via `npm --prefix frontend run lint`

The high-value regression points are:
1. optional-field import semantics
2. API/detail responses carrying `company`
3. list-page omission remaining intact

## Risks and Pitfalls

| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| migration added but schema contract not propagated | admin/detail/import can compile against stale types or silently ignore the field | one backend plan must touch model, schema, service, API tests together |
| import column absence clears company unexpectedly | violates locked D-12 and can destroy existing data during partial imports | branch on column presence, not only row value |
| CSV template updated but XLSX template forgotten | users depending on template download get inconsistent column sets | require both template builders and their tests to change in the same task |
| shared employee type updated but list page accidentally renders company | violates EMP-02 | leave list markup intentionally unchanged and add grep-verifiable acceptance criteria for absence |
| right-side archive list in EmployeeAdmin leaks company | subtle requirement miss because form and list live in same component | add the form field only; keep archive-card text lines unchanged |

## Recommended Plan Split

### Plan 01: Backend schema, import behavior, and regression coverage
- model + Alembic migration
- schemas and service normalization
- import aliases/templates/upsert semantics
- backend tests for create/update/detail/import

### Plan 02: Frontend admin/detail rollout and visibility guardrails
- frontend employee types
- admin form field wiring
- detail page display
- explicit list-page non-display verification

