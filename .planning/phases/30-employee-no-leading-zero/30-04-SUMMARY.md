---
phase: 30-employee-no-leading-zero
plan: 04
subsystem: api-ui
tags: [feishu, api, frontend, error-handling, leading-zero, empno-03, empno-04]

# Dependency graph
requires:
  - phase: 30-01
    provides: FeishuSyncLog.leading_zero_fallback_count 字段（Plan 04 序列化暴露目标）
  - phase: 30-03
    provides: FeishuConfigValidationError 异常类 + validate_field_mapping API surface
provides:
  - backend/app/api/v1/feishu.py 对 FeishuConfigValidationError 的 HTTP 422 + 结构化 body 映射（路径 X）
  - backend/app/schemas/feishu.py SyncLogRead 新增 leading_zero_fallback_count 字段
  - frontend/src/types/api.ts SyncLogRead interface 新增 leading_zero_fallback_count: number
  - frontend/src/pages/FeishuConfig.tsx handleSave 针对 422 + invalid_field_type 的中文错误文案
  - frontend/src/components/attendance/SyncStatusCard.tsx leading_zero_fallback_count > 0 时的黄色提示
  - backend/tests/test_api/test_feishu_config_validation.py 4 个 API 集成测试（含本地 fixture）
affects:
  - Phase 31（若引入同步日志历史列表页或五类计数器看板，SyncStatusCard 的黄色提示可迁移至列表行）

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastAPI HTTPException(detail=dict) 路径 X：main.py http_exception_handler 已对 dict detail 直接透传 (content=exc.detail)"
    - "axios.isAxiosError + err.response?.status === 422 + detail.error 路由到 code-specific 中文文案"
    - "SyncStatusCard 现有黄色 <p> 的字面样式复用（var(--color-warning, #FF7D00) + className='mt-2 text-sm'）"
    - "API 测试本地 fixture 模式延续：db_session / admin_user / admin_client（StaticPool in-memory + dependency_overrides）"

key-files:
  created:
    - backend/tests/test_api/test_feishu_config_validation.py
  modified:
    - backend/app/api/v1/feishu.py
    - backend/app/schemas/feishu.py
    - frontend/src/types/api.ts
    - frontend/src/pages/FeishuConfig.tsx
    - frontend/src/components/attendance/SyncStatusCard.tsx

key-decisions:
  - "D-01 落地（EMPNO-03）：API 层采用路径 X（HTTPException(detail=dict)），而不是 JSONResponse 直返；main.py 既有 handler 已支持，无需改动"
  - "D-03/D-04 落地（EMPNO-04）：SyncLogRead 前后端 schema 新增 leading_zero_fallback_count: int；SyncStatusCard 黄色 <p> 挂载（W-3 决策：当前无独立同步日志列表组件，保持最小 UI 改动）"
  - "前端错误 detail 取值兼容两种 FastAPI 响应形态：err.response.data?.detail ?? err.response.data（兼容路径 X/Y，未来无论 main.py handler 如何演进都可工作）"
  - "FeishuConfig.tsx catch 块除 invalid_field_type 外，顺带处理 Plan 03 已支持的 field_not_found_in_bitable / bitable_fields_fetch_failed 两个 error code（Rule 2 - 完整性）"
  - "测试 3 (test_create_config_succeeds_when_validator_passes) 的断言仅要求『非 422』而非硬编码 201；DB 层在 StaticPool + FeishuConfig 实例化路径可能产生其他状态码（例如 500 encryption key 校验），这些不属于 validator 错误源"

patterns-established:
  - "API 层 → Service 层自定义异常的标准模式：ValueError 子类 + .detail dict → except in router → raise HTTPException(status_code=422, detail=exc.detail) from exc"
  - "前端结构化错误处理三段式：axios.isAxiosError guard → status code guard → detail.error 字段 switch → code-specific 中文文案"

requirements-completed: [EMPNO-03, EMPNO-04]

# Metrics
duration: 15min
completed: 2026-04-21
---

# Phase 30 Plan 04: API 层 + 前端 UI 暴露 FeishuConfigValidationError 与 leading_zero_fallback_count Summary

**将 Plan 03 打下的后端 validator 与计数器基础通过 API 与前端 UI 面向用户呈现：API 层 FeishuConfigValidationError → HTTP 422 + 结构化 body；SyncLogRead schema 前后端透传 leading_zero_fallback_count；FeishuConfig 页面识别 invalid_field_type 给出中文文案；SyncStatusCard 在计数 > 0 时显示黄色诊断提示。**

