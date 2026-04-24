---
phase: 36-historical-performance-display
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, pydantic, import-service, performance]
requires:
  - phase: 34-performance-management-service-and-api
    provides: PerformanceRecord 基础模型、PerformanceService、绩效导入主链路
provides:
  - PerformanceRecord.comment 可空长文本存储
  - PerformanceRecordRead/CreateRequest comment 契约
  - PerformanceHistoryResponse schema 命名落位
  - performance_grades 导入 comment 别名与 merge 锁定策略
affects: [36-02, 36-03, historical-performance-display]
tech-stack:
  added: []
  patterns: [SQLite 兼容 batch_alter_table, comment 列 merge 有值才覆盖]
key-files:
  created:
    - alembic/versions/36_01_add_comment_to_performance_records.py
  modified:
    - backend/app/models/performance_record.py
    - backend/app/schemas/performance.py
    - backend/app/services/import_service.py
    - backend/app/services/performance_service.py
    - backend/tests/test_models/test_schema_models.py
    - backend/tests/test_services/test_import_service.py
    - backend/tests/test_services/test_performance_service.py
key-decisions:
  - "comment 列使用 Text nullable=True，存量行保持 NULL，不做数据写入脚本。"
  - "Excel merge 模式对 comment 采用有列即写、无列不改，避免重复导入误清空历史评语。"
  - "Schema 命名采用 PerformanceHistoryResponse，供 Plan 02/03 后续直接复用。"
patterns-established:
  - "Alembic migration 用 batch_alter_table 做 SQLite 兼容列变更。"
  - "导入路径对可选 comment 列统一做 None/空串规整，再决定是否覆盖 existing.comment。"
requirements-completed: [PERF-07]
duration: 49min
completed: 2026-04-24
---

# Phase 36 Plan 01: 历史绩效 comment 存储与导入基础 Summary

**PerformanceRecord 新增 comment 持久化字段，并补齐 schema / service / Excel 导入链路的评语写入能力。**

## Performance

- **Duration:** 49 min
- **Started:** 2026-04-24T02:35:46Z
- **Completed:** 2026-04-24T03:24:46Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- 在 [36_01_add_comment_to_performance_records.py](/Users/mac/PycharmProjects/Wage_adjust/alembic/versions/36_01_add_comment_to_performance_records.py:1) 建立 `36_01_add_comment_perf` migration，`down_revision='p34_02_tier_snapshot'`，upgrade/downgrade 可逆且无数据写入脚本。
- 在 [performance_record.py](/Users/mac/PycharmProjects/Wage_adjust/backend/app/models/performance_record.py:31)、[performance.py](/Users/mac/PycharmProjects/Wage_adjust/backend/app/schemas/performance.py:14)、[performance_service.py](/Users/mac/PycharmProjects/Wage_adjust/backend/app/services/performance_service.py:125) 补齐 `comment` 字段的 ORM / Pydantic / Service 契约。
- 在 [import_service.py](/Users/mac/PycharmProjects/Wage_adjust/backend/app/services/import_service.py:86) 与 [test_import_service.py](/Users/mac/PycharmProjects/Wage_adjust/backend/tests/test_services/test_import_service.py:325) 落地 Excel `评语/comment/备注` 三别名和 merge 模式锁定策略。

## Task Commits

1. **Task 1: Alembic 迁移 + PerformanceRecord.comment 字段**
   `4a4e6a3` RED, `c0e209e` GREEN, `8f9653b` 验收对齐
2. **Task 2: Pydantic schema 扩展 + PerformanceService.create_record 支持 comment**
   `e269ca8` RED, `944ea30` GREEN
3. **Task 3: ImportService performance_grades 支持可选 comment 列 + COLUMN_ALIASES 扩展**
   `70448b5` RED, `e61dfa8` GREEN

## Files Created/Modified

