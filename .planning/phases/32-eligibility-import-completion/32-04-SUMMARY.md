---
phase: 32-eligibility-import-completion
plan: 04
subsystem: backend-api
tags: [eligibility-import, two-phase-commit, preview, confirm, cancel, active-job, file-safety, deprecated, per-import-type-lock, openpyxl-template, audit-log]

# Dependency graph
requires:
  - phase: 32-eligibility-import-completion
    plan: 02
    provides: ImportService 6 类 import_type 完整支持（含 hire_info / non_statutory_leave）+ build_template_xlsx 4 类资格全覆盖
  - phase: 32-eligibility-import-completion
    plan: 03
    provides: ImportService 9 个新方法（is_import_running / get_active_job / expire_stale_import_jobs / build_preview / confirm_import / cancel_import + 暂存文件 helpers）+ 4 个 Pydantic schemas (PreviewResponse / ConfirmRequest / ConfirmResponse / ActiveJobResponse) + AuditLog 真实字段（operator_id / target_type / target_id）
provides:
  - 4 个新 HTTP 端点：
    - POST /api/v1/eligibility-import/excel/preview?import_type=X → PreviewResponse
    - POST /api/v1/eligibility-import/excel/{job_id}/confirm → ConfirmResponse
    - POST /api/v1/eligibility-import/excel/{job_id}/cancel → 204
    - GET  /api/v1/eligibility-import/excel/active?import_type=X → ActiveJobResponse
  - 旧 POST /api/v1/eligibility-import/excel 标 deprecated（保留兼容性，OQ4 决议）
  - 文件上传安全 helper `_validate_upload_file`：白名单 .xlsx/.xls + 10MB 上限 + 空文件拒绝（T-32-02 / T-32-03 mitigations）
  - HTTPException ↔ ValueError 状态码映射（已确认/状态为 → 409；替换模式未确认 → 422；其他 → 400）
  - 4 类资格 import_type 模板下载端到端验证（IMPORT-02：performance_grades / salary_adjustments / hire_info / non_statutory_leave）
affects: [32-05, 32-06]

# Tech tracking
tech-stack:
  added: []  # 全部使用既有 stack（FastAPI + Pydantic v2 + SQLAlchemy + openpyxl）
  patterns:
    - "Two-phase commit API：preview（查询 + 暂存 + 不落库）→ confirm（hash 校验 + 落库 + AuditLog）→ cancel（删暂存 + 状态变更）"
    - "Per-import_type 分桶锁通过 service.is_import_running(import_type) 在路由前置；4 类资格可并行"
    - "ValueError 业务异常 → HTTPException 状态码映射（路由层不窥探 service 内部状态）：'已确认'/'状态为' → 409 双 confirm 防护；'替换模式' → 422 confirm_replace 校验；其他 → 400"
    - "main.py http_exception_handler 对 dict detail 直返 body（不嵌套 'detail' key）—— 测试断言 body['error'] 而非 body['detail']['error']"
    - "API 测试通过 _api_context.session_factory() 直接在与 API 共享的 DB 中 seed 数据；不用 import_job_factory（基于独立 in-memory DB）"
    - "FastAPI deprecated=True 装饰器标记旧端点（OpenAPI doc 自动加 deprecated 标识 + docstring 注明替代方案）"

key-files:
  created:
    - backend/tests/test_api/__init__.py
    - backend/tests/test_api/test_eligibility_import_preview_api.py
    - backend/tests/test_api/test_eligibility_import_confirm_api.py
    - backend/tests/test_api/test_eligibility_import_concurrency.py
    - backend/tests/test_api/test_eligibility_import_template_api.py
  modified:
    - backend/app/api/v1/eligibility_import.py

