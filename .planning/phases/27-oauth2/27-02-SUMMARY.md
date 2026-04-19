---
phase: 27-oauth2
plan: 02
subsystem: frontend
tags: [feishu, oauth2, auth-context, react-router, callback-page]
dependency_graph:
  requires:
    - Plan 27-01 (types/api.ts FeishuCallbackPayload, services/auth.ts feishuCallback, utils/feishuErrors.ts resolveFeishuError)
    - frontend/src/utils/roleAccess.ts getRoleHomePath
    - react-router-dom 7 useSearchParams + useNavigate
  provides:
    - AuthContextValue.loginWithFeishu(code, state) => Promise<UserProfile>
    - FeishuCallbackPage React component with processing/success/failed states
    - Public route /auth/feishu/callback registered in App.tsx
  affects:
    - Plan 27-03 (FeishuLoginPanel QR widget) — once QR scan completes, SDK-triggered redirect lands on this callback page which consumes the code/state via the new hook
tech_stack:
  added: []
  patterns:
    - useEffect + useRef hasRunRef guard pattern (防 StrictMode 双挂载)
    - useEffect cleanup via cancelled flag (防卸载后 setState)
    - navigate(..., { replace: true }) 防 code/state 进入浏览器历史栈 (T-27-03)
    - React 文本节点 {errorMessage} 自动 HTML escape (T-27-01)
key_files:
  created:
    - frontend/src/pages/FeishuCallbackPage.tsx
  modified:
    - frontend/src/hooks/useAuth.tsx
    - frontend/src/App.tsx
decisions:
  - 回调页使用单个 useEffect 处理 code/state 解析 + 后端调用 + 跳转，避免多 effect 竞态
  - hasRunRef 紧挨 useEffect 开头判定，即使 React StrictMode 双挂载也只执行一次真实请求
  - 错误文案全部来自前端静态 COPY 表 (feishuErrors.ts)，不信任后端原文 (T-27-01)
  - 三状态 UI 通过条件渲染共享同一 <section className="surface"> 容器，视觉语言与 Login.tsx 对齐
metrics:
  duration: ~4 minutes (230s)
  completed_date: 2026-04-19
  tasks_total: 3
  tasks_completed: 3
requirements:
  - FUI-02
  - FUI-04
---

# Phase 27 Plan 02: 扩展 useAuth 与新建 FeishuCallbackPage Summary

**One-liner:** 在 useAuth Context 新增 loginWithFeishu 并实现 `/auth/feishu/callback` 公开回调路由与三状态 UI，让飞书 302 重定向后浏览器可完成 JWT 获取与角色首页跳转。

## Outcome

为 Phase 27 下游 Plan 03 的二维码扫码后跳转链路交付 3 项改动：

1. `frontend/src/hooks/useAuth.tsx` — `AuthContextValue` 新增 `loginWithFeishu(code, state): Promise<UserProfile>`，内部依次：`feishuCallback(code, state)` → `storeAuthSession(response)` → `setUser(response.user)` → `setAccessToken(response.tokens.access_token)` → 返回 `response.user`。失败时不写 localStorage、不动 context state，异常原样抛出让调用方 `catch`。依赖数组保持 `[accessToken, isBootstrapping, user]` 不变。
2. `frontend/src/pages/FeishuCallbackPage.tsx` — 新文件，组件挂载时：(a) `useSearchParams` 解析 `code` / `state`；(b) 缺失则立即进入 `failed` 状态并映射到 `unknown_error` COPY；(c) 齐全则调 `loginWithFeishu`，成功 → `getRoleHomePath(role)`（或 `must_change_password` 时跳 `/settings`），失败 → `resolveFeishuError('backend', err).message`；所有 `navigate` 均带 `{ replace: true }` 防 code/state 进历史栈；`useRef hasRunRef` + `useEffect cleanup cancelled flag` 防 StrictMode 双挂载导致后端拒绝 "授权码已使用"。
3. `frontend/src/App.tsx` — 顶部 import 字母序插入 `FeishuCallbackPage`，路由表公开段 `LoginPage` 与 `Navigate /register` 之间插入一行 `<Route element={<FeishuCallbackPage />} path="/auth/feishu/callback" />`。该路由**不在**任何 `ProtectedRoute` 下（匿名可访问）。

