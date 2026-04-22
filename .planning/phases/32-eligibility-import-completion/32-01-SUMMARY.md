---
phase: 32-eligibility-import-completion
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, fixtures, pytest, conftest, schema-migration, import-job, salary-adjustment]

# Dependency graph
requires:
  - phase: 31-feishu-sync-observability
    provides: alembic head 31_01_sync_log_observability + FeishuSyncLog two-phase migration template + per-sync_type lock pattern
provides:
  - ImportJob 模型扩展（overwrite_mode/actor_id/updated_at），支撑 D-12/D-13/D-17
  - SalaryAdjustmentRecord 业务键 UniqueConstraint(employee_id, adjustment_date, adjustment_type)，对齐飞书同步 (D-14 / Pitfall 4)
  - alembic 迁移 32_01_import_job_overwrite_mode（含 dedup + 三阶段加 NOT NULL 列）
  - 顶层 backend/tests/conftest.py，含 12 个共享 fixture（db_session/employee_factory/user_factory/import_job_factory/test_app/3 个 client/2 个 token/tmp_uploads_dir/xlsx_factory）
  - 4 类 import_type 的 xlsx builder（hire_info/non_statutory_leave/performance_grades/salary_adjustments）
  - Wave 0 scaffold 测试文件（15 个测试 GREEN）
affects: [32-02, 32-03, 32-04, 32-05, 32-06]

# Tech tracking
tech-stack:
  added: []  # 全部使用既有 stack
  patterns:
    - "三阶段 alembic 迁移：add nullable → backfill → alter NOT NULL（与 31_01 模式一致）"
    - "迁移内 dedup 后再加 UniqueConstraint（避免历史脏数据阻塞 schema 升级）"
    - "FK ON DELETE SET NULL 保留审计链（actor_id 与 audit_logs.operator_id 模式一致）"
    - "顶层 conftest.py 提供 ApiDatabaseContext + db_session 双轨 fixture（service 层 in-memory + API 层 file-based）"

key-files:
  created:
    - alembic/versions/32_01_import_job_overwrite_mode.py
    - backend/tests/conftest.py
    - backend/tests/fixtures/imports/__init__.py
    - backend/tests/fixtures/imports/builders.py
    - backend/tests/test_services/test_import_phase32_scaffold.py
    - .planning/phases/32-eligibility-import-completion/deferred-items.md
  modified:
    - backend/app/models/import_job.py
    - backend/app/models/salary_adjustment_record.py

key-decisions:
  - "ImportJob.overwrite_mode 默认 'merge'（向后兼容历史 ImportJob 行为）"
  - "ImportJob.actor_id 用 ForeignKey('users.id', ondelete='SET NULL')，与 audit_logs.operator_id 模式一致（RESEARCH Open Question 2 决议）"
  - "SalaryAdjustmentRecord 业务键选 (employee_id, adjustment_date, adjustment_type) 三字段，对齐飞书同步 _sync_salary_adjustments_body line 947-952（RESEARCH Open Question 1 决议）"
  - "迁移在加 UniqueConstraint 前先 dedup（保留 created_at 最新一条），并把 dedup count 写入 alembic.runtime.migration logger（运维审计）"
  - "PerformanceRecord 已有 uq_performance_employee_year（D-15），本期不新加约束"
  - "顶层 conftest.py 提供 in-memory db_session（service 层快）+ file-based ApiDatabaseContext（API 层 dep override）双轨"
  - "xlsx builder 包含未来 import_type（hire_info / non_statutory_leave）— 它们尚未进入 ImportService.SUPPORTED_TYPES，将由 32-02/32-03 plan 落地"

patterns-established:
  - "三阶段迁移加 NOT NULL 列（add nullable → backfill → alter not null）"
  - "迁移内 dedup + log to alembic logger，确保业务键约束加固对历史数据安全"
  - "顶层 conftest.py 暴露 12 个 fixture，下游 plan 的所有测试不再造同款 setup"
  - "xlsx builder 接收 with_serial_date / with_conflict 等关键场景开关"

requirements-completed: [IMPORT-01, IMPORT-05, IMPORT-06, IMPORT-07]

