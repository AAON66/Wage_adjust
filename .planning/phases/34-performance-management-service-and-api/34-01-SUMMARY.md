---
phase: 34-performance-management-service-and-api
plan: 01
subsystem: backend/models + backend/migrations
tags: [models, alembic, performance, schema, phase-34, wave-1]
requirements-completed: [PERF-08]
dependency-graph:
  requires: []
  provides:
    - PerformanceRecord.department_snapshot 列（D-07）
    - PerformanceTierSnapshot ORM 模型 + 表（D-01）
    - alembic 链 33_01_employee_salary → p34_01_dept_snapshot → p34_02_tier_snapshot
  affects:
    - Phase 34 Plan 03 (Service 层) 可直接 import 与读写
    - Phase 34 Plan 04 (UI 层) 通过 Service 间接消费
tech-stack:
  added:
    - SQLAlchemy 2.0 `JSON` 列类型（首次在本项目用于持久化档次映射 dict）
  patterns:
    - 复用 UUIDPrimaryKeyMixin + CreatedAtMixin + UpdatedAtMixin
    - 用 `batch_alter_table` 兼容 SQLite 的 ADD COLUMN（与 Phase 30/31 一致）
    - alembic migration 命名前缀 `p34_*`（标识 Phase 34 顺序）
key-files:
  created:
    - backend/app/models/performance_tier_snapshot.py
    - alembic/versions/p34_01_add_department_snapshot_to_performance_records.py
    - alembic/versions/p34_02_add_performance_tier_snapshot_table.py
    - backend/tests/test_models/test_performance_tier_snapshot.py
  modified:
    - backend/app/models/performance_record.py（+5 行：department_snapshot 列）
    - backend/app/models/__init__.py（+2 行：显式 re-export PerformanceTierSnapshot）
key-decisions:
  - computed_at 复用 UpdatedAtMixin.updated_at 而非独立列（与 D-01 等价化简：created_at = 首次建行时间，updated_at = 最近一次重算时间）
  - 用 SQL UPDATE 倒推 1 秒强制时间差（N-1 修复，禁用 time.sleep；不引入 freezegun 新依赖）
  - alembic migration 用 batch_alter_table 包裹 ADD COLUMN（虽 SQLite ADD COLUMN 原生支持，但与项目 Phase 30/31 现有 migration 风格保持一致）
  - PerformanceRecord 现有 5 列与 UniqueConstraint 完全保留，只 append 1 列
  - PerformanceTierSnapshot 不加外键到 employees（snapshot 是历史记录，员工删了仍要看历史）
metrics:
  start-time: 2026-04-22T07:45:25Z
  end-time: 2026-04-22T07:53:29Z
  duration-seconds: 484
  duration-human: ~8 分钟
  tasks-completed: 3 / 3
  files-created: 4
  files-modified: 2
  tests-added: 4
  tests-pass-rate: 4/4 (100%)
  regressions: 0 (engines 64/64 pass, schema_models 1/1 pass)
---

# Phase 34 Plan 01: 模型与 Migration 落地 Summary

数据持久化骨架已落地：PerformanceRecord 加 `department_snapshot` 列承接 PERF-08；新建 `PerformanceTierSnapshot` 模型作为档次重算结果的「单年一行」持久化锚点。两条 alembic migration 双向干净，4 个模型层 pytest 用例全绿，为 Wave 2 Service 层零阻塞铺路。

## What Got Built

### Task 1: 模型层（commit `ae20d62`）

**`backend/app/models/performance_record.py`**：在现有 5 列后追加 `department_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True, comment=...)`。`__tablename__`、`__table_args__`、其他列、`UniqueConstraint('employee_id', 'year', ...)` 均零修改。

**`backend/app/models/performance_tier_snapshot.py`**（新建）：

```python
class PerformanceTierSnapshot(
    UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base,
):
    __tablename__ = 'performance_tier_snapshots'
    __table_args__ = (
        UniqueConstraint('year', name='uq_performance_tier_snapshot_year'),
    )

    year: Mapped[int]                            # UNIQUE + index
    tiers_json: Mapped[dict]                     # {employee_id: 1|2|3|null}
    sample_size: Mapped[int]                     # default=0
    insufficient_sample: Mapped[bool]            # default=False
    distribution_warning: Mapped[bool]           # default=False
    actual_distribution_json: Mapped[dict]       # default=dict
    skipped_invalid_grades: Mapped[int]          # default=0
```

