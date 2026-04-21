---
phase: 30-employee-no-leading-zero
plan: 02
subsystem: import
tags: [import, excel, openpyxl, pandas, leading-zero, sanity-check, pytest]

# Dependency graph
requires:
  - phase: 17-batch-import-strict-validation
    provides: ImportService 既有 row_index 口径与 _import_* SAVEPOINT 模式
  - phase: 16-batch-import-progress-async
    provides: build_template_xlsx / _load_table 框架
provides:
  - Excel 模板四种类型工号列预设 cell.number_format='@'（覆盖 1-105 行）
  - 模板示例行工号统一为 '02651'，employees 上级工号 '02650'，直观展示前导零
  - certifications 模板的 certification_type / certification_stage 列同样预设文本格式
  - _dispatch_import 增加前导零丢失 sanity check（正则 ^\d+\.0$ 检测）
  - 错误消息含可执行三段式补救指引（CONTEXT.md D-07 原文）
  - bool mask 过滤坏行模式（保留原 pandas index，与 _import_* row_index 口径一致）
  - 8 个 pytest 回归测试（含 2 个 parametrize 展开为 14 项）
affects: [phase-31-feishu-leading-zero, phase-32-import-ux-improvements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "openpyxl cell.number_format='@' 预填充覆盖表头+示例+空行"
    - "pandas DataFrame bool mask 过滤而非 reset_index（保留原索引契约）"
    - "ImportService classmethod 工具函数（无 self 依赖的纯计算）"

key-files:
  created:
    - backend/tests/test_services/test_import_leading_zero.py
  modified:
    - backend/app/services/import_service.py

key-decisions:
  - "采用 D-09/D-10 的混合策略：模板端文本格式预设 + 读入端 sanity check 双保险"
  - "row_index 沿用既有 _import_* 的 pandas_idx + 1 口径，禁止 reset_index 以避免索引偏移"
  - "TEMPLATE_TEXT_PREFILL_ROWS = 105 = 表头(1) + 示例(1) + 103 空行（覆盖一般 HR 单批次录入量）"
  - "示例行工号 '02651' 取自用户原话，HR 一眼可识别前导零意图"
  - "本地定义 db_session fixture，禁止新建 conftest.py（沿用 test_import_partial_success.py 模式）"

patterns-established:
  - "Excel 模板下发端：通过 TEMPLATE_TEXT_COLUMNS 类常量声明每种 import_type 的文本类列"
  - "读入端校验：私有 classmethod + 类常量（_LEADING_ZERO_LOST_PATTERN / _EMPLOYEE_NO_KEY_COLUMNS）实现可测试的纯函数"

requirements-completed: [EMPNO-01, EMPNO-02]

# Metrics
duration: 18min
completed: 2026-04-21
---

# Phase 30 Plan 02: ImportService 工号前导零双端闭合 Summary

**Excel 模板强制工号列文本格式 (cell.number_format='@', 1-105 行) + _dispatch_import 前导零丢失 sanity check（正则 ^\d+\.0$ + bool mask 过滤），覆盖 employees / certifications / performance_grades / salary_adjustments 四种 import_type**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-21T01:26Z
- **Completed:** 2026-04-21T01:44Z
- **Tasks:** 3
- **Files modified:** 2 (1 modified + 1 created)

## Accomplishments

- **模板下发端 (EMPNO-01)** — `build_template_xlsx` 对四种类型的工号列、employees 直属上级工号列、certifications 认证类型/阶段列统一设 `cell.number_format = '@'`，预填充 1~105 行；示例行工号统一改为 `'02651'`（employees 直属上级 `'02650'`），HR 下载即看到带前导零的字符串示例
- **读入端 (EMPNO-02)** — `_dispatch_import` 在 `_normalize_columns` + 必填列校验之后、派发到具体 `_import_*` 之前插入 format sanity check：扫描 `employee_no` / `manager_employee_no` 列，凡值匹配 `^\d+\.0$` 的行直接进入 `failed_rows`，错误消息字面包含「格式异常（疑似丢失前导零）」+「请在 Excel 中将该列改为「文本」格式后重新上传」+「或从系统重新下载最新模板」
- **row_index 口径一致性** — sanity check 使用 `pandas_idx + 1`，与既有 `_import_employees` / `_import_certifications` / `_import_performance_grades` / `_import_salary_adjustments` 的 `int(index) + 1` 完全一致；坏行过滤通过 `dataframe.loc[~bad_mask].copy()` 实现，**不**调用 `reset_index(drop=True)`，保留原 pandas index 给下游 `_import_*` 使用
- **回归测试** — 8 个测试函数（pytest 展开为 14 项）全部 PASS；既有 import 测试集（`test_import_service.py` / `test_import_xlsx.py` / `test_import_idempotency.py` / `test_import_partial_success.py` / `test_import_certification.py`）共 28 项无回归

## Task Commits

Each task was committed atomically:

1. **Task 1: 改造 build_template_xlsx 统一工号列文本格式 + 示例行改为 '02651'** — `756e5fb` (feat)
2. **Task 2: _dispatch_import 增加 format sanity check（row_index 沿用既有口径）** — `754cf06` (feat)
3. **Task 3: 新增 pytest 测试 test_import_leading_zero.py（含本地 db_session fixture）** — `5405b49` (test)

## Files Created/Modified

- `backend/app/services/import_service.py` — 新增 `import re`，新增 4 个类常量（`TEMPLATE_TEXT_PREFILL_ROWS`, `TEMPLATE_TEXT_COLUMNS`, `_LEADING_ZERO_LOST_PATTERN`, `_EMPLOYEE_NO_KEY_COLUMNS`），新增 `_detect_leading_zero_loss_rows` classmethod，重写 `_dispatch_import` 加入 sanity check 分支（bool mask 过滤而非 reset_index），`build_template_xlsx` 四种 example 行工号 `'02651'` + 文本列 `cell.number_format='@'` 预填充循环
- `backend/tests/test_services/test_import_leading_zero.py` — 新建文件，本地 `db_session` fixture（不新建 conftest.py），8 个测试函数覆盖模板格式（4 个）+ sanity check 行为（4 个，含 row_index 契约一致性专项）

## Decisions Made

### Diff 摘要

**`build_template_xlsx` (Task 1):**
- 新增类常量 `TEMPLATE_TEXT_PREFILL_ROWS = 105` 与 `TEMPLATE_TEXT_COLUMNS` 字典，集中声明每种 import_type 的文本类列
- 四种类型示例行第 1 列由 `'EMP-1001'` 改为 `'02651'`；employees 第 10 列（直属上级工号）由 `''` 改为 `'02650'`
- 在写完 headers + example + 列宽后新增循环：通过 `COLUMN_ALIASES` 反向映射定位「系统字段名 → 中文表头名 → headers 索引」，对 `range(1, TEMPLATE_TEXT_PREFILL_ROWS + 1)` 各行该列设 `cell.number_format = '@'`
- 既有 header 样式（font / fill / alignment）与列宽逻辑保持不变，未删除原有代码

**`_dispatch_import` (Task 2):**
- 文件顶部新增 `import re`（紧跟 `import logging` 之后、第三方 `import pandas` 之前，符合既定 import 组织顺序）
- 新增类常量 `_LEADING_ZERO_LOST_PATTERN = re.compile(r'^\d+\.0$')` 与 `_EMPLOYEE_NO_KEY_COLUMNS = frozenset({'employee_no', 'manager_employee_no'})`
- 新增 classmethod `_detect_leading_zero_loss_rows(dataframe)` → `dict[int, tuple[int, str]]`，扫描两个关键键列，返回 `{pandas_idx: (pandas_idx + 1, col_name)}`
- 重写 `_dispatch_import`：在 `_normalize_columns` + 必填列校验之后插入 sanity check；若有坏行，逐条写入 `failed_rows`（含 `error_column` + 三段式 message），用 `bad_mask = dataframe.index.isin(bad_rows.keys())` + `dataframe.loc[~bad_mask].copy()` 过滤，**不**调用 `reset_index(drop=True)`
- 派发到具体 `_import_*` 时改用 `extend(...)` 累加结果，保留 sanity check 的 failed 记录与下游 success/failed 同列出现

## Deviations from Plan

None - plan executed exactly as written.

所有 grep-based 验收条件、Python import 验证、模板二进制验证、pytest 回归全部按 plan 要求一次性通过；CLAUDE.md 关于「评分/调薪/导入」核心规则与本 plan 改动不冲突。

## Issues Encountered

- 项目无 `python` 命令，只有 `python3` 与 `.venv/bin/python`。验证脚本统一使用 `/Users/mac/PycharmProjects/Wage_adjust/.venv/bin/python`，未引入 plan 之外的修改。

## Verification Results

### grep 验收条件

| 检查 | 命中数 | 通过 |
|------|--------|------|
| `TEMPLATE_TEXT_PREFILL_ROWS = 105` | 1 | ✅ |
| `TEMPLATE_TEXT_COLUMNS = {` | 1 | ✅ |
| `cell.number_format = '@'` | 1 | ✅ |
| `_LEADING_ZERO_LOST_PATTERN = re.compile` | 1 | ✅ |
| `_EMPLOYEE_NO_KEY_COLUMNS = frozenset` | 1 | ✅ |
| `def _detect_leading_zero_loss_rows` | 1 | ✅ |
| `dataframe.loc[~bad_mask]` | 1 | ✅ |
| `格式异常（疑似丢失前导零）` | 2 | ✅ |
| `请在 Excel 中将该列改为「文本」格式后重新上传` | 1 | ✅ |
| `或从系统重新下载最新模板` | 1 | ✅ |
| `^import re$` | 1 | ✅ |
| `_dispatch_import` 内 `reset_index(drop=True)` | 0 | ✅ |

### Python 运行时验证

```text
TEMPLATE_TEXT_PREFILL_ROWS: 105
TEMPLATE_TEXT_COLUMNS: 4 keys，覆盖全部 SUPPORTED_TYPES
EMPLOYEE_NO_KEY_COLUMNS: frozenset({'employee_no', 'manager_employee_no'})
pattern '1234.0' match: True
pattern '02651' match: False
pattern '1234' match: False

[employees] bytes=6197, A1='员工工号', A2='02651', col A 1-105 @=True, J1='直属上级工号', J2='02650', col J 1-105 @=True
[certifications] bytes=6269, A1='员工工号', A2='02651', col A 1-105 @=True, B='认证类型' col B 1-105 @=True, C='认证阶段' col C 1-105 @=True
[performance_grades] bytes=5615, A1='员工工号', A2='02651', col A 1-105 @=True
[salary_adjustments] bytes=5660, A1='员工工号', A2='02651', col A 1-105 @=True
```

### pytest 输出

新测试文件：

```text
backend/tests/test_services/test_import_leading_zero.py::test_template_employee_no_cell_format_is_text_for_all_types[employees] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_employee_no_cell_format_is_text_for_all_types[certifications] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_employee_no_cell_format_is_text_for_all_types[performance_grades] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_employee_no_cell_format_is_text_for_all_types[salary_adjustments] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_example_row_uses_leading_zero[employees] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_example_row_uses_leading_zero[certifications] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_example_row_uses_leading_zero[performance_grades] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_example_row_uses_leading_zero[salary_adjustments] PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_manager_employee_no_column_is_text PASSED
backend/tests/test_services/test_import_leading_zero.py::test_template_cert_type_and_stage_columns_are_text PASSED
backend/tests/test_services/test_import_leading_zero.py::test_dispatch_import_flags_leading_zero_lost_rows PASSED
backend/tests/test_services/test_import_leading_zero.py::test_dispatch_import_allows_valid_leading_zero_rows PASSED
backend/tests/test_services/test_import_leading_zero.py::test_manager_employee_no_also_checked PASSED
backend/tests/test_services/test_import_leading_zero.py::test_row_index_matches_existing_import_contract PASSED

============================== 14 passed in 2.21s ==============================
```

整体回归（含既有 import 测试集）：

```text
collected 42 items

backend/tests/test_services/test_import_service.py .......       [ 16%]
backend/tests/test_services/test_import_xlsx.py ..........       [ 40%]
backend/tests/test_services/test_import_idempotency.py ...       [ 47%]
backend/tests/test_services/test_import_partial_success.py ..... [ 59%]
backend/tests/test_services/test_import_certification.py ...     [ 66%]
backend/tests/test_services/test_import_leading_zero.py .........[100%]

============================== 42 passed in 4.00s ==============================
```

## User Setup Required

None - 本 plan 改动不引入新外部依赖、不需要环境变量、不影响数据库 schema。HR 在下次下载模板时自动获得新格式；Excel 老模板上传若工号列被错识别为数字将自动得到补救提示。

## Next Phase Readiness

- **EMPNO-01 / EMPNO-02 已完成。** 模板与读入端的双端闭合已通过自动化测试与运行时验证确认。
- 同 phase 内 30-03 (EMPNO-03 飞书字段类型校验) 与 30-04 (EMPNO-04 leading_zero_fallback_count 计数器) 与本 plan 完全独立，可并行执行（已属同一 wave）。
- 30-01 (FeishuService._map_fields 强制 text) 与本 plan 同 wave 1，互不依赖。
- 后续若引入 CSV 模板的文本列约束（CSV 无 cell.number_format 概念），需在 v1.5+ phase 单独评估。

## Self-Check

- [x] backend/app/services/import_service.py — 已修改并提交 (756e5fb, 754cf06)
- [x] backend/tests/test_services/test_import_leading_zero.py — 已创建并提交 (5405b49)
- [x] commit 756e5fb 存在于 git log
- [x] commit 754cf06 存在于 git log
- [x] commit 5405b49 存在于 git log

## Self-Check: PASSED

---
*Phase: 30-employee-no-leading-zero*
*Completed: 2026-04-21*
