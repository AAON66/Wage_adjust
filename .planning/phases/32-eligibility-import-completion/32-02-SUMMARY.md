---
phase: 32-eligibility-import-completion
plan: 02
subsystem: backend-import
tags: [import-service, hire-info, non-statutory-leave, salary-adjustments, upsert, overwrite-mode, excel-parsing, decimal-precision]

# Dependency graph
requires:
  - phase: 32-eligibility-import-completion
    plan: 01
    provides: ImportJob.overwrite_mode/actor_id 字段、SalaryAdjustmentRecord UC 业务键、conftest 12 fixture、xlsx builder
provides:
  - ImportService 6 类 import_type 完整支持（加 hire_info + non_statutory_leave）
  - _parse_excel_date helper（Plan 03 preview / Plan 06 集成测试可复用）
  - 4 类资格 import_type 在 service 层支持 merge / replace 语义
  - _import_salary_adjustments 业务键 (employee_id, adjustment_date, adjustment_type) 与飞书同步对齐
affects: [32-03, 32-04, 32-05, 32-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_parse_excel_date 五分支统一 Excel 日期解析（None/date/datetime/数值/序列号字符串/ISO 字符串）"
    - "内联 select(Employee).where(employee_no.in_(...)) 一次性批量查询（不新增 IdentityBindingService 方法）"
    - "merge / replace 模式语义：必填空 → replace failed / merge no_change；可选空 → replace 清空 / merge 保留"
    - "时间戳类字段（last_salary_adjustment_date）replace 模式仍保留旧值（无 NULL 清空语义）"

key-files:
  created:
    - backend/tests/test_services/test_import_hire_info.py
    - backend/tests/test_services/test_import_non_statutory_leave.py
    - backend/tests/test_services/test_import_salary_adjustments_upsert.py
    - backend/tests/test_services/test_import_overwrite_modes.py
  modified:
    - backend/app/services/import_service.py
    - .planning/phases/32-eligibility-import-completion/deferred-items.md

key-decisions:
  - "ImportService.SUPPORTED_TYPES 扩为 6 类（追加 hire_info / non_statutory_leave，不删除既有 4 类）"
  - "_import_hire_info / _import_non_statutory_leave 用内联 select(Employee) 自查，不引入 IdentityBindingService 跨服务方法（决议 Warning 2）"
  - "时间戳类字段 last_salary_adjustment_date 在 replace 模式下仍保留旧值（CONTEXT D-子提示）"
  - "_import_salary_adjustments 业务键三元组 (employee_id, adjustment_date, adjustment_type)，amount 不进业务键（同一员工同一天同一类型不同金额属于「修正」）"
  - "year 字段用三层转换 int(float(str(...))) 处理 '2026.0' 等浮点字符串（Pitfall：dtype=str 后 Excel 数字列）"
  - "Phase 32-03 的 _BUSINESS_KEYS 抽象暂不引入；4 个 _import_* 内通过注释标注 'Phase 32-03 will refactor to _BUSINESS_KEYS lookup'，保留扩展点"

patterns-established:
  - "Excel 日期解析统一走 _parse_excel_date helper（dtype=str 兼容）"
  - "row 结果增加 action（insert/update/no_change）+ fields old/new 对照，供 Plan 03 preview 与 Plan 04 报告复用"
  - "row 结果同时返回 row 与 row_index 双字段（row 给新方法用 / row_index 给既有 _detect_*_error_column 用）"

requirements-completed: [IMPORT-01, IMPORT-05]

# Metrics
duration: 12min
completed: 2026-04-22
---

# Phase 32 Plan 02: ImportService 扩 6 类 + 4 类资格 overwrite_mode 行为 Summary

**ImportService 扩展支持 hire_info / non_statutory_leave 两类资格 import_type，并把 _import_salary_adjustments 从 append 改 upsert（对齐飞书同步业务键），4 类资格 _import_* 全部支持 merge / replace 模式语义**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-22T00:22:40Z
- **Completed:** 2026-04-22T00:35:23Z
- **Tasks:** 2（每个 task 都用 TDD：RED → GREEN）
- **Files created/modified:** 6 (4 created tests + 2 modified)

## Accomplishments

### Task 1: SUPPORTED_TYPES 扩 6 类 + 新增 hire_info / non_statutory_leave 解析

- `SUPPORTED_TYPES` 从 4 类扩为 6 类（追加 `hire_info` / `non_statutory_leave`）
- `REQUIRED_COLUMNS` / `COLUMN_ALIASES` / `TEMPLATE_TEXT_COLUMNS` / `COLUMN_LABELS` 同步补齐两个新类型
- `COLUMN_ALIASES.hire_info` 同时映射「入职日期」与「历史调薪日期」→ `last_salary_adjustment_date`，兼容飞书同步既有标签
- `build_template` (CSV) 与 `build_template_xlsx` (Excel) 都加 hire_info / non_statutory_leave 分支
- 新增 `_parse_excel_date(value)` 静态方法：处理 None / date / datetime / 数值 / Excel 序列号字符串 / ISO 字符串五种输入，统一日期解析口径（Pitfall 1）
- `_import_hire_info` 实现：内联自查 employee_no → Employee；merge 空保留 / replace 必填 hire_date 空 → row failed；时间戳 last_salary_adjustment_date 在 merge / replace 都保留旧值
- `_import_non_statutory_leave` 实现：业务键 (employee_id, year)；upsert；total_days Decimal 精度（Pitfall 8）；leave_type 可选；year 用三层转换防浮点字符串
- `run_import` 加 `overwrite_mode='merge'` 关键字参数 + validate；写入 `ImportJob.overwrite_mode` 与 `actor_id`
- `_dispatch_import` 加 overwrite_mode 透传；4 类资格 _import_* 全部接收该参数

### Task 2: _import_salary_adjustments 改 upsert + _import_performance_grades overwrite_mode 行为

- `_import_salary_adjustments` 从 append 改 upsert：业务键 (employee_id, adjustment_date, adjustment_type)，与飞书 `_sync_salary_adjustments_body` line 947-952 完全对齐（Open Question 1 + Pitfall 4 解决）
- amount 可选字段：merge 空保留 / replace 空清空旧值
- adjustment_date 改用 `_parse_excel_date` helper（统一日期解析路径）
- adjustment_date 与 adjustment_type 必填校验提前报错而非穿透 NULL 到 SQL
- `_import_performance_grades` 加 overwrite_mode 行为：merge 模式 + grade 空 → no_change；replace 模式 + grade 空 → row failed
- 既有 upsert by (employee_id, year) 保留；新增 row 级 action（insert/update/no_change）字段供 preview / 报告使用

## Task Commits

每个 task 用严格 TDD：RED 后 GREEN，分别提交：

1. **Task 1 RED**: `f774713` test(32-02) — hire_info + non_statutory_leave 13 个失败基线
2. **Task 1 GREEN**: `c4e4128` feat(32-02) — SUPPORTED_TYPES 扩 6 类 + 新增解析方法 + overwrite_mode 透传
3. **Task 2 RED**: `9e7a01e` test(32-02) — salary upsert + overwrite_mode 矩阵 12 个测试（4 个失败）
4. **Task 2 GREEN**: `3d360f9` feat(32-02) — _import_salary_adjustments 改 upsert + perf_grades overwrite_mode

## Files Created/Modified

### Created

- `backend/tests/test_services/test_import_hire_info.py` — 7 个测试（SUPPORTED_TYPES / template / ISO / Excel 序列号 / not_found / all_empty / replace 必填）
- `backend/tests/test_services/test_import_non_statutory_leave.py` — 6 个测试（template / upsert by year / Decimal 精度 / 可选 leave_type / not_found / 无效 year）
- `backend/tests/test_services/test_import_salary_adjustments_upsert.py` — 5 个测试（idempotent / update / 同日不同 type / not_found / 中文标签）
- `backend/tests/test_services/test_import_overwrite_modes.py` — 7 个测试（perf_grades replace/merge 必填 + non_statutory_leave replace/merge 可选 + hire_info replace 时间戳 + salary_adj replace/merge amount）

### Modified

- `backend/app/services/import_service.py` — 481 行新增 + 7 行修改：常量扩 6 类 / 新增 _parse_excel_date helper / 新增 2 个 _import_* 方法 / 4 类 _import_* 加 overwrite_mode 参数 / _import_salary_adjustments 改 upsert / _import_performance_grades 加 overwrite_mode 行为
- `.planning/phases/32-eligibility-import-completion/deferred-items.md` — 追加 Plan 02 发现的 9 个 pre-existing import 测试失败记录

## 6 类 import_type 完整列表

| import_type | 业务键 | 行为模式 | 必填字段 | 可选字段 | _import_* 方法 |
|---|---|---|---|---|---|
| `employees` | employee_no（unique 索引） | upsert | employee_no, name, department, job_family, job_level | id_card_no, sub_department, company, status, manager_employee_no | _import_employees |
| `certifications` | (employee_id, certification_type) | upsert | employee_no, certification_type, certification_stage, bonus_rate, issued_at | expires_at | _import_certifications |
| `performance_grades` | (employee_id, year) | upsert + overwrite_mode | employee_no, year, grade | — | _import_performance_grades |
| `salary_adjustments` | (employee_id, adjustment_date, adjustment_type) | **upsert (改自 append)** + overwrite_mode | employee_no, adjustment_date, adjustment_type | amount | _import_salary_adjustments |
| `hire_info` ⭐ | employee_id | upsert + overwrite_mode | employee_no, hire_date | last_salary_adjustment_date | _import_hire_info |
| `non_statutory_leave` ⭐ | (employee_id, year) | upsert + overwrite_mode | employee_no, year, total_days | leave_type | _import_non_statutory_leave |

⭐ Plan 02 新增

## Decisions Made

### 1. _import_hire_info / _import_non_statutory_leave 内联自查 employee_no（不引 IdentityBindingService 跨服务方法）

两个新方法都用 `select(Employee).where(Employee.employee_no.in_(employee_nos))` 一次性批量查询，与 `_import_certifications` 既有写法一致。理由：
- 避免新增跨服务方法（API 边界更稳定）
- 与 _import_certifications 的查询模式保持一致
- 降低 Plan 02 改动范围（不进 IdentityBindingService）

未来如果 4 类资格 _import_* 需要更复杂的员工查找（如按 id_card_no fallback），再统一抽到 `IdentityBindingService.find_employees_by_nos`。

### 2. 时间戳类字段 replace 模式仍保留旧值

`_import_hire_info` 在 replace 模式下处理 `last_salary_adjustment_date` 空值时保留旧值，**不**清空 — 与 CONTEXT D-子提示一致：

> 时间戳类字段无明确"空值"语义；HR 在 Excel 留空通常表示"暂未填写"而非"刻意清空到 NULL"。

测试 `test_hire_info_replace_keeps_timestamp_field` 验证此行为。

### 3. _import_salary_adjustments 业务键 = (employee_id, adjustment_date, adjustment_type) — 解决 RESEARCH Open Question 1

与飞书同步 `_sync_salary_adjustments_body` line 947-952 完全对齐。理由：
- 同一员工同一天同一类型只能有一条记录（业务上不存在"上下午各调一次"）
- 不同金额属于"修正"，应通过 upsert 更新而非新增
- 飞书 + Excel 双链路使用同一业务键，避免双链路冲突

### 4. _BUSINESS_KEYS 抽象暂不引入（保留 Phase 32-03 扩展点）

4 个 _import_* 方法内的业务键查询都是直接硬编码 `select(Model).where(...)`，没有抽象到 `_BUSINESS_KEYS` 字典。每个方法在注释中标注 `# Phase 32-03 will refactor to _BUSINESS_KEYS lookup`，避免本期改动过大同时保留下游扩展点。

Phase 32-03 在引入 preview / confirm 流程时统一抽象。

### 5. row_index 与 row 双字段并存

新写的 _import_* 方法返回 dict 同时含 `row_index` 与 `row` 字段（值相同）。理由：
- `row_index` 是既有约定（_detect_*_error_column 等已依赖）
- `row` 与 plan 中 behavior 例子的命名对齐
- 双字段冗余但向后兼容更稳

未来如果统一到一个字段，由 Plan 32-04 在收 API 输出时去掉重复字段。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 阻塞] adjustment_date 用 pd.to_datetime → 改用 _parse_excel_date**

