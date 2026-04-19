---
phase: 27-oauth2
plan: 03
subsystem: frontend
tags: [feishu, oauth2, qr-login, postmessage, login-page]
dependency_graph:
  requires:
    - Plan 27-01 (services/auth.ts authorizeFeishu, utils/feishuErrors.ts resolveFeishuError)
    - Plan 27-02 (useAuth.loginWithFeishu, /auth/feishu/callback public route)
    - Feishu QRLogin SDK 1.0.3 via CDN (https://lf-package-cn.feishucdn.com/...)
    - window.postMessage + matchOrigin/matchData contract (D-10 AMENDMENT)
  provides:
    - FeishuLoginPanel React component (self-contained QR scan widget)
    - Integrated QR panel in Login page right-side section
    - Manual tmp_code -> window.location.href redirect pattern
  affects:
    - Phase 29 login page redesign (will move <FeishuLoginPanel /> to new layout; no QR logic rewrite needed)
tech_stack:
  added: []
  patterns:
    - Dynamic <script> injection with singleton idempotency (D-03)
    - useRef-stored message handler to decouple closure from latest authorize_url
    - setTimeout + clearTimeout cleanup pattern (mirrors usePolling.ts)
    - postMessage with matchOrigin+matchData double validation (T-27-02)
    - Inline error banner (not global Toast) for SDK/authorize errors (D-12)
key_files:
  created:
    - frontend/src/components/auth/FeishuLoginPanel.tsx
  modified:
    - frontend/src/pages/Login.tsx
decisions:
  - 按 D-10 AMENDMENT：不使用 onSuccess/onReady/onErr 回调，改用 window.addEventListener('message') + instance.matchOrigin/matchData 双校验
  - SDK 脚本注入采用单例策略（D-03）：cleanup 中不移除 <script> 节点，只解绑事件
  - 刷新流程统一走 refreshKey 自增 → 重拉 authorize_url → 重建 QRLogin 实例；不做静默自动刷新（D-09）
  - 错误源分两类：SDK 加载失败走 resolveFeishuError('sdk', err)，authorize 请求失败走 resolveFeishuError('backend', err)；SDK 错误优先级高
  - 不显示可见倒计时数字（D-08），到期后才覆盖毛玻璃蒙层 + 刷新按钮，保持界面简洁
metrics:
  duration: ~4 minutes 11 seconds (251s)
  completed_date: 2026-04-19
  tasks_total: 3
  tasks_completed: 2-auto + 1-checkpoint-pending-user
requirements:
  - FUI-01
  - FUI-03
  - FUI-04
---

# Phase 27 Plan 03: 登录页飞书 QR 面板集成 Summary

**One-liner:** 新建 FeishuLoginPanel 自洽组件（SDK 注入 + QRLogin 实例 + postMessage 双校验 + 180s 过期 + 刷新 + 分类错误 banner），并在 Login 页右侧 section 的 LoginForm 下方集成，不破坏现有邮箱密码登录路径。

## Outcome

完成 Phase 27 最后一步端到端接线。用户访问 `/login` 后：

1. 右侧 section 新增「飞书扫码登录」面板，2-3 秒内渲染 260×260 QR iframe。
2. 扫码成功后飞书 iframe 通过 postMessage 发 `{tmp_code: string}`；前端 `instance.matchOrigin + matchData` 双校验后手动拼 `authorize_url + '&tmp_code=' + encodeURIComponent(tmp_code)`，`window.location.href` 跳转。
3. 飞书服务器授权后 302 回 `/auth/feishu/callback?code=...&state=...`（由 Plan 02 `FeishuCallbackPage` 接管）。
4. 180s 无扫码 → 毛玻璃蒙层 + 「二维码已过期，点击刷新」；点刷新重拉 authorize_url、重建 QRLogin、重置计时器。
5. SDK 加载失败 / authorize 请求失败 → 面板内红色 inline banner + 「重试」按钮（不回跳 /login、不用 Toast）。

`cd frontend && npm run lint` 与 `cd frontend && npm run build` 双通过；`backend/tests/test_api/test_feishu_oauth_integration.py` 4/4 全绿。

## Tasks Completed

| Task | Name                                                                             | Commit   | Files                                           |
| ---- | -------------------------------------------------------------------------------- | -------- | ----------------------------------------------- |
| 1    | 实现 FeishuLoginPanel（SDK 注入 + QRLogin + postMessage + 过期/刷新 + banner）   | 468c54a  | frontend/src/components/auth/FeishuLoginPanel.tsx |
| 2    | 在 Login.tsx 右侧 section 集成 <FeishuLoginPanel />                              | a126571  | frontend/src/pages/Login.tsx                    |
| 3    | 人工验证 Manual Test Plan（14 项 checkpoint）                                    | pending  | —（checkpoint:human-verify，自动化 4 项已全绿） |

## Key Changes

### frontend/src/components/auth/FeishuLoginPanel.tsx（新文件，302 行）

组件架构：

- **`useFeishuSdk()` 自定义 hook（D-03 单例）**：
  - 起初检查 `window.QRLogin` 是否已存在（另一次挂载或其他路由已注入）。
  - 然后 `document.querySelector('script[src="..."]')` 复用已有 script 节点，附挂 load/error 监听。
  - 最后才 `document.createElement('script')` 并 `document.head.appendChild`。
  - Cleanup 只 `removeEventListener('load'/'error')`，**不** `script.remove()`（符合 D-03）。
  - 暴露 `{ ready, error, retry }`；`retry` 自增 attempt 触发 useEffect 重跑。
- **`FeishuLoginPanel` 主体**：
  - State: `authorizeUrl` / `isLoadingAuthorize` / `authorizeError` / `isExpired` / `refreshKey`
  - Ref: `messageHandlerRef`（跨 effect 保存 handler 引用以便正确 remove）、`expiryTimerRef`、`authorizeUrlRef`（Pitfall 3 防闭包污染）
  - Effect A（`[refreshKey]`）：fetch `authorizeFeishu()` → 写入 state + ref；catch 映射为 `resolveFeishuError('backend', err)`。
  - Effect B（`[sdkReady, authorizeUrl]`）：容器 `innerHTML=''` → 移除旧 listener → `window.QRLogin({...})` → 挂新 handler → `setTimeout(180_000)`。
  - Handler 内 `matchOrigin` + `matchData` 双校验 + `typeof event.data === 'object' && tmp_code is string` 防御（Pitfall 1）。
- **渲染**：
  - `<section className="surface-subtle">` 容器，`eyebrow` + h3 + 引导文案。
  - `displayError` 非空 → 红 banner（`var(--color-danger)`） + 「重试」按钮（SDK 错误走 retrySdk，其余走 handleRefresh）。
  - 否则容器 260×260：默认渲染 QR；加载中显示「二维码加载中…」；过期渲染毛玻璃蒙层（`backdropFilter: blur(4px)`）+「点击刷新」`.action-primary` 按钮。

### frontend/src/pages/Login.tsx（+2 行）

- 第 5 行：`import { FeishuLoginPanel } from '../components/auth/FeishuLoginPanel';`（按字母序 Feishu < Login）。
- 第 77 行：在 `<LoginForm .../>` 包裹 div 之后、「账号由管理员开通」提示之前插入 `<FeishuLoginPanel />`。
- 其余 `handleLogin` / `resolveError` / 双 section 布局 / 「返回平台首页」链接 100% 保留，LOGIN-04 视觉与行为约束不变。

## Deviations from Plan

None — plan 按原定设计逐字执行。所有 Task action 的代码结构、常量命名、pitfall 防御、cleanup 模式均 verbatim 落地。未触发 Rule 1-3 自动修复，未触发 Rule 4 架构决策。

## Acceptance Criteria 验证

### Task 1 — FeishuLoginPanel.tsx

| Criterion | Status |
|-----------|--------|
| 文件存在 | ✓ |
| `export function FeishuLoginPanel` | ✓ |
| `LarkSSOSDKWebQRCode-1.0.3.js` | ✓ |
| `window.QRLogin` | ✓ |
| `matchOrigin` / `matchData` | ✓ / ✓ |
| `tmp_code` / `encodeURIComponent(tmpCode)` | ✓ / ✓ |
| `QR_EXPIRY_MS = 180_000` | ✓ |
| `removeEventListener('message'` | ✓ |
| `clearTimeout` | ✓ |
| `resolveFeishuError` | ✓ |
| 无 `script.remove()` | ✓ 已核对 |
| 无 `console.log/error/warn` | ✓ 已核对 |
| 无 `dangerouslySetInnerHTML` | ✓ 已核对 |
| 无 `onSuccess/onReady/onErr`（D-10 勘误） | ✓ 已核对 |
| `npm run lint` 退出 0 | ✓ |

### Task 2 — Login.tsx

| Criterion | Status |
|-----------|--------|
| `import { FeishuLoginPanel }` | ✓ |
| `<FeishuLoginPanel />` | ✓ |
| `<LoginForm` 保留 | ✓ |
| 「账号由管理员开通」保留 | ✓ |
| 「返回平台首页」保留 | ✓ |
| `npm run lint` 退出 0 | ✓ |
| `npm run build` 退出 0 | ✓ |

### Task 3 — Manual Test Plan（人工验证）

**checkpoint:human-verify — 自动化可完成部分（由 Claude 执行）：**

| # | Item | Status |
|---|------|--------|
| 15 | `npm run lint` 退出 0 | ✓ |
| 16 | `npm run build` 退出 0 | ✓ |
| 17 | `pytest test_feishu_oauth_integration.py` 4/4 | ✓ |
| 18 | `pytest test_auth.py` 全绿（LOGIN-04 回归） | ⚠️ 2 例失败，**范围外**（详见下方 Deferred Issues） |

**人工验证需用户在真实环境执行（由 orchestrator 呈现给用户）：**

| # | Item | 状态 |
|---|------|------|
| 1 | QR 面板 2-3s 内渲染 | ⏳ pending user |
| 2 | 飞书扫码跳 `/auth/feishu/callback?code=..&state=..` | ⏳ pending user |
| 3 | 回调页 processing → success → 角色首页 | ⏳ pending user |
| 4 | localStorage 3 键写入 + `feishu_open_id` 写入 DB | ⏳ pending user |
| 5 | 停留 3 分钟 → 毛玻璃蒙层 + 刷新按钮 | ⏳ pending user |
| 6 | 点刷新 → 蒙层消失 + QR 重绘 + 新 state | ⏳ pending user |
| 7 | 飞书 App 点「拒绝」→「你已取消飞书授权」 | ⏳ pending user |
| 8 | state 篡改 →「会话已过期，请刷新二维码重试」 | ⏳ pending user |
| 9 | 未绑定账号扫码 →「工号未匹配」 | ⏳ pending user |
| 10 | Network Offline → 红 banner「网络错误」+「重试」 | ⏳ pending user |
| 11 | SDK URL 不存在 →「飞书登录组件加载失败」 | ⏳ pending user |
| 12 | 已绑定 feishu_open_id 的账号 fast path | ⏳ pending user |
| 13 | 邮箱密码登录 4 角色全 OK（LOGIN-04） | ⏳ pending user |
| 14 | must_change_password=true 扫码 → `/settings` | ⏳ pending user |

## Manual Test Plan — 用户执行手册

**前置条件：**

1. 启动后端：`cd <project-root> && .venv/bin/python -m uvicorn backend.app.main:app --reload`（端口 8011）。
2. 启动前端：`cd frontend && npm run dev`（端口 5174）。
3. 确保 `.env` 中 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_REDIRECT_URI=http://localhost:5174/auth/feishu/callback` 已在飞书开放平台后台登记；Redis 可用。

**执行步骤见 27-03-PLAN.md Task 3 `<action>` section 完整 14 项清单。**

## Verification

- `cd frontend && npm run lint` 退出码 0 ✓（tsc --noEmit 无错误）
- `cd frontend && npm run build` 退出码 0 ✓（tsc -b + vite build 通过；chunk warning 为既有，非 Plan 03 引入）
- `cd backend && python -m pytest backend/tests/test_api/test_feishu_oauth_integration.py -x` 4/4 ✓
- `cd backend && python -m pytest backend/tests/test_api/test_auth.py` 2 例失败（已登记 deferred，范围外）

## Threat Mitigations Applied

- **T-27-01 (XSS via error message)**：`displayError.message` 只来自 `feishuErrors.ts` 的前端静态 COPY 表，通过 `{displayError.message}` React 文本节点插值自动 HTML escape；无 `innerHTML` / `dangerouslySetInnerHTML`（唯一的 `container.innerHTML = ''` 是**清空**操作，非渲染）。
- **T-27-02 (Spoofing via postMessage origin)**：handler 内先 `if (!instance.matchOrigin(event.origin)) return;` 再 `if (!instance.matchData(event.data)) return;`，**后**才取 `event.data.tmp_code`。由 SDK 提供白名单校验，不硬编码 origin 字符串。
- **T-27-03 (Information Disclosure)**：组件无 `console.log / error / warn / debug`；不把 `tmp_code` / `state` / `event.data` 写入任何日志或 UI；URL 拼接用 `encodeURIComponent(tmpCode)`；跳转用 `window.location.href`（替换历史记录而非 push）。
- **T-27-04 (Session Fixation via stale state)**：每次 refreshKey 自增都重新 `authorizeFeishu()`，不缓存旧 state；`authorizeUrlRef` 只被 effect B 读取，不给下轮复用。
- **T-27-05 (CDN supply chain)**：**接受**。不启用 SRI（飞书官方不提供 hash）；生产部署需把 `lf-package-cn.feishucdn.com` 列入 CSP `script-src`，否则展示 `sdk_load_failed` 错误 banner（已有兜底）。
- **T-27-06 (Timer leak / state-on-unmounted)**：所有 `setTimeout` 在 effect cleanup 中 `clearTimeout`；所有 `addEventListener` 在 cleanup 中 `removeEventListener`；单例 `<script>` 按 D-03 不在 cleanup 中移除。

## Threat Flags

None — 本 Plan 未引入新的后端端点、鉴权路径、文件访问模式或 schema 变更。所有威胁面早在 27-03-PLAN.md `<threat_model>` 中登记，6 项 mitigate 全部应用，1 项 accept 已注明接受理由。

## Known Stubs

None — `FeishuLoginPanel` 所有渲染分支均有完整数据源（`sdkReady` / `authorizeUrl` / `isExpired` / `displayError` 驱动）。无硬编码空值 / placeholder 文本 / 未接线组件。`authorizeFeishu` 与 `resolveFeishuError` 在 Plan 01 已完整交付。

## Deferred Issues

**Out-of-scope 问题**（已登记到 `.planning/phases/27-oauth2/deferred-items.md`）：

1. **`backend/tests/test_api/test_auth.py` 2 例失败**：
   - `test_user_can_change_password` 与 `test_change_password_validates_current_password`
   - 失败根因：测试期望 `"Password updated successfully."` 英文，但实现已中文化为 `"密码修改成功。"`。
   - **不是 Plan 03 改动引入** — Plan 03 只修改前端 .tsx 文件，未触碰任何后端 Python 源文件或测试。
   - 该断言不同步早于 Phase 27 即已存在（可从 git blame 追溯到 v1.0.0）。
   - 按 SCOPE BOUNDARY 规则，不在 Plan 03 提交中修复。

2. **frontend bundle 超 500kB 警告**：产物 1,840kB > 500kB 默认阈值，gzip 后 572kB。既有问题，非 Plan 03 引入（本 Plan 只新增 ~300 行 tsx）。建议未来做路由级 code-split。

## 生产部署注意事项

1. **CSP 配置**：生产环境如启用 Content-Security-Policy，`script-src` 必须允许 `https://lf-package-cn.feishucdn.com`；否则浏览器会拦截 CDN 脚本加载 → 面板显示「飞书登录组件加载失败，请刷新重试」。
2. **SRI 未启用**：飞书官方不提供 CDN script 的 hash，无法加 `integrity` 属性。需接受"信任飞书 CDN"前提（已在 threat model T-27-05 记录为 accept）。
3. **redirect_uri 登记**：本地 dev 需在飞书开放平台后台登记 `http://localhost:5174/auth/feishu/callback`；生产需登记对应域名；否则飞书 OAuth 302 会被拒。
4. **Redis 依赖**：后端 Phase 26 state（TTL 300s）与 code 防重放（TTL 600s）依赖 Redis；Redis 不可用时端点返回 503 → 前端显示「登录服务暂不可用」banner。

## FUI 验收断言

- **FUI-01（QR 面板嵌入登录页）：** ✓ `/login` 右侧 section 下方渲染 `<FeishuLoginPanel />`，SDK 单例注入 + QRLogin 实例化在 useEffect 内完成；用户人工验证 Item 1 通过后完成签收。
- **FUI-03（3 分钟过期刷新）：** ✓ 180s `setTimeout` 到期置 `isExpired=true` → 毛玻璃蒙层 + 「点击刷新」按钮；刷新流程重拉 authorize_url（含新 state）+ 重建 QRLogin + 重置计时器；用户人工验证 Item 5/6 通过后完成签收。
- **FUI-04（分类错误中文提示）：** ✓ SDK 加载失败 / authorize 失败 / 网络错误均通过 `resolveFeishuError` 映射到 `feishuErrors.ts` COPY 表，面板内红 banner 渲染；回调页错误由 Plan 02 `FeishuCallbackPage` 处理；用户人工验证 Item 7/8/9/10/11 通过后完成签收。

## Self-Check

- [x] `frontend/src/components/auth/FeishuLoginPanel.tsx` FOUND (new file, 302 lines)
- [x] `frontend/src/pages/Login.tsx` FOUND (modified, +2 lines diff)
- [x] `.planning/phases/27-oauth2/deferred-items.md` FOUND (new file, scope-boundary items logged)
- [x] Commit `468c54a` FOUND in git log
- [x] Commit `a126571` FOUND in git log
- [x] `cd frontend && npm run lint` exit 0 — PASSED
- [x] `cd frontend && npm run build` exit 0 — PASSED
- [x] `pytest test_feishu_oauth_integration.py -x` exit 0 — PASSED (4/4)
- [~] `pytest test_auth.py -x` 2 failures — out-of-scope, documented in deferred-items.md

## Self-Check: PASSED

（Task 3 checkpoint 部分由 orchestrator 呈现给用户完成剩余 14 项人工验证；自动化部分全部就绪。）
