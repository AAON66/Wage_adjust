---
phase: 31-feishu-sync-observability
plan: 01
subsystem: feishu-sync-observability
tags: [data-layer, alembic-migration, orm, pydantic-literal, feishu-sync]
requires:
  - FeishuSyncLog ORM model (backend/app/models/feishu_sync_log.py)
  - SyncLogRead Pydantic schema (backend/app/schemas/feishu.py)
  - Alembic 30_01_leading_zero_fallback (down_revision chain)
provides:
  - FeishuSyncLog.sync_type column (String(32), NOT NULL) — discriminator for 5 sync types
  - FeishuSyncLog.mapping_failed_count column (Integer, NOT NULL, server_default='0') — field-mapping conversion failures counter
  - SyncTypeLiteral constant (backend/app/schemas/feishu.py) — reusable Literal for service/API/frontend
  - SyncStatusLiteral constant (backend/app/schemas/feishu.py) — adds 'partial' to status enum
  - SyncLogRead.sync_type + SyncLogRead.mapping_failed_count response fields
  - Alembic revision 31_01_sync_log_observability (data layer base for Plans 02/03/04)
affects:
  - backend/app/services/feishu_service.py (now passes sync_type='attendance' at both FeishuSyncLog call-sites)
  - backend/app/api/v1/feishu.py (_sync_log_to_read maps new fields into response)
  - backend/tests/test_api/test_feishu_config_validation.py (fixture updated to supply sync_type)
tech-stack:
  added: []
  patterns:
    - Two-phase Alembic migration (add nullable=True → UPDATE backfill → alter NOT NULL) for SQLite batch_alter_table safety
    - Module-level Literal constants exported from schemas for cross-layer reuse
    - File-based tempfile SQLite for migration tests (not in-memory) to exercise real batch_alter_table table-recreate path
key-files:
  created:
    - alembic/versions/31_01_feishu_sync_log_observability.py
    - backend/tests/test_models/__init__.py
    - backend/tests/test_models/test_feishu_sync_log_migration.py
  modified:
    - backend/app/models/feishu_sync_log.py
    - backend/app/schemas/feishu.py
    - backend/app/services/feishu_service.py
    - backend/app/api/v1/feishu.py
    - backend/tests/test_services/test_feishu_sync_log_model.py
    - backend/tests/test_api/test_feishu_config_validation.py
decisions:
  - D-01 / 白名单 Literal: sync_type 在 ORM 层只强制 NOT NULL (String(32))，白名单校验下沉到 Pydantic SyncTypeLiteral — 避开 SQLite Check constraint 跨库不一致问题
  - D-02 / mapping_failed_count server_default='0': 与 leading_zero_fallback_count 采用相同模式，旧行自动落 0
  - D-03 / 显式 UPDATE backfill 而非 server_default='attendance': 可审计，符合 Phase 30 既定迁移模式
  - D-09 / status Literal 收紧到 4 值（running/success/partial/failed）: partial 是 Phase 31 新增语义，ORM 层保留 String(32) 以支持未来扩展，入口校验在 Pydantic
  - [执行阶段新决策] 既然 ORM 已带 sync_type NOT NULL，所有 FeishuSyncLog(...) 构造点必须传 sync_type；Phase 31 Plan 01 阶段唯一现有使用者（FeishuService.sync_attendance + retry path）统一传 'attendance' (Rule 3 auto-fix)
metrics:
  duration: 7m 30s
  completed: 2026-04-21T04:02:07Z
  tasks_executed: 2
  commits: 4
  tests_added: 12 (8 model/schema + 4 migration)
  tests_total_green: 15 (3 pre-existing + 12 new)
---

# Phase 31 Plan 01: FeishuSyncLog 可观测性数据层 Summary

**One-liner:** FeishuSyncLog 新增 `sync_type` (5 类同步区分) + `mapping_failed_count` (字段映射失败计数) 两列，SyncLogRead schema 收紧 status 为 Literal['running','success','partial','failed'] 并导出 `SyncTypeLiteral`/`SyncStatusLiteral` 模块常量供 Plan 02/03 复用；Alembic 两阶段迁移 `31_01_sync_log_observability` 向下兼容 SQLite 并 auditable-backfill 存量行为 `attendance`。

