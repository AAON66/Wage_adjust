---
phase: 31-feishu-sync-observability
plan: 02
subsystem: feishu-sync-observability
tags: [service-refactor, sync-lifecycle, dataclass, per-sync-type-lock, d02-mapping-failed]
requires:
  - Phase 31 Plan 01 (sync_type + mapping_failed_count columns + SyncTypeLiteral)
  - FeishuSyncLog ORM + SyncLogRead schema
  - SessionLocal (backend/app/core/database.py)
  - _lookup_employee + _build_employee_map (Phase 30)
provides:
  - FeishuService._VALID_SYNC_TYPES: frozenset whitelist (5 sync types)
  - FeishuService._SyncCounters: @dataclass(frozen=True, slots=True) with 8 fields
  - FeishuService._derive_status(c): hard-cut partial rule (D-14)
  - FeishuService._apply_counters_to_log: single-point counter → log mapper
  - FeishuService._with_sync_log: unified sync lifecycle helper (D-10 / D-13)
  - FeishuService.is_sync_running(sync_type): per-sync_type bucket lock (D-15)
  - 5 refactored sync methods (all return FeishuSyncLog now, take triggered_by)
  - 5 new `_sync_<type>_body` private methods (return _SyncCounters)
affects:
  - backend/app/tasks/feishu_sync_tasks.py (will need update in Plan 03 —
    method(...) now returns FeishuSyncLog not dict; alias 'performance_grades' →
    'performance' also pending Plan 03)
tech-stack:
  added: []
  patterns:
    - Frozen dataclass with slots for type-safe counter transport
    - Dual-session pattern: independent SessionLocal() writes log (running +
      terminal + failed); business operations use self.db (D-13 — isolated tx)
    - Side-channel attribute for carrying non-counter metadata between helper
      and caller (attendance skipped_count patched after helper returns)
    - Swallow-finalize-exception pattern (Pitfall A): never overwrite business
      exception with a logging-layer failure
key-files:
  created:
    - backend/tests/test_services/test_feishu_sync_counters_dataclass.py (5 tests)
    - backend/tests/test_services/test_feishu_partial_status_derivation.py (12 tests)
    - backend/tests/test_services/test_feishu_with_sync_log_helper.py (8 tests)
    - backend/tests/test_services/test_feishu_per_sync_type_lock.py (5 tests)
    - backend/tests/test_services/test_feishu_sync_type_whitelist.py (3 tests)
    - backend/tests/test_services/test_feishu_sync_methods_write_log.py (7 tests)
    - backend/tests/test_services/test_feishu_mapping_failed_counter.py (6 tests)
    - .planning/phases/31-feishu-sync-observability/deferred-items.md
  modified:
    - backend/app/services/feishu_service.py (module-level + class internals)
decisions:
  - D-10 / _with_sync_log 独立 session：running log / terminal / failed-log
    三处都用独立 SessionLocal() commit，与 self.db 业务事务隔离。业务 rollback
    不影响 log 可见性（HR 始终能看到失败记录）。
  - D-11 / _SyncCounters frozen dataclass with slots：8 字段（success / updated /
    unmatched / mapping_failed / failed / leading_zero_fallback / total_fetched /
    unmatched_nos: tuple）；frozen 防业务侧误改、slots 降内存开销、tuple 满足
    frozen 约束。
  - D-14 / partial 硬切派生：unmatched + mapping_failed + failed > 0 → 'partial'，
    否则 'success'。leading_zero_fallback 不参与（Pitfall E — 它代表「救回来的」
    成功匹配）。
  - D-15 / is_sync_running(sync_type): 不传 sync_type 时查所有 running（向后兼容
    现有 trigger_sync 路径），传值时只查该 type 的 running log（支持 per-sync_type
    并发锁）。非白名单 sync_type 不抛异常，返回 False（让调用方决定拒绝逻辑）。
  - D-02 / mapping_failed 新语义：year/grade/adjustment_date/amount/hire_date/
    leave_days 等字段转换失败归 mapping_failed；emp_no 找不到归 unmatched；
    skipped_count 保留为「业务跳过」（目前仅 sync_attendance 使用）。
  - D-12 / sync_attendance 签名不变（Pitfall F）：(mode, triggered_by) →
    FeishuSyncLog 保持，sync_with_retry 不受影响。skipped_count 通过
    self._last_attendance_skipped_count 侧信道传出 helper（因为
    _apply_counters_to_log 不碰 skipped_count 列）。
  - [执行阶段新决策] Pitfall A-强化：_with_sync_log 的 finalize stage 若 SessionLocal()
    本身抛异常（而非 commit），也要吞异常；否则 business_exc 会被 finalize 失败
    遮盖。test_helper_finalize_exception_does_not_overwrite_business_exception
    覆盖此边界。
  - [执行阶段新决策] helper mode vs body mode：_with_sync_log 接收 `mode` 作为
    log.mode 的写入值；sync_attendance 额外用 `body_mode` 把同一 mode 显式
    转发给 _sync_attendance_body（避免 helper kwarg `mode` 与 body kwarg 重名
    冲突）。
