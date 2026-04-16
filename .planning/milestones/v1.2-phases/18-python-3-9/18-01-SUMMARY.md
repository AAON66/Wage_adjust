---
phase: 18-python-3-9
plan: 01
subsystem: backend-models
tags: [python39-compat, type-annotations, sqlalchemy, sqlite, dependencies]
dependency_graph:
  requires: []
  provides: [python39-model-compat, sqlite-fk-enforcement, pinned-numpy-pillow]
  affects: [all-model-imports, database-engine-init, requirements-txt]
tech_stack:
  added: []
  patterns: [typing-Optional-for-Mapped-nullable, event-listener-for-sqlite-pragma]
key_files:
  created: []
  modified:
    - backend/app/models/department.py
    - backend/app/models/evaluation.py
    - backend/app/models/audit_log.py
    - backend/app/models/certification.py
    - backend/app/models/eligibility_override.py
    - backend/app/models/attendance_record.py
    - backend/app/models/dimension_score.py
    - backend/app/models/webhook_endpoint.py
    - backend/app/models/submission.py
    - backend/app/models/webhook_delivery_log.py
    - backend/app/models/salary_recommendation.py
    - backend/app/models/salary_adjustment_record.py
    - backend/app/models/employee_handbook.py
    - backend/app/models/employee.py
    - backend/app/models/feishu_sync_log.py
    - backend/app/models/approval.py
    - backend/app/models/user.py
    - backend/app/models/sharing_request.py
    - backend/app/models/api_key.py
    - backend/app/core/database.py
    - requirements.txt
decisions:
  - "Mapped[X | None] -> Mapped[Optional[X]] only in runtime-evaluated positions (Mapped[] internals); function signatures left untouched since __future__ annotations protects them"
  - "Bare dict/list without subscripts (e.g. Mapped[dict]) left as-is since unsubscripted builtins are valid in 3.9"
  - "SQLite FK pragma applied via event.listen on connect, scoped to sqlite:// URLs only"
metrics:
  duration: 168s
  completed: 2026-04-08
---

# Phase 18 Plan 01: Model 类型注解降级与 SQLite FK 启用 Summary

19 个 SQLAlchemy model 文件中 PEP 604/585 运行时类型注解全部降级为 Python 3.9 兼容语法 (Optional[X], List[X])，SQLite 连接自动启用 PRAGMA foreign_keys=ON，numpy 和 Pillow 依赖版本锁定到 3.9 兼容版本。

## Task Results

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Model 文件类型注解降级 + 依赖版本锁定 | ed99b28 | Done |
| 2 | SQLite 外键约束启用 | af9f5bd | Done |

## Changes Made

### Task 1: Model 文件类型注解降级 + 依赖版本锁定

**PEP 604 降级 (19 files):**
- 所有 `Mapped[str | None]` -> `Mapped[Optional[str]]`
- 所有 `Mapped[int | None]` -> `Mapped[Optional[int]]`
- 所有 `Mapped[float | None]` -> `Mapped[Optional[float]]`
- 所有 `Mapped[datetime | None]` -> `Mapped[Optional[datetime]]`
- 所有 `Mapped[date | None]` -> `Mapped[Optional[date]]`
- 所有 `Mapped[Decimal | None]` -> `Mapped[Optional[Decimal]]`

**PEP 585 降级 (employee_handbook.py):**
- `Mapped[list[str]]` -> `Mapped[List[str]]` (2 处: key_points_json, tags_json)

**导入添加:**
- 每个修改文件增加 `from typing import Optional` (部分文件额外增加 `List`)
- 导入位置在 `from __future__ import annotations` 之后

**依赖锁定:**
- numpy: 2.2.1 -> 2.0.2
- pillow: 11.0.0 -> 10.4.0

### Task 2: SQLite 外键约束启用

- 在 `database.py` 顶部导入中添加 `event`
- 新增 `_set_sqlite_pragma()` 模块级函数，执行 `PRAGMA foreign_keys=ON`
- 在 `create_db_engine()` 中对 SQLite URL 注册 `event.listen(engine, 'connect', _set_sqlite_pragma)`
- PostgreSQL 连接不受影响

## Verification Results

- `grep -r 'Mapped[.*|.*None]' backend/app/models/` 返回 0 行
- `grep 'Optional[' backend/app/models/employee.py` 返回 5 行
- `grep 'numpy==2.0.2' requirements.txt` 匹配
- `grep 'pillow==10.4.0' requirements.txt` 匹配
- `grep 'Mapped[dict[' backend/app/models/employee_handbook.py` 返回 0
- `grep 'List[' backend/app/models/employee_handbook.py` 返回 2 行
- Python PRAGMA foreign_keys 查询返回 `FK enabled: 1`

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **仅降级运行时求值位置的类型注解** -- 函数参数和返回值注解 (`X | None`) 由 `from __future__ import annotations` 保护，不在运行时求值，无需降级
2. **裸 dict/list 不降级** -- `Mapped[dict]` 和 `Mapped[list]` 中的 `dict`/`list` 未带下标，Python 3.9 中作为类引用是合法的
3. **SQLite FK pragma 仅对 sqlite URL 生效** -- 通过检查 `database_url.startswith('sqlite')` 条件注册，PostgreSQL 不受影响

## Self-Check: PASSED

- All 21 modified files exist on disk
- Commit ed99b28 found in git log
- Commit af9f5bd found in git log
- 18-01-SUMMARY.md exists at expected path
