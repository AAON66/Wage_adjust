# Phase 20: 员工所属公司字段 - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

在现有员工档案链路中新增 `company`（所属公司）字段，覆盖 Employee model/schema、Alembic 迁移、批量导入、管理端手动维护，以及员工详情页展示。

本阶段不包含公司主数据管理、不新增公司筛选或搜索、不在员工列表页展示该字段，也不创建新的独立“员工档案详情页”。

</domain>

<decisions>
## Implementation Decisions

### 公司字段规则
- **D-01:** `company` 为可选自由文本字段，允许为空值。
- **D-02:** 所有写入入口（管理端表单、批量导入）对 `company` 做首尾空格裁剪后再保存。
- **D-03:** 本阶段不引入公司下拉选项、公司字典表或独立公司管理模块，`company` 直接保存为员工档案上的字符串值。

### 手动维护入口
- **D-04:** 管理端仅在现有 `EmployeeArchiveManager` 的新增/编辑表单中增加“所属公司”输入项。
- **D-05:** 员工档案管理页右侧的档案列表卡片不展示 `company`。
- **D-06:** 手动维护支持新增和后续修改，行为与现有员工档案字段保持一致。

### 详情页展示
- **D-07:** 员工所属公司显示在现有 `/employees/:employeeId` 页面顶部资料卡区域，与“部门 / 岗位族 / 岗位级别”处于同一层级。
- **D-08:** 不把 `company` 放到员工编号下方的次级说明文本里，也不单独新增一个“员工档案信息”区块。
- **D-09:** 员工列表页 `/employees` 不展示 `company`，继续保持当前卡片信息密度。

### 导入覆盖语义
- **D-10:** 员工批量导入中的 `company` 列为可选列，不升级为必填列。
- **D-11:** 当导入文件包含 `company` 列时：有值则覆盖为新的公司名，空白值则显式清空员工当前 `company`。
- **D-12:** 当导入文件不包含 `company` 列时：保留员工当前 `company` 不变。
- **D-13:** `company` 继续遵循现有员工导入的 `employee_no` upsert 语义，作为可变档案字段一起更新。

### the agent's Discretion
- 详情页资料卡中 `company` 与“当前周期”选择器的具体排布顺序和响应式换行方式
- 管理端表单中“所属公司”的占位文案、辅助提示文案
- Alembic revision 文件名与 revision id
- 后端是否沿用共享的 `EmployeeRead`/`EmployeeRecord` 合同返回 `company`，只要前端列表页不渲染、不筛选该字段即可

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` — Phase 20 goal and four success criteria
- `.planning/REQUIREMENTS.md` — `EMP-01` and `EMP-02` traceability and milestone requirement wording
- `.planning/PROJECT.md` — v1.2 milestone target feature states that company is detail-only, not a broader employee-list feature

### Backend employee profile flow
- `backend/app/models/employee.py` — Employee ORM model where `company` column must be added
- `backend/app/schemas/employee.py` — shared create/update/read schemas used by admin, list, and detail flows
- `backend/app/services/employee_service.py` — create/update normalization path for manual employee maintenance
- `backend/app/api/v1/employees.py` — list/get/patch endpoints that expose employee profile data
- `backend/app/services/import_service.py` — employee import templates, column aliases, row-level upsert behavior, and optional-field handling
- `backend/app/core/database.py` — project convention that schema changes are applied through Alembic before startup
- `alembic/versions/` — migration location; use SQLite-compatible Alembic pattern for adding the nullable column

### Frontend surfaces
- `frontend/src/components/employee/EmployeeArchiveManager.tsx` — current employee admin create/edit form and archive list that need distinct visibility rules
- `frontend/src/pages/EvaluationDetail.tsx` — current `/employees/:employeeId` detail page with the top employee profile cards
- `frontend/src/pages/Employees.tsx` — employee list page that must continue to omit `company`
- `frontend/src/services/employeeService.ts` — typed frontend service wrapper for employee CRUD reads/writes
- `frontend/src/types/api.ts` — `EmployeeRecord`, create/update payloads, and list response contracts
- `frontend/src/App.tsx` — route mapping confirming `/employees/:employeeId` is the existing detail surface

### Relevant regression coverage
- `backend/tests/test_services/test_employee_service.py` — manual create/update employee service expectations
- `backend/tests/test_services/test_import_service.py` — employee import upsert and optional-column handling
- `backend/tests/test_api/test_import_api.py` — import API flow and template behavior

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/employee/EmployeeArchiveManager.tsx`: already owns both employee create and edit flows, so `company` can be added without creating a new UI surface
- `frontend/src/pages/EvaluationDetail.tsx`: already renders the top employee information cards, making it the natural detail-only display location
- `backend/app/services/import_service.py`: already supports optional employee columns (`sub_department`, `id_card_no`, `manager_employee_no`) and row-level upsert logic

### Established Patterns
- Employee profile writes flow through `EmployeeCreate` / `EmployeeUpdate` schemas into `EmployeeService`
- Employee import uses `employee_no` as the stable upsert key and applies optional-field normalization per row
- Frontend employee list and employee detail both consume the shared employee API contract, so visibility control is primarily a rendering decision
- Schema evolution is Alembic-first; `init_database()` only creates missing tables and does not replace migrations

### Integration Points
- `backend/app/models/employee.py` + `alembic/versions/`: add the new nullable column and migrate existing databases
- `backend/app/schemas/employee.py` + `frontend/src/types/api.ts`: keep backend/frontend employee contracts aligned
- `backend/app/services/import_service.py`: add import alias/template support and implement the selected overwrite/clear semantics
- `frontend/src/components/employee/EmployeeArchiveManager.tsx`: add manual edit field without exposing it in the adjacent archive list
- `frontend/src/pages/EvaluationDetail.tsx`: render `company` in the existing top profile card region
- `frontend/src/pages/Employees.tsx`: verify `company` remains hidden from the list view

</code_context>

<specifics>
## Specific Ideas

- User accepted all recommended defaults for this phase in a single pass.
- “档案详情页” refers to the existing `/employees/:employeeId` route, not a brand-new profile page.
- No extra styling or interaction requirements were added beyond preserving the current information hierarchy.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-employee-company*
*Context gathered: 2026-04-09*