## Tasks Executed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | 扩展 FeishuSyncLog 模型 + SyncLogRead schema | `4978ff4` (RED), `f41d33a` (GREEN) | feishu_sync_log.py, feishu.py, feishu_service.py (call-sites), feishu.py API (converter), 2 test files |
| 2 | Alembic 两阶段迁移 + 迁移测试 | `0731034` (RED), `6512733` (GREEN) | 31_01_feishu_sync_log_observability.py, test_feishu_sync_log_migration.py, __init__.py |

## What Changed

### FeishuSyncLog ORM (backend/app/models/feishu_sync_log.py)

**Added fields (in stated column order — matches plan D-01 positioning):**

- `sync_type: Mapped[str] = mapped_column(String(32), nullable=False)` — 作为**首列**区分 5 类同步：`attendance` / `performance` / `salary_adjustments` / `hire_info` / `non_statutory_leave`
- `mapping_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')` — 放在 `failed_count` 之后，与 `leading_zero_fallback_count` 并列，专记录字段映射阶段（`_map_fields` / 格式转换）失败行数

**Docstring:** 更新为 Phase 31 语义说明（五类同步 + 字段映射失败计数 + skipped_count 语义收紧）。

### SyncLogRead Pydantic schema (backend/app/schemas/feishu.py)

**Added module-level Literal constants:**

```python
SyncTypeLiteral = Literal[
    'attendance',
    'performance',
    'salary_adjustments',
    'hire_info',
    'non_statutory_leave',
]
SyncStatusLiteral = Literal['running', 'success', 'partial', 'failed']
```

**为什么导出到模块级：** Plan 02 的 `SyncMetricsAccumulator` / `SyncLogService` helper 需要在入参处直接 import SyncTypeLiteral 做 type hint；Plan 03 的 CSV 导出路由需要以相同 Literal 列表做列头枚举；前端 `frontend/src/types/api.ts` 镜像时也以这些值为单一真源。避免散落的字符串拼写错误。

**SyncLogRead 字段变化：**

- **新增** `sync_type: SyncTypeLiteral`
- **新增** `mapping_failed_count: int = 0`（默认值 0 兼容 ORM 旧行，通过 server_default 填充）
- **收紧** `status: SyncStatusLiteral` (原为 `status: str`) — 非白名单值在 model_validate 入口立即 ValidationError

### Alembic migration (alembic/versions/31_01_feishu_sync_log_observability.py)

**Revision:** `31_01_sync_log_observability`
**Down revision:** `30_01_leading_zero_fallback`

**两阶段（显式 3 步分段）模式** — 按 31-RESEARCH.md Pitfall B / PITFALLS.md Pitfall 16：

1. **Stage 1 (batch_alter_table):** `add_column sync_type (nullable=True)` + `add_column mapping_failed_count (NOT NULL, server_default='0')`
2. **Stage 2 (op.execute):** `UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL` — D-03 显式可审计 backfill
3. **Stage 3 (batch_alter_table):** `alter_column sync_type nullable=False` — 最终态 NOT NULL 约束

**Downgrade:** batch_alter_table drop 两列（drop 顺序：`mapping_failed_count` → `sync_type`，保持 downgrade 对称）。

### Collateral fixes (Rule 3 — blocking issues caused by new NOT NULL)

**backend/app/services/feishu_service.py:** 两处 `FeishuSyncLog(...)` 构造点追加 `sync_type='attendance'`：
- `sync_attendance()` running-log 初始化
- `sync_with_retry()` all-retries-failed final-log 初始化

**backend/app/api/v1/feishu.py `_sync_log_to_read`:** 追加 `sync_type=log.sync_type` 与 `mapping_failed_count=log.mapping_failed_count` 字段映射，否则 Pydantic SyncLogRead 入口校验 missing-field 抛 ValidationError。

**backend/tests/test_api/test_feishu_config_validation.py:** 既有 `test_sync_logs_response_includes_leading_zero_fallback_count` 的 fixture 追加 `sync_type='attendance'`。

## Tests

### Model + schema tests (backend/tests/test_services/test_feishu_sync_log_model.py)

