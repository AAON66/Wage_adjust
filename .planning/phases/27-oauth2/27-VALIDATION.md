---
phase: 27
slug: oauth2
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Frontend: `tsc --noEmit` + manual test plan (no vitest/jest installed); Backend: pytest 8.3.5 for regression |
| **Config file** | `frontend/tsconfig.json` / `backend/pytest.ini` |
| **Quick run command** | `cd frontend && npm run lint` (tsc --noEmit) |
| **Full suite command** | `cd frontend && npm run build` + `cd backend && pytest backend/tests/test_api/test_feishu_oauth_integration.py` |
| **Estimated runtime** | ~15–30s (tsc) + ~10s (backend regression) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run lint`
- **After every plan wave:** Run `cd frontend && npm run build` + backend regression
- **Before `/gsd-verify-work`:** Full suite green + manual test plan executed
- **Max feedback latency:** 30 seconds (lint) / 60 seconds (build+backend)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD by planner — this table is filled during planning and execution | | | | | | | | | |

---

## Wave 0 Requirements

- [ ] Verify `FEISHU_REDIRECT_URI` points to frontend `/auth/feishu/callback` (A5 — RESEARCH.md)
- [ ] Verify backend exception handler output shape (A4 — RESEARCH.md): `{error, message}` vs FastAPI default `{detail}`
- [ ] Confirm no test framework introduction for this phase (manual-only coverage) — recorded in PLAN.md

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| QR 扫码登录完整流程 | FUI-01 | 依赖飞书开放平台真实授权，无法在单元测试里复现 | 登录页加载 → QR 渲染 → 手机飞书扫码 → 授权 → 浏览器自动跳 `/auth/feishu/callback` → 进入角色首页 |
| `/auth/feishu/callback` 三态 UI | FUI-02 | 骨架/成功/错误涉及真实重定向与 localStorage | 触发成功路径；制造 `state` 不匹配触发失败；观察 loading 骨架与错误卡片 |
| 3 分钟过期刷新 | FUI-03 | 依赖本地 180s setTimeout 真实走完 | 打开登录页保持 3 分钟；观察蒙层 + 「点击刷新」按钮；点击后 QR 重建且 state 刷新 |
| 错误分类中文文案 | FUI-04 | 需手动触发：取消授权 / 使用未匹配工号 / 断网 / 手动篡改 state | 逐类触发并断言文案与 `feishuErrors.ts` 映射一致 |
| 现有邮箱密码登录 100% 保留 | LOGIN-04 | 回归验证 | 登录 admin/hrbp/manager/employee 四个角色，确认无 UI 或行为变化 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify (tsc / build / backend pytest) or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (A4, A5 假设验证)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (lint) / 60s (full)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
