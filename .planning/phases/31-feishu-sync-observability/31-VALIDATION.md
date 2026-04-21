---
phase: 31
slug: feishu-sync-observability
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-21
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 (backend) + `tsc --noEmit` (frontend lint) |
| **Config file** | `backend/tests/conftest.py` (existing) |
| **Quick run command** | `pytest backend/tests/ -x --tb=short -k "feishu_sync_log or feishu_service_helper or feishu_api_sync_logs"` |
| **Full suite command** | `pytest backend/tests/ -x --tb=short && cd frontend && npm run lint` |
| **Estimated runtime** | ~30 seconds (quick) / ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `{full suite command}`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Wave 0 Strategy (Test Stub Ownership)

**Decision:** Wave 0 test scaffolding is **inlined into Wave 1+ TDD tasks** rather than a separate Wave 0 plan.

**Rationale:** Every code-producing task in Plans 01–03 carries `tdd="true"` with an explicit `<behavior>` block that enumerates the test cases. Each task's `<action>` Step includes the test-file creation (fixture + stubs + failing assertions) as Step 1 of the Red phase, and the `<verify>` block runs the test file immediately after implementation. This keeps Red → Green cycles co-located and avoids a phantom Wave 0 plan whose only job would be to create empty test files. The Nyquist principle (every task has an `<automated>` verify) is satisfied — no task references a missing test file.

**Coverage evidence (cross-checked with gap analysis below):** All 13 test files listed in the original "Wave 0 Requirements" checklist are created by tasks in Plans 01–03. Mapping:

| Original Wave 0 File | Created By |
|----------------------|------------|
| `test_feishu_sync_log_model.py` | Plan 01 Task 1 |
| `test_feishu_sync_log_migration.py` | Plan 01 Task 2 |
| `test_feishu_service_helper.py` (= `test_feishu_with_sync_log_helper.py`) | Plan 02 Task 1 |
| `test_feishu_service_counters.py` (= `test_feishu_sync_counters_dataclass.py` + `test_feishu_partial_status_derivation.py`) | Plan 02 Task 1 |
| `test_feishu_service_sync_performance.py` + 3 siblings (= `test_feishu_sync_methods_write_log.py`, consolidated) | Plan 02 Task 2 |
| `test_feishu_service_lock_bucket.py` (= `test_feishu_per_sync_type_lock.py`) | Plan 02 Task 1 |
| `test_feishu_sync_tasks_keys.py` | Plan 03 Task 2 |
| `test_feishu_api_sync_logs.py` (= `test_feishu_sync_logs_api.py`) | Plan 03 Task 1 |
| `test_feishu_api_unmatched_csv.py` (= `test_feishu_unmatched_csv.py`) | Plan 03 Task 2 |
| `test_feishu_api_trigger_409.py` (409 no-log + SC4 sequential) | Plan 03 Task 2 (merged into `test_feishu_unmatched_csv.py` / `test_feishu_sync_logs_api.py`) |

**Wave 0 Requirements checklist:** All 13 items ✅ satisfied via inline Wave 1+ creation (see Per-Task Verification Map below for the task-by-task proof).

---

## Per-Task Verification Map