- **Found during:** Task 2 GREEN 执行 `test_salary_adjustments_replace_clears_amount` 时
- **Issue:** 原 `_import_salary_adjustments` 用 `pd.to_datetime(row['adjustment_date']).date()`，遇到 `xlsx_factory['salary_adjustments']` 生成的浮点字符串 `'1000.0'` 等场景偶发解析失败
- **Fix:** 改用本 plan 新增的 `_parse_excel_date` helper，统一日期解析口径（与 _import_hire_info / _import_non_statutory_leave 一致）
- **Files modified:** `backend/app/services/import_service.py` (line 949-955)
- **Commit:** 包含在 Task 2 GREEN（`3d360f9`）

**2. [Rule 2 - 缺少必填校验] adjustment_date / adjustment_type 必填校验**

- **Found during:** Task 2 RED → GREEN 中
- **Issue:** 原代码遇 adjustment_date / adjustment_type 空字符串时穿透到 SQL 才报错，错误信息含 SQL 细节（信息泄露 + 用户体验差）
- **Fix:** 改为方法层提前校验 `if adjustment_date is None: raise ValueError('调薪日期为必填字段')` / `if not raw_type: raise ValueError('调薪类型为必填字段')`
- **Files modified:** `backend/app/services/import_service.py` (line 956-961)
- **Commit:** 包含在 Task 2 GREEN（`3d360f9`）