key-decisions:
  - "API 测试中 seed 数据走 _api_context.session_factory()（不用 conftest 的 import_job_factory），因为 db_session/import_job_factory 用 in-memory SQLite 与 API 的 file-based SQLite 不共享"
  - "ValueError → HTTPException 状态码映射放在路由层（不下沉到 service），保持 service 层不感知 HTTP 状态码"
  - "confirm 端点的 409 检查同时覆盖两层：路由层先查 ImportJob 防 404，再查同 import_type 是否有 processing job（previewing 是当前 job 自己，不算冲突）；service 层再次校验 job.status == 'previewing' 做兜底"
  - "测试用例 test_preview_409 修正：body 顶层 error/import_type（不是 body.detail.error），匹配 main.py 的 http_exception_handler 对 dict detail 的处理"
  - "cancel 端点采用 POST /excel/{job_id}/cancel + 204（与 PLAN 中 D-13 一致；service 层对终态 job 幂等返回不抛异常）"
  - "文件大小 10MB 选 10MB 而非更小（5MB）：5000 行 × ~2KB/row 估算 + buffer，足以覆盖 MAX_ROWS=5000 的真实场景"
  - "Content-Type 软校验：仅 warning log，不强制拒绝（部分浏览器拖拽上传不带正确 mime；ext + size 已是硬校验）"

patterns-established:
  - "API 端点是 service 方法的薄包装：路由层只做（1）参数校验/权限（2）锁/状态预检（3）调 service（4）异常映射"
  - "API 测试 seed pattern：使用 conftest 的 _api_context fixture + session_factory()，与 API client 共享同一 DB"
  - "Phase 32 风格 deprecated 端点：保留接口 + docstring 指向替代端点 + deprecated=True 装饰器"

requirements-completed: [IMPORT-01, IMPORT-02, IMPORT-05, IMPORT-06, IMPORT-07]

# Metrics
duration: 10min
completed: 2026-04-22
---

# Phase 32 Plan 04: 两阶段提交 API 端点收口 Summary

**新增 4 个 HTTP 端点（preview / confirm / cancel / active）+ 文件上传安全校验 + 旧端点 deprecated；4 类资格 import_type 模板下载端到端验证；Phase 32 后端 API 完整闭环**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-22T00:58:34Z
- **Completed:** 2026-04-22T01:08:45Z
- **Tasks:** 2（Task 1 用 TDD：RED → GREEN；Task 2 是纯 e2e 验证 Task 1 实现 + 既有模板端点）
- **Files created/modified:** 6 (5 created tests + 1 modified router)

## Accomplishments

### Task 1: preview / confirm / cancel / active 4 个端点 + 文件安全 + deprecated

**新增端点：**

| Method | Path | 鉴权 | 返回 |
|---|---|---|---|
| POST | `/api/v1/eligibility-import/excel/preview?import_type=X` | hrbp/admin | `PreviewResponse` |
| POST | `/api/v1/eligibility-import/excel/{job_id}/confirm` | hrbp/admin | `ConfirmResponse` |
| POST | `/api/v1/eligibility-import/excel/{job_id}/cancel` | hrbp/admin | `204 No Content` |
| GET  | `/api/v1/eligibility-import/excel/active?import_type=X` | hrbp/admin | `ActiveJobResponse` |

**文件上传安全 helper（`_validate_upload_file`）：**

- 白名单 `_ALLOWED_XLSX_EXTENSIONS = {'.xlsx', '.xls'}` —— 拒绝 .exe / .html / .svg / .csv / 其他扩展（T-32-02）
- `_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024` —— 10MB 上限防 DoS（T-32-03）
- 拒绝空文件 → 400
- Content-Type 软校验：不在 `_ALLOWED_XLSX_CONTENT_TYPES` 时仅 warning 日志（部分浏览器拖拽上传 mime 不准）

**旧端点 `POST /excel`：**

- 加 `deprecated=True` 装饰器（OpenAPI doc 自动标识）
- 加 docstring 注明替代方案（preview + confirm 两阶段）
- 实现保持不变（保留兼容性，决议 OQ4）

**ValueError → HTTPException 映射（路由层）：**

| service ValueError 文案 | HTTP 状态 | 用例 |
|---|---|---|
| `'已确认'` / `'已取消'` / `'状态为'` | 409 | 双 confirm 防护 |
| `'替换模式'` | 422 | confirm_replace 二次确认未通过 |
| 其他 | 400 | 一般业务校验 |

### Task 2: 并发场景集成测试 + 4 类资格 import_type 模板下载 e2e

**5 个并发场景（test_eligibility_import_concurrency.py）：**