Each row links `task_id → plan → wave → REQ-ID → threat_ref → secure_behavior → test type → automated command → file_exists → status`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P01-T1 | 01 | 1 | IMPORT-03, IMPORT-04 (D-01, D-02, D-09) | T-31-05 | Pydantic `Literal` 白名单在 SyncLogRead 边界拒绝非法 sync_type / status | unit | `pytest backend/tests/test_services/test_feishu_sync_log_model.py -x -v` | created by P01-T1 (Red stubs first) | ✅ inline |
| P01-T2 | 01 | 1 | IMPORT-03, IMPORT-04 (D-03) | T-31-01, T-31-04 | Backfill 用常量 `'attendance'` + `WHERE sync_type IS NULL` 无 user input；迁移可审计 | migration | `pytest backend/tests/test_models/test_feishu_sync_log_migration.py -x -v` | created by P01-T2 | ✅ inline |
| P02-T1 | 02 | 2 | IMPORT-03, IMPORT-04 (D-10, D-11, D-13, D-14, D-15) | T-31-06, T-31-08, T-31-09 | 独立 SessionLocal 写 log 事务隔离；finalize 异常 swallow 不覆盖 business exc；`_SyncCounters` frozen dataclass 防拼写 | unit | `pytest backend/tests/test_services/test_feishu_sync_counters_dataclass.py backend/tests/test_services/test_feishu_partial_status_derivation.py backend/tests/test_services/test_feishu_with_sync_log_helper.py backend/tests/test_services/test_feishu_per_sync_type_lock.py backend/tests/test_services/test_feishu_sync_type_whitelist.py -x -v` | created by P02-T1 (5 files) | ✅ inline |
| P02-T2 | 02 | 2 | IMPORT-03, IMPORT-04 (D-02, D-10, D-11, D-12) | T-31-07, T-31-10 | body fn 只返回 `_SyncCounters`；helper 单点映射到 FeishuSyncLog；error_message 截断 2000 字符防泄漏 | integration | `pytest backend/tests/test_services/test_feishu_sync_methods_write_log.py backend/tests/test_services/test_feishu_mapping_failed_counter.py -x -v` | created by P02-T2 | ✅ inline |
| P03-T1 | 03 | 3 | IMPORT-03, IMPORT-04 (D-05, D-06) | T-31-12, T-31-15 | `require_roles('admin', 'hrbp')` 守门；Pydantic Query 边界 (ge=1, le=100) 防大分页；`SyncTypeLiteral` 拒非法值 | API integration | `pytest backend/tests/test_api/test_feishu_sync_logs_api.py -x -v` | created by P03-T1 | ✅ inline |
| P03-T2 | 03 | 3 | IMPORT-03, IMPORT-04 (D-08, D-15, D-16, D-17, Pitfall C/G/H) | T-31-12, T-31-13, T-31-17, T-31-19 | CSV 端点 admin+hrbp 守门 + `db.get` 参数化防 SQLi；Celery alias `canonical_sync_type` 规范化防 sync_type 污染；`is_sync_running('attendance')` 分桶锁 | API integration + task | `pytest backend/tests/test_api/test_feishu_unmatched_csv.py backend/tests/test_tasks/test_feishu_sync_tasks_keys.py backend/tests/test_services/test_feishu_expire_stale.py -x -v` | created by P03-T2 | ✅ inline |
| P04-T1 | 04 | 4 | IMPORT-03, IMPORT-04 (D-01, D-02, D-05, D-07, D-09) | T-31-14 | TypeScript strict 收紧 SyncLogRead 类型；`<ProtectedRoute allowedRoles={['admin', 'hrbp']}/>` 前端守门 (defense in depth 配合后端) | lint | `cd frontend && npm run lint` | Task 1 creates minimal stub SyncLogsPage.tsx so lint passes before Task 2 fills it | ✅ lint-gated |
| P04-T2 | 04 | 4 | IMPORT-03, IMPORT-04 (D-04, D-06, D-07, D-08, D-09) | T-31-14, T-31-16 | 组件纯 TS，无 eval；CSV 下载走 JWT-authenticated axios；mode 列按 sync_type 条件渲染 (D-04) 不泄漏非 attendance 语义 | lint + build | `cd frontend && npm run lint && cd frontend && npm run build` | 7 files created by P04-T2 (overwrites Task 1 stub) | ✅ lint+build |
| P04-T3 | 04 | 4 | IMPORT-03, IMPORT-04 (全部 D-05 ~ D-09, SC4) | 全部 T-31-01 ~ T-31-20 (UAT 综合) | 人工验证 6 维度（Copywriting/Visuals/Color/Typography/Spacing/Registry Safety）+ SC4 双触发观测 + CSV 下载 + 角色守门 | manual | 浏览器对照 Manual-Only Verifications 清单 | — (checkpoint) | 🟡 gated by human |

**Automated coverage:** 8/9 tasks with `<automated>` verify commands (88.9%). The single manual task (P04-T3) is an explicit `type="checkpoint:human-verify"` — not a Nyquist violation because the preceding 8 tasks cover all automated contracts.

**Sampling continuity:** No 3 consecutive tasks without automated verify. All waves have at least one automated gate before advancing.

---

## Wave 0 Requirements

Test file stubs that must exist before Wave 1 can begin (per RESEARCH.md §Validation Architecture). **All satisfied by inline creation in Wave 1–3 TDD tasks** — see Wave 0 Strategy section above for the mapping and rationale.