- `alembic/versions/36_01_add_comment_to_performance_records.py` - 新增 `comment` 列 migration，行 13-36 定义 revision、up/down。
- `backend/app/models/performance_record.py` - 行 31-35 新增 `Text` 类型 `comment`。
- `backend/app/schemas/performance.py` - 行 27、48、88 新增 `PerformanceRecordRead.comment`、`PerformanceRecordCreateRequest.comment`、`PerformanceHistoryResponse`。
- `backend/app/services/performance_service.py` - 行 125-173 让 `create_record()` 在新建与 UPSERT 两条路径都处理 `comment`。
- `backend/app/services/import_service.py` - 行 86-92 增 3 个别名；行 888-923 实现导入 comment 规整与 guarded update。
- `backend/tests/test_models/test_schema_models.py` - 行 78-146 覆盖默认值、长文本持久化、migration upgrade/downgrade。
- `backend/tests/test_services/test_performance_service.py` - 行 160-220 左右补 `comment` create/upsert/max_length 契约测试。
- `backend/tests/test_services/test_import_service.py` - 行 325-534 补 6 条 performance_grades comment 导入测试。

## Decisions Made

- migration 仅做 DDL，不做任何 UPDATE；`comment` 的历史空值语义保留为 NULL。
- manual 路径依赖 `Field(max_length=2000)` 卡住超长 comment；Excel 路径只做空值规整，不额外截断。
- merge 模式采用 `if comment_value is not None: existing.comment = comment_value`，避免无 comment 列的重导入把已有评语清空。

## Verification

- `./.venv/bin/pytest backend/tests/test_models/ -x -v`：13 passed
- `./.venv/bin/pytest backend/tests/test_services/test_performance_service.py -x -v`：33 passed
- `./.venv/bin/pytest backend/tests/test_services/test_import_service.py -x -v -k "performance_grades"`：6 passed
- `./.venv/bin/pytest backend/tests/test_services/test_import_service.py -q`：13 passed
- `./.venv/bin/pytest backend/tests -q`：35 failed, 796 passed, 1 skipped, 35 xfailed

## Deviations from Plan

### Execution Boundary

**1. API 透传未在本计划内完成**
- **Found during:** Task 2
- **Issue:** 计划要求修改 `backend/app/api/v1/performance.py` 透传 `payload.comment`，但本次用户明确限定可写文件集，不包含该文件。
- **Action:** 仅交付本次拥有所有权的 model / schema / service / import / tests / migration；未越权修改 API 文件。
- **Impact:** `PerformanceRecordCreateRequest.comment` 已就绪，但 `POST /api/v1/performance/records` 端到端透传仍需持有该文件的后续执行者补上。

---

**Total deviations:** 0 auto-fixed，1 个执行边界偏差
**Impact on plan:** 数据层与导入层目标完成；计划级 API 闭环未完全达成。

## Issues Encountered

- `backend/tests -q` 全量回归存在 35 个失败，主要分布在 approval/auth/import/task/Redis 相关套件，不在本次 8 个受控文件范围内，未在本计划中处理。
- `alembic` 验收 grep 要求 `down_revision = '...'` 纯赋值格式；实现后追加一次 metadata 对齐提交 `8f9653b`。

## User Setup Required

None - 本计划未引入新的外部服务配置。

## Known Stubs

None.

## Next Phase Readiness

- Plan 02 可以直接复用 `PerformanceHistoryResponse` 与 `PerformanceRecordRead.comment`。
- `sync_performance_records` 仍按本期约定写 `comment=None`，未扩展飞书 mapping。
- `backend/app/api/v1/performance.py` 的 `comment=payload.comment` 透传仍待后续持有者补齐，否则手动创建接口不会写入 comment。

## Self-Check: PASSED

- `FOUND: .planning/phases/36-historical-performance-display/36-01-SUMMARY.md`
- `FOUND: 4a4e6a3`
- `FOUND: c0e209e`
- `FOUND: e269ca8`
- `FOUND: 944ea30`
- `FOUND: 70448b5`
- `FOUND: e61dfa8`
- `FOUND: 8f9653b`

---
*Phase: 36-historical-performance-display*
*Completed: 2026-04-24*