# Metrics
duration: 30min
completed: 2026-04-22
---

# Phase 32 Plan 01: Schema + Test Scaffold 基线 Summary

**ImportJob 加 overwrite_mode/actor_id/updated_at 三列 + SalaryAdjustmentRecord 加业务键 UniqueConstraint + 顶层 12-fixture conftest 就绪**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-21T23:48Z（worktree base reset）
- **Completed:** 2026-04-22T00:18Z
- **Tasks:** 2
- **Files created/modified:** 8

## Accomplishments

- `import_jobs` 表三阶段迁移成功：新增 `overwrite_mode VARCHAR(16) NOT NULL DEFAULT 'merge'` + `actor_id VARCHAR(36) FK users.id ON DELETE SET NULL` + `updated_at DATETIME server_default=now() onupdate=now()`
- `salary_adjustment_records` 表加 `uq_salary_adj_employee_date_type` UniqueConstraint，迁移内含 SQLite-safe dedup（保留每个业务键 created_at 最新一条）+ 写入 alembic logger 供运维审计
- `alembic upgrade head` / `alembic downgrade -1` / `alembic upgrade head` 双向通过；新 head 为 `32_01_import_job_overwrite_mode`
- 顶层 `backend/tests/conftest.py` 提供 12 个共享 fixture（DB 4 个 + Storage 1 个 + xlsx 1 个 + API 6 个），下游 Plan 02-06 测试无需重复造 setup
- 4 类 import_type 的 xlsx builder（含 with_serial_date / with_conflict 选项，覆盖关键场景）
- 15 个 scaffold 测试 GREEN，验证模型字段、约束、fixture 全部就绪

## Task Commits

每个 task 原子提交，TDD 任务多个 commit：

1. **Task 1 (TDD RED): scaffold tests 失败基线** — `7596bd8` (test)
2. **Task 1 (TDD GREEN): ImportJob/SalaryAdj schema 落地** — `d5ac0c7` (feat)
3. **Task 2: 顶层 conftest + xlsx builders** — `64f48cc` (feat)

## Files Created/Modified

### Created

- `alembic/versions/32_01_import_job_overwrite_mode.py` — 三阶段迁移：import_jobs 加 3 列 + salary_adjustment_records dedup + 加 UC
- `backend/tests/conftest.py` — 顶层 12 fixture
- `backend/tests/fixtures/imports/__init__.py` — 空包
- `backend/tests/fixtures/imports/builders.py` — 4 个 xlsx builder
- `backend/tests/test_services/test_import_phase32_scaffold.py` — 15 个 Wave 0 scaffold 测试
- `.planning/phases/32-eligibility-import-completion/deferred-items.md` — 记录 pre-existing 失败/警告（out-of-scope）

### Modified

- `backend/app/models/import_job.py` — 新增 overwrite_mode / actor_id / updated_at 字段
- `backend/app/models/salary_adjustment_record.py` — `__table_args__` 加 UniqueConstraint

## Decisions Made

### 1. SalaryAdjustmentRecord 业务键 = (employee_id, adjustment_date, adjustment_type) — 对 RESEARCH.md Open Question 1 的最终答复

选「飞书同款 3 字段业务键」，对齐 `backend/app/services/feishu_service.py:_sync_salary_adjustments_body` line 947-952。理由：
- 业务对齐：飞书同步与 Excel 导入两条链路使用同一业务键，避免双链路冲突
- 简单：3 字段 vs 4 字段（不含 amount），同一员工同一天同一类型的不同金额属于"修正"而非"新行"，应通过 upsert 处理（D-14 由下游 plan 实现）

### 2. ImportJob.actor_id 用 ON DELETE SET NULL — 对 RESEARCH.md Open Question 2 的最终答复

选 `ForeignKey('users.id', ondelete='SET NULL')`，与既有 `audit_logs.operator_id` FK 行为一致：
- 用户被删除后，ImportJob 不级联删除（保留审计链）
- actor_id 自动置 NULL（匿名化），仍可通过 import_type/file_name 追溯
- 与 STRIDE T-32-10（accept）一致