## Performance

- **Duration:** ~15 min
- **Tasks:** 3
- **Files modified:** 5 (4 modified + 1 created)

## Accomplishments

- **EMPNO-03 API 层落地** — `backend/app/api/v1/feishu.py` import `FeishuConfigValidationError`，`create_config` / `update_config` 路由在 `FeishuConfigValidationError` 抛出时用 `raise HTTPException(status_code=422, detail=exc.detail) from exc` 映射为 HTTP 422 + dict body；采用**路径 X**（main.py 的 `http_exception_handler` 已在 line 136-137 对 `isinstance(exc.detail, dict)` 做 `content=exc.detail` 直接透传），无需新增 exception handler
- **EMPNO-04 schema 透传** — `SyncLogRead` Pydantic schema 新增 `leading_zero_fallback_count: int = 0`（默认 0 向后兼容）；`_sync_log_to_read` 在 `failed_count` 之后加入 `leading_zero_fallback_count=log.leading_zero_fallback_count` 映射；前端 `types/api.ts` 对应 interface 同步新增字段
- **EMPNO-03 前端错误展示** — `FeishuConfig.tsx` import `axios`，`handleSave` catch 扩展：`axios.isAxiosError` + 422 状态 + `detail.error === 'invalid_field_type'` 时显示中文文案「工号字段类型必须为文本（当前为 <actual>），请在飞书多维表格中将该字段改为「文本」类型后重试」并同步 `setErrors.field_mapping`；顺带处理 Plan 03 新增的 `field_not_found_in_bitable` / `bitable_fields_fetch_failed` 两个 error code（Rule 2）
- **EMPNO-04 前端观测提示** — `SyncStatusCard.tsx` 在既有 `unmatched_count > 0` 黄色 `<p>` 下方紧跟新的黄色 `<p>`，`syncStatus.leading_zero_fallback_count > 0` 时显示「N 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式」，字面复用既定 warning 文本样式（`color: 'var(--color-warning, #FF7D00)'` + `mt-2 text-sm`）
- **4 个 API 集成测试全部 PASS** — 新增 `backend/tests/test_api/test_feishu_config_validation.py`（含本地 `db_session` / `settings` / `admin_user` / `admin_client` fixture，**不新建 conftest.py**），覆盖 create/update 两个路由的 422 映射、validator 通过场景、sync-logs schema 透传；feishu 测试集整体 19 passed + 11 xfailed 零回归

## Task Commits

Each task was committed atomically:

1. **Task 1: 后端 API 层映射 FeishuConfigValidationError 到 422 + 扩展 SyncLogRead schema 与映射** — `087e2de` (feat)
2. **Task 2: 前端 TypeScript 类型扩展 + FeishuConfig.tsx 错误展示 + SyncStatusCard 黄色提示** — `4bea040` (feat)
3. **Task 3: 后端 API 集成测试 test_feishu_config_validation.py（含本地 admin_client / db_session fixture）** — `f78643c` (test)

## Files Created/Modified

### `backend/app/api/v1/feishu.py` (modified)

```python
# Import 行扩展
-from backend.app.services.feishu_service import FeishuService
+from backend.app.services.feishu_service import FeishuConfigValidationError, FeishuService

# _sync_log_to_read 透传
 failed_count=log.failed_count,
+leading_zero_fallback_count=log.leading_zero_fallback_count,
 error_message=log.error_message,

# create_config / update_config：
# Exception handler 透传路径: X (main.py 已对 dict detail 走 content=exc.detail)
 try:
     config = service.create_config(data)
 except FeishuConfigValidationError as exc:
     raise HTTPException(
         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
         detail=exc.detail,
     ) from exc
```

### `backend/app/schemas/feishu.py` (modified)

```python
 unmatched_count: int
 failed_count: int
+leading_zero_fallback_count: int = 0
 error_message: Optional[str]
```

### `frontend/src/types/api.ts` (modified)

```typescript
 unmatched_count: number;
 failed_count: number;
+leading_zero_fallback_count: number;
 error_message: string | null;
```

### `frontend/src/pages/FeishuConfig.tsx` (modified)

