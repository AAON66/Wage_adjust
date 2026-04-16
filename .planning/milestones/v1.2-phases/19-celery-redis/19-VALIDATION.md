---
phase: 19
slug: celery-redis
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
updated: 2026-04-09
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | backend/tests/ (existing test structure) |
| **Quick run command** | `python3 -m pytest backend/tests/test_celery_app.py backend/tests/test_api/test_health.py -q --timeout=30` |
| **Full suite command** | `python3 -m pytest backend/tests/ -v --timeout=60` |
| **Phase gate command** | `bash scripts/verify_celery_runtime.sh` |
| **Estimated runtime** | unit feedback ~30s; Docker runtime proof up to ~120s |

---

## Sampling Rate

- **After code-task commits:** Run targeted unit checks within 30 seconds:
  - `python3 -m pytest backend/tests/test_celery_app.py -q --timeout=30`
  - `python3 -m pytest backend/tests/test_api/test_health.py -q --timeout=30`
- **After runtime-proof task:** Run `bash scripts/verify_celery_runtime.sh` as the slower phase gate
- **After every plan wave:** Run `python3 -m pytest backend/tests/ -v --timeout=60`
- **Before `/gsd-verify-work`:** Full suite must be green and `19-03-runtime-proof.log` must contain `PHASE19_PROOF=ok`
- **Max feedback latency:** 30 seconds for unit tasks; 120 seconds for the Docker-backed runtime gate

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | ASYNC-01 | T-19-01 | Celery app config / task registration stays intact | unit | `python3 -m pytest backend/tests/test_celery_app.py -q --timeout=30` | ✅ | existing |
| 19-02-01 | 02 | 2 | ASYNC-04 | — | health endpoint degrades safely when worker unavailable | unit | `python3 -m pytest backend/tests/test_api/test_health.py -q --timeout=30` | ✅ | existing |
| 19-02-02 | 02 | 2 | ASYNC-04 | — | docker compose syntax remains valid | smoke | `docker compose config --quiet` | ✅ | existing |
| 19-03-01 | 03 | 3 | ASYNC-01 | T-19-06 | SessionLocal bind matches worker dispose target and reconnects after dispose | unit | `python3 -m pytest backend/tests/test_celery_app.py -q --timeout=30` | ✅ | planned update |
| 19-03-02 | 03 | 3 | ASYNC-01, ASYNC-04 | T-19-07, T-19-08 | Redis -> queue -> worker -> result runtime proof and traceability closure | phase-gate | `bash scripts/verify_celery_runtime.sh` | ❌ W3 | pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/test_celery_app.py` — 已存在，覆盖 Celery app 基础配置与 task 注册
- [x] `backend/tests/test_api/test_health.py` — 已存在，覆盖 `/api/v1/health/celery`
- [ ] `scripts/celery_runtime_probe.py` — 由 19-03 创建，用于稳定打印 task_id / result
- [ ] `scripts/verify_celery_runtime.sh` — 由 19-03 创建，用于生成 Phase 19 runtime proof

*初始 Wave 0 测试缺口已关闭；19-03 新增的是 phase-gate 级运行时验证工件。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker daemon availability | ASYNC-01, ASYNC-04 | 本地环境可能未启动 Docker | 若 `bash scripts/verify_celery_runtime.sh` 报 Docker 不可用，先启动 Docker Desktop/daemon，再重跑脚本 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or a defined phase-gate command
- [x] Sampling continuity maintained: unit feedback stays under 30s for code tasks
- [x] Wave 0 covers pre-existing Celery and health endpoint tests
- [x] No watch-mode flags
- [x] Docker runtime proof classified as a slower phase gate rather than quick feedback
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