metrics:
  duration: ~45m
  completed: 2026-04-21T10:30:00Z
  tasks_executed: 2
  commits: 4
  tests_added: 46
  tests_total_green: 46 (+12 Phase 30 leading_zero regression pass, +15 Phase 31-01 regression pass)
---

# Phase 31 Plan 02: FeishuService 五方法统一 sync_log 调度 Summary

**One-liner:** 把 FeishuService 五个同步方法（attendance + performance + salary_adjustments + hire_info + non_statutory_leave）从「各自手写 log / 返回 dict」的冗余模式，重构为「统一通过 `_with_sync_log` helper 调度 + 返回 `_SyncCounters` frozen dataclass」的可维护架构；独立 SessionLocal 事务隔离业务 rollback 不影响 log；`is_sync_running(sync_type)` 升级为 per-sync_type 分桶锁；`mapping_failed_count` 按 D-02 新语义覆盖 year/grade/date/amount 字段类型转换失败；`sync_attendance` 外部签名不变（Pitfall F）sync_with_retry 不受影响。

## Tasks Executed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 1 | _SyncCounters + _derive_status + _with_sync_log helper + per-sync_type lock | `cff92c6` (RED), `e3b26aa` (GREEN) | feishu_service.py + 5 test files (33 tests) |
| 2 | Refactor 5 sync_* methods to use helper + D-02 mapping_failed semantics | `c94b829` (RED), `a767f51` (GREEN) | feishu_service.py + 2 test files (13 tests) |

## API 契约（供 Plan 03 路由层 / Plan 04 前端间接消费）

### Module-level exports (backend/app/services/feishu_service.py)

```python
_VALID_SYNC_TYPES: frozenset[str]
# frozenset({'attendance', 'performance', 'salary_adjustments', 'hire_info', 'non_statutory_leave'})

@dataclass(frozen=True, slots=True)
class _SyncCounters:
    success: int = 0                        # → log.synced_count
    updated: int = 0                        # → log.updated_count
    unmatched: int = 0                      # → log.unmatched_count
    mapping_failed: int = 0                 # → log.mapping_failed_count (D-02 new)
    failed: int = 0                         # → log.failed_count
    leading_zero_fallback: int = 0          # → log.leading_zero_fallback_count (Phase 30)
    total_fetched: int = 0                  # → log.total_fetched
    unmatched_nos: tuple[str, ...] = ()     # → log.unmatched_employee_nos (JSON list)

def _derive_status(c: _SyncCounters) -> str:
    """unmatched + mapping_failed + failed > 0 → 'partial', else 'success'."""

def _apply_counters_to_log(log: FeishuSyncLog, c: _SyncCounters) -> None:
    """Single-point mapping: _SyncCounters → FeishuSyncLog columns + status derivation."""
```

### FeishuService class methods

```python
def _with_sync_log(
    self,
    sync_type: str,
    fn: Callable,
    *,
    triggered_by: str | None = None,
    mode: str = 'full',
    **kwargs,
) -> str:
    """Returns sync_log_id. Three-stage lifecycle in independent sessions:
       Stage 1: SessionLocal() creates running log
       Stage 2: fn(sync_log_id=..., **kwargs) runs on self.db; returns _SyncCounters
       Stage 3: SessionLocal() writes terminal (success/partial/failed)
       Business exception → log.status='failed' + re-raise
       Finalize exception → swallowed (Pitfall A: never shadow business exception)
    """

def is_sync_running(self, sync_type: str | None = None) -> bool:
    """Per-sync_type bucket lock (D-15).
       - None: any running log (backward compatible with old trigger_sync)
       - Whitelisted type: that type's running log
       - Invalid type: returns False (no exception, delegates to caller)
    """
```