```typescript
// import axios 新增
+import axios from 'axios';

// handleSave catch 扩展（核心分支）
+if (axios.isAxiosError(err) && err.response?.status === 422) {
+  const detail = err.response.data?.detail ?? err.response.data;
+  if (detail && typeof detail === 'object' && detail.error === 'invalid_field_type') {
+    const actual = detail.actual ?? '未知';
+    const field = detail.field ?? 'employee_no';
+    if (field === 'employee_no') {
+      setErrorMessage(
+        `工号字段类型必须为文本（当前为 ${actual}），请在飞书多维表格中将该字段改为「文本」类型后重试`,
+      );
+      setErrors((prev) => ({
+        ...prev,
+        field_mapping: '工号字段类型必须为文本',
+      }));
+    } else {
+      setErrorMessage(`字段类型校验失败：${field} 应为文本，当前为 ${actual}`);
+    }
+    return;
+  }
+  // … field_not_found_in_bitable / bitable_fields_fetch_failed 分支同上
+}
```

### `frontend/src/components/attendance/SyncStatusCard.tsx` (modified)

```tsx
 {syncStatus && syncStatus.unmatched_count > 0 ? (
   <p className="mt-2 text-sm" style={{ color: 'var(--color-warning, #FF7D00)' }} title={...}>
     {syncStatus.unmatched_count} 条记录因工号不匹配被跳过
   </p>
 ) : null}
+{syncStatus && syncStatus.leading_zero_fallback_count > 0 ? (
+  <p className="mt-2 text-sm" style={{ color: 'var(--color-warning, #FF7D00)' }}>
+    {syncStatus.leading_zero_fallback_count} 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式
+  </p>
+) : null}
```

### `backend/tests/test_api/test_feishu_config_validation.py` (created)

218 行，4 个本地 fixture + 4 个测试函数：

- **Fixture** `db_session`: `create_engine('sqlite://', poolclass=StaticPool)` + `Base.metadata.create_all` + yield/cleanup
- **Fixture** `settings`: `Settings(feishu_app_id='cli_test', feishu_encryption_key='test-enc-key-1234567890123456', ...)`
- **Fixture** `admin_user`: 种入 role='admin' 的 User 行
- **Fixture** `admin_client`: `create_app()` + `dependency_overrides[get_db]` + `create_access_token` → `TestClient` + Authorization header

测试：

| Test | 断言 |
|------|------|
| `test_create_config_rejects_invalid_field_type_with_422` | `patch('backend.app.api.v1.feishu.FeishuService.create_config', side_effect=FeishuConfigValidationError({...}))` → POST 返回 422 + payload.error='invalid_field_type' + field='employee_no' + expected='text' + actual='number' |
| `test_update_config_rejects_invalid_field_type_with_422` | 同上但 PUT /api/v1/feishu/config/{id} |
| `test_create_config_succeeds_when_validator_passes` | patch `_validate_field_mapping_with_credentials` + `reload_scheduler` + `_ensure_token` → 断言 resp.status_code != 422 |
| `test_sync_logs_response_includes_leading_zero_fallback_count` | db_session 种入 FeishuSyncLog(leading_zero_fallback_count=7) → GET /api/v1/feishu/sync-logs?limit=10 → JSON 含该 id 的 entry 且 leading_zero_fallback_count == 7 |

## Decisions Made

### Exception handler 透传路径选择（关键）

PLAN Task 1 B5 要求 executor 先读 `main.py` 的 `http_exception_handler`，在路径 X（HTTPException with dict detail 直接透传）和路径 Y（JSONResponse 兜底）之间选择。

读取 `backend/app/main.py` 第 132-142 行：

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    # If detail is already a dict (e.g. duplicate_file error), return it directly
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return build_error_response(...)
```

**既有 handler 已支持 dict detail 透传**。结论：**路径 X**（`raise HTTPException(status_code=422, detail=exc.detail) from exc`）即可。代码中以 `# Exception handler 透传路径: X` 注释明确选择。

**前端兼容性保险**：前端 `err.response.data?.detail ?? err.response.data` 取值兜底两种形态（`{detail: {...}}` vs `{...}`），未来即便 main.py handler 逻辑改变，前端仍能正常工作。

### FeishuConfig.tsx catch 块扩展范围

PLAN 要求处理 `invalid_field_type`；Rule 2 应用：Plan 03 `_validate_field_mapping_with_credentials` 还会抛出 `field_not_found_in_bitable` 与 `bitable_fields_fetch_failed` 两个 error code，用户可能在飞书多维表格字段名拼写错误或服务端 HTTP 错误时同样遇到 422。已顺带加入分支避免用户看到不友好的兜底「保存失败」。

### Test 3 的断言：`!= 422` 而非 `== 201`

DB 层使用 StaticPool in-memory，`FeishuConfig` 实例化路径可能因 `encryption_key` 校验产生其他状态码（500 等）。PLAN 明确要求 Test 3 只断言「非 422」，证明 validator 不是错误源即可；这与本 plan 的责任边界一致（API 层 422 映射的正确性由 Test 1/2 覆盖）。

