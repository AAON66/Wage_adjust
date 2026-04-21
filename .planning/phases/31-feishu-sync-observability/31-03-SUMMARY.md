---
phase: 31-feishu-sync-observability
plan: 03
subsystem: feishu-sync-observability
tags: [api-endpoints, csv-export, celery-key-migration, per-sync-type-lock, d08-unmatched-csv, d15-d16-409-semantics]
requires:
  - Phase 31 Plan 01 (sync_type + mapping_failed_count columns + SyncTypeLiteral)
  - Phase 31 Plan 02 (FeishuService._with_sync_log + is_sync_running(sync_type) + 5 sync methods returning FeishuSyncLog + triggered_by kwarg)
  - FastAPI Query parameter validation (Pydantic Literal boundary)
  - csv / io stdlib for CSV generation
provides:
  - GET /api/v1/feishu/sync-logs?sync_type=&page=&page_size= (paginated, filtered, admin+hrbp)
  - GET /api/v1/feishu/sync-logs/{log_id}/unmatched.csv (text/csv; charset=utf-8, first 20 rows, admin+hrbp)
  - POST /api/v1/feishu/sync per-sync_type 409 lock with detail.sync_type (D-16 — no log written on 409)
  - FeishuService.get_sync_logs(*, sync_type, page, page_size, limit) with backward-compat
  - feishu_sync_eligibility_task canonical 'performance' key + 'performance_grades' alias (TODO phase-32)
  - triggered_by=operator_id forwarded to all 4 Celery-routed sync methods
affects:
  - Plan 04 frontend (SyncLogsPage consumes paginated list + sync_type Tab + CSV download)
  - Ops upgrade checklist (drain Celery broker before removing 'performance_grades' alias in phase-32)
tech-stack:
  added: []
  patterns:
    - Pydantic Literal as Query param type for 422 boundary validation (no hand-written whitelist check)
    - Stdlib csv.writer + StringIO for small CSV export (20-row cap; no StreamingResponse needed)
    - canonical_sync_type normalization at Celery task entry (alias transparent to service layer)
    - Backward-compat helper signature: keyword-only `limit` shortcircuits page/page_size for polling callers
key-files:
  created:
    - backend/tests/test_services/test_feishu_get_sync_logs.py (5 tests)
    - backend/tests/test_api/test_feishu_sync_logs_api.py (11 tests)
    - backend/tests/test_api/test_feishu_unmatched_csv.py (13 tests)
    - backend/tests/test_services/test_feishu_expire_stale.py (2 tests)
    - backend/tests/test_tasks/__init__.py
    - backend/tests/test_tasks/test_feishu_sync_tasks_keys.py (7 tests)
  modified:
    - backend/app/services/feishu_service.py (get_sync_logs signature upgrade)
    - backend/app/api/v1/feishu.py (list route + CSV route + trigger_sync 409)
    - backend/app/tasks/feishu_sync_tasks.py (canonical sync_type + alias + triggered_by forwarded)
decisions:
  - D-05 / D-06 / API Query params: sync_type (SyncTypeLiteral optional), page (int ge=1), page_size (int ge=1 le=100); defaults page=1 page_size=20; started_at desc sort
  - D-08 / CSV endpoint: single-column 'employee_no' header + first 20 unmatched; text/csv; charset=utf-8; Content-Disposition filename=sync-log-{log_id}-unmatched.csv; admin+hrbp only
  - D-15 / D-16 / trigger_sync 409: is_sync_running(sync_type='attendance') bucket lock; 409 detail includes sync_type; on 409 no FeishuSyncLog is written (avoids 'rejected' row noise)
  - D-17 / expire_stale_running_logs: called before lock check to clean all 5 sync_type stale logs uniformly
  - Pitfall C / H / Celery alias: 'performance' is canonical; 'performance_grades' is kept as sync_methods dict alias for one release (TODO phase-32 remove); canonical_sync_type normalization for Celery state/meta/payload; FeishuSyncLog.sync_type always written as canonical form by service layer
  - Backward-compat limit: get_sync_logs(limit=N) shortcircuits pagination — AttendanceManagement polling continues to work; Plan 04 may later migrate frontend to page/page_size
  - 0 hand-written whitelist check in API: Pydantic Literal validation at Query parameter level returns 422 automatically; service layer accepts any string (matches D-15 is_sync_running semantics)
  - CSV defense-in-depth: no leading `'` for CSV Injection defense added this phase (employee_no sourced from Feishu/DB, not direct user input); accepted per T-31-16 threat model disposition
  - Celery result payload shape: changed from legacy `{synced, skipped, failed}` dict to FeishuSyncLog-sourced `{sync_log_id, sync_type, status, synced, updated, unmatched, mapping_failed, failed, total, leading_zero_fallback_count}` — reflects Plan 02 return-type contract change
  - [执行阶段新决策] Did NOT re-introduce `limit` as API Query param: Pydantic Query(default=20) for page_size gives identical semantics for no-arg callers; keeps API surface minimal
  - [执行阶段新决策] CSV endpoint uses `db.get(FeishuSyncLog, log_id)` (primary-key lookup) not a query — simpler 404 handling and ORM-level parameterization prevents SQL injection (T-31-13)
