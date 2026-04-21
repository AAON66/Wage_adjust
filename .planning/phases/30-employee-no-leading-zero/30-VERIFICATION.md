---
phase: 30-employee-no-leading-zero
verified: 2026-04-21T10:30:00Z
status: human_needed
score: 4/4 must-haves verified
re_verification: false
human_verification:
  - test: "HR 在 Excel 中打开系统下发的模板，手动录入 01234 到「员工工号」列 → 保存并重新打开 xlsx"
    expected: "单元格值保持 01234 字符串（不被 Excel 自动转换为 1234）；前导零被保留"
    why_human: "Excel 行为是桌面软件的实际交互，自动化无法直接验证 Excel.exe 的保存-重开行为；cell.number_format=='@' 已在代码层自动化断言通过"
  - test: "HR 在 FeishuConfig 页面把 employee_no 映射到飞书多维表格中类型为「数字」的字段并点击保存"
    expected: "页面出现红色错误提示：『工号字段类型必须为文本（当前为 number），请在飞书多维表格中将该字段改为「文本」类型后重试』；配置未保存"
    why_human: "需要真实飞书多维表格环境才能制造一个「数字」类型字段；自动化已通过 mock httpx.get 返回 type=2 验证后端 validator 行为，但实际飞书 SaaS 响应结构需人工确认"
  - test: "HR 在 AttendanceManagement 页面观察 SyncStatusCard，当某次同步产生 leading_zero_fallback_count > 0 时"
    expected: "卡片底部出现黄色文字：『N 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式』；顶层 status 不被降级"
    why_human: "需要真实飞书同步链路产生容忍匹配才能触发 > 0 场景；自动化已在测试中直接用 _lookup_employee(fallback_counter=...) 验证计数器语义、也验证了 API 层 /sync-logs 返回该字段"
---

# Phase 30: 工号前导零修复 Verification Report

**Phase Goal:** HR 导入或飞书同步的员工工号能完整保留前导零，下游所有匹配/导入/同步动作在稳定的 `employee_no` 键上运行
**Verified:** 2026-04-21T10:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | HR 从「下载模板」拿到的 xlsx 文件中工号列是文本格式，在 Excel 里手动录入 `01234` 保存不会变成 `1234` | ✓ VERIFIED | 4 种模板的 A 列第 1/50/105 行 `cell.number_format == '@'`；示例行值 `'02651'`（字符串）；自动化测试 14 项 PASS（含 parametrize 展开） |
| 2 | 三条写入链路（Excel 导入 / 飞书同步 / 手动表单录入）对同一个工号字符串 `01234` 的读取结果一致，写入数据库后保留前导零不被转为数字 | ✓ VERIFIED | Excel: `pd.read_excel(dtype=str)` + `_detect_leading_zero_loss_rows` 拦截 `'1234.0'`；飞书: `_map_fields` 删除 `str(int(value))` 分支，float 输入产出 `'2615.0'` + warning；手动录入: `EmployeeBase.employee_no: str` Pydantic 约束拒绝 int/float JSON 输入（运行时验证 `input_value=1234, input_type=int` 被 reject） |
| 3 | 管理员在飞书多维表格绑定配置页尝试把 `employee_no` 字段选成「数字」类型时被阻止保存，并看到「配置错误：工号字段类型必须为 text」 | ✓ VERIFIED (automated) / ? HUMAN (end-to-end) | `_validate_field_mapping_with_credentials` 在 `create_config` / `update_config` 调用前强制校验；非 text 字段抛 `FeishuConfigValidationError({'error': 'invalid_field_type', 'field': 'employee_no', 'expected': 'text', 'actual': '<name>'})`；API 层 except 映射 422 + dict body；前端 FeishuConfig.tsx 走 `axios.isAxiosError && status===422 && detail.error==='invalid_field_type'` 路由到中文文案。自动化端到端（mock httpx）PASS。真实飞书多维表格端的人工冒烟保留在 human_verification |
| 4 | 存量数据未迁移但未来写入路径已修复；`_build_employee_map` 匹配时对 leading-zero 差异（如 `1234` vs `01234`）仍能容忍匹配并在日志里打出告警 metrics，便于后续观测 | ✓ VERIFIED | `_build_employee_map` 改为返回 DB 真实视图（不预填充 stripped）；`_lookup_employee` 实例方法 + `fallback_counter` 关键字参数，fallback 分支对 emp_map 每个 key 做 `lstrip('0')` 比对，命中时 `counter['count'] += 1`；5 个 sync_* 方法在开头创建 counter 并在完成时落入 `sync_log.leading_zero_fallback_count`（sync_attendance）或返回 dict 中（其余 4 个方法）；场景 A/B/C/D 自动化 PASS；GET `/api/v1/feishu/sync-logs` 序列化该字段，SyncStatusCard 渲染黄色诊断提示 |