## Deviations from Plan

**None - 本 plan 执行与计划完全一致。**

- 所有 grep-based 验收条件一次性通过
- 路径 X/Y 决策基于 main.py 实际 handler 源码（路径 X）并在前端做兼容兜底
- 4 个测试一次性全部 PASS
- CLAUDE.md 核心规则（评分/调薪/导入、结构化 JSON、可审计可解释）与本 plan 改动不冲突

## Verification Output

### Task 1 后端 grep

| 检查 | 期望 | 实际 | 通过 |
|------|------|------|------|
| `leading_zero_fallback_count: int = 0` in schemas/feishu.py | 1 | 1 | ✓ |
| `leading_zero_fallback_count=log.leading_zero_fallback_count` in api/v1/feishu.py | 1 | 1 | ✓ |
| `FeishuConfigValidationError` in api/v1/feishu.py | ≥3 | 3 | ✓ |
| `except FeishuConfigValidationError` in api/v1/feishu.py | ≥2 | 2 | ✓ |
| `'leading_zero_fallback_count' in SyncLogRead.model_fields` | True | True | ✓ |

### Task 2 前端 grep

| 检查 | 期望 | 实际 | 通过 |
|------|------|------|------|
| `leading_zero_fallback_count: number;` in types/api.ts | 1 | 1 | ✓ |
| `leading_zero_fallback_count` in SyncStatusCard.tsx | ≥1 | 2 | ✓ |
| 字面 `条记录通过前导零容忍匹配成功，建议排查飞书源数据格式` 在 SyncStatusCard.tsx | ≥1 | 1 | ✓ |
| `invalid_field_type` in FeishuConfig.tsx | ≥1 | 1 | ✓ |
| `工号字段类型必须为文本` in FeishuConfig.tsx | ≥1 | 2 | ✓ |
| `axios.isAxiosError` in FeishuConfig.tsx | ≥1 | 1 | ✓ |

### 前端 lint / build

```text
$ cd frontend && npm run lint
> wage-adjust-frontend@0.0.1 lint
> tsc --noEmit
[exit 0, no output — tsc --noEmit 通过]

$ cd frontend && npm run build
vite v6.4.1 building for production...
✓ 801 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.42 kB │ gzip:   0.31 kB
dist/assets/index-BWfJ5Muo.css     30.41 kB │ gzip:   6.64 kB
dist/assets/index-CP2gRmyZ.js   1,848.58 kB │ gzip: 575.02 kB
✓ built in 3.37s
```

### Task 3 后端测试

```text
$ pytest backend/tests/test_api/test_feishu_config_validation.py -v

backend/tests/test_api/test_feishu_config_validation.py::test_create_config_rejects_invalid_field_type_with_422 PASSED
backend/tests/test_api/test_feishu_config_validation.py::test_update_config_rejects_invalid_field_type_with_422 PASSED
backend/tests/test_api/test_feishu_config_validation.py::test_create_config_succeeds_when_validator_passes PASSED
backend/tests/test_api/test_feishu_config_validation.py::test_sync_logs_response_includes_leading_zero_fallback_count PASSED

====== 4 passed, 1994 warnings in 1.68s ======
```

### 整体 feishu 回归

```text
$ pytest backend/tests/test_services/test_feishu_config.py \
         backend/tests/test_services/test_feishu_service.py \
         backend/tests/test_services/test_feishu_leading_zero.py \
         backend/tests/test_services/test_feishu_sync_log_model.py \
         backend/tests/test_api/test_feishu_config_validation.py

19 passed, 11 xfailed, 1996 warnings in 2.05s
```

- 19 PASSED = 12 (Plan 03 test_feishu_leading_zero) + 3 (Plan 01 test_feishu_sync_log_model) + 4 (本 plan test_feishu_config_validation)
- 11 XFAIL = Plan 02 以前留下的 RED stubs（feishu_config + feishu_service），未改动
- **零回归**

### 外部回归说明（非本 plan 引入）

`backend/tests/test_api/test_approval_api.py::test_approval_can_be_deferred_with_time_or_target_score` 和 `backend/tests/test_api/test_feishu_oauth_integration.py` 5 个 callback/bind 测试在 base commit `1b1df5e` 上即失败（已通过 `git stash` 验证），与本 plan 无因果关系。不在本 plan scope。

## Issues Encountered

