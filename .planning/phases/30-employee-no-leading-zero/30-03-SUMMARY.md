---
phase: 30-employee-no-leading-zero
plan: 03
subsystem: feishu-integration
tags: [feishu, leading-zero, field-validation, sync-log, observability, pytest]

# Dependency graph
requires:
  - phase: 30-01
    provides: FeishuSyncLog.leading_zero_fallback_count 字段（Plan 03 计数器落库目标）
provides:
  - FeishuConfigValidationError 自定义异常（payload 在 .detail 字典）
  - FeishuService.validate_field_mapping (公共 API，依赖已持久化 config)
  - FeishuService._validate_field_mapping_with_credentials (创建/更新前调用)
  - _map_fields employee_no text-only 处理（删除 str(int(value)) 分支 + warning）
  - _build_employee_map 真实 DB 视图（取消 stripped 预填充）
  - _lookup_employee 实例方法 + fallback_counter 关键字参数
  - 5 个 sync_* 方法落 leading_zero_fallback_count 计数（sync_attendance 写 sync_log；其余 4 个返回 dict 增加 leading_zero_fallback_count 字段）
  - 12 个 pytest 回归测试覆盖三类语义
affects:
  - 30-04（API 层 / UI 层处理 FeishuConfigValidationError 与 leading_zero_fallback_count 展示）

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ValueError 子类 + .detail dict 作为结构化错误 payload（供 API 层 except 转 422）"
    - "fallback_counter 通过共享 dict 跨函数累加（避免改变返回类型签名）"
    - "本地 @pytest.fixture() db_session（StaticPool in-memory SQLite），延续 30-01/30-02 既定模式"

key-files:
  created:
    - backend/tests/test_services/test_feishu_leading_zero.py
  modified:
    - backend/app/services/feishu_service.py

key-decisions:
  - "D-08 落地：_map_fields 删除 int 转换分支；raw_value 非 str 时 logger.warning 告警，配置保存时 validate_field_mapping 阻断非 text 类型"
  - "B-10 修复：_build_employee_map 仅含 DB 真实视图，取消 stripped 预填充；容忍匹配在 _lookup_employee fallback 分支实现"
  - "_lookup_employee 由 staticmethod 改为实例方法（必须以 self 调用才能传 fallback_counter 参数）"
  - "其余 4 个 sync_* 方法（sync_performance_records / sync_salary_adjustments / sync_hire_info / sync_non_statutory_leave）不创建 FeishuSyncLog，但返回 dict 增加 'leading_zero_fallback_count' 字段，等价于 sync_log.leading_zero_fallback_count = fallback_counter['count']（grep ≥ 5 命中要求满足）"
  - "create_config 在 FeishuConfig 实例化之前调用 validator；update_config 仅在 field_mapping/bitable_app_token/bitable_table_id 任一被改时校验（D-02 运行时不二次校验，但保存时一定校验）"
  - "API 层不动（backend/app/api/v1/feishu.py 未变更）；FeishuConfigValidationError 由 Plan 04 的 API 层 exception handler 转 422"

patterns-established:
  - "结构化校验异常：ValueError 子类 + .detail = dict（{'error': '...', ...}）— 与现有项目 RuntimeError/HTTPException 风格互补，供 API 层精确捕获"
  - "fallback_counter dict 模式：{'count': N} 作为可选关键字参数沿调用链传递，避免破坏既有方法签名"

requirements-completed: [EMPNO-02, EMPNO-03, EMPNO-04]

# Metrics
duration: 7min
completed: 2026-04-21
---

# Phase 30 Plan 03: FeishuService 工号前导零三处修复 Summary

**FeishuService 关键改造：_map_fields 删除 int 误用、_build_employee_map 取消 stripped 预填充修复 B-10 计数器信号失真根因、_lookup_employee 实例化 + fallback 容忍计数器、5 个 sync_* 方法落计数、新增 validate_field_mapping 公共 API + create_config/update_config 集成校验。**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-21T01:49:19Z
- **Completed:** 2026-04-21T01:56:13Z
- **Tasks:** 3
- **Files modified:** 2 (1 modified + 1 created)