加上 mixin 提供的 `id` / `created_at` / `updated_at` 共 10 列，符合 D-01 要求。

**`backend/app/models/__init__.py`**：在保留 `load_model_modules()` 的同时显式 `from backend.app.models.performance_tier_snapshot import PerformanceTierSnapshot`，让 `from backend.app.models import PerformanceTierSnapshot` 直接成功（W-3 集成视角验证要求）。

### Task 2: Migration 层（commit `fb53fb4`）

**`p34_01_add_department_snapshot_to_performance_records.py`**：`down_revision='33_01_employee_salary'`。`upgrade` 用 `batch_alter_table('performance_records')` 添加列；`downgrade` drop 列。**不**跑数据回填（D-07 严格执行：按当前部门回填会引入虚假快照，违反「快照」语义）。

**`p34_02_add_performance_tier_snapshot_table.py`**：`down_revision='p34_01_dept_snapshot'`。`upgrade` `create_table` 全量 10 列 + `UNIQUE(year)` + 创建 `ix_performance_tier_snapshots_year` 索引；`downgrade` drop 索引 + drop 表。Boolean / Integer 列加 `server_default` 让 migration-only 路径（绕开 ORM）也能工作。

**双向运行已验证**：
```
upgrade head → downgrade -2 → upgrade head：3 次全部 0 退出，alembic heads 输出唯一 head = p34_02_tier_snapshot。
```

### Task 3: 测试层（commit `02a8529`）

**`backend/tests/test_models/test_performance_tier_snapshot.py`**（4 用例）：

1. `test_round_trip_persists_all_fields` — 写入完整 7 业务字段（含 JSON），expire_all + 重新查询，所有字段值（含 dict 反序列化）逐一断言一致
2. `test_unique_year_constraint` — 同 year=2025 插两行，second commit 抛 `IntegrityError`，验证 `UNIQUE(year)` 约束生效
3. `test_default_values_applied` — 仅设必填三字段（year + tiers_json + actual_distribution_json），其余字段自动取默认值（sample_size=0 / boolean=False / skipped=0）
4. `test_updated_at_changes_on_update` — **N-1 修复**：用 `text('UPDATE ... SET updated_at = :t')` 把 updated_at 倒推 1 秒，再做正常 ORM UPDATE，断言新 `updated_at > past`。**全程不调用 `time.sleep`**，CI / 高负载机器零波动。

`grep -n "time.sleep" backend/tests/test_models/test_performance_tier_snapshot.py` 结果：仅 docstring/comment 中说明性提及，无实际调用。

## Verification Results

| 检查项 | 命令 | 结果 |
|--------|------|------|
| Model import + 字段存在 + UNIQUE 约束 | `python -c "from backend.app.models...; assert ..."` | OK |
| Alembic upgrade head | `.venv/bin/alembic upgrade head` | exit 0，3 个 migration 顺序执行 |
| Alembic downgrade -2 | `.venv/bin/alembic downgrade -2` | exit 0，2 个 migration 顺序回滚 |
| Alembic upgrade head（再次） | `.venv/bin/alembic upgrade head` | exit 0，干净往返 |
| 表/列 schema 检查 | inspector.get_columns(...) | 全字段齐全 + UNIQUE(year) 存在 |
| 模型测试 | `pytest backend/tests/test_models/test_performance_tier_snapshot.py -v` | 4 passed |
| 全 test_models 套件 | `pytest backend/tests/test_models/` | 9 passed |
| 引擎层非回归 | `pytest backend/tests/test_engines/` | 64 passed |
| N-1 验证：无 time.sleep | `grep -n "time.sleep" ...` | 仅出现在 docstring/comment |

## Deviations from Plan

无。Plan 完全按写定的 3 task / 6 文件 / 4 测试用例落地，0 deviation。

技术细节微调（不属于 deviation，属于 plan 内 explicit guidance 的执行决策）：
- 两条 alembic migration 都用 `batch_alter_table` 包裹（与 Phase 30/31 项目惯例一致）
- 代码 `Sequence`/`Union` import 风格与已有 alembic migration（如 `33_01_employee_salary_components.py`）保持一致

## Phase 34-03 Service 层接口契约

`PerformanceTierSnapshot` ORM 已就绪，Plan 03 可直接：

```python
from backend.app.models import PerformanceTierSnapshot
```

**业务字段速查表（供 Plan 03 写 query/mapper 直接 reference）：**

