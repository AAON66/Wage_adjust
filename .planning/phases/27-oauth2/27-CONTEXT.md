# Phase 27: 飞书 OAuth2 前端集成 - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

前端集成飞书 OAuth2 扫码登录：在登录页嵌入飞书 QR 扫码面板，新增 `/auth/feishu/callback` 路由处理 OAuth 回调并签发 JWT，实现二维码 3 分钟过期刷新与分类中文错误提示。不做粒子动态背景（Phase 28）与登录页完整双栏重设计（Phase 29），现有邮箱密码登录流程保持不变。

</domain>

<decisions>
## Implementation Decisions

### QR SDK 加载与初始化
- **D-01:** 飞书 QR SDK 通过官方 CDN 脚本动态注入加载（`useEffect` 内 `document.createElement('script')` 指向 `https://lf-package-cn.feishucdn.com/...QRLogin.js`，onload 后调用 `window.QRLogin(...)`）；不使用 npm 包，不自实现二维码获取与轮询。
- **D-02:** `authorize_url` 与 `state` 在 `FeishuLoginPanel` 组件挂载时调用后端 `GET /api/v1/auth/feishu/authorize` 一次获取，作为 `goto` 传入 `QRLogin` 配置。不做延迟懒加载，不做定时器预拉取，与后端 state Redis TTL 300s 匹配。
- **D-03:** 脚本注入要处理 onerror / CSP 阻塞：脚本加载失败时显示错误状态（见 D-11），并在下一次重试或刷新时重新注入。组件卸载时不必移除已加载的全局脚本（单例模式）。

### 回调路由形态
- **D-04:** 新增独立路由 `/auth/feishu/callback` 对应独立组件 `FeishuCallbackPage`，路由在 `App.tsx` 中注册为公开路由（不包 ProtectedRoute）。
- **D-05:** `FeishuCallbackPage` 挂载时用 `useSearchParams` 解析 URL 的 `code` / `state` → 调用 `useAuth.loginWithFeishu(code, state)` → 成功后用 `useNavigate(getRoleHomePath(role), { replace: true })` 跳转到角色首页；若 `must_change_password` 为 true，沿用 `Login.tsx` 现有逻辑跳 `/settings`。
- **D-06:** 回调页可见 UI 分三种状态：(1) 处理中 → 显示 `surface` 风格骨架卡片「正在完成飞书登录…」；(2) 成功 → 短暂停留立即跳转；(3) 失败 → 居中错误卡片 + 「返回登录」按钮（跳 `/login`）。
- **D-07:** `useAuth` 新增 `loginWithFeishu(code: string, state: string): Promise<UserProfile>` 方法，内部调用 `auth service` 新增的 `feishuCallback(code, state)`，返回 `AuthResponse`（与 Phase 26 后端契约一致），随后调 `storeAuthSession` 写入 localStorage 并更新 context state，签名语义与现有 `login(payload)` 保持一致。

### 二维码过期与刷新
- **D-08:** 前端启动本地 180s 倒计时（setTimeout，不显示可见倒计时数字，保持界面简洁）。到期后在 QR 画布上覆盖毛玻璃蒙层 + 「二维码已过期，点击刷新」按钮。
- **D-09:** 用户点击刷新时：重新调用 `/auth/feishu/authorize` 获取新 `state` + `authorize_url` → 销毁旧 `QRLogin` 实例（`iframe.remove()` 或容器清空）→ 重建 `QRLogin` 实例 → 重置 180s 倒计时。不做后台静默自动刷新，避免无人操作时浪费 Redis TTL。
- **D-10:** 扫码过程中的状态完全依赖飞书 SDK 的 `onSuccess` / `onReady` / `onErr` 回调。`onSuccess` 由 SDK 自动触发浏览器重定向到 `goto`（即 `/auth/feishu/callback`），无需前端手动处理。**不额外轮询后端检查扫码状态**（Phase 26 未提供此端点）。

### 错误分类与展示
- **D-11:** 新建 `frontend/src/utils/feishuErrors.ts` 集中映射中文文案，覆盖至少这些分类：
  - `authorization_cancelled` — 用户取消授权
  - `employee_not_matched` — 工号未匹配，请联系管理员开通
  - `state_invalid_or_expired` — 会话已过期，请刷新二维码重试
  - `code_expired_or_replayed` — 授权码已失效，请重新扫码
  - `redis_unavailable` — 登录服务暂不可用（503），请稍后重试
  - `network_error` — 网络错误，请检查连接
  - `sdk_load_failed` — 飞书登录组件加载失败
  - `unknown_error` — 登录失败，请稍后重试
  映射函数签名：`resolveFeishuError(source: 'backend' | 'sdk', payload: unknown) => { code: string; message: string }`。