metrics:
  duration: ~7m 30s
  completed: 2026-04-21T06:04:53Z
  tasks_executed: 2
  commits: 4
  tests_added: 38 (5 service get_sync_logs + 11 API list + 13 CSV/409 + 2 expire_stale + 7 Celery keys)
  tests_total_green: 115 (38 new + 77 Phase 30/31-01/31-02 regression)
---

# Phase 31 Plan 03: API + Celery Task 层就绪 Summary

**One-liner:** 把 Plan 02 落地的 service 层能力（`_with_sync_log` / `is_sync_running(sync_type)` / 5 方法返回 `FeishuSyncLog`）暴露给 HTTP 和 Celery 层：`GET /api/v1/feishu/sync-logs` 支持 `sync_type` + `page` + `page_size` Pydantic Literal 校验分页；新增 `GET /sync-logs/{id}/unmatched.csv` 单列 CSV 端点（D-08，admin+hrbp 守门，前 20 条）；`POST /api/v1/feishu/sync` 升级为 per-sync_type='attendance' 分桶锁（D-15），409 detail 带 `sync_type` 字段且**不写 FeishuSyncLog**（D-16）；`feishu_sync_eligibility_task` 统一 `sync_methods` canonical key `'performance'` 并保留 `'performance_grades'` alias 过渡一个 release（Pitfall C / H），全链路 `triggered_by=operator_id` 传递到 service 方法完成审计闭环。

## Tasks Executed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | get_sync_logs + GET /sync-logs 扩展 sync_type / page / page_size | `f6eaf79` (RED), `5145e4a` (GREEN) | feishu_service.py, feishu.py, 2 test files (16 tests) |
| 2 | CSV 端点 + trigger_sync 409 per-sync_type + Celery task key 迁移 + expire_stale 五类 | `65a03ac` (RED), `9beb4fe` (GREEN) | feishu.py, feishu_sync_tasks.py, 3 test files + 1 `__init__.py` (22 tests) |

## API 契约（给前端 Plan 04 消费）

### GET /api/v1/feishu/sync-logs

**Query params:**
- `sync_type?: SyncTypeLiteral` — 可选，五类之一；非白名单值 → 422
- `page?: int` — 默认 1，`ge=1`；`page=0` → 422
- `page_size?: int` — 默认 20，`ge=1 le=100`；`page_size=200` → 422

**Role gate:** `admin + hrbp`（`employee / manager → 403`；未登录 → 401）

**Response:** `200 OK` + `List[SyncLogRead]`（Plan 01 schema，含 `sync_type`、`mapping_failed_count`、`status: Literal['running','success','partial','failed']`）

**排序:** `started_at DESC`（分页用 offset = `(page-1) * page_size`）

### GET /api/v1/feishu/sync-logs/{log_id}/unmatched.csv

**Path param:** `log_id: str` — FeishuSyncLog UUID；不存在 → 404

**Role gate:** `admin + hrbp`