**Score:** 4/4 observable truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/feishu_sync_log.py` | 新增 `leading_zero_fallback_count: Mapped[int]` 字段 | ✓ VERIFIED | Line 29: `leading_zero_fallback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')`；位于 `failed_count` 之后、`error_message` 之前 |
| `alembic/versions/30_01_add_leading_zero_fallback_count.py` | Alembic 迁移 batch_alter_table 添加列 | ✓ VERIFIED | revision `30_01_leading_zero_fallback`，down_revision `a26_01_feishu_open_id`；`upgrade()` 用 `op.batch_alter_table('feishu_sync_logs').add_column(Integer NOT NULL server_default='0')`；`downgrade()` 调 `drop_column`。`alembic upgrade head` 验证通过，`PRAGMA table_info` 确认 `(15, 'leading_zero_fallback_count', 'INTEGER', 1, "'0'", 0)`；alembic 当前 head 为本迁移 |
| `backend/app/services/import_service.py` | `build_template_xlsx` 文本格式 + `_dispatch_import` sanity check | ✓ VERIFIED | `TEMPLATE_TEXT_PREFILL_ROWS=105`、`TEMPLATE_TEXT_COLUMNS` 字典定义 4 种 import_type 的文本类列；`_LEADING_ZERO_LOST_PATTERN=re.compile(r'^\d+\.0$')`；`_EMPLOYEE_NO_KEY_COLUMNS=frozenset({'employee_no','manager_employee_no'})`；`_detect_leading_zero_loss_rows` classmethod；`_dispatch_import` 用 `dataframe.loc[~bad_mask].copy()` 过滤（无 `reset_index(drop=True)`）；错误消息字面包含「格式异常（疑似丢失前导零）」+「请在 Excel 中将该列改为「文本」格式后重新上传」+「或从系统重新下载最新模板」 |
| `backend/app/services/feishu_service.py` | `_map_fields` text-only + `_build_employee_map` + `_lookup_employee` + validate_field_mapping | ✓ VERIFIED | `FeishuConfigValidationError(ValueError)` 含 `.detail` 字典；`_map_fields` 已删除 `str(int(value))` 分支，raw_value 非 str 时 `logger.warning('飞书 employee_no 非文本类型，已强制转字符串（可能已丢失前导零）')`；`_build_employee_map` 返回 `{emp_no: emp_id for ...}`（无 stripped 预填充）；`_lookup_employee` 实例方法 + `fallback_counter: dict[str, int] \| None = None` 关键字参数，fallback 分支遍历 `emp_map.items()` 做 `lstrip('0')` 比对；`validate_field_mapping` 与 `_validate_field_mapping_with_credentials` 新增，`create_config` 在 `FeishuConfig(...)` 实例化之前调用 validator，`update_config` 在 field_mapping / bitable 坐标变更时条件性调用 |
| `backend/app/api/v1/feishu.py` | 422 映射 + SyncLogRead 透传 | ✓ VERIFIED | Line 24 import `FeishuConfigValidationError, FeishuService`；`create_config` 与 `update_config` 两个路由各 `except FeishuConfigValidationError → HTTPException(422, detail=exc.detail)`（路径 X，main.py 已透传 dict detail）；`_sync_log_to_read` 含 `leading_zero_fallback_count=log.leading_zero_fallback_count`；API 集成测试 4 项 PASS |
| `backend/app/schemas/feishu.py` | SyncLogRead 新增字段 | ✓ VERIFIED | Line 80: `leading_zero_fallback_count: int = 0`；`SyncLogRead.model_fields` 含该 key（运行时确认 True） |
| `frontend/src/types/api.ts` | TS interface 新增字段 | ✓ VERIFIED | Line 791: `leading_zero_fallback_count: number;`；`tsc --noEmit` 通过 |
| `frontend/src/pages/FeishuConfig.tsx` | invalid_field_type 错误展示 | ✓ VERIFIED | `axios.isAxiosError` guard + `status===422` + `detail.error==='invalid_field_type'` 路由到「工号字段类型必须为文本（当前为 ${actual}）...」文案，同时 `setErrors.field_mapping='工号字段类型必须为文本'`；另处理 `field_not_found_in_bitable` / `bitable_fields_fetch_failed` 兜底 |
| `frontend/src/components/attendance/SyncStatusCard.tsx` | leading_zero_fallback_count>0 黄色提示 | ✓ VERIFIED | Lines 85-89: `{syncStatus && syncStatus.leading_zero_fallback_count > 0 ? ( <p className="mt-2 text-sm" style={{ color: 'var(--color-warning, #FF7D00)' }}> ... 建议排查飞书源数据格式 </p> ) : null}` |
| `backend/tests/test_services/test_feishu_sync_log_model.py` | 模型字段测试 | ✓ VERIFIED | 本地 `db_session` fixture（StaticPool in-memory），3 个测试全 PASS |
| `backend/tests/test_services/test_import_leading_zero.py` | 模板+sanity check 测试 | ✓ VERIFIED | 本地 fixture，8 个测试函数（parametrize 展开 14 项）全 PASS |
| `backend/tests/test_services/test_feishu_leading_zero.py` | _map_fields / fallback / validate 测试 | ✓ VERIFIED | 本地 fixture，12 个测试全 PASS（含 B-10 修复 4 场景 + validator 3 场景） |
| `backend/tests/test_api/test_feishu_config_validation.py` | API 422 集成测试 | ✓ VERIFIED | 本地 4 个 fixture（db_session/settings/admin_user/admin_client），4 个测试全 PASS |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `build_template_xlsx` | Excel 工号列文本格式 | openpyxl `cell.number_format='@'` | ✓ WIRED | 4 种类型模板运行时验证：A 列第 1/50/105 行均为 `'@'`；示例行值 `'02651'`（字符串） |
| `_dispatch_import` | failed_rows with 格式异常 message | 正则 `^\d+\.0$` 检测 + bool mask 过滤 | ✓ WIRED | 测试 `test_dispatch_import_flags_leading_zero_lost_rows` 构造 `{'employee_no': '1234.0'}` 行 → 返回含 row_index=2, status='failed', message 含「格式异常（疑似丢失前导零）」的 dict；合法 `'02651'` 行不被误标 |
| `_map_fields` | employee_no text-only | 删除 str(int(value)) + logger.warning | ✓ WIRED | 运行时验证：float 2615.0 → `'2615.0'` + warning 触发；str '02615' → '02615' + 无 warning |
| `_lookup_employee fallback` | fallback_counter['count'] += 1 | `for map_key, map_id in emp_map.items(): if (map_key.lstrip('0') or '0') == stripped_key` | ✓ WIRED | 场景 A/D PASS（计数+1）、场景 B/C PASS（计数 0）、miss PASS（返回 None 不改变 counter） |
| sync_* 方法 | `sync_log.leading_zero_fallback_count` 落库 | `fallback_counter: dict[str, int] = {'count': 0}` + `sync_log.leading_zero_fallback_count = fallback_counter['count']` | ✓ WIRED | `sync_attendance` success/failure 两路径均写 `sync_log.leading_zero_fallback_count`；其余 4 个 sync 方法（不创建 FeishuSyncLog）在返回 dict 中加入 `'leading_zero_fallback_count': fallback_counter['count']`。grep ≥ 10 次命中 |
| `FeishuService.validate_field_mapping` | `list_bitable_fields` → 类型校验 | HTTP GET bitable fields + type=1 白名单匹配 | ✓ WIRED | Mock httpx 返回 type=1 → PASS；返回 type=2 → 抛 `{'error':'invalid_field_type','field':'employee_no','expected':'text','actual':'number'}`；field_name 不存在 → 抛 `field_not_found_in_bitable` |
| `create_config` / `update_config` | `_validate_field_mapping_with_credentials` | 实例化 FeishuConfig 之前调用（保存前阻断） | ✓ WIRED | create_config 在 `config = FeishuConfig(...)` 之前调 validator；update_config 在 `needs_validation = data.field_mapping \|\| data.bitable_*` 时计算 effective 参数后调 validator |
| `api/v1/feishu.py create/update_config` | 422 + dict body | `except FeishuConfigValidationError → raise HTTPException(422, detail=exc.detail) from exc` | ✓ WIRED | `test_create_config_rejects_invalid_field_type_with_422` / `test_update_config_rejects_invalid_field_type_with_422` 断言 status_code==422 + payload 结构严格匹配 |
| `_sync_log_to_read` | SyncLogRead.leading_zero_fallback_count | `leading_zero_fallback_count=log.leading_zero_fallback_count` 映射 | ✓ WIRED | `test_sync_logs_response_includes_leading_zero_fallback_count` 种入 `FeishuSyncLog(leading_zero_fallback_count=7)` → GET `/api/v1/feishu/sync-logs` 返回 entry 含 `leading_zero_fallback_count==7` |
| `FeishuConfig.tsx handleSave catch` | invalid_field_type 中文文案 | `axios.isAxiosError + status===422 + detail.error='invalid_field_type'` | ✓ WIRED | setErrorMessage 调用字面包含「工号字段类型必须为文本（当前为 ${actual}）...」；setErrors.field_mapping 同步标红 |
| `SyncStatusCard.tsx` | `leading_zero_fallback_count > 0` 黄色提示 | Conditional JSX `<p>` with `color: var(--color-warning)` | ✓ WIRED | JSX 渲染字面包含「条记录通过前导零容忍匹配成功，建议排查飞书源数据格式」 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `SyncStatusCard.tsx` | `syncStatus.leading_zero_fallback_count` | `getLatestSyncStatus` / `/api/v1/feishu/sync-logs` | 是（DB `FeishuSyncLog.leading_zero_fallback_count` 字段 → `_sync_log_to_read` 映射 → SyncLogRead 序列化 → Axios → state） | ✓ FLOWING |
| `FeishuConfig.tsx handleSave error branch` | `err.response.data.detail` | POST/PUT `/api/v1/feishu/config` 422 响应 | 是（`FeishuConfigValidationError.detail` → HTTPException detail=dict → main.py handler content=dict → axios response.data） | ✓ FLOWING |
| ImportService 模板 xlsx | openpyxl Workbook | `build_template_xlsx` 生成 BytesIO | 是（运行时 4 种类型模板均产出 >5000 字节合法 xlsx，openpyxl 可读回） | ✓ FLOWING |
| ImportService sanity check failed_rows | `bad_rows` dict from DataFrame | `pd.read_excel(dtype=str)` → `_normalize_columns` → `_detect_leading_zero_loss_rows` | 是（测试构造 '1234.0' → 被识别并写入 failed_rows；合法 '02651' 不被误标） | ✓ FLOWING |
| FeishuSyncLog.leading_zero_fallback_count（sync_attendance） | `fallback_counter['count']` 累加 | `_lookup_employee` fallback 分支命中 | 是（单元测试场景 A/D 证明计数器确实被 +1；sync_attendance 落库路径代码串通） | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Alembic 迁移可应用 | `python -m alembic upgrade head` | `Running upgrade a26_01_feishu_open_id -> 30_01_leading_zero_fallback` 成功；`PRAGMA table_info` 返回 `(15, 'leading_zero_fallback_count', 'INTEGER', 1, "'0'", 0)` | ✓ PASS |
| Phase 30 测试集 | `pytest test_feishu_sync_log_model.py test_import_leading_zero.py test_feishu_leading_zero.py test_feishu_config_validation.py -v` | `33 passed in 3.68s` | ✓ PASS |
| 回归测试（既有 feishu + import 测试集） | `pytest test_feishu_config.py test_feishu_service.py test_import_service.py test_import_xlsx.py test_import_idempotency.py test_import_partial_success.py test_import_certification.py` | `28 passed, 11 xfailed`（xfail 为 Phase 30 之前留下的 RED stub，与本 phase 无关） | ✓ PASS |
| 前端 tsc --noEmit | `cd frontend && npm run lint` | 退出 0，无 type error | ✓ PASS |
| 模板生成行为 | 运行时对 4 种 import_type 调用 `build_template_xlsx` → openpyxl 读回 | header='员工工号' / example='02651' / row1/row50/row105 cell.number_format='@' 全部通过 | ✓ PASS |
| `_map_fields` 行为 | 运行时 float 2615.0 + str '02615' 两输入对比 | float → '2615.0' + warning；str → '02615' + 无 warning | ✓ PASS |
| `_lookup_employee` 场景 A/B | 运行时 DB={'02615':'uuid-1'}、查询 '2615' vs '02615' | A: counter=1 + 命中；B: counter=0 + 命中 | ✓ PASS |
| `EmployeeBase.employee_no` 拒绝 int | Pydantic `EmployeeBase(employee_no=1234, ...)` | 抛 `ValidationError: employee_no: Input should be a valid string [type=string_type, input_value=1234, input_type=int]` | ✓ PASS |
| `EmployeeBase.employee_no` 接受带前导零 str | `EmployeeBase(employee_no='01234', ...)` | 成功，`e.employee_no == '01234'` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EMPNO-01 | 30-02 | Excel 导入模板使用 openpyxl `cell.number_format = '@'` 文本格式 | ✓ SATISFIED | 4 种模板 1-105 行工号列 cell.number_format=='@'；employees manager_employee_no 列同；certifications 认证类型/阶段列同；示例行 '02651'。14 测试 PASS |
| EMPNO-02 | 30-02, 30-03 | Excel 读取端 + 手动录入端 + 飞书同步端三链路统一按字符串读入 | ✓ SATISFIED | Excel: `pd.read_excel(dtype=str)` + sanity check 正则 `^\d+\.0$` 拦截 `'1234.0'`；手动录入: `EmployeeBase.employee_no: str` Pydantic 拒绝 int/float；飞书: `_map_fields` 删除 `str(int(value))` + warning |
| EMPNO-03 | 30-03, 30-04 | 飞书多维表格绑定配置页校验 `employee_no` 字段类型必须为 text；非 text 类型阻止保存 | ✓ SATISFIED | `validate_field_mapping` + `_validate_field_mapping_with_credentials` 实现；create/update_config 保存前调用；非 text 抛结构化 `FeishuConfigValidationError`；API 层映射 422；前端中文文案展示。Mock 端到端 PASS。**真实飞书多维表格端的人工冒烟保留** |
| EMPNO-04 | 30-01, 30-03, 30-04 | 存量数据保持现状；`_build_employee_map` 保留 leading-zero 容忍匹配并加 metrics 告警 | ✓ SATISFIED | `_build_employee_map` 真实视图（取消 stripped 预填充 B-10 修复）；`_lookup_employee` fallback 实现容忍匹配 + 计数器；FeishuSyncLog 新增 `leading_zero_fallback_count` 字段 + Alembic 迁移；`sync_attendance` 落库、其余 4 个 sync 方法返回 dict 曝光；API / schema / UI 全链路透传；黄色诊断提示 |