- [x] `backend/tests/test_services/test_feishu_sync_log_model.py` — created by Plan 01 Task 1 (sync_type NOT NULL + mapping_failed_count DEFAULT 0 tests)
- [x] `backend/tests/test_models/test_feishu_sync_log_migration.py` — created by Plan 01 Task 2 (Alembic upgrade/downgrade + backfill)
- [x] `backend/tests/test_services/test_feishu_with_sync_log_helper.py` — created by Plan 02 Task 1 (`_with_sync_log` running/terminal/failed paths)
- [x] `backend/tests/test_services/test_feishu_sync_counters_dataclass.py` — created by Plan 02 Task 1 (`_SyncCounters` frozen dataclass + fields)
- [x] `backend/tests/test_services/test_feishu_partial_status_derivation.py` — created by Plan 02 Task 1 (12+ `_derive_status` cases)
- [x] `backend/tests/test_services/test_feishu_per_sync_type_lock.py` — created by Plan 02 Task 1 (`is_sync_running(sync_type)` per-type locking)
- [x] `backend/tests/test_services/test_feishu_sync_type_whitelist.py` — created by Plan 02 Task 1 (ValueError on invalid sync_type)
- [x] `backend/tests/test_services/test_feishu_sync_methods_write_log.py` — created by Plan 02 Task 2 (4 sync methods × counters fill, consolidated)
- [x] `backend/tests/test_services/test_feishu_mapping_failed_counter.py` — created by Plan 02 Task 2 (year/grade/date mapping_failed dispatching)
- [x] `backend/tests/test_tasks/test_feishu_sync_tasks_keys.py` — created by Plan 03 Task 2 (`performance_grades → performance` alias + canonical normalization)
- [x] `backend/tests/test_api/test_feishu_sync_logs_api.py` — created by Plan 03 Task 1 (`GET /feishu/sync-logs?sync_type=&page=` + role gate + 409 no-log + SC4 sequential)
- [x] `backend/tests/test_api/test_feishu_unmatched_csv.py` — created by Plan 03 Task 2 (CSV 20-row cap, filename, role gate)
- [x] `backend/tests/test_services/test_feishu_expire_stale.py` — created by Plan 03 Task 2 (all 5 sync_types expire correctly)

*Frontend: existing `tsc --noEmit` covers TypeScript contract changes in `frontend/src/types/api.ts`. No Vitest/Jest harness installed — UI validation is manual via `npm run dev` + browser (see Manual-Only Verifications).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/feishu/sync-logs` 页面 admin+hrbp 可访问；employee/manager 被 `<ProtectedRoute>` 拦截 | IMPORT-04 / D-05 | 前端无自动化测试框架 | `npm run dev` → 以 admin / hrbp / employee / manager 四角色各登录一次，确认前两者看到菜单 + 能打开页面，后两者菜单项不可见且直连 URL 被重定向 |
| Tab 切换 `全部 / 考勤 / 绩效 / 薪调 / 入职信息 / 社保假勤` 正确刷 `sync_type` query param | IMPORT-04 / D-06 | 前端无自动化测试框架 | `npm run dev` → 打开 `/feishu/sync-logs` → 依次点 6 个 Tab，Network 面板确认 `GET /api/v1/feishu/sync-logs?sync_type=...&page=1&page_size=20` 参数变化 |
| 五色 badge `{success, updated, unmatched, mapping_failed, failed}` 视觉可辨（绿/蓝/橙/紫/红），0 值置灰 | IMPORT-04 / D-07 | 视觉验证 | `npm run dev` → 触发一次含 unmatched + mapping_failed 的同步（mock 或用 staging 数据）→ 截图 badge cluster 对比 Phase 30 SyncStatusCard 色板 |
| 「下载未匹配工号 CSV」按钮仅在 `unmatched_count > 0` 时启用；点击下载文件名 `sync-log-{log_id}-unmatched.csv` 单列 `employee_no` 最多 20 行 | IMPORT-03 / D-08 | 浏览器文件下载 + CSV 内容人工核对 | `npm run dev` → 构造 `unmatched_employee_nos` > 20 的日志 → 点击下载 → 打开 CSV 确认单列 header + ≤20 行 + 文件名匹配正则 |
| 详情抽屉展示 `error_message` / `unmatched_employee_nos` 全量列表 / `leading_zero_fallback_count` 黄字提示 | IMPORT-04 / D-07 | 视觉 + 交互 | `npm run dev` → 点击 badge → 抽屉打开 → 确认三块内容可见 |
| 「模式」列对 `sync_type='attendance'` 显示 full/incremental；其他 sync_type 显示 `—` | IMPORT-04 / D-04 | 视觉验证 | `npm run dev` → 打开 `/feishu/sync-logs` → 切到「全部」Tab → 核对 attendance 行显示模式 badge，其他行显示 `—` |
| SC4: HR 连续双击同步按钮，锁定期内看到 409 错误提示而非第二条 log；锁释放后触发，日志出现两条独立记录 | IMPORT-04 / D-15/D-16 | 需真实 Celery + Redis 环境观测竞态 | 启动 backend + Celery worker + Redis → 在 manual QA 页面连点两次「同步绩效」→ 确认第一次 202 + 第二次 409 + `feishu_sync_logs` 表中仅一条 running → 等待完成 → 第三次点击 → 确认新增第二条独立 log |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (via inline Wave 1+ creation — see Wave 0 Strategy)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (revision iter-1, 2026-04-21) — Per-Task Verification Map populated for all 9 tasks across 4 plans; Wave 0 ownership documented (inlined into TDD tasks per project pattern); `nyquist_compliant` flipped to true.