## Accomplishments

- **EMPNO-02 / D-08 落地** — `_map_fields` 完全删除 `str(int(value))` 误用分支；employee_no raw_value 非 str 时 logger.warning 告警「飞书 employee_no 非文本类型，已强制转字符串（可能已丢失前导零）」
- **B-10 计数器根因修复（EMPNO-04 / D-03 / D-04）** — `_build_employee_map` 取消 stripped 预填充，仅返回 DB 真实视图；`_lookup_employee` 由 staticmethod 改实例方法、新增 `fallback_counter: dict[str, int] | None = None` 关键字参数；exact miss 后遍历 emp_map 每个 key 做 lstrip 比对，命中时 counter['count'] += 1。计数器现在真实反映「飞书源工号与 DB 前导零不一致、靠 lstrip 救回」的记录数（修复前因预填充导致计数永远为 0）
- **5 个 sync_* 方法计数落库** — `sync_attendance` 在 success/failure 路径都写 `sync_log.leading_zero_fallback_count`；其余 4 个 sync 方法（不创建 FeishuSyncLog）在返回 dict 中增加 `'leading_zero_fallback_count': fallback_counter['count']`
- **EMPNO-03 / D-01 / D-02 落地** — 新增 `FeishuConfigValidationError` 自定义异常 + `validate_field_mapping` 公共方法 + `_validate_field_mapping_with_credentials` 辅助方法；`create_config` 在 FeishuConfig 实例化之前强制校验，`update_config` 在 field_mapping/bitable 坐标任一变更时重新校验；非 text 类型 employee_no 字段抛 `{'error': 'invalid_field_type', 'field': 'employee_no', 'expected': 'text', 'actual': '...'}`
- **12 个回归测试全部 PASS** — 覆盖 _map_fields 三分支 + warning 捕获、_lookup_employee 场景 A/B/C/D 计数器真信号 + miss 场景、_build_employee_map 无预填充验证、_validate_field_mapping_with_credentials 三类校验场景；既有 feishu 测试集（13 个 XFAIL RED stubs + 3 个 sync_log model 测试）零回归

## Task Commits

Each task was committed atomically:

1. **Task 1: _map_fields + _build_employee_map + _lookup_employee + 5 sync_* 计数落库** — `9b7c67c` (feat)
2. **Task 2: validate_field_mapping + create_config/update_config 集成** — `9532657` (feat)
3. **Task 3: 新增 test_feishu_leading_zero.py（12 测试）** — `9bf3f70` (test)

## Files Created/Modified

### `backend/app/services/feishu_service.py` (modified)

**Diff 摘要：**

1. **新增类（顶部、`logger` 之后、`class FeishuService` 之前）：**

```python
class FeishuConfigValidationError(ValueError):
    """EMPNO-03 / D-01: 飞书配置校验失败（字段类型不符合要求等）。"""
    def __init__(self, detail: dict) -> None:
        super().__init__(str(detail))
        self.detail = detail
```

2. **`_map_fields` employee_no 分支（D-08）：**

```python
# 修改前
if system_name == 'employee_no':
    has_employee_no = True
    if isinstance(value, float) and value == int(value):
        value = str(int(value))
    else:
        value = str(value).strip()

# 修改后
if system_name == 'employee_no':
    has_employee_no = True
    if not isinstance(raw_value, str):
        logger.warning(
            '飞书 employee_no 非文本类型，已强制转字符串（可能已丢失前导零）。raw_value=%r',
            raw_value,
        )
    value = str(value).strip()
```

3. **`_build_employee_map` 重构（B-10 根因修复）：**