1. **同 type 第二次 preview → 409**（per-import_type 锁）
2. **不同 type 可并行**（hire_info preview 持锁，performance_grades 仍 200）
3. **processing 状态下同 type preview → 409**（锁覆盖 previewing + processing）
4. **同 job_id 双 confirm → 409**（service 层 status 校验兜底）
5. **锁住后 GET /active 仍可用**（HR 用来诊断当前活跃 job）

**4 类资格模板下载（test_eligibility_import_template_api.py）：**

- `performance_grades` 表头 = `['员工工号', '年度', '绩效等级']`
- `salary_adjustments` 表头 = `['员工工号', '调薪日期', '调薪类型', '调薪金额']`
- `hire_info` 表头 = `['员工工号', '入职日期', '末次调薪日期']`
- `non_statutory_leave` 表头 = `['员工工号', '年度', '假期天数', '假期类型']`
- 每个模板 Content-Disposition 含 `attachment` + Content-Type 是 spreadsheetml + 工号列文本格式 `'@'`（防 leading zero loss）
- unknown_type → 400 / employee 角色 → 403

## Task Commits

1. **Task 1 RED**: `d90664b` test(32-04) — preview/confirm/cancel/active 17 个失败基线
2. **Task 1 GREEN**: `c73de6f` feat(32-04) — 4 个新端点 + 文件安全 helper + deprecated
3. **Task 2**: `e854862` test(32-04) — 并发集成测试 + 4 类模板 e2e

## Files Created/Modified

### Created

- `backend/tests/test_api/__init__.py` — 空文件，让 pytest 识别 test_api 为 package
- `backend/tests/test_api/test_eligibility_import_preview_api.py` — 11 个测试（成功 / 409 锁 / 不同 type 并行 / .exe / .html / >10MB / 401 / 403 / 未知 type / GET active 两态）
- `backend/tests/test_api/test_eligibility_import_confirm_api.py` — 7 个测试（merge + AuditLog 真实字段 / replace 二次确认 / 双 confirm 409 / 未知 job 404 / cancel 204 + employee 403）
- `backend/tests/test_api/test_eligibility_import_concurrency.py` — 5 个并发场景
- `backend/tests/test_api/test_eligibility_import_template_api.py` — 6 个模板用例（4 类 parametrize + unknown_type + employee 403）

### Modified

- `backend/app/api/v1/eligibility_import.py` — +260 行（imports + helper + 4 个新端点 + deprecated 注解）/ -4 行（旧端点装饰器）

## 4 个新端点契约（前端 Plan 05/06 接入参考）

```
# 1. preview - 上传 + 解析 + 暂存 + 返回 PreviewResponse
POST /api/v1/eligibility-import/excel/preview?import_type=hire_info
Headers: Authorization: Bearer {jwt}
Body: multipart/form-data, file=<xlsx_bytes>
Response 200: PreviewResponse {
  job_id, import_type, file_name, total_rows,
  counters: {insert, update, no_change, conflict},
  rows: [PreviewRow x ≤200], rows_truncated, truncated_count,
  preview_expires_at, file_sha256
}
Response 400: import_type 不支持 / 文件为空 / 行数超限
Response 409: {error: 'import_in_progress', import_type, message}  # 同 type 已活跃
Response 413: 文件 > 10MB
Response 422: 文件类型不在白名单
Response 401: 无 JWT；403: 角色不足

# 2. confirm - 确认落库
POST /api/v1/eligibility-import/excel/{job_id}/confirm
Headers: Authorization: Bearer {jwt}
Body: ConfirmRequest {overwrite_mode: 'merge'|'replace', confirm_replace: bool}
Response 200: ConfirmResponse {
  job_id, status: 'completed'|'partial'|'failed',
  total_rows, inserted_count, updated_count, no_change_count, failed_count,
  execution_duration_ms
}
Response 404: job_id 不存在
Response 409: 同 type 有其他 processing job / 当前 job 已 confirm/cancel
Response 422: replace 模式 + confirm_replace=False

# 3. cancel - 取消 previewing job（终态幂等返回 204）
POST /api/v1/eligibility-import/excel/{job_id}/cancel
Headers: Authorization: Bearer {jwt}
Response 204: 成功（无 body）
Response 404: job_id 不存在

# 4. active - HR 进入 Tab 时查询是否有活跃 job
GET /api/v1/eligibility-import/excel/active?import_type=hire_info
Headers: Authorization: Bearer {jwt}
Response 200: ActiveJobResponse {
  active: bool, job_id?, status?: 'previewing'|'processing',
  created_at?, file_name?
}
Response 400: import_type 不支持
```