| 字段 | 类型 | 约束 | 用途 |
|------|------|------|------|
| `id` | `str` (UUID) | PK | 主键，UUIDPrimaryKeyMixin 提供 |
| `created_at` | `datetime` (UTC tz) | NOT NULL | 首次建行时间 |
| `updated_at` | `datetime` (UTC tz) | NOT NULL, onupdate=utc_now | **充当 D-01 的 `computed_at`**：每次重算 UPSERT 后会自动刷新 |
| `year` | `int` | NOT NULL, **UNIQUE**, indexed | 唯一年份键（D-05 锁住此行做 SELECT FOR UPDATE NOWAIT） |
| `tiers_json` | `dict` (JSON) | NOT NULL | `{employee_id: 1\|2\|3\|null}` 完整映射，可直接喂给 Phase 33 `TierAssignmentResult.tiers` 序列化结果 |
| `sample_size` | `int` | NOT NULL, default 0 | 样本大小（已剔除 invalid grades） |
| `insufficient_sample` | `bool` | NOT NULL, default False | < `Settings.performance_tier_min_sample_size` 触发 |
| `distribution_warning` | `bool` | NOT NULL, default False | 偏离 ±5% 触发 |
| `actual_distribution_json` | `dict` (JSON) | NOT NULL | `{1: 0.22, 2: 0.68, 3: 0.10}` |
| `skipped_invalid_grades` | `int` | NOT NULL, default 0 | 跳过的异常 grade 数 |

**Plan 03 Service 层 UPSERT 模式建议**（D-05 一致）：

```python
# 先尝试拿现有行
snap = (
    db.query(PerformanceTierSnapshot)
    .filter_by(year=year)
    .with_for_update(nowait=True)  # PostgreSQL 触发 SELECT FOR UPDATE NOWAIT
    .one_or_none()
)
if snap is None:
    snap = PerformanceTierSnapshot(year=year, ...)
    db.add(snap)
else:
    snap.tiers_json = result.tiers          # UpdatedAtMixin 自动刷新 updated_at
    snap.sample_size = result.sample_size
    ...
db.commit()
```

**Phase 33 引擎输出映射**（W-3 集成视角验证）：

| Phase 33 `TierAssignmentResult` 字段 | → Plan 34 Snapshot 列 |
|--------------------------------------|------------------------|
| `tiers: dict[str, int \| None]` | `tiers_json` |
| `insufficient_sample: bool` | `insufficient_sample` |
| `distribution_warning: bool` | `distribution_warning` |
| `actual_distribution: dict[int, float]` | `actual_distribution_json` |
| `sample_size: int` | `sample_size` |
| `skipped_invalid_grades: int` | `skipped_invalid_grades` |

**`PerformanceRecord.department_snapshot` Service 层赋值（D-08）**：

```python
# PerformanceService.create_record() / import_records()
record = PerformanceRecord(
    employee_id=emp.id,
    employee_no=emp.employee_no,
    year=year,
    grade=grade,
    source=source,
    department_snapshot=emp.department,  # 当时值，None 时也写 None 不抛异常
)
```

## Known Stubs

无。本 plan 范围严格限定 model + migration + 模型层单测，不引入任何 UI / Service stub；所有交付物都是终态实现。

## Self-Check: PASSED

文件存在性检查：

```
[x] backend/app/models/performance_tier_snapshot.py
[x] backend/app/models/performance_record.py（已修改）
[x] backend/app/models/__init__.py（已修改）
[x] alembic/versions/p34_01_add_department_snapshot_to_performance_records.py
[x] alembic/versions/p34_02_add_performance_tier_snapshot_table.py
[x] backend/tests/test_models/test_performance_tier_snapshot.py
```

Commit 存在性检查：

```
[x] ae20d62 — Task 1 (model 层)
[x] fb53fb4 — Task 2 (alembic migration)
[x] 02a8529 — Task 3 (4 个 pytest 用例)
```

成功标准核对：

- [x] All 3 tasks executed
- [x] Each task committed individually (3 commits)
- [x] SUMMARY.md created in plan directory
- [x] alembic upgrade head 成功 + downgrade -2 + upgrade head 双向干净
- [x] 4 新测试通过 (test_round_trip / test_unique_year / test_default_values / test_updated_at)
- [x] 无 time.sleep 残留（仅 docstring/comment 提及）
- [x] 引擎层 64 测试 0 回归