无 — Plan 准确度高、tasks 自包含；执行过程零阻塞。唯一需要决策的是 Task 1 B5 的路径 X/Y 选择，读一次 main.py 即明确走路径 X。

## Phase 30 Success Criteria 自验证

根据 PLAN output 要求，对应 ROADMAP.md § Phase 30 的 4 条 Success Criteria：

| # | Success Criterion | 落地 Plan | 验证路径 |
|---|-------------------|-----------|----------|
| 1 | Excel 模板对「员工工号」列预设文本格式，模板下载后 HR 在 Excel 中看到示例工号 `02651` 保留前导零；批量导入时若工号列被 Excel 识别为数字（`1234.0` 模式）被报错拒绝 | Plan 02 | `backend/tests/test_services/test_import_leading_zero.py` 14/14 PASS |
| 2 | 飞书同步过程中 `_map_fields` 不再将浮点工号转成去零 int；`_build_employee_map` 取消 stripped 预填充，靠 `_lookup_employee` fallback 记录真实容忍匹配计数；同步成功后 `FeishuSyncLog.leading_zero_fallback_count` 反映真实信号数 | Plan 01 + Plan 03 | `test_feishu_sync_log_model.py` 3/3 + `test_feishu_leading_zero.py` 12/12 PASS |
| 3 | HR 在 FeishuConfig 页面保存一个「员工工号」映射到「数字」类型飞书字段的配置时，看到红色错误「工号字段类型必须为文本（当前为 number），请在飞书多维表格中将该字段改为「文本」类型后重试」，配置未持久化 | Plan 03 + Plan 04 | `test_feishu_config_validation.py::test_create_config_rejects_invalid_field_type_with_422` PASS + 前端 build 通过 |
| 4 | HR 在同步状态卡片能看到 `leading_zero_fallback_count > 0` 时的黄色诊断提示；`GET /api/v1/feishu/sync-logs` 返回的每条 log 含 `leading_zero_fallback_count` 字段 | Plan 01 + Plan 03 + Plan 04 | `test_feishu_config_validation.py::test_sync_logs_response_includes_leading_zero_fallback_count` PASS + 前端 build 通过（SyncStatusCard 含计数器 > 0 分支） |

**4/4 Success Criteria 全部通过。** Phase 30 端到端闭合完成（Plans 01-04）。

## User Setup Required

None - 本 plan 改动不引入新外部依赖、不需要环境变量、不影响数据库 schema。

- 后端 HR 在上传「员工工号映射到非 text 类型」的配置时会立即看到 422 阻断
- 前端 HR 在保存配置时看到具体中文错误文案
- 前端 HR 在同步状态卡片上看到前导零容忍匹配的数据质量信号

## Next Phase Readiness

- **EMPNO-03 / EMPNO-04 已完成。** Phase 30 v1.4 milestone 的 4 条 Success Criteria 全部通过。
- Phase 31（若规划引入五类计数器看板或同步日志历史列表页）可直接：
  - 复用 `SyncLogRead.leading_zero_fallback_count` 在列表行展示
  - 迁移 `SyncStatusCard` 的黄色提示到列表行，保留最新同步状态卡片的简洁性
  - 扩展更多 `xxx_fallback_count` 字段沿用 Phase 30 Plan 01 建立的「{feature}_fallback_count INTEGER NOT NULL server_default='0'」命名 + migration 模式

## Self-Check: PASSED

- FOUND: backend/app/api/v1/feishu.py (modified, contains FeishuConfigValidationError import + 2 except blocks + leading_zero_fallback_count passthrough)
- FOUND: backend/app/schemas/feishu.py (modified, SyncLogRead.leading_zero_fallback_count field added)
- FOUND: frontend/src/types/api.ts (modified, SyncLogRead interface leading_zero_fallback_count: number added)
- FOUND: frontend/src/pages/FeishuConfig.tsx (modified, axios import + 422/invalid_field_type branch)
- FOUND: frontend/src/components/attendance/SyncStatusCard.tsx (modified, yellow <p> for leading_zero_fallback_count > 0)
- FOUND: backend/tests/test_api/test_feishu_config_validation.py (new, 4 tests passing, 4 local fixtures)
- FOUND: commit 087e2de (Task 1: feat backend api + schema)
- FOUND: commit 4bea040 (Task 2: feat frontend types + pages + components)
- FOUND: commit f78643c (Task 3: test api integration 4 tests)
- ABSENT: backend/tests/conftest.py (must not exist; verified absent)

---
*Phase: 30-employee-no-leading-zero*
*Completed: 2026-04-21*