### 5 sync method signatures (所有返回 FeishuSyncLog)

```python
def sync_attendance(self, mode: str, triggered_by: str | None = None) -> FeishuSyncLog:
    # 外部签名不变（Pitfall F — sync_with_retry 依赖）

def sync_performance_records(
    self, *, app_token: str, table_id: str,
    field_mapping: dict[str, str] | None = None,
    triggered_by: str | None = None,
) -> FeishuSyncLog:

def sync_salary_adjustments(
    self, *, app_token: str, table_id: str,
    field_mapping: dict[str, str] | None = None,
    triggered_by: str | None = None,
) -> FeishuSyncLog:

def sync_hire_info(
    self, *, app_token: str, table_id: str,
    field_mapping: dict[str, str] | None = None,
    triggered_by: str | None = None,
) -> FeishuSyncLog:

def sync_non_statutory_leave(
    self, *, app_token: str, table_id: str,
    field_mapping: dict[str, str] | None = None,
    triggered_by: str | None = None,
) -> FeishuSyncLog:
```

## D-02 mapping_failed vs skipped 分流规则（各方法落地情况）

| Method | mapping_failed (D-02 新语义) | skipped (业务跳过) | unmatched |
|--------|------------------------------|--------------------|-----------|
| sync_performance_records | year 解析失败 / grade ∉ ABCDE / year 或 grade 为 None | (无业务跳过) | emp_no 找不到 |
| sync_salary_adjustments | adjustment_date 解析失败 / adjustment_type 为 None / amount 无效 | (无业务跳过) | emp_no 找不到 |
| sync_hire_info | hire_date / last_salary_adjustment_date 解析失败；或两者都缺失 | (无业务跳过) | emp_no 找不到 / Employee 对象消失 |
| sync_non_statutory_leave | year 解析失败 / total_days 非数字 / year 或 total_days 为 None | (无业务跳过) | emp_no 找不到 |
| sync_attendance | 0（Deferred — 保持现状） | 源数据更旧（source_modified_at <= existing.source_modified_at） | emp_no 找不到 |

## is_sync_running 升级的兼容性说明

- `is_sync_running()` — 无参形式完全向后兼容：查询所有 running log，与 Phase 30 行为相同。
  现有 `trigger_sync` 路由调用无需改动。
- `is_sync_running('performance')` — 只查 sync_type='performance' 的 running log；支持
  per-sync_type 并发锁（D-15）。Plan 03 的 Celery task 可以让不同类型的同步并行执行，
  只在同类型触发时返回 409。
- `is_sync_running('invalid_type')` — 不抛异常，返回 False（白名单校验留给 helper 入口
  或调用方，让 is_sync_running 保持零副作用）。

## 为什么 attendance skipped_count 用侧信道传递

**问题:** `_apply_counters_to_log` 只处理 `_SyncCounters` 的 8 个字段，不碰 `log.skipped_count`
列。attendance 有语义上有效的「业务跳过」（源数据更旧），但 `_SyncCounters` 没有 `skipped` 字段
（D-11 决策 — 让 skipped 只属于 attendance 的 Phase 31 遗留）。

**解决方案:** sync_attendance body 内把 skipped 写入 `self._last_attendance_skipped_count`；
sync_attendance 外部方法在 helper 返回后、用 self.db 把 skipped_count 补写到 log 上
再 commit 一次。

**为什么不加 _SyncCounters.skipped?** 会导致其他四个方法（都没有业务跳过场景）传 0，
增加误用空间（「填 0 还是填 None 还是不传？」），且 31-CONTEXT §deferred 明确
「sync_attendance 的 skipped_count 语义重新分类到 mapping_failed — 风险大，等实战数据验证」。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] helper 的 Stage 3 SessionLocal() 本身抛异常未吞掉**