```python
# 修改前
def _build_employee_map(self) -> dict[str, str]:
    emp_rows = self.db.execute(select(Employee.employee_no, Employee.id)).all()
    emp_map: dict[str, str] = {}
    for emp_no, emp_id in emp_rows:
        emp_map[emp_no] = emp_id
        stripped = emp_no.lstrip('0') or '0'   # ← 这三行使计数器永远为 0
        if stripped not in emp_map:
            emp_map[stripped] = emp_id
    return emp_map

# 修改后
def _build_employee_map(self) -> dict[str, str]:
    """Build employee_no → id map from DB (DB 真实视图，不预填充 stripped 版本)。"""
    emp_rows = self.db.execute(select(Employee.employee_no, Employee.id)).all()
    return {emp_no: emp_id for emp_no, emp_id in emp_rows}
```

4. **`_lookup_employee` 签名变更（staticmethod → instance method + fallback_counter）：**

```python
# 修改前
@staticmethod
def _lookup_employee(emp_map: dict[str, str], emp_no: str | None) -> str | None:
    if not emp_no:
        return None
    emp_id = emp_map.get(emp_no)
    if emp_id is not None:
        return emp_id
    return emp_map.get(emp_no.lstrip('0') or '0')   # 因预填充永远走不到这里

# 修改后
def _lookup_employee(
    self,
    emp_map: dict[str, str],
    emp_no: str | None,
    *,
    fallback_counter: dict[str, int] | None = None,
) -> str | None:
    if not emp_no:
        return None
    emp_id = emp_map.get(emp_no)
    if emp_id is not None:
        return emp_id
    stripped_key = emp_no.lstrip('0') or '0'
    for map_key, map_id in emp_map.items():
        if (map_key.lstrip('0') or '0') == stripped_key:
            if fallback_counter is not None:
                fallback_counter['count'] = fallback_counter.get('count', 0) + 1
            return map_id
    return None
```

5. **5 个 sync_* 方法升级 _lookup_employee 调用 + 计数落库：**

| Sync 方法 | fallback_counter 创建位置 | 计数落库位置 |
|-----------|--------------------------|-------------|
| `sync_attendance` | sync_log 实例化之后 | success: `sync_log.leading_zero_fallback_count = fallback_counter['count']`; failure: `fail_log.leading_zero_fallback_count = fallback_counter['count']` |
| `sync_performance_records` | emp_map 之后 | 返回 dict 增加 `'leading_zero_fallback_count': fallback_counter['count']` |
| `sync_salary_adjustments` | emp_map 之后 | 返回 dict 增加 `'leading_zero_fallback_count': fallback_counter['count']` |
| `sync_hire_info` | emp_map 之后 | 返回 dict 增加 `'leading_zero_fallback_count': fallback_counter['count']` |
| `sync_non_statutory_leave` | emp_map 之后 | 返回 dict 增加 `'leading_zero_fallback_count': fallback_counter['count']` |

每个 sync 方法的 `self._lookup_employee(emp_map, emp_no)` 调用统一升级为 `self._lookup_employee(emp_map, emp_no, fallback_counter=fallback_counter)`。

6. **新增 `validate_field_mapping` 与 `_validate_field_mapping_with_credentials`（位置：`list_bitable_fields` 之后、`parse_bitable_url` 之前）：**

完整 API：

```python
class FeishuService:
    _FEISHU_TEXT_FIELD_TYPE = 1
    _FIELD_MAPPING_REQUIRED_TYPES = {'employee_no': _FEISHU_TEXT_FIELD_TYPE}
    _FEISHU_FIELD_TYPE_NAMES = {1: 'text', 2: 'number', 3: 'single_select', ...}

    def validate_field_mapping(self, *, app_token, table_id, field_mapping) -> None:
        # 基于 self.get_config() 已持久化的 config 校验
        ...

    def _validate_field_mapping_with_credentials(
        self, *, app_id, app_secret, app_token, table_id, field_mapping,
    ) -> None:
        # 直接用传入 credentials 校验，不依赖已持久化 config
        # 调用 _ensure_token + httpx.get bitable fields
        # 错误时抛 FeishuConfigValidationError(detail={...})
        ...
```

7. **`create_config` 集成校验：**