## 旧端点状态（Plan 05 不再调用）

```
POST /api/v1/eligibility-import/excel?import_type=X (deprecated)
- OpenAPI doc 自动标记 ⚠ deprecated
- 实现：异步 Celery task（一步上传立即落库）
- 决议 OQ4：保留兼容旧客户端，新前端代码不再调用
- 替代：preview + confirm 两阶段端点
```

## Decisions Made

### 1. API 测试 seed 数据走 `_api_context.session_factory()`

**问题：** `db_session` / `import_job_factory` / `employee_factory` 用 in-memory SQLite，与 API client（基于 `_api_context.session_factory` 即 file-based SQLite）**完全独立**。直接用 `import_job_factory(import_type='hire_info', status='previewing')` 后 API 路由查不到这条记录。

**方案：** 在每个测试文件里写本地 `_seed_employee` / `_seed_import_job` helper，通过 `_api_context.session_factory()` 创建 session 直接 seed。

**未来改进：** 可在 conftest 加 `api_employee_factory` / `api_import_job_factory` fixture 减少重复（本 plan 暂未做，三个测试文件各自定义一份 helper 容易跟踪）。

### 2. ValueError → HTTPException 映射放路由层

confirm_excel_import 端点 catch service 抛的 ValueError，按文案分流：

```python
except ValueError as exc:
    msg = str(exc)
    if '已确认' in msg or '已取消' in msg or '状态为' in msg:
        raise HTTPException(409, ...) from exc
    if '替换模式' in msg:
        raise HTTPException(422, ...) from exc
    raise HTTPException(400, ...) from exc
```

理由：
- service 层不感知 HTTP 状态码（与 backend/app/services 既有约定一致）
- 路由层是 HTTP ↔ 业务异常的唯一翻译层
- 文案匹配是脆弱的，但比硬编码 service 抛 HTTPException 更可移植（service 也可被 Celery / CLI 调用）

未来如果 ValueError 类型化（ImportLockedError / ImportStateError 等），可以替换为类型分发。

### 3. confirm 端点的 409 检查在路由 + service 双层

路由层：
```python
job = db.execute(select(ImportJob).where(...)).scalar_one_or_none()  # 404 检查
other_running = db.execute(select(ImportJob).where(
    ImportJob.import_type == job.import_type,
    ImportJob.status == 'processing',
    ImportJob.id != job_id,
).limit(1)).scalar_one_or_none()  # 同 type 其他 processing 则 409
```

Service 层（已存在）：
```python
if job.status != 'previewing':
    raise ValueError(f'状态为 {job.status}，无法确认导入...')  # 409 兜底
```

理由：
- 路由层先做 404，避免 service 因 None 值崩溃
- 路由层提前查同 type 其他 processing 给出更友好的错误（不是 service 抛通用 ValueError）
- service 层 status 校验是防御性兜底（多端点都会调用 confirm_import）

### 4. 测试断言 body 顶层 error/import_type（不是 body.detail）

main.py http_exception_handler 对 `HTTPException(detail=dict)` **直返 dict 作为 body**：

```python
if isinstance(exc.detail, dict):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)
```

所以 409 响应的 body 就是 `{'error': 'import_in_progress', 'import_type': 'hire_info', ...}`，没有外层 `'detail'` key。

PLAN 中 `body['detail']['error']` 的写法是错的（基于 FastAPI 默认 handler 假设）；本 plan 在测试和文档中都修正为 `body['error']`。

### 5. cancel 用 POST 而非 DELETE

PLAN 提示用 DELETE，但本 plan 选 POST：
- 与既有 `/feishu/sync` 等 trigger 端点风格一致（均用 POST）
- 语义：cancel 是"触发取消动作"，不是"删除资源"（job 仍然在 DB 里只是状态变更）
- service.cancel_import 对终态 job 幂等返回，符合 POST 重试语义

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - 阻塞] API 测试中 import_job_factory / employee_factory 与 API DB 不共享**