- **Found during:** Task 1 写 test_helper_finalize_exception_does_not_overwrite_business_exception
- **Issue:** 原计划文档的 helper 骨架里 `finalize_db = SessionLocal()` 发生在 try/except 外，
  一旦 SessionLocal() 抛异常（而非 commit 抛），business_exc 会被 NameError 遮盖
- **Fix:** 把 SessionLocal() 调用本身也包在 try/except，失败时 logger.exception 记录并
  跳过 finalize（business_exc 仍被重抛）
- **Files modified:** backend/app/services/feishu_service.py (_with_sync_log Stage 3)
- **Commit:** `e3b26aa`

**2. [Rule 3 - Blocking] helper `mode` kwarg 与 body kwarg 重名冲突**

- **Found during:** Task 2 test_sync_attendance_signature_mode_triggered_by_returns_feishu_sync_log
- **Issue:** `_with_sync_log` 签名已吃掉 `mode`（写入 log.mode），转发 **kwargs 到 body 时再出现
  `mode=` 会抛「got multiple values」TypeError
- **Fix:** 在 `sync_attendance` 同时传 `mode=mode` 和 `body_mode=mode`；body 签名改名为 `body_mode`
  并在函数体 `mode = body_mode`
- **Files modified:** backend/app/services/feishu_service.py
- **Commit:** `a767f51`

### No Rule 4 architectural changes

所有改动都在 service 内部，没有 DB schema / 新服务 / 新库 / 新认证机制的变动 — 符合 Plan 02
「service 层重构」的边界。

## Deferred to Plan 03 (not fixed here)

- **backend/app/tasks/feishu_sync_tasks.py:39-62** — Celery task 仍把 `method(...)` 的返回
  值当 dict 处理 (`result.get('synced', 0)` 等)。随 Plan 02 这些方法改为返回 `FeishuSyncLog`，
  Celery task 会在第一次真实执行时 AttributeError。Plan 03 必须更新该 task：
  1. `result` 改名为 `sync_log: FeishuSyncLog`
  2. `update_state meta` 改读 `sync_log.synced_count / failed_count / total_fetched / etc.`
  3. alias `'performance_grades' → 'performance'` (Pitfall H) — 不要立即删 key，留过渡期
  4. 新增 canonical sync_type normalizer 在写入 FeishuSyncLog 前（暂不需要，因为
     sync_methods dict 映射已经规范了 method，sync_type 字符串由 service 写入）

- **API trigger_sync endpoint** — 前置调用 `is_sync_running()` 目前仍是无参全局锁；Plan 03 让
  触发绩效同步的新 endpoint 调 `is_sync_running('performance')` 实现 per-type 锁。

- **sync_attendance 的 skipped_count 语义重新分类** — 31-CONTEXT §deferred 明确推迟到 v1.5+。

## Regression Coverage

### Phase 30 / 31-01 tests unchanged (all green)

- `backend/tests/test_services/test_feishu_leading_zero.py` — 12/12 passed
- `backend/tests/test_services/test_feishu_sync_log_model.py` — 11/11 passed (with 31-01 additions)
- `backend/tests/test_models/test_feishu_sync_log_migration.py` — 4/4 passed
- `backend/tests/test_api/test_feishu_config_validation.py` — passed (includes
  test_sync_logs_response_includes_leading_zero_fallback_count with Phase 31-01 fixture)

### Pre-existing failures (not caused by 31-02)

记录在 `.planning/phases/31-feishu-sync-observability/deferred-items.md`：

- `backend/tests/test_services/test_feishu_oauth_service.py` 9 failures +
  `backend/tests/test_api/test_feishu_oauth_integration.py` 5 failures：
  `feishu_oauth_service.py:198` 调 `FeishuService._lookup_employee(emp_map, feishu_employee_no)`
  缺少 `emp_no` positional argument。经 `git stash` baseline 确认为 Phase 30 以前就存在的
  调用点 signature mismatch bug。Phase 31 Plan 02 只碰 5 个 sync 方法，OAuth 不在范围。

## Threat Flags

无新增威胁面。本 plan 的威胁都在 `<threat_model>` (T-31-06 ~ T-31-11) 内显式处理：