`cd frontend && npm run lint` 与 `cd frontend && npm run build` 双通过。

## Tasks Completed

| Task | Name                                                          | Commit   | Files                                                |
| ---- | ------------------------------------------------------------- | -------- | ---------------------------------------------------- |
| 1    | useAuth 新增 loginWithFeishu                                  | 1834fbf  | frontend/src/hooks/useAuth.tsx                       |
| 2    | 新建 FeishuCallbackPage（处理/成功/失败三状态）                | 89285a2  | frontend/src/pages/FeishuCallbackPage.tsx            |
| 3    | App.tsx 注册 /auth/feishu/callback 公开路由                   | ef9606a  | frontend/src/App.tsx                                 |

## Key Changes

### frontend/src/hooks/useAuth.tsx (11 插入)

- Line 6：`feishuCallback as feishuCallbackRequest,` 按字母序插入 services/auth import 列表。
- AuthContextValue 类型新增 `loginWithFeishu: (code: string, state: string) => Promise<UserProfile>;`，放在 `login` 后、`register` 前。
- `handleLogin` 之后、`refreshProfile` 之前新增 `async function handleLoginWithFeishu(code, state)`：调 `feishuCallbackRequest` → `storeAuthSession` → `setUser` → `setAccessToken` → 返回 `response.user`。
- `useMemo` value 对象加入 `loginWithFeishu: handleLoginWithFeishu`，依赖数组保持 `[accessToken, isBootstrapping, user]` 不变。

### frontend/src/pages/FeishuCallbackPage.tsx (新文件，150 行)

- imports：`useEffect / useRef / useState` + `useNavigate / useSearchParams` + `useAuth / resolveFeishuError / getRoleHomePath`。
- `type CallbackState = 'processing' | 'success' | 'failed'` 三状态联合类型。
- `useEffect` 开头 `hasRunRef` 守卫 + `cancelled` flag 清理；`searchParams.get('code')` / `'state'` 缺失 → 立即 failed + `unknown_error` COPY；齐全 → `void run()` 异步处理成功/失败。
- 成功路径：`navigate(getRoleHomePath(profile.role), { replace: true })` 或 `navigate('/settings', { replace: true, state: { forcePasswordChange: true, from: getRoleHomePath(profile.role) } })`。
- 失败路径：`setErrorMessage(resolveFeishuError('backend', err).message)`。
- UI 三个条件分支共享 `<section className="surface animate-fade-up">` 居中卡片容器；failed 分支额外渲染 `<button className="action-primary" onClick={() => navigate('/login', { replace: true })}>返回登录</button>`。
- 严格无 `innerHTML` / `dangerouslySetInnerHTML` / `console.log` / `console.error`。

### frontend/src/App.tsx (2 插入)

- 第 18 行（import 段）：字母序插入 `import { FeishuCallbackPage } from "./pages/FeishuCallbackPage";` 紧邻 `FeishuConfigPage`。
- 第 424 行（路由表公开段）：在 `<Route element={<LoginPage />} path="/login" />` 之后、`<Route element={<Navigate replace to="/login" />} path="/register" />` 之前插入：
  ```tsx
  <Route element={<FeishuCallbackPage />} path="/auth/feishu/callback" />
  ```
- 其他路由、ProtectedRoute 嵌套、既有 HomePage / WorkspacePage / EmployeeScopedEvaluationPage 完全未动。

## Deviations from Plan

None — plan 原样执行，所有 action 中规定的代码片段 verbatim 落地。无需触发 Rule 1-3 自动修复；未触发 Rule 4 架构级决策。

## Verification

- `cd frontend && npm run lint` 退出码 0（tsc --noEmit 通过）。
- `cd frontend && npm run build` 退出码 0（tsc -b + vite build；产物 `dist/index.html` + `dist/assets/index-*.js/.css` 生成；chunk size 警告为既有、与本次改动无关）。
- Task 1 acceptance criteria 全绿（loginWithFeishu 签名、handleLoginWithFeishu 声明、feishuCallback 别名、useMemo value 字段、storeAuthSession 两处调用）。
- Task 2 acceptance criteria 全绿（文件存在、export function、useSearchParams、loginWithFeishu、resolveFeishuError、replace:true 出现 3 处 >= 2、无 innerHTML、hasRunRef）。
- Task 3 acceptance criteria 全绿（import、path、element、路由位置在第一个 ProtectedRoute 元素行号之前即 424<427）。