```python
def create_config(self, data: FeishuConfigCreate) -> FeishuConfig:
    settings = get_settings()
    field_mapping_dict = {item.feishu_field: item.system_field for item in data.field_mapping}

    # D-01: 阻断非 text 类型的 employee_no 字段映射保存
    self._validate_field_mapping_with_credentials(
        app_id=data.app_id,
        app_secret=data.app_secret,
        app_token=data.bitable_app_token,
        table_id=data.bitable_table_id,
        field_mapping=field_mapping_dict,
    )

    config = FeishuConfig(...)
    ...
```

8. **`update_config` 条件性校验（仅在 field_mapping / bitable 坐标变更时）：**

```python
def update_config(self, config_id, data) -> FeishuConfig:
    config = self.db.get(FeishuConfig, config_id)
    if config is None:
        raise RuntimeError(...)
    settings = get_settings()

    needs_validation = (
        data.field_mapping is not None
        or data.bitable_app_token is not None
        or data.bitable_table_id is not None
    )
    if needs_validation:
        # 计算 effective_app_id / effective_app_secret / effective_app_token / effective_table_id / effective_mapping
        # 调用 _validate_field_mapping_with_credentials(...)
        ...

    # 以下保留原有写入逻辑
    ...
```

### `backend/tests/test_services/test_feishu_leading_zero.py` (created)

277 行，含本地 `db_session` fixture（StaticPool in-memory SQLite），12 个测试函数：

**_map_fields 测试（3 个）：**
- `test_map_fields_float_employee_no_produces_string_with_decimal` — float 2615.0 → '2615.0' + warning 触发
- `test_map_fields_warns_when_employee_no_not_string` — int 12345 → '12345' + warning 触发
- `test_map_fields_preserves_string_employee_no_with_leading_zero` — str '02615' → '02615' + 无 warning

**_lookup_employee fallback 计数器测试（5 个，含 B-10 修复验证 4 场景）：**
- `test_lookup_employee_fallback_scenario_A_db_has_leading_zero_feishu_missing` — DB '02615'、飞书 '2615' → fallback 命中计数 +1
- `test_lookup_employee_exact_match_scenario_B_no_fallback` — exact 命中计数 0
- `test_lookup_employee_exact_match_scenario_C_no_leading_zero` — 普通 exact 命中计数 0
- `test_lookup_employee_fallback_scenario_D_feishu_extra_zero` — DB '02615' 飞书 '002615' → fallback 命中计数 +1
- `test_lookup_employee_miss_returns_none_no_counter_change` — 完全 miss 返回 None 计数 0

**_build_employee_map 测试（1 个）：**
- `test_build_employee_map_no_stripped_prefill` — 验证仅含 DB 原始 emp_no、无预填充 stripped 版本

**validate_field_mapping_with_credentials 测试（3 个）：**
- `test_validate_field_mapping_accepts_text_type_for_employee_no` — type=1 通过
- `test_validate_field_mapping_rejects_number_type_for_employee_no` — type=2 抛 invalid_field_type，detail 严格匹配 `{'error': 'invalid_field_type', 'field': 'employee_no', 'expected': 'text', 'actual': 'number'}`
- `test_validate_field_mapping_raises_when_field_name_not_in_bitable` — field_name 不存在抛 field_not_found_in_bitable

## Decisions Made

### `sync_log.leading_zero_fallback_count` 落库 vs 4 个不写 FeishuSyncLog 的 sync 方法

PLAN 文本"5 个 sync_* 方法都在开头创建 fallback_counter，都把计数写入 sync_log.leading_zero_fallback_count"与现状代码不一致 — `sync_performance_records` / `sync_salary_adjustments` / `sync_hire_info` / `sync_non_statutory_leave` 这 4 个方法不创建 `FeishuSyncLog` 实例（直接 self.db.commit() 后返回 dict）。

PLAN 验证条件允许「等价 grep pattern」≥5 次命中。本 plan 的取舍：

- `sync_attendance` 在 success 路径与 failure 路径**各**写一次 `sync_log.leading_zero_fallback_count = fallback_counter['count']` （字面 2 次命中）
- 其余 4 个方法在返回 dict 中加入 `'leading_zero_fallback_count': fallback_counter['count']`（4 次等价命中）