- T-31-06 (Tampering `_SyncCounters`) — frozen=True 使 body 无法写错字段；helper 单点
  `_apply_counters_to_log` 映射；TypeError 在 body 返回非 _SyncCounters 时立即抛
- T-31-07 (Info disclosure error_message) — `str(exc)[:2000]` 限长；UI 侧展示由 Plan 03
  路由层 + Plan 04 前端配合做 admin/hrbp 守门
- T-31-08 (DoS finalize 无限重试) — Stage 3 的 try/except 吞掉 finalize 异常，不 reraise；
  Celery autoretry_for 由 Plan 03 的 task 层负责（max_retries=2）
- T-31-09 (Repudiation log 丢失) — D-13 独立 SessionLocal() 落实；test_helper_rollback_isolation
  验证 business rollback 不影响 running log 可见性
- T-31-10 (Elev of privilege triggered_by 篡改) — body fn 签名 `*, sync_log_id, **kwargs`
  不接收 triggered_by；helper Stage 1 直接写入 running log，body 无法改动
- T-31-11 (per-sync_type lock 绕过) — helper 不自带锁（避免与 API 层锁重复）；锁由 Plan 03
  API 层前置调用 `is_sync_running(sync_type)`

## Consumer Readiness (for Plans 03 / 04)

- **Plan 03 API 路由层** 可直接 `service.sync_performance_records(..., triggered_by=user.id)`
  → 返回 `FeishuSyncLog`。路由可 SyncLogRead.model_validate(log) 序列化。
- **Plan 03 Celery task** 必须改写 `feishu_sync_eligibility_task` 处理 FeishuSyncLog 返回值
  （详见 Deferred 章节）。
- **Plan 03 trigger endpoint** 可调 `service.is_sync_running('performance')` 做 per-type
  409 守门。
- **Plan 04 前端 SyncLogsPage** 数据源已就绪：每次同步后 FeishuSyncLog 包含完整的五类计数器
  + leading_zero_fallback_count + 派生的 partial status。

## Self-Check: PASSED

- FOUND: backend/app/services/feishu_service.py
  - `_VALID_SYNC_TYPES: frozenset[str] = frozenset({...})` ✓
  - `@dataclass(frozen=True, slots=True)` ✓
  - `class _SyncCounters:` ✓
  - `def _derive_status(c: _SyncCounters) -> str:` ✓
  - `def _apply_counters_to_log(log: FeishuSyncLog, c: _SyncCounters)` ✓
  - `def _with_sync_log(self, sync_type: str, fn: Callable, *, ...)` ✓
  - `def is_sync_running(self, sync_type: str | None = None) -> bool:` ✓
  - 5 public sync methods returning FeishuSyncLog ✓
  - 5 `_sync_<type>_body` private methods returning _SyncCounters ✓
  - 0 occurrences of `'performance_grades'` ✓
  - 0 occurrences of `return {'synced':` ✓
- FOUND: backend/tests/test_services/test_feishu_sync_counters_dataclass.py (5 tests)
- FOUND: backend/tests/test_services/test_feishu_partial_status_derivation.py (12 tests)
- FOUND: backend/tests/test_services/test_feishu_with_sync_log_helper.py (8 tests)
- FOUND: backend/tests/test_services/test_feishu_per_sync_type_lock.py (5 tests)
- FOUND: backend/tests/test_services/test_feishu_sync_type_whitelist.py (3 tests)
- FOUND: backend/tests/test_services/test_feishu_sync_methods_write_log.py (7 tests)
- FOUND: backend/tests/test_services/test_feishu_mapping_failed_counter.py (6 tests)
- FOUND commit: cff92c6 (Task 1 RED)
- FOUND commit: e3b26aa (Task 1 GREEN)
- FOUND commit: c94b829 (Task 2 RED)
- FOUND commit: a767f51 (Task 2 GREEN)
- VERIFIED: `pytest` on all 7 new test files → 46 passed
- VERIFIED: `pytest backend/tests/test_services/test_feishu_leading_zero.py` → 12 passed (Phase 30 regression green)
- VERIFIED: `pytest backend/tests/test_services/test_feishu_sync_log_model.py backend/tests/test_models/test_feishu_sync_log_migration.py` → 15 passed (Phase 31-01 regression green)