**保留 3 个原有 leading-zero 测试**（只调整 fixture 与 raw SQL INSERT 以包含 sync_type）**+ 新增 8 个 Phase 31 测试**：

- `test_create_log_with_sync_type_performance` — ORM 写入 + 按 sync_type 查询
- `test_mapping_failed_count_defaults_to_zero` — ORM default=0 生效
- `test_sync_type_is_required` — NOT NULL 违反抛 IntegrityError
- `test_mapping_failed_count_accepts_positive` — 显式设值
- `test_all_five_sync_type_values_are_persistable` — 5 种值全部可独立保存
- `test_sync_log_read_accepts_partial_status` — Literal 支持 'partial'
- `test_sync_log_read_rejects_invalid_status` — Literal 拒绝 'bogus'
- `test_sync_log_read_rejects_invalid_sync_type` — Literal 拒绝 'unknown_type'

### Migration tests (backend/tests/test_models/test_feishu_sync_log_migration.py)

使用 tempfile-backed SQLite URL + 真实 `alembic.command.upgrade/downgrade`（不是 in-memory，因为 batch_alter_table table-recreate 在文件模式下更贴近生产）。

- `test_upgrade_to_31_01_creates_sync_type_and_mapping_failed_count_columns`
- `test_upgrade_backfills_existing_rows_to_attendance` — 先 upgrade 到 30_01，手动 INSERT 一行无 sync_type 的行，再 upgrade 到 31_01 → 该行 sync_type='attendance'、mapping_failed_count=0
- `test_upgrade_enforces_sync_type_not_null` — Stage 3 alter_column 后 INSERT 不含 sync_type 抛 IntegrityError
- `test_downgrade_from_31_01_drops_both_columns`

**结果：** `pytest backend/tests/test_services/test_feishu_sync_log_model.py backend/tests/test_models/test_feishu_sync_log_migration.py` → **15 passed**（3 pre-existing + 12 new）。

### Smoke test

`alembic heads` → `31_01_sync_log_observability (head)` ✓
`alembic upgrade head` on clean tempfile SQLite（/tmp/smoke_31_01.db）跑通全链，feishu_sync_logs 末态三列验证：
- `sync_type VARCHAR(32) NOT NULL default=None`（Stage 3 后 server_default 被移除，正确）
- `mapping_failed_count INTEGER NOT NULL default='0'`
- `leading_zero_fallback_count INTEGER NOT NULL default='0'`（Phase 30 遗留）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FeishuService 两处 FeishuSyncLog 构造缺少 sync_type**
- **Found during:** Task 1 运行 `test_feishu_service.py` 发现 `sync_attendance()` + retry path 抛 IntegrityError
- **Fix:** 两处构造点均追加 `sync_type='attendance'`（Phase 30 STATE 确认当前唯一使用方就是 sync_attendance）
- **Files modified:** backend/app/services/feishu_service.py
- **Commit:** `f41d33a`

**2. [Rule 3 - Blocking] API `_sync_log_to_read` 漏字段导致 SyncLogRead 入口校验 missing-field**
- **Found during:** Task 1 运行 test_feishu_config_validation.py 发现 ValidationError: sync_type/mapping_failed_count missing
- **Fix:** converter 追加 `sync_type=log.sync_type`、`mapping_failed_count=log.mapping_failed_count` 映射
- **Files modified:** backend/app/api/v1/feishu.py
- **Commit:** `f41d33a`

**3. [Rule 3 - Blocking] 既有 test_feishu_config_validation.py::test_sync_logs_response_includes_leading_zero_fallback_count fixture 未传 sync_type**
- **Found during:** Task 1 该测试在新 model NOT NULL 约束下 IntegrityError
- **Fix:** fixture 追加 `sync_type='attendance'`
- **Files modified:** backend/tests/test_api/test_feishu_config_validation.py
- **Commit:** `f41d33a`

### No architectural changes (no Rule 4)

没有数据模型结构性改动、没有换库、没有破坏性 API 变更 — 符合"数据层扩展基座"的 Plan 01 边界。

## A2 Assumption Review (关键前置)

**假设 A2：** Phase 31 之前 `feishu_sync_logs` 表内所有存量行都来自 `sync_attendance`（唯一写入方）。

**运行迁移前检查方式：**

