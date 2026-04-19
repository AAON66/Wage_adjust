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

> **D-17 amendment (2026-04-19)**：QR 链路已从 Phase 27 移除，相关 manual test 项（原 QR 扫码流程、3 分钟过期刷新、SDK 加载失败 smoke test）已删除。剩余项均围绕整页跳转授权。

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 整页跳转授权登录完整流程 | FUI-01 (post D-17) | 依赖飞书开放平台真实授权 | 登录页加载 → 右侧面板显示「使用飞书账号登录」按钮 → 点击 → 跳飞书授权页 → 同意 → 回 `/auth/feishu/callback` → 进入角色首页 |
| `/auth/feishu/callback` 三态 UI | FUI-02 | 骨架/成功/错误涉及真实重定向与 localStorage | 触发成功路径；制造 `state` 不匹配触发失败；观察 loading 骨架与错误卡片 |
| 错误分类中文文案 | FUI-04 | 需手动触发：取消授权 / 使用未匹配工号 / 断网 / 手动篡改 state | 逐类触发并断言文案与 `feishuErrors.ts` 映射一致 |
| 现有邮箱密码登录 100% 保留 | LOGIN-04 | 回归验证 | 登录 admin/hrbp/manager/employee 四个角色，确认无 UI 或行为变化 |
| `must_change_password` 分支 | FAUTH | 飞书登录成功后若后端返回 `must_change_password=true`，应跳 `/settings` 而不是角色首页 | 用 must_change_password=true 的已绑定账号走飞书授权流程 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify (tsc / build / backend pytest) or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (A4, A5 假设验证)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (lint) / 60s (full)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