- **D-12:** 错误展示分两个场景：(1) `FeishuCallbackPage` 处理失败 → 页面居中错误卡片（`surface` 样式）+ 错误文案 + 「返回登录」按钮；(2) `LoginPage` 的 `FeishuLoginPanel` 内部 SDK 加载失败 / authorize 请求失败 → 面板内红色 inline banner（`color: var(--color-danger)`）+ 「重试」按钮。不使用全局 Toast，不通过 `/login?error=` 回跳模式。

### 登录页布局边界（Phase 27 vs Phase 29）
- **D-13:** 新增独立组件 `frontend/src/components/auth/FeishuLoginPanel.tsx`，放在现有 `Login.tsx` 右侧「访问入口」section 内部（`LoginForm` 下方，通过 `gap` 分隔）。保持现有左右双 section 结构不变，现有邮箱密码登录 100% 保留（验证 LOGIN-04 保留约束）。
- **D-14:** `FeishuLoginPanel` 完全自洽 / 无副作用：内部管理 authorize 请求、SDK 脚本注入、`QRLogin` 实例生命周期、倒计时、刷新、错误展示；对外 props 最小化（可选 `onSuccess?: () => void` 覆盖默认跳转，默认走 `window.location.href = authorize_url` 或 SDK 自动重定向）。Phase 29 重设计时只需把 `<FeishuLoginPanel />` 搬到新布局，不需要重写任何 QR 逻辑。

### Claude's Discretion
- CDN 脚本的具体 URL 与版本（跟随飞书官方最新稳定版，必要时写入常量）
- `QRLogin` 配置项细节（`width` / `height` / `style` / `iframeStyle` 等视觉参数）
- 骨架屏和错误卡片的精确视觉细节（遵循现有 `surface` / `action-primary` / `eyebrow` 类）
- 倒计时实现机制（`setTimeout` + cleanup on unmount）
- 跳转目标细节（复用 `getRoleHomePath(profile.role)`，与 `Login.tsx` 一致）
- `must_change_password` 场景处理（飞书成功后若后端返回 `must_change_password=true` 同样跳 `/settings`）
- 测试策略：单元测试覆盖 `feishuErrors.ts` 映射表、`FeishuCallbackPage` 组件（mock auth service）、`FeishuLoginPanel` mount/expiry 行为；SDK 集成部分手动在浏览器验证

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 26 产物（后端契约）
- `.planning/phases/26-oauth2/26-CONTEXT.md` — Phase 26 全部 OAuth 决策（state TTL、code 防重放、错误码映射、feishu_open_id 绑定逻辑）
- `.planning/phases/26-oauth2/26-02-SUMMARY.md` — callback 端点返回 `AuthResponse`（而非裸 TokenPair）的决策记录
- `backend/app/api/v1/auth.py` — `GET /api/v1/auth/feishu/authorize` 与 `POST /api/v1/auth/feishu/callback` 的请求/响应结构
- `backend/app/services/feishu_oauth_service.py` — 后端错误码映射（20002/20003/20004/20010）与 Redis 503 降级策略

### 现有前端资产（复用基线）
- `frontend/src/pages/Login.tsx` — 登录页双栏 section 结构 + 视觉语言
- `frontend/src/hooks/useAuth.tsx` — AuthContext 的 `login` / `register` 方法签名与状态同步模式
- `frontend/src/services/auth.ts` — `storeAuthSession` / `fetchCurrentUser` / `AUTH_SESSION_EVENT` 跨标签同步
- `frontend/src/services/api.ts` — Axios 实例、JWT Authorization 拦截器、401 自动 refresh 流程
- `frontend/src/components/auth/LoginForm.tsx` — 现有邮箱密码表单组件（保持并排）
- `frontend/src/types/api.ts` — `AuthResponse` / `TokenPair` / `UserProfile` 类型（Phase 27 需扩充 `FeishuCallbackPayload` / `FeishuAuthorizeResponse`）
- `frontend/src/utils/roleAccess.ts` — `getRoleHomePath` 登录后跳转目标
- `frontend/src/App.tsx` — 路由表（需新增 `/auth/feishu/callback` 公开路由）