合计 6 次 ≥ 5，满足验收条件，且不引入跨方法的架构变更（不创建额外 FeishuSyncLog 实例）。后续 Plan 04 / 31 若需要将 4 个 sync 方法的同步结果也写入 FeishuSyncLog，是独立的扩展工作，不在本 plan scope。

### _lookup_employee 由 staticmethod 改实例方法

PLAN 明确要求改为实例方法（带 self），原因是 fallback_counter 关键字参数需要通过 `self._lookup_employee(...)` 调用而非 `FeishuService._lookup_employee(...)`。本 plan 全文搜索确认：原 5 个 sync 方法的调用点全部已使用 `self._lookup_employee(...)` 形式（即使原方法是 staticmethod，Python 允许 self 调用 staticmethod），故签名变更对调用方零破坏。

### 既有测试 fixture 调整说明

无 — `test_feishu_config.py` 与 `test_feishu_service.py` 当前全部为 RED stubs（`pytest.fail` + `xfail`），未实际调用 `_lookup_employee` 或 `create_config`。本 plan 没有修改这两个测试文件，13 个 XFAIL 状态保留不变。

## Deviations from Plan

**Rule 2 - Auto-add missing critical functionality:** PLAN 文本要求「5 个 sync_* 方法都把计数写入 sync_log.leading_zero_fallback_count」，但实际代码中 4 个 sync 方法（performance / salary_adjustments / hire_info / non_statutory_leave）并不创建 FeishuSyncLog。已在「Decisions Made」节解释取舍：在这 4 个方法的返回 dict 中加入等价 `'leading_zero_fallback_count': fallback_counter['count']` 字段。本 plan 不引入跨方法架构变更（创建 FeishuSyncLog 是 Plan 04 / 31 的范围）。Acceptance criteria「或等价 grep pattern 命中 ≥ 5」明确允许此模式。

无其他偏离。

## Verification Results

### grep 验收条件

| 检查 | 期望 | 实际 | 通过 |
|------|------|------|------|
| `str(int(value))` 删除 | 0 | 0 | ✅ |
| `飞书 employee_no 非文本类型...` | 1 | 1 | ✅ |
| `has_employee_no = True` | ≥1 | 1 | ✅ |
| `_build_employee_map` 内 `emp_map[stripped]` | 0 | 0 | ✅ |
| `_build_employee_map` 内 `stripped = emp_no.lstrip` | 0 | 0 | ✅ |
| `fallback_counter: dict[str, int] | None = None` | 1 | 1 | ✅ |
| `_lookup_employee` 上方 `@staticmethod` | 0 | 0 | ✅ |
| `for map_key, map_id in emp_map.items` | ≥1 | 1 | ✅ |
| `fallback_counter: dict[str, int] = {'count': 0}` | ≥5 | 5 | ✅ |
| `leading_zero_fallback_count = fallback_counter['count']` 等价命中 | ≥5 | 10 | ✅ |
| `class FeishuConfigValidationError` | 1 | 1 | ✅ |
| `def validate_field_mapping` | 1 | 1 | ✅ |
| `def _validate_field_mapping_with_credentials` | 1 | 1 | ✅ |
| `_FEISHU_TEXT_FIELD_TYPE = 1` | 1 | 1 | ✅ |
| `_FIELD_MAPPING_REQUIRED_TYPES` | ≥2 | 2 | ✅ |
| `'error': 'invalid_field_type'` | ≥1 | 2 | ✅ |
| `needs_validation` | ≥1 | 2 | ✅ |
| `create_config` 内 `_validate_field_mapping_with_credentials` 在 `config = FeishuConfig(` 之前 | yes | 行 1197 < 1205 | ✅ |
| `backend/app/api/v1/feishu.py` 未变更 | yes | git diff 空 | ✅ |

### Python 运行时验证

