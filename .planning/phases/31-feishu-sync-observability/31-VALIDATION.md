---
phase: 31
slug: feishu-sync-observability
status: draft
nyquist_compliant: false
wave_0_complete: false
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

## Per-Task Verification Map

*Filled by planner after plans are drafted. Each task row links `task_id → plan → wave → REQ-ID → threat_ref → secure_behavior → test type → automated command → file_exists → status`.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *TBD by planner* | | | | | | | | | |

---

## Wave 0 Requirements

Test file stubs that must exist before Wave 1 can begin (per RESEARCH.md §Validation Architecture). Planner should assign these to Wave 0 tasks:

- [ ] `backend/tests/test_feishu_sync_log_model.py` — sync_type NOT NULL + mapping_failed_count DEFAULT 0 stubs
- [ ] `backend/tests/test_feishu_sync_log_migration.py` — Alembic upgrade/downgrade + backfill stubs
- [ ] `backend/tests/test_feishu_service_helper.py` — `_with_sync_log` running/terminal/failed path stubs
- [ ] `backend/tests/test_feishu_service_counters.py` — `_SyncCounters` dataclass + partial derivation stubs
- [ ] `backend/tests/test_feishu_service_sync_performance.py` — counters fill stubs (4 sync methods × 1 test file each acceptable or consolidated)
- [ ] `backend/tests/test_feishu_service_sync_salary_adjustments.py`
- [ ] `backend/tests/test_feishu_service_sync_hire_info.py`
- [ ] `backend/tests/test_feishu_service_sync_non_statutory_leave.py`
- [ ] `backend/tests/test_feishu_service_lock_bucket.py` — `is_sync_running(sync_type)` per-type locking stubs
- [ ] `backend/tests/test_feishu_sync_tasks_keys.py` — `performance_grades → performance` key rename + alias stubs
- [ ] `backend/tests/test_feishu_api_sync_logs.py` — `GET /feishu/sync-logs?sync_type=&page=` + role gate stubs
- [ ] `backend/tests/test_feishu_api_unmatched_csv.py` — CSV endpoint stubs (20-row cap, filename, role gate)
- [ ] `backend/tests/test_feishu_api_trigger_409.py` — 409 does NOT write log, SC4 two-records-after-release

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
| SC4: HR 连续双击同步按钮，锁定期内看到 409 错误提示而非第二条 log；锁释放后触发，日志出现两条独立记录 | IMPORT-04 / D-15/D-16 | 需真实 Celery + Redis 环境观测竞态 | 启动 backend + Celery worker + Redis → 在 manual QA 页面连点两次「同步绩效」→ 确认第一次 202 + 第二次 409 + `feishu_sync_logs` 表中仅一条 running → 等待完成 → 第三次点击 → 确认新增第二条独立 log |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