**Response headers:**
- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename=sync-log-{log_id}-unmatched.csv`

**Response body:**
```csv
employee_no
E001
E002
...
```
- Header 行恒为 `employee_no`
- 数据行：`json.loads(log.unmatched_employee_nos)[:20]` — 最多 20 行
- 空 / NULL 时只返回 header（test_csv_header_only_when_unmatched_empty 覆盖）
- 特殊字符（逗号 / 引号 / 换行）由 `csv.writer` 自动 quoting / escaping

### POST /api/v1/feishu/sync — 409 升级

**Role gate:** `admin + hrbp`

**Happy path:** `200 OK` + `SyncTriggerResponse(sync_log_id='pending', status='running', ...)`

**Conflict path (D-15 / D-16):**
- 前置调 `service.expire_stale_running_logs(timeout_minutes=30)`（D-17，覆盖五类 sync_type）
- 若 `service.is_sync_running(sync_type='attendance') == True` → 409
- **409 detail JSON 结构：**
  ```json
  {
    "error": "sync_in_progress",
    "sync_type": "attendance",
    "message": "考勤同步正在进行中，请稍后再试"
  }
  ```
- **D-16:** 409 发生时**不写** FeishuSyncLog（测试 `test_trigger_sync_409_when_attendance_running` 验证 count 不变）
- **不同 sync_type 不阻塞:** Celery 触发的 `performance/hire_info/...` 同步正在进行时，考勤 `/sync` 端点依然可 200（测试 `test_trigger_sync_not_blocked_by_other_sync_type`）

## Celery task canonical_sync_type 规范化

**Task 入口签名不变**（向后兼容 in-flight broker 消息）：

```python
feishu_sync_eligibility_task(
    sync_type: str,                        # 允许 'performance' 或 'performance_grades'
    app_token: str,
    table_id: str,
    field_mapping: dict[str, str],
    operator_id: str | None = None,        # 转发 triggered_by
)
```

**内部规范化:**

```python
canonical_sync_type = 'performance' if sync_type == 'performance_grades' else sync_type
# Used in update_state meta + returned payload
```

**`sync_methods` dict:**

```python
{
    'performance': service.sync_performance_records,
    'performance_grades': service.sync_performance_records,  # TODO(phase-32): remove alias
    'salary_adjustments': service.sync_salary_adjustments,
    'hire_info': service.sync_hire_info,
    'non_statutory_leave': service.sync_non_statutory_leave,
}
```

**service method 调用:** 固定传 `triggered_by=operator_id`，service 层 `_with_sync_log` 写入 `FeishuSyncLog.triggered_by` 字段。

**`FeishuSyncLog.sync_type` 永远写 canonical 形式**（Plan 02 service 层职责 — Celery task 不直接写 log）。

## Alias 生命周期

| Milestone | Action |
|-----------|--------|
| **Phase 31 (current)** | `'performance_grades'` 作为 `sync_methods` dict 的 alias key，Celery 入口接受两种字符串 |
| **Phase 32 计划** | 1. `grep -r "performance_grades" backend/` 应返回 0 行（除 alembic 旧迁移 backfill） 2. `sync_methods` 删除 alias key 3. `backend/app/schemas/eligibility_import.py:6 ELIGIBILITY_IMPORT_TYPES` 同步移除 `'performance_grades'` 4. `canonical_sync_type` 规范化行可选删除（alias 消失后无副作用） |
| **上线前运维 checklist** | 1. 升级前 drain Redis broker: `celery -A backend.app.celery_app inspect active` + `purge` 如有活跃 `'performance_grades'` 任务 2. Alembic heads 为 `31_01_sync_log_observability`（Plan 01 已落地） 3. 部署 Phase 31 后 2-3 个调度周期验证绿盘，再在 Phase 32 移除 alias |

## 运维上线 Checklist

### 部署顺序

1. **数据库迁移（如未跑）:** `alembic upgrade head` — Plan 01 已在 `31_01_sync_log_observability` revision 两阶段加列（`sync_type NOT NULL`、`mapping_failed_count INTEGER NOT NULL DEFAULT 0`）
2. **Celery broker drain:** `celery -A backend.app.celery_app inspect active` 确认无 in-flight `feishu_sync_eligibility_task(sync_type='performance_grades')`。若存在，执行 `celery -A backend.app.celery_app purge` 或让其消费完；本 release 虽保留 alias，但 canonical 形式更清晰
3. **后端部署:** `uvicorn backend.app.main:app --reload` → `pytest backend/tests -k feishu` 应该 **132+ 通过**（16 pre-existing OAuth 失败非本 plan 引入，已 deferred-items 记录）
4. **冒烟验证:**
   - `curl -H "Authorization: Bearer {admin_token}" "http://localhost:8011/api/v1/feishu/sync-logs?sync_type=attendance&page=1&page_size=5"` → 200 + JSON list
   - `curl -H "Authorization: Bearer {admin_token}" "http://localhost:8011/api/v1/feishu/sync-logs/{log_id}/unmatched.csv" -o out.csv && head -1 out.csv` → `employee_no`
   - `curl -X POST -H "Authorization: Bearer {admin_token}" -d '{"mode":"full"}' -H "Content-Type: application/json" http://localhost:8011/api/v1/feishu/sync` 两次连打，第二次应返回 409 + `{"error":"sync_in_progress","sync_type":"attendance",...}`

