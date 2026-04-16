---
phase: 23
slug: eligibility-import
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 (backend) / tsc --noEmit (frontend) |
| **Config file** | `backend/tests/` (pytest), `frontend/tsconfig.json` (tsc) |
| **Quick run command** | `python -m pytest backend/tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest backend/tests/ -q && cd frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest backend/tests/ -q && cd frontend && npx tsc --noEmit`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | ELIGIMP-02 | — | N/A | unit | `python -m pytest backend/tests/test_import_service.py -x -q` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | FEISHU-01 | — | N/A | unit | `python -m pytest backend/tests/test_feishu_service.py -x -q` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 2 | ELIGIMP-01 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |
| 23-02-02 | 02 | 2 | ELIGIMP-03 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_import_eligibility.py` — stubs for ELIGIMP-02 (new import types)
- [ ] `backend/tests/test_feishu_rate_limit.py` — stubs for FEISHU-01 (rate limiter)

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 4 Tab 切换展示 | ELIGIMP-01 | 需要浏览器 | 1. 打开调薪资格管理页面 2. 验证 4 个 Tab 可切换 |
| 拖拽连线字段映射 | ELIGIMP-03 | 需要浏览器交互 | 1. 输入飞书 URL 2. 拖拽建立字段映射 3. 确认映射正确 |
| 导入结果统计+错误导出 | ELIGIMP-04 | 需要完整服务栈 | 1. 导入含错误的 Excel 2. 验证统计数字 3. 导出错误 CSV |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
