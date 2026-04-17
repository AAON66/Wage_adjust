---
phase: 25
slug: tech-debt-cleanup
status: validated
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-17
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Backend)** | pytest 8.3.5 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest backend/tests/test_eval_pipeline.py -x -q` |
| **Full suite command** | `python -m pytest backend/tests/ -x -q` |
| **Frontend type check** | `cd frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~5 seconds (backend), ~10 seconds (frontend tsc) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/test_eval_pipeline.py -x -q`
- **After every plan wave:** Run `python -m pytest backend/tests/ -x -q && cd frontend && npx tsc --noEmit`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | DEBT-01 | T-25-01 | InMemoryRateLimiter 从 core 导入，无本地副本 | unit | `python -m pytest backend/tests/test_eval_pipeline.py::test_redis_rate_limiter_fallback -x` | ✅ | ✅ green |
| 25-01-02 | 01 | 1 | DEBT-02 | T-25-02 | FeishuSyncPanel 使用 useTaskPolling，显示进度 | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework or fixtures needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FeishuSyncPanel 使用 useTaskPolling hook 并显示进度条 | DEBT-02 | 项目无前端组件测试框架（无 jest/vitest），仅 tsc 编译检查 | 1. grep 确认 `useTaskPolling` import 和调用存在<br>2. grep 确认无 `setTimeout` 和 `getSyncStatus` 残留<br>3. grep 确认 `progress.processed` 进度显示存在<br>4. `npx tsc --noEmit` 编译通过 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter — blocked by DEBT-02 manual-only

**Approval:** validated 2026-04-17 (partial — 1 automated, 1 manual-only)

---

## Validation Audit 2026-04-17

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 0 |
| Escalated | 1 (DEBT-02 → manual-only) |

_Audited: 2026-04-17_
_Auditor: Claude (validate-phase orchestrator)_