### 回滚策略

- Alembic downgrade 不是本 plan 必需（schema 未改）；只需 `git revert 9beb4fe 65a03ac 5145e4a f6eaf79` 回到 Phase 31 Plan 02 的 commit `33cf835`
- 前端 Plan 04 尚未落地，因此 API 层变动不会立即影响用户可见流程；Attendance 轮询（无 sync_type 参数）继续正常工作

## Deviations from Plan

### 无 Rule 1 / 2 / 3 自动修复

Plan 03 全部按计划执行，零代码 bug / 缺失功能 / 阻塞问题。唯二微小差异：

**1. [Clarification] `limit` 参数保留但不在 API Query 暴露**

- **Plan 设计:** service 层保留 `limit` kwarg 向后兼容 AttendanceManagement `getSyncLogs(limit=20)`
- **执行选择:** API Query 只暴露 `page / page_size`，不暴露 `limit`（因为 `page_size=20` 默认值行为等价）。service 层 `limit` kwarg 仅供内部调用方（无 HTTP 入口）
- **Why:** 避免 API 有两种分页参数共存的歧义；Plan 04 前端可直接用 `page_size`，无需迁移 `limit`

**2. [Clarification] Celery task return payload shape 变化属既定契约**

- Plan 02 已声明 `method(...)` 返回 `FeishuSyncLog`（非 dict）；Plan 03 Celery task 的 `result` 内 `{synced, updated, unmatched, mapping_failed, failed, total, ...}` 直接从 FeishuSyncLog 字段 serialize
- **兼容性影响:** 如果有 downstream Celery consumer 监听 task result backend，字段名从 `{synced, skipped, failed}` → `{synced, updated, unmatched, mapping_failed, failed}`（skipped 只对 attendance 有意义，其他 sync_type 固定 0 — 按 Plan 02 D-02 mapping_failed 新语义）
- 本项目没有其他 Celery consumer 依赖该 task 的 result backend（通过 `grep AsyncResult` 确认零调用）

### 无 Rule 4 架构变更

无 schema / 新服务 / 新库 / 新认证机制 — 符合 Plan 03 「API + Celery layer exposure」边界。

## Regression Coverage

### New tests

| File | Tests | Commit |
|------|-------|--------|
| `test_feishu_get_sync_logs.py` | 5 | `f6eaf79` / `5145e4a` |
| `test_feishu_sync_logs_api.py` | 11 | `f6eaf79` / `5145e4a` |
| `test_feishu_unmatched_csv.py` | 13 | `65a03ac` / `9beb4fe` |
| `test_feishu_expire_stale.py` | 2 | `65a03ac` |
| `test_feishu_sync_tasks_keys.py` | 7 | `65a03ac` / `9beb4fe` |
| **Total** | **38** | |

### Phase 30 + 31-01 + 31-02 regression

- `test_feishu_leading_zero.py` — 12 passed
- `test_feishu_sync_log_model.py` — 11 passed
- `test_feishu_sync_log_migration.py` — 4 passed
- `test_feishu_sync_counters_dataclass.py` — 5 passed
- `test_feishu_partial_status_derivation.py` — 12 passed
- `test_feishu_with_sync_log_helper.py` — 8 passed
- `test_feishu_per_sync_type_lock.py` — 5 passed
- `test_feishu_sync_type_whitelist.py` — 3 passed
- `test_feishu_sync_methods_write_log.py` — 7 passed
- `test_feishu_mapping_failed_counter.py` — 6 passed
- `test_feishu_config_validation.py` — 4 passed
- **Total: 77 regression passed**