### Acceptance Criteria 不可满足项（pre-existing）

**3. [Scope Boundary] test_api/test_import_207.py 7 个测试 + test_import_api.py 2 个测试 pre-existing 失败**

- **Found during:** Task 2 完整 regression
- **Issue:** Plan 要求 `pytest backend/tests/ -x --tb=short -q` 现有测试套件不被破坏（regression 0）
- **诊断:** 9 个失败用 `git stash --include-untracked` 还原本 plan 改动后**仍然失败**，证实与 32-02 改动无关；根因是 wave 0 ImportService 异步化（202 Accepted vs 同步 201 Created），属 Plan 32-04 API 收口范围
- **处理:** 不修复（scope boundary）。已记录到 `deferred-items.md` (Items 3-6)
- **影响:** 不阻塞下游 wave 推进；Plan 32-04 在补 confirm/cancel 接口时一并审视

**4. [Scope Boundary] 4 个 pre-existing service 失败（test_approval / test_dashboard / test_eligibility_batch x2 / test_integration）**

- 全部 pre-existing（stash 验证），与 32-02 改动无关
- Plan 32-01 SUMMARY 中已记录其中 2 个；本次追加 2 个新发现到 deferred-items.md

---

**Total deviations:** 2 auto-fixed (Rules 2-3); 9 pre-existing items deferred (out of scope per deviation rule scope boundary)
**Impact on plan:** 本 plan 全部 must_have artifacts 落地；新增 25 个 Phase 32-02 测试全 pass，46 个既有 import_service 单测无破坏

