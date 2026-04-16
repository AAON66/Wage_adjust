---
phase: 20-employee-company
verified: 2026-04-09T04:21:50Z
status: passed
score: 9/9 must-haves verified
---

# Phase 20: Employee Company Verification Report

**Phase Goal:** HR 可为员工设置所属公司，并在档案详情中查看  
**Verified:** 2026-04-09T04:21:50Z  
**Status:** passed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Employee ORM / schema / manual service 写路径支持可选 `company`，并在写入前 trim | ✓ VERIFIED | `backend/app/models/employee.py:23` adds the column; `backend/app/schemas/employee.py:15,32` adds create/update contract fields; `backend/app/services/employee_service.py:37-44,53-69` trims on create/update; `backend/tests/test_services/test_employee_service.py:35-60,138-203` proves create/update/clear behavior. |
| 2 | Alembic migration 为 `employees.company` 增加 nullable indexed column，并可在 SQLite 路径执行 | ✓ VERIFIED | `alembic/versions/e55f2f84b5d1_add_company_to_employee.py:23-32` uses `batch_alter_table('employees')`; temp SQLite spot-check ran `python3 -m alembic upgrade head` successfully and observed `company_column=True`, `company_index=True`. |
| 3 | 批量导入在 CSV/XLSX 含 `company` 列时会把公司值写入员工记录 | ✓ VERIFIED | `backend/app/services/import_service.py:432-489` reads `company` when present and persists it; `backend/tests/test_services/test_import_service.py:38-58` verifies CSV write; `backend/tests/test_services/test_import_xlsx.py:49-72` verifies XLSX write. |
| 4 | 员工导入满足“列存在时空白清空，列缺失时保留原值”语义 | ✓ VERIFIED | `backend/app/services/import_service.py:436-445,482-501` gates updates on `has_company_column`; `backend/tests/test_services/test_import_service.py:117-176` verifies clear, restore, and preserve semantics. |
| 5 | CSV / XLSX 模板与导入 API 对 `company` 字段保持一致 | ✓ VERIFIED | `backend/app/services/import_service.py:219-260` includes `所属公司` in CSV/XLSX templates; `backend/tests/test_services/test_import_service.py:68-73`, `backend/tests/test_services/test_import_xlsx.py:152-165`, and `backend/tests/test_api/test_import_api.py:91-116` verify template and API behavior. |
| 6 | Frontend shared employee types 与 backend shared schema 对齐，不产生 TS drift | ✓ VERIFIED | `frontend/src/types/api.ts:72-110` includes `company` on record/create/update contracts; this matches `backend/app/schemas/employee.py:9-36`; `npm --prefix frontend run lint` passed (`tsc --noEmit`). |
| 7 | 管理端员工编辑表单可手动新增、修改和清空 `company` | ✓ VERIFIED | `frontend/src/components/employee/EmployeeArchiveManager.tsx:6-17,28-40,71-91,136-138` wires `company` through initial form state, edit backfill, submit path, and input control; `frontend/src/services/employeeService.ts:14-21` submits create/update payloads. |
| 8 | `/employees/:employeeId` 顶部资料卡显示所属公司 | ✓ VERIFIED | `frontend/src/pages/EvaluationDetail.tsx:630-635` fetches employee detail and stores it in state; `frontend/src/pages/EvaluationDetail.tsx:2212-2218` renders `employee.company ?? '未设置'` in the top profile-card grid. |
| 9 | `/employees` 列表页与 EmployeeArchiveManager 右侧档案列表都不展示 `company` | ✓ VERIFIED | `frontend/src/pages/Employees.tsx:141-153` renders only department / job family / job level; static check returned `employee.company=False`, `所属公司=False`; `frontend/src/components/employee/EmployeeArchiveManager.tsx:209-233` keeps the right-side summary lines company-free, and a focused slice check returned `company=False`, `所属公司=False`. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/app/models/employee.py` | `Employee.company` ORM column | ✓ VERIFIED | `company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)` at line 23. |
| `backend/app/schemas/employee.py` | shared company contract for create / update / read | ✓ VERIFIED | `company` appears in `EmployeeBase`, `EmployeeUpdate`, and therefore `EmployeeRead` via inheritance. |
| `backend/app/services/employee_service.py` | normalized manual create/update persistence | ✓ VERIFIED | Create and update both normalize `company` with `.strip()` and clear empty values. |
| `alembic/versions/*_add_company_to_employee.py` | migration for `employees.company` | ✓ VERIFIED | Wildcard resolves to `alembic/versions/e55f2f84b5d1_add_company_to_employee.py`; upgrade/downgrade matches model shape and executed in temp SQLite verification. |
| `backend/app/services/import_service.py` | company alias / template / upsert semantics | ✓ VERIFIED | Contains `所属公司` alias/label/template support and presence-aware update logic via `has_company_column`. |
| `backend/tests/test_import_service.py` | company import overwrite / clear / preserve regression coverage | ✓ VERIFIED | Plan frontmatter path is stale; actual coverage lives in `backend/tests/test_services/test_import_service.py` and passed in the phase regression suite. |
| `frontend/src/types/api.ts` | frontend employee company contract | ✓ VERIFIED | `EmployeeRecord`, `EmployeeCreatePayload`, and `EmployeeUpdatePayload` all include `company`. |
| `frontend/src/components/employee/EmployeeArchiveManager.tsx` | admin form wiring for company | ✓ VERIFIED | Form state, edit backfill, and submit path all carry `company`; right-side summary intentionally omits it. |
| `frontend/src/pages/EvaluationDetail.tsx` | detail-only company rendering | ✓ VERIFIED | Renders `employee.company` in the existing top summary grid. |
| `frontend/src/pages/Employees.tsx` | list visibility guardrail | ✓ VERIFIED | Consumes shared employee records but does not render `company`. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `backend/app/services/employee_service.py` | `backend/app/schemas/employee.py` | create/update payloads normalize `company` before persistence | WIRED | `EmployeeCreate` / `EmployeeUpdate` include `company`, and service normalization uses those payloads directly. |
| `backend/app/services/import_service.py` | `backend/app/models/employee.py` | employee import writes `company` only when the source table includes the column | WIRED | Helper tooling false-negative was pattern-specific; actual code stores the condition in `has_company_column` and uses it for both create and update paths. |
| `alembic/versions/e55f2f84b5d1_add_company_to_employee.py` | `backend/app/models/employee.py` | schema migration matches nullable indexed `company` field | WIRED | Migration adds `sa.String(length=128)` nullable column and non-unique index, matching the ORM definition. |
| `frontend/src/components/employee/EmployeeArchiveManager.tsx` | `frontend/src/types/api.ts` | `EmployeeCreatePayload` / `EmployeeRecord` carry `company` through form state | WIRED | The component uses the shared payload and record types for both create and edit flows. |
| `frontend/src/pages/EvaluationDetail.tsx` | `frontend/src/services/employeeService.ts` | detail page reads `company` from shared employee payload | WIRED | `fetchEmployee(employeeId)` populates `employee` state before rendering the company card. |
| `frontend/src/pages/Employees.tsx` | `frontend/src/types/api.ts` | shared type includes `company`, but the list view intentionally omits it from render output | WIRED | This is a negative guardrail: the list consumes `EmployeeListResponse` but only renders name, employee number, department, job family, and job level. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `backend/app/services/import_service.py` | `company` | `row['company']` gated by `has_company_column` | Yes | ✓ FLOWING |
| `frontend/src/components/employee/EmployeeArchiveManager.tsx` | `form.company` | Text input -> `updateForm('company', ...)` -> `createEmployee` / `updateEmployee` API calls | Yes | ✓ FLOWING |
| `frontend/src/pages/EvaluationDetail.tsx` | `employee.company` | `fetchEmployee(employeeId)` -> `/api/v1/employees/{id}` -> `EmployeeRead.model_validate(employee)` | Yes | ✓ FLOWING |
| `frontend/src/pages/Employees.tsx` | `employee` list items | `fetchEmployees(...)` -> shared `EmployeeRecord` payloads | Yes; `company` intentionally not rendered | ✓ FLOWING WITH GUARDRAIL |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 20 backend regression suite | `python3 -m pytest backend/tests/test_services/test_employee_service.py backend/tests/test_services/test_import_service.py backend/tests/test_services/test_import_xlsx.py backend/tests/test_api/test_employee_cycle_api.py backend/tests/test_api/test_import_api.py -q` | `35 passed, 4 warnings in 5.32s` | ✓ PASS |
| Frontend type / contract verification | `npm --prefix frontend run lint` | `tsc --noEmit` exited 0 | ✓ PASS |
| SQLite migration execution | temp-db `python3 -m alembic upgrade head` spot-check | `ALEMBIC_OK`, `company_column=True`, `company_index=True` | ✓ PASS |
| `/employees` list does not leak company | static source check on `frontend/src/pages/Employees.tsx` | `employee.company=False`, `所属公司=False` | ✓ PASS |
| Employee admin right-side archive summary does not leak company | focused source slice check on `frontend/src/components/employee/EmployeeArchiveManager.tsx` | `company=False`, `所属公司=False` | ✓ PASS |

Supplemental user-provided evidence:
- Regression gate: `python3 -m pytest backend/tests/test_celery_app.py backend/tests/test_api/test_health.py -q` → `16 passed`
- Schema drift check: `verify schema-drift 20` → `drift_detected: false`

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `EMP-01` | `20-01-PLAN.md`, `20-02-PLAN.md` | Employee 模型新增 `company`，支持通过批量导入和管理端手动设置 | ✓ SATISFIED | Backend model/schema/service/import path is wired and covered by passing tests; frontend admin form carries `company` through create/edit flows. |
| `EMP-02` | `20-02-PLAN.md` | 所属公司仅在员工档案详情页展示，不出现在员工列表等其他页面 | ✓ SATISFIED | `EvaluationDetail.tsx` renders the company card; `Employees.tsx` and EmployeeArchiveManager right-side list omit the field. |

Orphaned Phase 20 requirements: none.  
Note: `.planning/REQUIREMENTS.md` still lists `EMP-01` and `EMP-02` as `Pending`; this verification confirms both are satisfied in the current codebase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No blocker stubs/placeholders in the phase 20 implementation paths | - | Scan hits were limited to benign input `placeholder` text and unrelated conditional `return null` branches in `EvaluationDetail.tsx`. |

### Gaps Summary

No goal-blocking gaps were found.

Phase 20 achieves the roadmap contract and the plan-specific must-haves. The backend persists `company`, imports it from CSV/XLSX with the required overwrite/clear/preserve semantics, the migration executes on SQLite, the admin form can submit it, the detail page renders it, and the list-style surfaces keep it hidden.

---

_Verified: 2026-04-09T04:21:50Z_  
_Verifier: Claude (gsd-verifier)_