### 3. PerformanceRecord 已有 uq_performance_employee_year，本期不动 — D-15 决议

`backend/app/models/performance_record.py` 已有 `UniqueConstraint('employee_id', 'year', name='uq_performance_employee_year')`，本期不重复。

### 4. 迁移内 dedup + log — 防止历史脏数据阻塞 UC 加固

如果 `salary_adjustment_records` 中存在同业务键重复行（append 模式残留），加 UC 会失败导致迁移阻塞。本次在 batch_alter 加 UC 前先 SQLite-safe `DELETE WHERE id NOT IN (keepers)`，并把 dedup 前后差异写入 `alembic.runtime.migration` logger，供运维审计。

### 5. 顶层 conftest.py 双轨：service 层 in-memory + API 层 file-based

- `db_session` (in-memory + StaticPool)：service 层单测快，每个测试独立 schema
- `_api_context` (file-based SQLite)：API 测试需要 dep override，文件 DB 跨 connection 持久化
- 两套独立 DB，互不污染

### 6. xlsx builder 包含未来 import_type

`hire_info` 和 `non_statutory_leave` 当前**不在** `ImportService.SUPPORTED_TYPES = {'employees', 'certifications', 'performance_grades', 'salary_adjustments'}` 中。Builder 提前就位是为了 32-02/32-03 plan 实现这两个 import_type 时测试能直接 import 使用。

## Deviations from Plan

### Auto-fixed Issues

无 Rules 1-3 触发的代码自动修复。本 plan 是 schema + fixture 基线，无业务逻辑改动。

### Acceptance Criteria 不可满足项（pre-existing）

**1. [Rule 4 不触发 - Scope Boundary] alembic check 报 pending model changes 警告**

- **Found during:** Task 1 verification
- **Issue:** Plan 要求 `alembic check 不报"pending model changes"警告`。运行后报告大量 `feishu_*/uploaded_files/sharing_requests/certifications/users.must_change_password` 的 server_default drift，以及 `users.feishu_open_id` 的 unique index 漂移
- **诊断:** 用 `grep -E "overwrite_mode|actor_id|uq_salary_adj|import_job|32_01"` 验证 — Phase 32 字段**没有**任何一个出现在警告中。所有 drift 都是 pre-existing
- **处理:** 不修复（scope boundary，与本 plan 改动无关）。已记录到 `deferred-items.md`，建议单独开 chore plan 修复 server_default 与历史迁移对齐
- **Verification:** Phase 32 字段全部正确生效（pytest 5/5 schema tests PASS）

**2. [Rule 4 不触发 - Scope Boundary] test_eligibility_batch.py 2 个测试 pre-existing 失败**

- **Found during:** Task 2 regression check
- **Issue:** `test_filter_before_paginate_status_filter` 和 `test_filter_before_paginate_page_2` 失败
- **诊断:** 用 `git checkout 80aba34 -- import_job.py salary_adjustment_record.py`（还原本 plan 改动前的代码状态）后，这两个测试**仍然失败**。证实与 Phase 32 schema 改动无关
- **处理:** 不修复（scope boundary，pre-existing）。已记录到 `deferred-items.md`
- **影响:** 不阻塞 Phase 32 推进；后续 plan 35（员工端自助体验）启动前由 owner 单独 spike 修复

---

**Total deviations:** 0 auto-fixed; 2 pre-existing items deferred (out of scope per deviation rule scope boundary)
**Impact on plan:** 本 plan 全部 must_have artifacts 落地；pre-existing 问题由 deferred-items.md 跟踪，不影响下游 wave 推进

## Issues Encountered

无业务逻辑问题。唯一处理工作是确认 pre-existing 警告/失败与本 plan 改动无关（已诊断 + 记录）。

## User Setup Required

None — 本 plan 是 schema + fixture 基线，无外部服务配置变更。

## 下游 Plan 接入指引（02-06 必读）

### Schema 接入