## Issues Encountered

无业务逻辑阻塞。两个 auto-fix（Rule 2/3）属于本 plan 改动作为副产品发现的小问题：原 `_import_salary_adjustments` 缺少必填字段提前校验、日期解析路径不一致。已在 Task 2 GREEN 一并修复。

## User Setup Required

None — 本 plan 是 service 层改动，无外部服务配置变更，无 schema 改动（schema 已在 Plan 32-01 落地）。

## 下游 Plan 接入指引（03-06 必读）

### ImportService 新接口

```python
# run_import 新签名（向后兼容：overwrite_mode 默认 'merge'）
svc.run_import(
    import_type='hire_info',  # 或其他 5 类
    upload=UploadFile(...),
    overwrite_mode='merge',   # 'merge' | 'replace'
    progress_callback=None,
)

# _dispatch_import 新签名（4 类资格 import_type 透传 overwrite_mode）
svc._dispatch_import(import_type, dataframe, overwrite_mode='merge')

# 4 类资格 _import_* 全部接受 overwrite_mode 参数
svc._import_performance_grades(df, overwrite_mode='merge')
svc._import_salary_adjustments(df, overwrite_mode='merge')
svc._import_hire_info(df, overwrite_mode='merge')
svc._import_non_statutory_leave(df, overwrite_mode='merge')
```