**Orphan check:** REQUIREMENTS.md 将 EMPNO-01/02/03/04 全部映射到 Phase 30；plans 的 `requirements_addressed` 合计覆盖 EMPNO-01/02/03/04。无遗漏。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | 无 TODO/FIXME/placeholder 新增 | — | Phase 30 新增代码无空实现、无 hardcoded 空数据、无 `return null` 替代实现 |

备注：
- `_lookup_employee` 在完全 miss 时 `return None` 是合法空状态（无匹配），非 stub
- 前端 `setErrorMessage('保存失败')` 是兜底，真实错误码路径已覆盖 invalid_field_type / field_not_found_in_bitable / bitable_fields_fetch_failed
- 自动化测试代码中出现的空 dict / `{}` 全部为初始状态（后续被断言覆盖），非 stub

### Human Verification Required

自动化覆盖已足够验证代码契约。以下 3 项需要人工在真实环境验证完整端到端体验：

#### 1. Excel 桌面软件实际保存-重开前导零

**Test:**
1. 后端启动，登录 HR 账号
2. 进入「批量导入」页面，点击「下载模板」（任选一种 import_type，如 employees）
3. 用 Excel（或 WPS / LibreOffice Calc）打开下载的 .xlsx
4. 在「员工工号」列的第 3 行（第一个空行）录入 `01234`，然后 Ctrl+S 保存
5. 关闭并重新打开该 xlsx

