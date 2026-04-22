---
phase: 34-performance-management-service-and-api
plan: 03
subsystem: backend/services + backend/api/v1 + backend/schemas + backend/tests
tags: [services, api, schemas, tests, performance, phase-34, wave-2]
requirements-completed: [PERF-05]
requirements-partial: [PERF-01, PERF-02, PERF-08]
dependency-graph:
  requires:
    - 34-01 (PerformanceTierSnapshot 模型 + PerformanceRecord.department_snapshot 列)
    - 34-02 (TierCache + 自定义异常 + Settings 字段)
  provides:
    - PerformanceService 类（6 方法：list_records / create_record /
      get_tier_summary / recompute_tiers / invalidate_tier_cache / list_available_years）
    - 5 个 REST API 端点 /api/v1/performance/* 全部 admin/hrbp 鉴权
    - 6 个 Pydantic schemas（PerformanceRecordRead / PerformanceRecordsListResponse /
      PerformanceRecordCreateRequest / TierSummaryResponse / RecomputeTriggerResponse /
      AvailableYearsResponse）
    - import_service.confirm_import 在 performance_grades 路径同步触发档次重算 hook
    - ConfirmResponse 新增可选字段 tier_recompute_status: Literal[5 values] | None
    - _import_performance_grades 两条分支均写 department_snapshot=employee.department
  affects:
    - Phase 34 Plan 04 (UI 层) 可直接 axios 调用 5 端点
    - Phase 35 ESELF-03 在 /performance/me/tier 保留位上挂 handler
    - HR Excel 导入路径自此填充 PerformanceRecord.department_snapshot（不再永远 NULL）
tech-stack:
  added:
    - backend/app/services/performance_service.py（414 行）
    - backend/app/api/v1/performance.py（208 行，5 端点 + 1 注释保留位）
    - backend/app/schemas/performance.py（82 行，6 schemas）
    - backend/tests/test_services/test_performance_service.py（20 cases）
    - backend/tests/test_api/test_performance_api.py（13 cases）
    - backend/tests/test_services/test_import_service_perf_hook.py（6 cases）
  patterns:
    - 行锁 SQLite/PostgreSQL 双路径策略（dialect.name 检测 + try/except OperationalError）
    - ThreadPoolExecutor + future.result(timeout=5) 同步阻塞但 wait=False 让超时后台继续
    - http_exception_handler 利用 exc.detail 是 dict 时直接返回 content（无 detail wrapper）
    - lazy import 在方法内（_run_tier_recompute_hook）避免 import_service ↔ performance_service 循环
    - mock TierCache（spec=TierCache）+ MagicMock dialect 强制 SQLite 走 PostgreSQL 路径
key-files:
  created:
    - backend/app/services/performance_service.py
    - backend/app/api/v1/performance.py
    - backend/app/schemas/performance.py
    - backend/tests/test_services/test_performance_service.py
    - backend/tests/test_api/test_performance_api.py
    - backend/tests/test_services/test_import_service_perf_hook.py
  modified:
    - backend/app/api/v1/router.py（+2 行：import + include_router）
    - backend/app/services/import_service.py（+~110 行：B-1 双分支修复 +
      confirm_import hook 调用 + _run_tier_recompute_hook 方法）
    - backend/app/schemas/import_preview.py（+10 行：W-1 ConfirmResponse 扩字段）
key-decisions:
  - 行锁 SQLite/PostgreSQL 双路径：SQLite dialect.name 检测后 warn log 跳过 NOWAIT；
    PostgreSQL 真实加锁；测试用 monkeypatch dialect 强制走 PostgreSQL 路径覆盖
  - W-1 扩 ConfirmResponse 字段而非用 result_summary 透传：让前端通过强类型字段
    直接 toast 不同状态（completed / in_progress / busy_skipped / failed），无需解析
    嵌套 JSON；保持向后兼容（None 默认值不破坏 eligibility_import.py）
  - ThreadPoolExecutor 5s 超时不强制 shutdown：fut.result(timeout) 超时后 ex.shutdown(wait=False)
    让后台线程继续完成重算；前端通过 GET /tier-summary 的 computed_at 时间戳轮询
  - B-1 在 _import_performance_grades 显式赋值（D-08）：不用 SQLAlchemy event listener，
    避免隐式行为；insert + existing 两条分支都覆盖（pytest grep 验证 ≥ 2 命中）
  - http_exception_handler 利用 exc.detail dict 直返：API tests assert resp.json()['error']
    而不是 resp.json()['detail']['error']
  - PerformanceTierEngine 默认参数化（Settings.performance_tier_min_sample_size 注入）
    + 接受 ctor 注入便于 mock；recompute_tiers 测试用 fake_engine.assign 验证传入数据
metrics:
  start-time: 2026-04-22T08:08:37Z
  end-time: 2026-04-22T08:30:00Z
  duration-seconds: 1283
  duration-human: ~21 分钟
  tasks-completed: 3 / 3
  files-created: 6
  files-modified: 3
  tests-added: 39
  tests-pass-rate: 39/39 (100%)
  regressions: 0 (engines 64 + models 9 + tier_cache 12 + import suite 21 全绿)
---

# Phase 34 Plan 03: PerformanceService + 5 REST 端点 + Import Hook + B-1/B-2/B-3/W-1 修复 Summary

Wave 2 落地：把 Phase 33 Engine + Wave 1 模型与基础设施串起来，提供 HR/admin 视角的完整后端能力栈：列表分页、单条新增、档次摘要查询、手动重算、年份下拉源 5 个 REST 端点；以及在 HR 上传 Excel confirm 后同步触发档次重算的 hook（最长阻塞 5 秒，超时后台继续，失败不阻塞 import 落库）。同时修复 4 个关键 blocker（B-1 部门快照写入断链 / B-2 锁竞争测试缺失 / B-3 前端年份下拉 hack / W-1 ConfirmResponse 状态透传）。

## What Got Built

### Task 1: PerformanceService + 6 Pydantic schemas（commit `108b397`）

**`backend/app/schemas/performance.py`** (82 行，6 schemas)：

| Schema | 用途 |
|--------|------|
| `PerformanceRecordRead` | 列表/单条响应；含 employee_name (Service 填充) + department_snapshot |
| `PerformanceRecordsListResponse` | 列表分页响应（items + total + page + page_size + total_pages） |
| `PerformanceRecordCreateRequest` | POST /records 请求体（year ge=2000 le=2100；grade A-E；source pattern 校验） |
| `TierSummaryResponse` | D-09 平铺 9 字段（tiers_count 含 'none' 键） |
| `RecomputeTriggerResponse` | POST /recompute-tiers 响应 |
| `AvailableYearsResponse` | **B-3** GET /available-years 响应 |

**`backend/app/services/performance_service.py`** (414 行)：`PerformanceService` 类含 6 公开方法：

```python
class PerformanceService:
    def __init__(self, db, *, settings=None, cache=None, engine=None): ...
    def list_records(self, *, year=None, department=None, page=1, page_size=50): ...
    def create_record(self, *, employee_id, year, grade, source='manual'): ...
    def list_available_years(self) -> list[int]: ...   # B-3
    def invalidate_tier_cache(self, years): ...
    def get_tier_summary(self, year) -> TierSummaryResponse | None: ...
    def recompute_tiers(self, year) -> TierSummaryResponse: ...
```

**关键实现细节：**
- **D-08 部门快照**：`create_record` 在 insert + existing 两条分支均显式 `department_snapshot=employee.department`；employee.department=None 时也写 None（不抛异常）
- **D-05 行锁**：`_acquire_year_lock(year)` 检测 `db.bind.dialect.name`，SQLite 走 warn 降级路径；PostgreSQL 真实 `SELECT id ... FOR UPDATE NOWAIT`；OperationalError 含 `_BUSY_LOCK_HINTS` 关键词（could not obtain lock / lock not available / could not serialize / database is locked）→ `TierRecomputeBusyError(year)`
- **D-04 重算失败**：除 Busy/Failed 异常外的所有 Exception → `TierRecomputeFailedError(year, str(exc))`；rollback DB
- **D-09 tiers_count**：用 `Counter` 统计 `tiers_json` 4 键，键名 `'1'/'2'/'3'/'none'`
- **D-10 / get 路径**：cache miss + 表 miss 时返回 None，由 API 层转 404
- **B-3**：空表时返回 `[date.today().year]`，避免前端 dropdown 空选项

**严格无 fastapi 依赖**：`grep "from fastapi" backend/app/services/performance_service.py` 无输出；`raise` 仅命中 `ValueError + TierRecompute*Error`。

### Task 2: 5 端点 API + router 注册 + B-1 修复 + W-1 扩字段 + import hook（commit `768ded5`）

**`backend/app/api/v1/performance.py`** (208 行)：

| Method | Path | Roles | 异常映射 |
|--------|------|-------|----------|
| GET | `/performance/records` | admin, hrbp | — |
| POST | `/performance/records` | admin, hrbp | ValueError → 422 |
| GET | `/performance/tier-summary` | admin, hrbp | None → 404 `no_snapshot` (D-10) |
| POST | `/performance/recompute-tiers` | admin, hrbp | BusyError → 409 / FailedError → 500 |
| GET | `/performance/available-years` | admin, hrbp | — (B-3) |
| (注释) | `/performance/me/tier` | — | Phase 35 ESELF-03 保留位（无 handler，404）|

**`_make_service` helper**：注入 Redis cache（`get_redis()` 抛 → None 降级），保持 service 层零网络感知。

**`backend/app/api/v1/router.py`**：在 handbooks 与 public 之间按字母序加 import + include_router。

**`backend/app/services/import_service.py` 修改：**

1. **B-1 修复（行 893-908 _import_performance_grades）：**
   - existing 更新分支：`existing.department_snapshot = employee.department`
   - insert 分支：`PerformanceRecord(..., department_snapshot=employee.department)`
   - HR 通过 Excel 导入的所有绩效记录都填充 department_snapshot（PERF-08 / SC-4）

2. **confirm_import hook（行 ~1933）+ W-1 字段写回：**
   - `if job.import_type == 'performance_grades' and job.status in ('completed', 'partial'): tier_recompute_status = self._run_tier_recompute_hook(job)`
   - ConfirmResponse 实例化加 `tier_recompute_status=tier_recompute_status`

3. **`_run_tier_recompute_hook(job) -> str` 新方法（~85 行）：**
   - 抽取 affected years：扫 `result_summary['execution']['rows']`；兜底查 1 分钟内 source='excel' 不同 year
   - 调 `perf_service.invalidate_tier_cache(affected_years)`
   - `ThreadPoolExecutor(max_workers=1) + fut.result(timeout=5s)`
   - TierRecomputeBusyError → `'busy_skipped'` (D-06)
   - TierRecomputeFailedError → `'failed'` (D-04，仅 log 不重抛)
   - FutureTimeout → `'in_progress'`（`ex.shutdown(wait=False)` 让后台继续）
   - 全部成功 → `'completed'`

**`backend/app/schemas/import_preview.py` W-1 修复：**
```python
class ConfirmResponse(BaseModel):
    ...existing fields...
    tier_recompute_status: Literal[
        'completed', 'in_progress', 'busy_skipped', 'failed', 'skipped',
    ] | None = Field(default=None, description='...')
```

非 performance_grades 路径默认 None，向后兼容 eligibility_import.py 的全部既有调用。

### Task 3: 39 cases 测试 全绿（commit `7a8f722`）

| 测试文件 | Cases | 关键覆盖 |
|----------|-------|----------|
| `test_performance_service.py` | 20 | 6 方法 + B-2 锁竞争 mock + B-3 distinct desc + Engine 集成 + cache 协作 |
| `test_performance_api.py` | 13 | 5 端点 happy + 4 角色 RBAC + 404/409/422/500 + B-3 admin 200 |
| `test_import_service_perf_hook.py` | 6 | B-1 双分支 + B-2 busy_skipped + happy + D-04 不阻塞 + 非 perf 路径 |

**B-2 mock 模板（test_performance_service.py:325）：**
```python
def test_recompute_tiers_busy_raises_TierRecomputeBusyError_via_mock(
    db_session, employee_factory, monkeypatch,
):
    fake_dialect = MagicMock(); fake_dialect.name = 'postgresql'
    monkeypatch.setattr(service.db.bind, 'dialect', fake_dialect)

    def _fake_execute(stmt, *args, **kwargs):
        if 'FOR UPDATE NOWAIT' in str(stmt).upper():
            raise OperationalError(
                'SELECT', {},
                Exception('could not obtain lock on row in relation tier'),
            )
        return original_execute(stmt, *args, **kwargs)
    monkeypatch.setattr(service.db, 'execute', _fake_execute)

    with pytest.raises(TierRecomputeBusyError) as exc_info:
        service.recompute_tiers(2026)
    assert exc_info.value.year == 2026
```

**测试运行：**
```
============================== 39 passed in 2.80s ==============================
```

**回归验证（106 测试 0 失败）：**
- engines 64/64
- models 9/9
- tier_cache 12/12
- import_confirm + import_overwrite_modes + import_partial_success + import_idempotency 21/21

## Phase 34-04 Frontend 接口契约（Wave 3 直接消费）

| Endpoint | Method | Query Params | Response Schema |
|----------|--------|--------------|-----------------|
| `/api/v1/performance/records` | GET | `year?` `department?` `page?=1` `page_size?=50` | `PerformanceRecordsListResponse{ items, total, page, page_size, total_pages }` |
| `/api/v1/performance/records` | POST | body=`PerformanceRecordCreateRequest{ employee_id, year, grade, source? }` | `PerformanceRecordRead`（201）|
| `/api/v1/performance/tier-summary` | GET | `year` (required) | `TierSummaryResponse{ year, computed_at, sample_size, insufficient_sample, distribution_warning, tiers_count{1,2,3,none}, actual_distribution{1,2,3}, skipped_invalid_grades }` 或 404 `{ error: 'no_snapshot', year, hint }` |
| `/api/v1/performance/recompute-tiers` | POST | `year` (required) | `RecomputeTriggerResponse{ year, computed_at, sample_size, insufficient_sample, distribution_warning, message }` 或 409 `{ error: 'tier_recompute_busy', year, retry_after_seconds: 5 }` 或 500 `{ error: 'tier_recompute_failed', year }` |
| `/api/v1/performance/available-years` | GET | — | `AvailableYearsResponse{ years: list[int] }` (空表时返回 `[今年]`) |

**全部 Bearer JWT + role in (admin, hrbp)；employee/manager → 403。**

**ConfirmResponse 扩字段（`/api/v1/eligibility-import/excel/{job_id}/confirm` 现有端点）：**
```typescript
interface ConfirmResponse {
  job_id: string;
  status: 'completed' | 'partial' | 'failed';
  // ...其他既有字段
  tier_recompute_status?: 'completed' | 'in_progress' | 'busy_skipped' | 'failed' | 'skipped' | null;
}
```
仅 `import_type='performance_grades'` 时填充；前端可基于此字段切换 toast：
- `completed` → 「档次已重算」
- `in_progress` → 「档次正在后台重算（约 1 分钟后刷新）」
- `busy_skipped` → 「HR 手动重算正在执行，本次自动重算已跳过」
- `failed` → 「档次重算失败，请稍后手动重算」
- `null` → 不显示档次相关 toast（非 perf_grades 导入）

## Deviations from Plan

**Plan 要求 ≥ 28 cases，实际交付 39 cases（+39%）**：

| 文件 | Plan 最低 | 实际 | 增量原因 |
|------|-----------|------|----------|
| test_performance_service.py | 13 | 20 | + invalidate_tier_cache None 兜底 / list_available_years 空表两个路径 / cache miss 计数验证 |
| test_performance_api.py | 11 | 13 | + 4 角色 RBAC 全覆盖 / 9 字段 schema 完整断言 |
| test_import_service_perf_hook.py | 4 | 6 | + 单独 happy + failure 路径分离覆盖 / 非 perf_grades 显式 mock 验证 |

**额外修复（不属偏离，但属于 plan 之外的发现）：**

1. **`_record_counter` 进程级计数器**：在 `_make_records` helper 中加全局计数避免 employee_no 跨测试函数冲突 — Rule 1 (Bug)。`employee_factory` 自身的 counter 是 fixture 级 reset，但同一测试函数内 `_make_records` 多次调用会撞 employee_no。
2. **`test_create_record_handles_null_department` mock 策略调整**：Employee.department NOT NULL 约束阻止直接 UPDATE 为 None；改用 monkeypatch `service.db.get` 返回 stub 实例覆盖该路径 — Rule 3（解锁测试）。
3. **`test_recompute_tiers_updates_existing_snapshot` 改为业务数据变化验证**：原 plan 用 `updated_at` 时间戳变化验证（不可靠 — JSON dict 重新赋值同值时 SQLAlchemy 可能不发 UPDATE），改为加 30 条 grade='A' 记录后 sample_size 60→90 + snap.id 不变验证 — Rule 1（更稳定的等价验证）。
4. **API 错误响应 shape 适配**：发现 `http_exception_handler` 在 `exc.detail` 是 dict 时直接 return content（无 detail wrapper），测试 assert 路径调整为 `resp.json()['error']` 而非 `resp.json()['detail']['error']` — Rule 1（适配既有处理器约定）。

无任何架构层面的偏离 — 全部按 D-01..D-15 决策落地。

## Verification Results

| 检查项 | 命令 | 结果 |
|--------|------|------|
| Service 6 方法 + 6 schemas import | `python -c "from backend.app.services.performance_service import PerformanceService; ..."` | OK |
| 4 routes registered | `python -c "from backend.app.api.v1.router import api_router; ..."` | 4 条 /performance/* 路径全在 |
| B-1 双分支 grep | `grep "department_snapshot=employee.department\|existing.department_snapshot = employee.department" backend/app/services/import_service.py` | 2 行匹配 |
| B-2 mock 测试 grep | `grep "test_recompute_tiers_busy_raises_TierRecomputeBusyError_via_mock\|test_recompute_tiers_busy_in_import_hook" ...` | 2 行匹配 |
| B-3 端点 grep | `grep '/available-years' backend/app/api/v1/performance.py` | 命中 |
| W-1 字段 grep | `grep "tier_recompute_status" backend/app/schemas/import_preview.py` | 命中 |
| Service 不 import fastapi | `grep "from fastapi" backend/app/services/performance_service.py` | 无输出 |
| API 异常 catch | `grep "TierRecomputeBusyError\|TierRecomputeFailedError" backend/app/api/v1/performance.py` | 4 处命中 |
| 总测试通过 | `pytest backend/tests/test_services/test_performance_service.py backend/tests/test_api/test_performance_api.py backend/tests/test_services/test_import_service_perf_hook.py` | **39 passed** |
| 回归 | `pytest backend/tests/test_engines/ backend/tests/test_models/ test_tier_cache + 4 import` | **106 passed**, 0 failed |

## Known Stubs

无功能性 stub。`/performance/me/tier` 是有意为之的 Phase 35 保留位（路由文件中仅注释，无 handler），调用会自然返回 404，未在 ROADMAP Phase 34 SC 中。

## Threat Flags

无新增威胁面。本 plan 严格在 plan 的 `<threat_model>` 范围内交付：
- T-34-01 → 全部端点 require_roles('admin','hrbp')，pytest 4 角色 RBAC 全覆盖（hrbp 200 + admin 200 + employee 403 + manager 403）
- T-34-02 → records 列表只暴露 employee_no/name/grade/department_snapshot/source，无敏感 PII；tier-summary 仅聚合数字
- T-34-03 → FOR UPDATE NOWAIT + B-2 mock 路径强制回归
- T-34-04 → Pydantic schema 严格类型校验
- T-34-05 → D-04 + W-1：失败不阻塞 + 状态透传
- T-34-06 → AuditLog 已写 import_confirmed（手动 recompute audit Phase 35 补）

## Self-Check: PASSED

**Created files exist:**
- FOUND: backend/app/services/performance_service.py
- FOUND: backend/app/api/v1/performance.py
- FOUND: backend/app/schemas/performance.py
- FOUND: backend/tests/test_services/test_performance_service.py
- FOUND: backend/tests/test_api/test_performance_api.py
- FOUND: backend/tests/test_services/test_import_service_perf_hook.py

**Modified files contain expected changes:**
- FOUND: backend/app/api/v1/router.py（performance_router import + include）
- FOUND: backend/app/services/import_service.py（B-1 双分支 + hook + _run_tier_recompute_hook）
- FOUND: backend/app/schemas/import_preview.py（W-1 ConfirmResponse 扩字段）

**Commits exist:**
- FOUND: 108b397 — Task 1 (PerformanceService + schemas)
- FOUND: 768ded5 — Task 2 (API + import hook + B-1 + W-1)
- FOUND: 7a8f722 — Task 3 (39 cases tests)

**Success criteria：**
- [x] All 3 tasks executed
- [x] Each task committed individually with --no-verify
- [x] B-1 grep ≥ 2 matches in import_service.py
- [x] B-2 grep ≥ 2 matches across both test files
- [x] B-3 grep `/available-years` in performance.py
- [x] W-1 grep `tier_recompute_status` in import_preview.py
- [x] pytest 39 passed (Service 20 + API 13 + import_hook 6)
- [x] No regression in existing engines/models/tier_cache/import suite (106 passed)