### Pre-existing failures (not caused by 31-03)

16 failures in `-k feishu` broad selection are pre-existing, documented in Plan 02 `deferred-items.md`:

- `test_feishu_oauth_service.py` (9 failures) + `test_feishu_oauth_integration.py` (5 failures): `feishu_oauth_service.py:372` call to `FeishuService._lookup_employee()` missing `emp_no` positional argument. Confirmed via `git stash` baseline — exists on `33cf835` (pre-Plan 03). Out of scope.
- `test_feishu_leading_zero.py` (2 failures when run alongside other tests in same pytest session): order-dependent test isolation bug in pre-existing test; passes in isolation (12 passed). Out of scope.

## Consumer Readiness (for Plan 04 frontend)

### Axios service contract

```typescript
// frontend/src/services/feishuService.ts (to be added/updated by Plan 04)
export async function getSyncLogs(params: {
  sync_type?: 'attendance' | 'performance' | 'salary_adjustments' | 'hire_info' | 'non_statutory_leave',
  page?: number,    // default 1
  page_size?: number,  // default 20, max 100
}): Promise<SyncLogRead[]> {
  const response = await api.get<SyncLogRead[]>('/feishu/sync-logs', { params });
  return response.data;
}

export async function downloadUnmatchedCsv(logId: string): Promise<void> {
  const response = await api.get<Blob>(`/feishu/sync-logs/${logId}/unmatched.csv`, {
    responseType: 'blob',
  });
  // Trigger browser download — filename from Content-Disposition
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sync-log-${logId}-unmatched.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
```

### SyncLogsPage Tab → sync_type 映射

| Tab 标签 | API sync_type 值 |
|----------|-------------------|
| 全部 | 不传 sync_type 参数 |
| 考勤 | `attendance` |
| 绩效 | `performance`（注意不是 `performance_grades`） |
| 薪调 | `salary_adjustments` |
| 入职信息 | `hire_info` |
| 社保假勤 | `non_statutory_leave` |

### 409 错误处理

Plan 04 前端在点击「触发同步」按钮后处理 409 响应：

```typescript
try {
  await triggerSync({ mode: 'full' });
} catch (err) {
  if (axios.isAxiosError(err) && err.response?.status === 409) {
    const detail = err.response.data.detail;
    toast.warning(`${detail.message}（sync_type=${detail.sync_type}）`);
    // Do NOT create a rejected log row on the UI — D-16
  }
}
```

### TypeScript 类型镜像（to be added in Plan 04）

```typescript
export type SyncTypeLiteral =
  | 'attendance'
  | 'performance'
  | 'salary_adjustments'
  | 'hire_info'
  | 'non_statutory_leave';

export type SyncStatusLiteral = 'running' | 'success' | 'partial' | 'failed';

export interface SyncLogRead {
  id: string;
  sync_type: SyncTypeLiteral;
  mode: string;
  status: SyncStatusLiteral;
  total_fetched: number;
  synced_count: number;
  updated_count: number;
  skipped_count: number;
  unmatched_count: number;
  mapping_failed_count: number;
  failed_count: number;
  leading_zero_fallback_count: number;
  error_message: string | null;
  unmatched_employee_nos: string[] | null;
  started_at: string;       // ISO 8601
  finished_at: string | null;
  triggered_by: string | null;
}
```

## Known Stubs / Deferred Items

- **Pre-existing feishu_oauth_service _lookup_employee signature mismatch (16 tests):** 记录在 Plan 02 `deferred-items.md`，非本 plan 触发。Phase 32 或独立 bug-fix PR 处理。
- **Celery task result backend consumer 兼容性:** 理论上 result payload shape 从 `{synced, skipped, failed}` → `{synced, updated, unmatched, mapping_failed, failed, total, ...}`；经 `grep AsyncResult` 本项目无 downstream 消费者，无需兼容改造。
- **CSV Injection defense-in-depth（`'` 前缀）:** T-31-16 已 accept disposition；v1.5+ 项目级议题再评估。
- **frontend `/feishu/sync-logs` 路由 + SyncLogsPage 组件:** Plan 04 范围，不在本 plan。
- **'performance_grades' alias 移除:** Phase 32 TODO（本 plan 保留一个 release 过渡期）。