```sql
-- Dev 本地（本次 executor 运行时）
SELECT COUNT(*) FROM feishu_sync_logs;  -- 返回 0（本 dev DB 无历史记录，A2 平凡成立）
```

**Prod 上线前建议：**

```sql
-- 生产 DB 验证 A2（迁移前）
SELECT COUNT(*) FROM feishu_sync_logs;
-- 若返回 > 0，抽查：SELECT mode, status, COUNT(*) FROM feishu_sync_logs GROUP BY mode, status;
-- 目前无法按 sync_type 区分（列尚不存在），回看 triggered_by + 业务时间窗确认均为考勤同步触发
```

**若 A2 不成立（迁移误分类风险）：** 该行会被 backfill 为 `'attendance'`，但不丢失；后续可由 Plan 02/03 人工 UPDATE 修正。记录该风险到 SUMMARY 已满足 STRIDE T-31-04（Repudiation, disposition=accept）。

## Consumer Readiness (for Plans 02/03)

- Plan 02 `SyncMetricsAccumulator` 可直接 `from backend.app.schemas.feishu import SyncTypeLiteral, SyncStatusLiteral` 做 type hint
- Plan 02 `SyncLogService.create_running_log(sync_type: SyncTypeLiteral, mode: str, ...)` 的入参契约已就绪
- Plan 03 CSV 导出路由可以 `list(typing.get_args(SyncTypeLiteral))` 获取列头枚举
- 前端 `frontend/src/types/api.ts`（Plan 03 / 04 涉及）可镜像相同 Literal 列表

## Known Stubs / Deferred Items

- **生产 DB A2 核验（不在本 plan 范围）：** 上线前需跑 `SELECT COUNT(*) FROM feishu_sync_logs` + 抽样确认历史行确为考勤触发
- **Pre-existing test failures（不属于本 plan）：** `git stash`+baseline 对比确认 29 条失败均与 Phase 31 Plan 01 改动无关（OAuth、rate_limit、password、approval、dashboard、integration、import 等独立域），日志到 `.planning/phases/31-feishu-sync-observability/deferred-items.md` 候选追踪（本 plan 不处理）
- **`alembic upgrade head` 对 dev wage_adjust.db 的真实运行（未执行）：** 本地 wage_adjust.db 与 alembic 链已不一致（`table departments already exists` 报错），属 pre-existing dev-DB 偏移问题；本 plan 通过 clean tempfile smoke + pytest 覆盖已充分，不尝试修复 dev DB
- **numpy 2.2.1 / Pillow 升级** — 按 PROJECT.md 既有跟踪项保留

## Threat Flags

无新增威胁面。沿用本 plan 的 STRIDE 寄存器（T-31-01 ~ T-31-05），所有 mitigate 项已在实现中落地（参数化 SQL / Pydantic Literal boundary 校验 / 无新 PII surface）。

## Self-Check: PASSED

- FOUND: backend/app/models/feishu_sync_log.py (sync_type Mapped[str] + mapping_failed_count Mapped[int])
- FOUND: backend/app/schemas/feishu.py (SyncTypeLiteral + SyncStatusLiteral + SyncLogRead narrowed status)
- FOUND: alembic/versions/31_01_feishu_sync_log_observability.py (revision 31_01_sync_log_observability)
- FOUND: backend/tests/test_models/__init__.py
- FOUND: backend/tests/test_models/test_feishu_sync_log_migration.py (4 tests)
- FOUND: backend/tests/test_services/test_feishu_sync_log_model.py (11 tests; 3 retained + 8 new)
- FOUND commit: 4978ff4 (RED 1)
- FOUND commit: f41d33a (GREEN 1 + Rule 3 fixes)
- FOUND commit: 0731034 (RED 2)
- FOUND commit: 6512733 (GREEN 2)
- VERIFIED: `alembic heads` → 31_01_sync_log_observability (head)
- VERIFIED: `python -c "from backend.app.schemas.feishu import SyncLogRead, SyncTypeLiteral, SyncStatusLiteral"` prints OK
- VERIFIED: `pytest backend/tests/test_services/test_feishu_sync_log_model.py backend/tests/test_models/test_feishu_sync_log_migration.py -x -v` → 15 passed