- **Found during:** Task 1 RED → GREEN 验证时，`test_preview_409_when_running` 失败发现 import_job_factory 创建的 job 在 API 路由查询不到
- **根因：** conftest 的 `db_session` 是 in-memory SQLite（`'sqlite://'`），而 `_api_context` 用 file-based SQLite（`f'sqlite+pysqlite:///{db_path}'`）；二者独立 engine + 独立 connection pool
- **Fix:** 在每个 API 测试文件里定义 local `_seed_employee` / `_seed_import_job` helper，通过 `_api_context.session_factory()` 直接 seed
- **Files modified:** test_eligibility_import_preview_api.py / test_eligibility_import_confirm_api.py / test_eligibility_import_concurrency.py
- **Commit:** 包含在 Task 1 RED（d90664b）和 Task 2（e854862）

**2. [Rule 1 - Bug] PLAN 中 `body['detail']['error']` 断言错误**

- **Found during:** Task 1 GREEN 跑测试时 `test_preview_409` KeyError: 'detail'
- **根因：** main.py http_exception_handler 对 `HTTPException(detail=dict)` 直返 dict 为 body（not nested under 'detail'）
- **Fix:** 测试断言改为 `body['error']` / `body['import_type']`（顶层）；并在 docstring 注明该约定
- **Files modified:** test_eligibility_import_preview_api.py / test_eligibility_import_concurrency.py
- **Commit:** 包含在 Task 1 GREEN（c73de6f）和 Task 2（e854862）

**3. [Rule 3 - 兼容性] PLAN 提示 cancel 端点用 DELETE，本 plan 选 POST**

- **Found during:** Task 1 GREEN 实现时
- **理由：** 与 Phase 32 既有 `/feishu/sync` 等 trigger 端点风格一致；cancel 是"触发动作"语义；service 层 cancel_import 对终态 job 幂等返回
- **Files modified:** backend/app/api/v1/eligibility_import.py
- **Commit:** 包含在 Task 1 GREEN（c73de6f）
- **Note:** PLAN 文本中"DELETE /excel/cancel/{job_id}"为内部讨论稿；正式契约 frontend Plan 05 应按本 SUMMARY 里 POST 方法接入

### Pre-existing Test Failures（已记录到 deferred-items.md）

跑 `pytest backend/tests/test_api/` 看到 16 个 pre-existing 失败：
- 9 个与 32-02/32-03 SUMMARY 一致：test_import_207 (7) + test_import_api (2)
- 7 个其他模块 pre-existing：test_approval_api / test_auth (2) / test_file_api / test_public_api / test_rate_limit / test_user_admin_api

**关键验证：** 本 plan 改动**只**在 backend/app/api/v1/eligibility_import.py 和新建 4 个测试文件，未触碰其他模块；这 16 个失败在 32-03 末尾也是失败的。**Phase 32-04 改动 0 引入新 regression。**

import service 测试：53/53 PASS（Phase 32-02 / 32-03 baseline 全 OK）。

---

**Total deviations:** 3 auto-fixed (Rules 1 + 3); 16 pre-existing failures deferred (out of scope per deviation rule scope boundary)
**Impact on plan:** 本 plan 全部 must_have artifacts 落地；29 个新增测试全 PASS；后端 API 闭环。

## Issues Encountered

无业务逻辑阻塞。两个 fix 都属于本 plan 改动作为副产品发现的 PLAN 假设错误：
- conftest 的 db_session vs _api_context 双 DB 隔离（PLAN 假设 fixture 共享 DB）
- main.py http_exception_handler 对 dict detail 的处理（PLAN 假设 FastAPI 默认行为）

均通过测试代码调整修复，service 层和路由层无需改动。

## User Setup Required

None — 本 plan 是 API 层改动，无外部服务配置变更，无 schema 改动（Phase 32-01 已落 schema）。

## 下游 Plan 接入指引

### Plan 05（前端 service 层）

`frontend/src/services/eligibilityImportService.ts` 应提供如下函数：