**Expected:** 第 3 行 A 列显示 `01234`（含前导零），不被转换为 `1234`

**Why human:** Excel.exe / 其他 Office 软件的单元格格式处理是桌面软件行为，无法通过自动化断言（`cell.number_format=='@'` 已在代码层自动化断言通过，但用户可见行为依赖 Office 实际遵守该约束）

#### 2. 真实飞书多维表格「数字」类型字段触发 422

**Test:**
1. 在飞书多维表格中创建一个 bitable，把其中一个字段显式设为「数字」类型
2. 后端启动，登录 admin，进入 FeishuConfig 页面
3. 填入 app_id / app_secret / app_token / table_id，将 `employee_no` 映射到该「数字」字段
4. 点击「保存配置」

**Expected:**
- 页面顶部红色错误文案：「工号字段类型必须为文本（当前为 number），请在飞书多维表格中将该字段改为「文本」类型后重试」
- 字段映射区域的 field_mapping 行被标红
- HTTP 请求返回 422，response.data.detail 结构为 `{error: 'invalid_field_type', field: 'employee_no', expected: 'text', actual: 'number'}`
- 数据库 feishu_configs 表无新行（配置未持久化）

**Why human:** 需要真实飞书多维表格 API（含租户 tenant_access_token + 合法的 app_token/table_id）才能验证 `list_bitable_fields` 返回的 type 字段 schema；自动化已用 mock httpx 验证路由器与前端契约，真实 SaaS 响应结构需人工冒烟