## Threat Flags

无新增威胁面。本 plan 的威胁都在 Plan 03 `<threat_model>`（T-31-12 ~ T-31-20）内显式处理：

- T-31-12 (Info disclosure CSV PII) — `require_roles('admin', 'hrbp')` enforced; test_csv_{employee,manager}_forbidden + test_csv_unauthenticated_returns_401 验证 403/401 ✓
- T-31-13 (Tampering SQL injection on log_id) — `db.get(FeishuSyncLog, log_id)` 参数化查询 ✓
- T-31-14 (Info disclosure frontend bypass) — backend API 403 闭合（Plan 04 前端 ProtectedRoute 再加一层）
- T-31-15 (DoS large page_size) — `page_size: int = Query(le=100)` ✓
- T-31-16 (CSV Injection Excel execution) — accept disposition，不加 `'` 前缀 ✓
- T-31-17 (Concurrent 409-bypass race) — accept；expire_stale 兜底 ✓
- T-31-18 (404 vs 403 timing leak) — accept（项目级策略）✓
- T-31-19 (Celery alias audit ambiguity) — canonical_sync_type 规范化；FeishuSyncLog.sync_type 永远 canonical ✓
- T-31-20 (Celery operator_id trust) — accept；API 层 `current_user.id` 写入 ✓

## Self-Check: PASSED

- FOUND: backend/app/services/feishu_service.py
  - `def get_sync_logs(self, *, sync_type: str | None = None, page: int = 1, page_size: int = 20, limit: int | None = None) -> list[FeishuSyncLog]` ✓
- FOUND: backend/app/api/v1/feishu.py
  - `import csv, io` ✓
  - `from fastapi import ..., Query, Response` ✓
  - `from backend.app.schemas.feishu import ..., SyncTypeLiteral` ✓
  - `from backend.app.models.feishu_sync_log import FeishuSyncLog` ✓
  - `sync_type: SyncTypeLiteral | None = Query(default=None)` ✓
  - `page: int = Query(default=1, ge=1)` ✓
  - `page_size: int = Query(default=20, ge=1, le=100)` ✓
  - `@router.get('/sync-logs/{log_id}/unmatched.csv')` ✓
  - `media_type='text/csv; charset=utf-8'` ✓
  - `'Content-Disposition': f'attachment; filename=sync-log-{log_id}-unmatched.csv'` ✓
  - `is_sync_running(sync_type='attendance')` ✓
  - `'sync_type': 'attendance'` in 409 detail ✓
- FOUND: backend/app/tasks/feishu_sync_tasks.py
  - `canonical_sync_type = 'performance' if sync_type == 'performance_grades' else sync_type` ✓
  - `'performance': service.sync_performance_records` ✓
  - `'performance_grades': service.sync_performance_records` (alias) ✓
  - `TODO(phase-32): remove performance_grades alias` ✓
  - `triggered_by=operator_id` ✓
- FOUND: backend/tests/test_services/test_feishu_get_sync_logs.py (5 tests)
- FOUND: backend/tests/test_api/test_feishu_sync_logs_api.py (11 tests)
- FOUND: backend/tests/test_api/test_feishu_unmatched_csv.py (13 tests)
- FOUND: backend/tests/test_services/test_feishu_expire_stale.py (2 tests)
- FOUND: backend/tests/test_tasks/__init__.py
- FOUND: backend/tests/test_tasks/test_feishu_sync_tasks_keys.py (7 tests)
- FOUND commit: f6eaf79 (RED Task 1)
- FOUND commit: 5145e4a (GREEN Task 1)
- FOUND commit: 65a03ac (RED Task 2)
- FOUND commit: 9beb4fe (GREEN Task 2)
- VERIFIED: `pytest` on all 5 new test files → 38 passed
- VERIFIED: `pytest` on Phase 30 + 31-01 + 31-02 test files → 77 passed (regression green)
- VERIFIED: grep acceptance criteria all pass
