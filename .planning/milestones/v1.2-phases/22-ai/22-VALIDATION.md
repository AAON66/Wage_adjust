---
phase: 22
slug: ai
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 (backend) / tsc --noEmit (frontend) |
| **Config file** | `backend/tests/` (pytest), `frontend/tsconfig.json` (tsc) |
| **Quick run command** | `python -m pytest backend/tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest backend/tests/ -q && cd frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest backend/tests/ -q && cd frontend && npx tsc --noEmit`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | ASYNC-02 | — | N/A | unit | `python -m pytest backend/tests/test_evaluation_tasks.py -x -q` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | ASYNC-03 | — | N/A | unit | `python -m pytest backend/tests/test_import_tasks.py -x -q` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 1 | ASYNC-02 | — | N/A | integration | `python -m pytest backend/tests/test_tasks_api.py -x -q` | ❌ W0 | ⬜ pending |
| 22-03-01 | 03 | 2 | ASYNC-02 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_evaluation_tasks.py` — stubs for ASYNC-02 (Celery evaluation task)
- [ ] `backend/tests/test_import_tasks.py` — stubs for ASYNC-03 (Celery import task)
- [ ] `backend/tests/test_tasks_api.py` — stubs for task polling endpoint

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 前端轮询进度显示 | ASYNC-02, ASYNC-03 | 需要浏览器环境 + Redis + Celery worker | 1. 启动 Redis + Worker 2. 触发评估 3. 观察状态文字变化 4. 确认完成后自动刷新 |
| Worker 隔离：单任务失败不影响其他 | ASYNC-02 | 需要实际 worker 进程 | 1. 提交两个评估任务 2. 模拟第一个 LLM 超时 3. 确认第二个正常完成 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