### Manual Test Plan 覆盖情况

| 项 | 描述 | 本 Plan 可触发 | 说明 |
|----|------|--------------|------|
| #2 | 访问 `/auth/feishu/callback?code=X&state=Y` → processing 骨架 | 部分可验（需手动打开浏览器） | 本 Plan 仅能静态验证组件存在；真实 code/state 需 Plan 03 + 后端 Phase 26 联动 |
| #3 | 无 query 访问 → 立即 failed 卡片 | **完全可验** | 直接 `http://localhost:5174/auth/feishu/callback` 即会触发 `resolveFeishuError('backend', new Error('缺少授权参数'))` |
| #7 | 工号未匹配 → employee_not_matched 中文文案 | 依赖 Plan 03 | 需真实飞书 code 返回后端 400 + "工号" detail 才能触发 |
| #8 | state 过期 → state_invalid_or_expired 文案 | 依赖 Plan 03 | 需后端 Redis state 过期（>300s） |
| #9 | 授权码重放 → code_expired_or_replayed 文案 | 依赖 Plan 03 | 需后端 code 防重放记录触发 |
| #12 | Redis 503 → redis_unavailable 文案 | 部分可验 | 可 `curl -X POST /api/v1/auth/feishu/callback` 手造 503 验证映射 |
| #14 | 返回登录按钮跳 `/login` | **完全可验** | 无 query 访问后点击按钮即可验证 |

完整链路验证（#2 / #7 / #8 / #9）需待 Plan 03 `FeishuLoginPanel` + 真实飞书扫码 + 后端 Phase 26 Redis/code 存活完成联调，本 Plan 只验证前端层契约。

## Threat Mitigations Applied

- **T-27-01** (XSS via error message)：`errorMessage` 只来自 `resolveFeishuError('backend', err).message`，该函数返回值来自 feishuErrors.ts 的前端静态 `COPY` 表；JSX 中通过 `{errorMessage}` 文本节点插值，React 自动 HTML escape；**未**使用 `innerHTML` / `dangerouslySetInnerHTML`。
- **T-27-03** (Information Disclosure 通过 code/state 泄漏)：(a) 3 处 `navigate` 调用全部带 `{ replace: true }`，code/state 不进历史栈；(b) 组件内无 `console.log` / `console.error` / `console.warn` / `console.debug`；(c) UI 渲染不展示 code / state 明文，只展示中文文案。grep 验证通过。
- **T-27-04** (Session Fixation)：前端只原样转发用户 URL 中的 code/state 给后端 Plan 26 `/auth/feishu/callback` 端点，由后端 Redis TTL 300s + 一次性消费 + code 防重放 600s 处理；前端不缓存 state、不复用旧 state。
- **T-27-06** (DoS / 卸载后 setState)：(a) `useEffect` 开头 `if (hasRunRef.current) return` 防 StrictMode 双挂载；(b) `cleanup` 设 `cancelled = true`；(c) `setState('success' / 'failed')` 前均检查 `if (cancelled) return` 。

## Threat Flags

None — 本 Plan 未引入新的网络端点、鉴权路径、文件访问模式或 schema 变更。所有威胁面早在 27-02-PLAN.md 的 `<threat_model>` 中登记，已全部应用 mitigate。

## Known Stubs

None — FeishuCallbackPage 三状态 UI 全部由 `useState<CallbackState>` 驱动，不存在硬编码空值 / placeholder 文本 / 未接线组件。`loginWithFeishu` 消费的 `feishuCallback` 服务函数与 `storeAuthSession` 均由 Plan 01 已完整交付。

## Self-Check

- [x] frontend/src/hooks/useAuth.tsx FOUND, modified (+11 lines diff)
- [x] frontend/src/pages/FeishuCallbackPage.tsx FOUND, new file (150 lines)
- [x] frontend/src/App.tsx FOUND, modified (+2 lines diff)
- [x] Commit 1834fbf FOUND in git log
- [x] Commit 89285a2 FOUND in git log
- [x] Commit ef9606a FOUND in git log
- [x] `cd frontend && npm run lint` exit 0 — PASSED
- [x] `cd frontend && npm run build` exit 0 — PASSED

## Self-Check: PASSED