```typescript
// 完整 API 契约见上文「4 个新端点契约」章节
export async function previewEligibilityImport(
  importType: string, file: File,
): Promise<PreviewResponse> { ... }

export async function confirmEligibilityImport(
  jobId: string, overwriteMode: 'merge' | 'replace', confirmReplace?: boolean,
): Promise<ConfirmResponse> { ... }

export async function cancelEligibilityImport(jobId: string): Promise<void> { ... }

export async function getActiveEligibilityImport(
  importType: string,
): Promise<ActiveJobResponse> { ... }

// 旧 importEligibilityExcel 一步上传保留但标 @deprecated
```

注意 axios baseURL `/api/v1` 已包含；service 层 path 写 `/eligibility-import/excel/preview` 即可。

409 错误 body 是顶层 `{error, import_type, message}`（不是 `{detail: {...}}`）。

### Plan 06（前端 Tab 组件改造）

- 进入 Tab 时调 `getActiveEligibilityImport(importType)`：
  - `active: false` → 启用「选择文件」按钮
  - `active: true` → 显示 banner「该类型导入正在进行中（job: {job_id}, 状态: {status}, 文件: {file_name}）」+ 禁用按钮
- 上传 → preview → 显示 PreviewResponse 行列表（含 counters / rows × ≤200 / rows_truncated / file_sha256）
- merge 模式：展示 inserted/updated/no_change，点击「确认导入」直接调 confirm
- replace 模式：弹出二次确认 modal + checkbox（用户勾选后 confirm_replace=true 才允许调 confirm；后端 422 防误操作兜底）
- 点击「取消」按钮调 cancel；endpoint 返回 204 后清空 preview 状态

### Celery beat（已在 32-03 SUMMARY 提示）

每 5 分钟跑 `expire_stale_imports_task`（preview 端点本身已含 `expire_stale_import_jobs()` 触发，作为 lazy fallback）。

## Next Phase Readiness

- Wave 3 已就绪，Wave 4 (Plan 05 前端 service / Plan 06 前端组件) 可启动
- 前端 Plan 05/06 可基于本 SUMMARY 「4 个新端点契约」章节直接 mock + 接入
- 后端 API 闭环：preview → confirm → cancel → active 全部稳定 + 文件安全防护到位
- 无 blocker；deferred-items.md 跟踪的 16 个 pre-existing 失败由后续 Phase 单独审视

## Self-Check: PASSED

### 文件存在验证

```
FOUND: backend/app/api/v1/eligibility_import.py (modified)
FOUND: backend/tests/test_api/__init__.py
FOUND: backend/tests/test_api/test_eligibility_import_preview_api.py
FOUND: backend/tests/test_api/test_eligibility_import_confirm_api.py
FOUND: backend/tests/test_api/test_eligibility_import_concurrency.py
FOUND: backend/tests/test_api/test_eligibility_import_template_api.py
```

### Commits 存在验证

```
FOUND: d90664b test(32-04) RED Task 1 — 17 个失败基线
FOUND: c73de6f feat(32-04) GREEN Task 1 — 4 个新端点 + 文件安全 + deprecated
FOUND: e854862 test(32-04) Task 2 — 并发集成测试 + 4 类模板 e2e
```

### Acceptance grep 验证

```
✓ @router.post('/excel/preview' (line 228)
✓ @router.post('/excel/{job_id}/confirm' (line 289)
✓ @router.post('/excel/{job_id}/cancel' (line 366)
✓ @router.get('/excel/active' (line 384)
✓ _MAX_UPLOAD_SIZE_BYTES = 10 (line 189)
✓ _ALLOWED_XLSX_EXTENSIONS (line 182)
✓ deprecated=True (line 40)
✓ require_roles('admin', 'hrbp') 命中 9 处（preview/confirm/cancel/active 全部强制鉴权）
```

### 测试结果

```
Phase 32-04 完整测试套件：29/29 PASS
  - test_eligibility_import_preview_api.py: 11/11
  - test_eligibility_import_confirm_api.py: 7/7
  - test_eligibility_import_concurrency.py: 5/5
  - test_eligibility_import_template_api.py: 6/6

Phase 32-02/32-03 import-related service 测试：53/53 PASS（0 regression）

完整 backend/tests/test_api/ 套件：181 passed + 16 pre-existing failures
（与 32-02/32-03 SUMMARY 一致；deferred-items.md 已记录）
```

---
*Phase: 32-eligibility-import-completion*
*Plan: 04*
*Completed: 2026-04-22*