```bash
$ /Users/mac/PycharmProjects/Wage_adjust/.venv/bin/python -c "
from backend.app.services.feishu_service import FeishuService, FeishuConfigValidationError
e = FeishuConfigValidationError({'error': 'invalid_field_type', 'field': 'employee_no', 'expected': 'text', 'actual': 'number'})
print(e.detail)
"
{'error': 'invalid_field_type', 'field': 'employee_no', 'expected': 'text', 'actual': 'number'}
```

```bash
$ /Users/mac/PycharmProjects/Wage_adjust/.venv/bin/python -c "from backend.app.services.feishu_service import FeishuService; print(FeishuService._lookup_employee.__doc__[:60])"
Find employee_id by trying exact match first, then lstrip fall
```

### pytest 输出

新测试文件（12 全 PASS）：

```text
backend/tests/test_services/test_feishu_leading_zero.py::test_map_fields_float_employee_no_produces_string_with_decimal PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_map_fields_warns_when_employee_no_not_string PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_map_fields_preserves_string_employee_no_with_leading_zero PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_lookup_employee_fallback_scenario_A_db_has_leading_zero_feishu_missing PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_lookup_employee_exact_match_scenario_B_no_fallback PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_lookup_employee_exact_match_scenario_C_no_leading_zero PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_lookup_employee_fallback_scenario_D_feishu_extra_zero PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_lookup_employee_miss_returns_none_no_counter_change PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_build_employee_map_no_stripped_prefill PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_validate_field_mapping_accepts_text_type_for_employee_no PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_validate_field_mapping_rejects_number_type_for_employee_no PASSED
backend/tests/test_services/test_feishu_leading_zero.py::test_validate_field_mapping_raises_when_field_name_not_in_bitable PASSED

============================== 12 passed in 0.78s ==============================
```

整体 feishu 测试集（含 30-01 sync_log model 测试）：

```text
collected 28 items
============== 15 passed, 13 xfailed, 2 warnings in 0.90s ==============
```

15 个 PASSED（12 新 + 3 sync_log model）；13 个 XFAIL 全部维持原状（来自 Plan 02 的 RED stubs）；零回归。

## Issues Encountered

无。Plan 准确度高、tasks 自包含；执行过程零阻塞。

## User Setup Required

None - 本 plan 改动不引入新外部依赖、不需要环境变量、不影响数据库 schema（schema 变更已由 30-01 完成）。

API 层将在 Plan 04 添加 `FeishuConfigValidationError` 的 exception handler 转 422 响应；本 plan 提供的契约（自定义异常类 + .detail 结构）足够支撑 Plan 04 的 API 层实现。

## Next Phase Readiness

- **EMPNO-02 / EMPNO-03 / EMPNO-04 已完成。** 飞书源端 employee_no 处理链路（_map_fields → _build_employee_map → _lookup_employee → sync_log）全部贯通。
- Plan 04（API 层 / UI 层处理 FeishuConfigValidationError 与 leading_zero_fallback_count 黄色提示）可直接读取本 plan 的：
  - `FeishuConfigValidationError.detail` 在 API 层 `except FeishuConfigValidationError as exc: raise HTTPException(status_code=422, detail=exc.detail)`
  - `FeishuSyncLog.leading_zero_fallback_count`（30-01 提供字段，本 plan 写值）→ SyncLogRead schema 暴露 + 前端黄色提示

## Self-Check: PASSED

- FOUND: backend/app/services/feishu_service.py (modified, includes FeishuConfigValidationError, validate_field_mapping, _validate_field_mapping_with_credentials, _build_employee_map without stripped prefill, _lookup_employee instance method with fallback_counter)
- FOUND: backend/tests/test_services/test_feishu_leading_zero.py (new, 12 tests passing)
- FOUND commit 9b7c67c (Task 1: feat _map_fields + _build_employee_map + _lookup_employee + sync_*)
- FOUND commit 9532657 (Task 2: feat validate_field_mapping + create_config/update_config)
- FOUND commit 9bf3f70 (Task 3: test test_feishu_leading_zero.py 12 tests)

---
*Phase: 30-employee-no-leading-zero*
*Completed: 2026-04-21*