#### 3. 真实飞书同步触发 leading_zero_fallback_count > 0 黄色提示

**Test:**
1. 在 DB 种入员工 `employee_no='02615'`
2. 在飞书多维表格中插入一行数据，工号字段录入 `2615`（缺失前导零）
3. 保存飞书配置（employee_no 映射到飞书的文本字段）
4. 触发一次同步（手动或定时）
5. 等同步完成，进入飞书同步管理页面观察 SyncStatusCard

**Expected:**
- 卡片出现黄色文字：「1 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式」
- 顶层 status 保持 success / partial（不因 fallback 命中而降级为 failed）
- `GET /api/v1/feishu/sync-logs?limit=10` 返回最新 log 的 `leading_zero_fallback_count==1`

**Why human:** 需要真实飞书同步链路产生容忍匹配才能触发 > 0 场景；自动化已在单元测试中直接用 `_lookup_employee(fallback_counter=...)` 验证计数器语义、在 API 测试中验证 `/sync-logs` 返回该字段，但真实数据流端到端观察只能人工测试

### Gaps Summary

**无 gaps。** Phase 30 的 4 条 ROADMAP Success Criteria 与 4 条 Requirement (EMPNO-01..04) 在代码层面全部落地：

- 模板 & 读入端双端闭合（EMPNO-01 / EMPNO-02）— 14 项测试 PASS
- 飞书 `_map_fields` 去 int 误用 + B-10 根因修复（取消 stripped 预填充）+ 计数器语义修复（EMPNO-02 / EMPNO-04）— 12 项测试 PASS
- 配置保存前字段类型校验 + API 422 映射 + 前端错误展示（EMPNO-03）— 4 项 API 测试 + 验证器单元测试 PASS
- Alembic 迁移 + SyncLogRead 前后端 schema 透传 + SyncStatusCard 黄色提示（EMPNO-04）— 3 项模型测试 + API 透传测试 PASS

手动录入路径的 Pydantic `EmployeeBase.employee_no: str` 约束由 CONTEXT.md § Claude's Discretion 第一条明确认定为「现状足够」，运行时验证确认拒绝 int 输入、接受 `'01234'` 保留前导零。

**注意事项：**
- 本地 `wage_adjust.db` 在验证时尚未升级到新 head（停在 `a26_01_feishu_open_id`）；运行 `alembic upgrade head` 成功应用迁移，`leading_zero_fallback_count` 列正确落地。应用启动时 `init_database` 会自动创建含该字段的表结构，不阻塞运行
- 3 项人工验证保留原因是：真实 Excel 桌面软件 / 真实飞书 SaaS / 真实同步链路的端到端体验需要人类操作，自动化已在代码契约层面全部覆盖

---

_Verified: 2026-04-21T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