- **alembic down_revision:** 后续 plan 加新迁移时，`down_revision = '32_01_import_job_overwrite_mode'`
- **ImportJob 新字段：**
  - `overwrite_mode: str` (NOT NULL, default 'merge')，写入端口请显式传 'merge'/'replace'
  - `actor_id: str | None` (FK users.id ON DELETE SET NULL)，由 confirm 端点写入 `current_user.id`
  - `updated_at: datetime` (server_default=now, onupdate=now)，自动更新无需手写
- **SalaryAdjustmentRecord upsert：** 下游 `_import_salary_adjustments` 改为 upsert 时，业务键用 `(employee_id, adjustment_date, adjustment_type)`，可用 `INSERT ... ON CONFLICT(uq_salary_adj_employee_date_type) DO UPDATE`（SQLite 原生支持）

### Fixture 接入

下游测试只需 `from backend.tests.fixtures.imports.builders import build_xxx_xlsx`（builder 模块）即可拿到 xlsx 字节，pytest 会自动从顶层 `conftest.py` 注入以下 fixture：

| Fixture | 类型 | 用途 |
|---------|------|------|
| `db_session` | Session | service 层单测（in-memory + StaticPool） |
| `employee_factory` | callable | 创建 Employee（默认 P5 工程岗） |
| `user_factory` | callable | 创建 User（默认 hrbp + 'Password123'） |
| `import_job_factory` | callable | 创建 ImportJob（含 Phase 32 新字段） |
| `tmp_uploads_dir` | Path | 隔离 STORAGE_BASE_DIR 到 tmp_path |
| `xlsx_factory` | dict[str, callable] | 4 类 xlsx builder 入口 |
| `test_app` | FastAPI app | API 测试 app（dep 已 override） |
| `client_anon` | TestClient | 无 token |
| `client_hrbp` | TestClient | 含 hrbp Bearer header |
| `client_employee` | TestClient | 含 employee Bearer header |
| `hrbp_user_token` | str | hrbp JWT |
| `employee_user_token` | str | employee JWT |

### xlsx Builder 入口

```python
# backend/tests/fixtures/imports/builders.py
build_hire_info_xlsx(rows=None, *, with_serial_date=False) -> bytes
build_non_statutory_leave_xlsx(rows=None, *, with_conflict=False) -> bytes
build_performance_grades_xlsx(rows=None) -> bytes
build_salary_adjustments_xlsx(rows=None) -> bytes
```

## Next Phase Readiness

- Wave 1 已就绪，Wave 2 (Plan 02 ImportService two-phase + Plan 03 per-type lock) 可并行启动
- 下游 plan executor 读本 SUMMARY 即可知道：
  - 模型字段名 + 默认值
  - alembic revision id（加新迁移用）
  - fixture 名称 + 签名（写测试用）
  - xlsx builder 入口（写测试用）
- 无 blocker；`deferred-items.md` 跟踪的 pre-existing 失败不在本 phase 范围

## Self-Check: PASSED

### 文件存在验证

```
FOUND: alembic/versions/32_01_import_job_overwrite_mode.py
FOUND: backend/app/models/import_job.py (modified)
FOUND: backend/app/models/salary_adjustment_record.py (modified)
FOUND: backend/tests/conftest.py
FOUND: backend/tests/fixtures/imports/__init__.py
FOUND: backend/tests/fixtures/imports/builders.py
FOUND: backend/tests/test_services/test_import_phase32_scaffold.py
FOUND: .planning/phases/32-eligibility-import-completion/deferred-items.md
```

### Commits 存在验证

```
FOUND: 7596bd8 test(32-01): RED scaffold tests
FOUND: d5ac0c7 feat(32-01): GREEN ImportJob/SalaryAdj schema
FOUND: 64f48cc feat(32-01): top-level conftest + xlsx builders
```

### 测试结果

```
backend/tests/test_services/test_import_phase32_scaffold.py: 15/15 PASS
pytest backend/tests/ --collect-only: 647 tests collected, 0 errors
Regression on related modules (10 file scope): 86 passed, 2 failed (pre-existing per deferred-items.md)
```

---
*Phase: 32-eligibility-import-completion*
*Plan: 01*
*Completed: 2026-04-22*