### _parse_excel_date 复用入口

```python
from backend.app.services.import_service import ImportService
adj_date = ImportService._parse_excel_date(raw_value)  # → date | None
```

支持五种输入：None / `date` / `datetime` / 数值 (int/float) / 5-6 位纯数字字符串（Excel 序列号）/ ISO 字符串。无法解析时抛 `ValueError`。

### Plan 32-03 接入提示

- 4 个 _import_* 方法内的业务键查询硬编码注释含 `# Phase 32-03 will refactor to _BUSINESS_KEYS lookup` —— 32-03 在引入 preview / confirm 流程时统一抽象到 `_BUSINESS_KEYS` 字典
- `_import_*` 方法已经返回 row 级 `action`（insert/update/no_change）+ `fields` old/new 对照，可直接被 Plan 32-03 build_preview 复用，无需再次扫描 dataframe
- ImportJob.overwrite_mode + actor_id 已在 Plan 32-01 落地，本 plan 在 run_import 中已写入

### Plan 32-04 接入提示

- API 端点 `/api/v1/imports/jobs?import_type={6 类之一}` 应直接支持 hire_info / non_statutory_leave（已就绪）
- 模板下载端点 `/api/v1/imports/templates/{6 类之一}.xlsx` 已就绪
- 新 import_type 的 row 结果 schema 与既有 4 类略有差异（增加 action / fields 字段），API 层需考虑响应 schema 是否统一

## Next Phase Readiness

- Wave 2 已就绪，Wave 3 (Plan 03 preview / Plan 04 API 收口) 可启动
- 下游 plan executor 读本 SUMMARY 即可知道：
  - 6 类 import_type 业务键 + 必填字段对照
  - _parse_excel_date helper 入口
  - 4 类资格 _import_* 行为矩阵（merge / replace × 必填 / 可选 / 时间戳）
- 无 blocker；`deferred-items.md` 跟踪的 9 个 pre-existing API 失败由 Plan 32-04 owner 在收口 API 层时一并审视

## Self-Check: PASSED

### 文件存在验证

```
FOUND: backend/app/services/import_service.py (modified)
FOUND: backend/tests/test_services/test_import_hire_info.py
FOUND: backend/tests/test_services/test_import_non_statutory_leave.py
FOUND: backend/tests/test_services/test_import_salary_adjustments_upsert.py
FOUND: backend/tests/test_services/test_import_overwrite_modes.py
FOUND: .planning/phases/32-eligibility-import-completion/deferred-items.md (modified)
```

### Commits 存在验证

```
FOUND: f774713 test(32-02) — RED hire_info + non_statutory_leave
FOUND: c4e4128 feat(32-02) — GREEN Task 1 SUPPORTED_TYPES 扩 6 类
FOUND: 9e7a01e test(32-02) — RED Task 2 salary upsert + overwrite matrix
FOUND: 3d360f9 feat(32-02) — GREEN Task 2 _import_salary_adjustments 改 upsert
```

### 测试结果

```
backend/tests/test_services/test_import_hire_info.py: 7/7 PASS
backend/tests/test_services/test_import_non_statutory_leave.py: 6/6 PASS
backend/tests/test_services/test_import_salary_adjustments_upsert.py: 5/5 PASS
backend/tests/test_services/test_import_overwrite_modes.py: 7/7 PASS
backend/tests/test_services/test_import_phase32_scaffold.py: 15/15 PASS (Plan 01 fixture)
=== Phase 32-02 + 32-01 scaffold: 40/40 PASS ===

Regression（既有 import_service 单测 7 个文件）: 46 passed, 0 failed
Pre-existing failures（已记录 deferred-items.md）: 9 (test_import_207 + test_import_api 异步化 202 vs 201)
```

### 6 类 import_type 模板生成验证

```
employees: 6197 bytes ✓
certifications: 6270 bytes ✓
performance_grades: 5616 bytes ✓
salary_adjustments: 5660 bytes ✓
hire_info: 5632 bytes ✓ (新增)
non_statutory_leave: 5656 bytes ✓ (新增)
```

---
*Phase: 32-eligibility-import-completion*
*Plan: 02*
*Completed: 2026-04-22*