### 需求与范围
- `.planning/REQUIREMENTS.md` — FUI-01 ~ FUI-04 验收标准（QR SDK 嵌入、回调路由、3 分钟刷新、分类错误提示）；Out of Scope 中明确禁止扫码/密码 Tab 切换与 user_access_token 持久化
- `.planning/ROADMAP.md` Phase 27 section — Depends on Phase 26；Success Criteria 4 条

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `storeAuthSession(auth: AuthResponse)` + `fetchCurrentUser()` — 登录成功后直接复用，飞书回调无需新建 session 存储路径
- `useAuth().login(payload)` — 扩展为 `loginWithFeishu(code, state)` 的签名范式（返回 `Promise<UserProfile>`，失败时抛异常让页面 catch）
- `api` Axios 实例（`services/api.ts`）— 复用其 baseURL、JWT 拦截器、401 refresh 逻辑；飞书新增的两个端点不需要 Authorization header（公开端点）
- `surface` / `eyebrow` / `action-primary` / `action-secondary` / `animate-fade-up` CSS 类 — `FeishuLoginPanel` 与 `FeishuCallbackPage` 视觉语言与登录页一致
- `getRoleHomePath(role)` — 登录后按角色跳转
- `AUTH_SESSION_EVENT` — 跨标签同步，`storeAuthSession` 已自动触发，无需额外处理

### Established Patterns
- 所有 auth 相关 API 封装放在 `services/auth.ts`，新方法 `authorizeFeishu()` / `feishuCallback(code, state)` 遵循同样风格（async 函数 + 明确返回类型）
- 错误处理模式：`axios.isAxiosError(err)` 提取 `response.data.message` → 统一为中文文案
- 类型定义集中在 `types/api.ts`，新增 `FeishuAuthorizeResponse { authorize_url, state }` 与 `FeishuCallbackPayload { code, state }`
- 组件按业务域组织在 `components/auth/`，`FeishuLoginPanel` 与 `FeishuCallbackPage` 自然归档

### Integration Points
- `App.tsx` 路由表：在 `/login` 路由下新增 `<Route element={<FeishuCallbackPage />} path="/auth/feishu/callback" />`（公开，不在 `ProtectedRoute` 下）
- `Login.tsx` 右侧 `section`：在 `<LoginForm />` 之后插入 `<FeishuLoginPanel />`
- `useAuth.tsx`：在 `AuthContextValue` 类型增加 `loginWithFeishu`，在 `AuthProvider` 实现对应函数并加入 `useMemo` value
- `services/auth.ts`：新增 `authorizeFeishu()` 与 `feishuCallback(code, state)` 导出函数

</code_context>

<specifics>
## Specific Ideas

- 飞书官方 QR 组件名为 `window.QRLogin`，文档示例配置项：`{ id: <container-id>, goto: <authorize_url>, width, height, style, onSuccess, onReady, onErr }`。`goto` 直接接收后端返回的完整 `authorize_url`（已含 state、redirect_uri、scope）
- 飞书 SDK `onSuccess` 会自动让浏览器重定向到 `goto` 指定 URL 的 `redirect_uri`（即 `/auth/feishu/callback?code=...&state=...`），前端不需要手动处理跳转
- 视觉保持克制：QR 面板不额外加标题党式 hero 文案，仅 `eyebrow` + 「扫码登录」+ 二维码 + 过期/错误提示，与左侧邮箱登录视觉权重对等
- CSS 变量使用现有 `var(--color-ink)` / `var(--color-steel)` / `var(--color-primary)` / `var(--color-danger)` / `var(--color-bg-subtle)` / `var(--color-border)`

</specifics>

<deferred>
## Deferred Ideas

- 粒子动态背景（LOGIN-02, LOGIN-03）→ Phase 28
- 登录页完整左右双栏重设计（LOGIN-01）→ Phase 29（FeishuLoginPanel 将被平移到新布局）
- 飞书工作台免登（`tt.requestAccess`）→ 未来里程碑，需应用上架飞书工作台（REQUIREMENTS.md Out of Scope 已注明）
- 扫码 ↔ 密码 Tab 切换模式 — REQUIREMENTS.md Out of Scope 明确禁止（QR SDK 容器销毁重建会闪烁）
- 持久化飞书 `user_access_token` — REQUIREMENTS.md Out of Scope 明确禁止（不必要的安全风险）
- E2E 集成测试套件 — REQUIREMENTS.md deferred，Phase 27 仅要求单元 + 手动测试

</deferred>

---

*Phase: 27-oauth2*
*Context gathered: 2026-04-19*
