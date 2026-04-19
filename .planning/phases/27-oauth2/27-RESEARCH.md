# Phase 27: 飞书 OAuth2 前端集成 - Research

**Researched:** 2026-04-19
**Domain:** React 18 / react-router-dom v7 / 飞书 QRLogin Web SDK / OAuth2 回调
**Confidence:** HIGH（后端契约、代码基线）/ MEDIUM（QRLogin SDK 细节 — 官方文档页在 sandbox 中无法直连，结论来自多个一致的社区实现）

## Summary

Phase 27 的技术核心并不是 React 或路由本身，而是**正确对接飞书 QRLogin Web SDK 的 postMessage 协议**。研究发现 CONTEXT.md D-10 的措辞（「扫码过程中的状态完全依赖飞书 SDK 的 `onSuccess` / `onReady` / `onErr` 回调」「`onSuccess` 由 SDK 自动触发浏览器重定向」）与飞书官方 SDK 的实际行为不完全一致：**QRLogin 1.0.3 没有这三个回调**，它只通过 `window.postMessage` 发送 `{tmp_code}` 对象，前端必须自己监听 `message` 事件、用 `QRLoginObj.matchOrigin` / `matchData` 校验，然后把 `tmp_code` 拼到 `goto` 后面**手动**重定向。

第二个关键事实：**前端无任何测试基础设施**（没有 vitest/jest/RTL/Playwright），所有已存在的前端代码都没有单元测试。Phase 27 若要做"单元测试覆盖 feishuErrors 映射表 / FeishuCallbackPage / FeishuLoginPanel"（CONTEXT.md 讨论区给的建议），**必须把引入 vitest + @testing-library/react 的基础设施建设作为 Wave 0 前置任务**，否则应降级为"手动浏览器验证 + ESLint（`tsc --noEmit`）"。

第三个关键事实：`frontend/src/main.tsx` **并未**用 `<React.StrictMode>` 包裹 `<App>`。这意味着 useEffect 不会在开发时双重执行，放松了幂等性约束——但代码仍需写成幂等，因为未来可能启用 StrictMode，而且 QR 刷新逻辑本身就是"销毁重建"，cleanup 必须正确。

**Primary recommendation:**
实现路径清晰可落地。遵循 CONTEXT.md 所有 14 条锁定决策，但要**修正 D-10 的 onSuccess 语义**：改为"监听 postMessage → 校验 origin/data → 拼 tmp_code 并 `window.location.href = goto&tmp_code=...` 导航"。脚本注入与实例销毁用标准的 `useEffect + cleanup` 模式，测试策略降级为手动浏览器验证 + 可选 Wave 0 引入 vitest（本 phase 不强依赖）。

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 ~ D-14)

**QR SDK 加载与初始化：**
- **D-01** 飞书 QR SDK 通过官方 CDN 脚本动态注入加载（`useEffect` 内 `document.createElement('script')` 指向 `https://lf-package-cn.feishucdn.com/...QRLogin.js`，onload 后调用 `window.QRLogin(...)`）；不使用 npm 包，不自实现二维码获取与轮询。
- **D-02** `authorize_url` 与 `state` 在 `FeishuLoginPanel` 组件挂载时调用后端 `GET /api/v1/auth/feishu/authorize` 一次获取，作为 `goto` 传入 `QRLogin` 配置。不做延迟懒加载，不做定时器预拉取，与后端 state Redis TTL 300s 匹配。
- **D-03** 脚本注入要处理 onerror / CSP 阻塞：脚本加载失败时显示错误状态（见 D-11），并在下一次重试或刷新时重新注入。组件卸载时不必移除已加载的全局脚本（单例模式）。

**回调路由形态：**
- **D-04** 新增独立路由 `/auth/feishu/callback` 对应独立组件 `FeishuCallbackPage`，路由在 `App.tsx` 中注册为公开路由（不包 ProtectedRoute）。
- **D-05** `FeishuCallbackPage` 挂载时用 `useSearchParams` 解析 URL 的 `code` / `state` → 调用 `useAuth.loginWithFeishu(code, state)` → 成功后用 `useNavigate(getRoleHomePath(role), { replace: true })` 跳转到角色首页；若 `must_change_password` 为 true，沿用 `Login.tsx` 现有逻辑跳 `/settings`。
- **D-06** 回调页可见 UI 分三种状态：(1) 处理中 → 显示 `surface` 风格骨架卡片「正在完成飞书登录…」；(2) 成功 → 短暂停留立即跳转；(3) 失败 → 居中错误卡片 + 「返回登录」按钮（跳 `/login`）。
- **D-07** `useAuth` 新增 `loginWithFeishu(code: string, state: string): Promise<UserProfile>` 方法，内部调用 `auth service` 新增的 `feishuCallback(code, state)`，返回 `AuthResponse`，随后调 `storeAuthSession` 写入 localStorage 并更新 context state。

**二维码过期与刷新：**
- **D-08** 前端启动本地 180s 倒计时（setTimeout，不显示可见倒计时数字）。到期后在 QR 画布上覆盖毛玻璃蒙层 + 「二维码已过期，点击刷新」按钮。
- **D-09** 用户点击刷新时：重新调用 `/auth/feishu/authorize` 获取新 `state` + `authorize_url` → 销毁旧 `QRLogin` 实例（`iframe.remove()` 或容器清空）→ 重建 `QRLogin` 实例 → 重置 180s 倒计时。
- **D-10** 扫码过程中的状态完全依赖飞书 SDK 回调；**不额外轮询后端检查扫码状态**。⚠️ 本研究发现 D-10 关于"`onSuccess` 由 SDK 自动触发重定向"的描述不准确 — 参见"飞书 QRLogin SDK 参考"章节的勘误。

**错误分类与展示：**
- **D-11** 新建 `frontend/src/utils/feishuErrors.ts` 映射中文文案，覆盖 8 类错误（`authorization_cancelled` / `employee_not_matched` / `state_invalid_or_expired` / `code_expired_or_replayed` / `redis_unavailable` / `network_error` / `sdk_load_failed` / `unknown_error`）。
- **D-12** 错误展示分两个场景：回调页 → 居中错误卡片 + 「返回登录」；登录页 QR 面板 → 面板内红色 inline banner + 「重试」按钮。不使用全局 Toast，不通过 `/login?error=` 回跳模式。

**布局边界：**
- **D-13** 新增独立组件 `FeishuLoginPanel.tsx`，放在现有 `Login.tsx` 右侧 section 内部（`LoginForm` 下方，`gap` 分隔）。现有邮箱密码登录 100% 保留（LOGIN-04）。
- **D-14** `FeishuLoginPanel` 完全自洽 / 无副作用：内部管理 authorize 请求、SDK 脚本注入、`QRLogin` 实例生命周期、倒计时、刷新、错误展示；对外 props 最小化。

### Claude's Discretion
- CDN 脚本的具体 URL 与版本（跟随飞书官方最新稳定版，必要时写入常量）
- `QRLogin` 配置项细节（`width` / `height` / `style` 等视觉参数）
- 骨架屏和错误卡片的精确视觉细节（遵循现有 `surface` / `action-primary` / `eyebrow` 类）
- 倒计时实现机制（`setTimeout` + cleanup on unmount）
- 跳转目标细节（复用 `getRoleHomePath(profile.role)`，与 `Login.tsx` 一致）
- `must_change_password` 场景处理（飞书成功后若后端返回 `must_change_password=true` 同样跳 `/settings`）
- 测试策略：单元测试覆盖 `feishuErrors.ts`、`FeishuCallbackPage`、`FeishuLoginPanel`；SDK 集成部分手动在浏览器验证。**注意：本研究发现前端无测试基础设施，需评估是否把 vitest 引入降级为"可选 Wave 0 任务"**。

### Deferred Ideas (OUT OF SCOPE)
- 粒子动态背景（LOGIN-02, LOGIN-03）→ Phase 28
- 登录页完整左右双栏重设计（LOGIN-01）→ Phase 29（FeishuLoginPanel 将被平移到新布局）
- 飞书工作台免登（`tt.requestAccess`）→ 未来里程碑
- 扫码 ↔ 密码 Tab 切换模式 — REQUIREMENTS.md Out of Scope 明确禁止
- 持久化飞书 `user_access_token` — Out of Scope 明确禁止
- E2E 集成测试套件 — Phase 27 仅要求单元 + 手动测试
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **FUI-01** | 登录页嵌入飞书 QR SDK 扫码面板，用户扫码后自动触发 OAuth 授权流程 | "飞书 QRLogin SDK 参考" 提供 CDN URL、`QRLogin()` 参数表、iframe + postMessage 通信协议；"React 集成模式" 给出动态脚本注入和 StrictMode-safe cleanup |
| **FUI-02** | 前端 `/auth/feishu/callback` 路由处理 OAuth 回调，解析 code/state 后调用后端接口完成登录 | "react-router-dom v7 模式" 给出 `useSearchParams` + `useNavigate` 用法；"后端 API 契约" 提供 `POST /auth/feishu/callback` 精确请求/响应 shape |
| **FUI-03** | QR 二维码支持 3 分钟自动刷新，过期后显示刷新提示 | "计时器 / iframe 泄漏风险" 详述 `setTimeout` + cleanup 模式；"QR 刷新流程" 给出销毁旧 `QRLogin` 实例的具体 DOM 操作（`innerHTML = ''` + 新实例） |
| **FUI-04** | 飞书登录失败时显示分类中文错误提示 | "错误码映射表" 给出后端 HTTP 状态码 + `detail` 中文文案 → 前端分类码 → 用户文案的三层映射 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

| 约束 | 要求 |
|------|------|
| 技术栈 | React（前端）、FastAPI（后端）、Python（主语言）、DeepSeek（LLM）、PyCharm 可调试 |
| 中文沟通 | 所有错误文案、UI 文本必须中文；注释可中文；代码变量名用英文 |
| 类型化 | TS `strict: true`；接口用 `interface`；类型放 `types/api.ts`；`void` 前缀 floating promise |
| 命名 | 组件 `PascalCase.tsx`；服务/工具 `camelCase.ts`；Hook `useXxx.tsx`；module constants `SCREAMING_SNAKE_CASE` |
| 错误处理 | 前端统一 `axios.isAxiosError()` 提取 `response.data.detail` / `message`；Service 层不做 try/catch，让页面/组件处理 |
| 测试 | 「完成任务前必须测试」；前端当前无测试基础设施；手动浏览器验证必须覆盖上传、列表、筛选、评分展示、登录流程等关键路径 |
| 阻塞 | 缺关键配置（如 `FEISHU_APP_ID`）→ 不得伪造完成，必须记录阻塞 |
| 一次聚焦一个任务 | Phase 27 只做前端飞书集成，不动邮箱密码登录、不动路由保护、不改其它页面 |

## Standard Stack

### Core（已在项目中，不需新装）
| 库 | 版本 | 用途 | Why Standard |
|---|------|------|--------------|
| react | 18.3.1 | UI 框架 | 项目已用，无需变更 `[VERIFIED: package.json]` |
| react-dom | 18.3.1 | DOM 渲染 | 项目已用 `[VERIFIED: package.json]` |
| react-router-dom | 7.6.0 | 路由、`useSearchParams`、`useNavigate` | 项目已用，v7 API 兼容 `[VERIFIED: package.json]` |
| axios | 1.8.4 | HTTP 客户端 | 项目已用，`services/api.ts` 提供 JWT 拦截器 `[VERIFIED: package.json]` |
| typescript | 5.8.3 | 类型安全 | 项目已用，strict mode `[VERIFIED: package.json]` |

### Supporting
| 对象 | 类型 | 用途 | When to Use |
|------|------|------|-------------|
| 飞书 QRLogin SDK (1.0.3) | 外部 CDN 脚本 | 渲染扫码二维码、postMessage 回传 tmp_code | 仅在 `FeishuLoginPanel` 挂载时注入 |
| `window.QRLogin` | 全局函数 | SDK 暴露的实例构造器 | 脚本 load 成功后可用 |

### Alternatives Considered
| 代替方案 | 可否使用 | 为什么不选 |
|----------|----------|------------|
| npm 包 `@larksuite/sso-js-sdk` | ❌ | 飞书官方从未发布过正式 npm 包；D-01 已锁定 CDN 方案 |
| 后端轮询扫码状态端点 | ❌ | Phase 26 未提供此端点；D-10 已明确禁止 |
| `@lark-base-open/js-sdk` | ❌ | 这是飞书多维表格 JS SDK，与登录 SSO 无关 |
| 自绘 QR（使用 `qrcode` npm 包 + 后端轮询） | ❌ | 违反 D-01；飞书登录必须走官方 SDK 保证安全性和用户体验 |

**安装方式：**
不通过 npm 安装。通过在 `FeishuLoginPanel` 的 `useEffect` 内动态注入 `<script>` 标签加载。**不**修改 `frontend/index.html` 全局 `<head>`（会在未用飞书登录的页面也拉远程脚本）。

**版本验证：**
`[CITED: multiple community sources, 2024-2026]` 1.0.3 是当前推荐版本；1.0.1/1.0.2 是旧版，1.0.1 需要手机端 + 网页端双次确认，1.0.3 只需手机一次确认。`[ASSUMED]` 1.0.3 是最新稳定版 — 飞书官方文档页在研究 sandbox 中无法直连（网络受限），实施时应在浏览器打开 https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/qr-sdk-documentation 再确认一次是否仍推荐 1.0.3。

## Backend API Contract（已由 Phase 26 交付）

### GET `/api/v1/auth/feishu/authorize`

**请求：**
- 无鉴权（公开端点）
- 无请求 body / query 参数
- HTTP GET

**成功响应（200）：**
```ts
interface FeishuAuthorizeResponse {
  authorize_url: string;  // 完整飞书授权 URL，已含 client_id/redirect_uri/state
  state: string;          // CSRF token（base64url，32 bytes），Redis TTL 300s
}
```

**说明：**
- 后端端点实际返回类型为 `dict[str, str]`（`backend/app/api/v1/auth.py:273`），未声明 Pydantic `response_model`。内容即上表两字段，键名为 snake_case。
- `authorize_url` 示例（来自 `backend/app/services/feishu_oauth_service.py:55`）：
  `https://accounts.feishu.cn/open-apis/authen/v1/authorize?client_id=cli_xxx&response_type=code&redirect_uri=<url-encoded>&state=<state>`
- 前端把整个 `authorize_url` 原样作为 `QRLogin({goto: ...})` 的 `goto` 参数，**不要**自己重新拼 URL。

**错误响应：**
| HTTP | `detail` 中文文案 | 何时出现 | 前端映射到 |
|------|-------------------|----------|-----------|
| 503 | `认证服务暂不可用，请稍后重试` | Redis 不可达 | `redis_unavailable` |
| 网络错误 | — | 请求失败 | `network_error` |

### POST `/api/v1/auth/feishu/callback`

**请求：**
- 无鉴权（公开端点）
- `Content-Type: application/json`
- Body：
  ```ts
  interface FeishuCallbackPayload {
    code: string;    // 飞书授权码，1-512 字符，从 URL query 拿
    state: string;   // CSRF state，1-128 字符，从 URL query 拿
  }
  ```
  `[VERIFIED: backend/app/schemas/user.py:154-156]`

**成功响应（200）：**
```ts
interface AuthResponse {
  user: UserProfile;    // 含 must_change_password、role、feishu_open_id 等
  tokens: TokenPair;    // access_token + refresh_token + token_type='bearer'
}
```
`[VERIFIED: backend/app/schemas/user.py:92-95]`

**说明：**
- 该端点**不**返回裸 `TokenPair`（Phase 26 Plan 02 明确决策 - `.planning/phases/26-oauth2/26-02-SUMMARY.md` Deviations #4），与 `POST /auth/register` 一致。
- `user.feishu_open_id: Optional[str]` 字段已在 `UserRead` 中 `[VERIFIED: backend/app/schemas/user.py:37]`，但**前端 `types/api.ts` 的 `UserProfile` 目前缺少该字段** — Phase 27 应补齐为 `feishu_open_id: string | null`（向下兼容）。
- `user.must_change_password: boolean` 字段已在 `UserProfile` 中 `[VERIFIED: frontend/src/types/api.ts:13]` — 回调页成功分支必须检查这个字段并走与 `Login.tsx:28` 一致的跳转逻辑。

**错误响应（所有都是 `{detail: "<中文文案>"}` 结构，FastAPI 默认格式）：**

`[VERIFIED: backend/app/services/feishu_oauth_service.py + backend/tests/test_api/test_feishu_oauth_integration.py]`

| HTTP | `detail` 中文原文 | 触发条件 | 前端映射到 |
|------|-------------------|----------|-----------|
| 400 | `无效的 state 参数，请重新发起授权` | state 不在 Redis 或已被消费 | `state_invalid_or_expired` |
| 400 | `授权码已使用` | 同一 code 二次提交（Redis 防重放） | `code_expired_or_replayed` |
| 400 | `授权码已过期，请重新授权` | 飞书 20004 | `code_expired_or_replayed` |
| 400 | `工号未匹配，请联系管理员开通` | `_find_or_bind_user` 失败（无匹配员工或员工未绑定 User） | `employee_not_matched` |
| 403 | `应用未获得用户授权，请联系管理员` | 飞书 20010（用户拒绝授权 / app 权限不够） | `authorization_cancelled` |
| 500 | `飞书应用配置错误，请联系管理员` | 飞书 20002（app_id/app_secret 错） | `unknown_error` + 记录日志 |
| 502 | `飞书认证服务异常` | 飞书其它错误码 | `unknown_error` |
| 502 | `获取飞书用户信息失败` | user_info 接口返回非 0 | `unknown_error` |
| 503 | `认证服务暂不可用，请稍后重试` | Redis 不可达 | `redis_unavailable` |

**⚠️ 关键实现细节：** FastAPI 的 `HTTPException(detail=...)` 默认把 `detail` 放在 response body 的 `detail` 键下，**不是** `message` 或 `error`。但项目的 `backend/app/main.py` 可能有自定义 exception handler 把它改写成 `{error, message}` — 让 planner 在 Task 中**明确验证**这一点（读 `main.py` 的 `@app.exception_handler(HTTPException)`）。两种格式都要兼容：

```ts
function extractBackendError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: string; message?: string } | undefined;
    return data?.detail ?? data?.message ?? '登录失败，请稍后重试';
  }
  return '登录失败，请稍后重试';
}
```
这也是 `frontend/src/App.tsx:51` 现有代码的模式（同时 fallback 到 `detail` 和 `message`）。

## Architecture Patterns

### Recommended File Structure
```
frontend/src/
├── components/
│   └── auth/
│       ├── FeishuLoginPanel.tsx       # 新增 — 登录页 QR 面板
│       ├── LoginForm.tsx              # 不动（保留邮箱密码登录）
│       └── RegisterForm.tsx           # 不动
├── pages/
│   ├── FeishuCallbackPage.tsx         # 新增 — /auth/feishu/callback 路由
│   └── Login.tsx                      # 轻改 — 在右侧 section 加 <FeishuLoginPanel/>
├── services/
│   └── auth.ts                        # 新增 2 个 export: authorizeFeishu(), feishuCallback()
├── hooks/
│   └── useAuth.tsx                    # 轻改 — AuthContextValue 增 loginWithFeishu
├── utils/
│   └── feishuErrors.ts                # 新增 — resolveFeishuError 映射函数
└── types/
    └── api.ts                         # 新增 2 个 interface + 补 UserProfile.feishu_open_id
App.tsx                                # 轻改 — 加一个 <Route> 声明
```

### Pattern 1: 动态脚本注入（StrictMode-safe）

**Source:** React 18 官方 + 社区最佳实践 `[CITED: dev.to/jherr, dev.to/ag-grid]`

```tsx
// Source: https://dev.to/jherr/react-18-useeffect-double-call-for-apis-emergency-fix-27ee
const QR_SDK_URL =
  'https://lf-package-cn.feishucdn.com/obj/feishu-static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.3.js';

function useFeishuSdk(): { ready: boolean; error: Error | null } {
  const [ready, setReady] = useState<boolean>(() => typeof window !== 'undefined' && !!(window as any).QRLogin);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Idempotency: if QRLogin already on window (from an earlier mount in StrictMode or
    // from another panel), consider it ready — the SDK is a singleton.
    if ((window as any).QRLogin) {
      setReady(true);
      return;
    }

    // Idempotency: check DOM for an existing script node with the same src.
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${QR_SDK_URL}"]`);
    if (existing) {
      if ((window as any).QRLogin) {
        setReady(true);
      } else {
        existing.addEventListener('load', () => setReady(true), { once: true });
        existing.addEventListener('error', () => setError(new Error('sdk_load_failed')), { once: true });
      }
      return;
    }

    const script = document.createElement('script');
    script.src = QR_SDK_URL;
    script.async = true;
    const handleLoad = () => setReady(true);
    const handleError = () => setError(new Error('sdk_load_failed'));
    script.addEventListener('load', handleLoad, { once: true });
    script.addEventListener('error', handleError, { once: true });
    document.head.appendChild(script);

    // D-03: 不移除全局脚本（单例）；只解绑事件，避免对后续再次挂载造成干扰。
    return () => {
      script.removeEventListener('load', handleLoad);
      script.removeEventListener('error', handleError);
    };
  }, []);

  return { ready, error };
}
```

**关键点：**
- 第一次检查 `window.QRLogin` 处理"脚本已由其它页面加载"的场景。
- 第二次检查 DOM 已有 `<script src=...>` 处理"StrictMode 双挂载 / 用户从 /login 跳 /settings 又回 /login"的场景。
- 不在 cleanup 里 `script.remove()` — 这是 **D-03 明确决定的单例策略**（也符合飞书 CDN 脚本只需加载一次）。

### Pattern 2: QRLogin 实例 + postMessage 监听

**Source:** 多个社区实现 `[CITED: cnblogs/xutongbao, juejin/7501203502665891866, CSDN/144227680]`

```tsx
// Source: https://www.cnblogs.com/xutongbao/p/18161614
declare global {
  interface Window {
    QRLogin?: (cfg: QRLoginConfig) => QRLoginInstance;
  }
}

interface QRLoginConfig {
  id: string;
  goto: string;
  width?: string | number;
  height?: string | number;
  style?: string;
}

interface QRLoginInstance {
  matchOrigin: (origin: string) => boolean;
  matchData: (data: unknown) => boolean;
}

function mountQrLogin(
  containerId: string,
  gotoUrl: string,
  onScanned: (tmpCode: string) => void,
): QRLoginInstance | null {
  if (!window.QRLogin) return null;

  // Clear container to prevent stacked QR codes on refresh.
  const container = document.getElementById(containerId);
  if (container) container.innerHTML = '';

  const instance = window.QRLogin({
    id: containerId,
    goto: gotoUrl,
    width: '260',
    height: '260',
    style: 'width:260px;height:260px;border:none',
  });

  const handler = (event: MessageEvent): void => {
    if (!instance.matchOrigin(event.origin)) return;
    if (!instance.matchData(event.data)) return;
    // 1.0.3: event.data is object { tmp_code: string }
    const tmpCode = (event.data as { tmp_code?: string }).tmp_code;
    if (!tmpCode) return;
    onScanned(tmpCode);
  };
  window.addEventListener('message', handler);

  // Caller is responsible for calling window.removeEventListener('message', handler)
  // — but we need to return it; store it on the instance or via a closure.
  (instance as unknown as { __handler: typeof handler }).__handler = handler;
  return instance;
}
```

**关键点 — 勘误 D-10：** 扫码成功后，SDK **不会** 自动重定向。前端必须：
1. 在 `onScanned` 回调里手动构造 `const redirectUrl = \`${gotoUrl}&tmp_code=${encodeURIComponent(tmpCode)}\``。
2. 手动执行 `window.location.href = redirectUrl`。
3. 浏览器请求该 URL → 飞书服务器做授权 → 重定向到 `redirect_uri`（即 `/auth/feishu/callback?code=...&state=...`）。

所以"SDK 自动触发重定向"的说法**在字面上不对**，但 D-10 实质要表达的"前端不做扫码状态轮询"结论**是对的**。

### Pattern 3: 180 秒倒计时与刷新

```tsx
function useQrExpiry(onExpire: () => void, enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    const timer = window.setTimeout(onExpire, 180_000);
    return () => window.clearTimeout(timer);
  }, [enabled, onExpire]);
}
```

刷新流程（点击「刷新」按钮）：
1. `setIsExpired(false)`
2. 重新 `GET /api/v1/auth/feishu/authorize` → 拿新 `authorize_url`
3. 清空 `document.getElementById('feishu-qr-container').innerHTML = ''`
4. 移除旧的 message listener（`window.removeEventListener('message', oldHandler)`）
5. 调 `window.QRLogin({...})` 重新渲染 + 挂新 listener
6. `setIsExpired(false)`，重新启动 180s 倒计时

**关键：** 每次刷新都要 `innerHTML = ''` 清空容器，否则二维码会叠加 `[CITED: CSDN/145040888 — 飞书二维码登录注意点]`。

### Pattern 4: 回调页 useSearchParams

```tsx
// Source: https://reactrouter.com/api/hooks/useSearchParams (v7)
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useAuth } from '../hooks/useAuth';
import { resolveFeishuError } from '../utils/feishuErrors';
import { getRoleHomePath } from '../utils/roleAccess';

type CallbackState = 'processing' | 'success' | 'failed';

export function FeishuCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithFeishu } = useAuth();
  const [state, setState] = useState<CallbackState>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    const code = searchParams.get('code');
    const stateParam = searchParams.get('state');

    if (!code || !stateParam) {
      setState('failed');
      setErrorMessage(resolveFeishuError('backend', { detail: '缺少授权参数' }).message);
      return;
    }

    async function run() {
      try {
        const profile = await loginWithFeishu(code!, stateParam!);
        if (cancelled) return;
        setState('success');
        if (profile.must_change_password) {
          navigate('/settings', {
            replace: true,
            state: { forcePasswordChange: true, from: getRoleHomePath(profile.role) },
          });
        } else {
          navigate(getRoleHomePath(profile.role), { replace: true });
        }
      } catch (err) {
        if (cancelled) return;
        setState('failed');
        setErrorMessage(resolveFeishuError('backend', err).message);
      }
    }
    void run();
    return () => { cancelled = true; };
  }, [searchParams, loginWithFeishu, navigate]);

  // ... render 三种状态
}
```

### Anti-Patterns to Avoid

- **在 `index.html` 全局 `<head>` 注入 QRLogin 脚本** — 所有页面都会拉 CDN 脚本，浪费带宽，违反 D-14"自洽无副作用"原则。
- **用 `new URLSearchParams(window.location.search)` 代替 `useSearchParams()`** — 不会在 URL 变化时触发重渲染；违反 react-router-dom 惯例。
- **在 cleanup 里 `script.remove()`** — D-03 明确锁定单例策略；且 StrictMode 双挂载会出现"第二次挂载还没开始就把脚本删了"的时序问题。
- **不清空 QR 容器直接再调 `QRLogin()`** — 会叠加多个二维码 `[CITED: CSDN/145040888]`。
- **把 `tmp_code` 发给后端** — 后端只接受 `code`（授权码），不接受 `tmp_code`（临时扫码码）。两者是不同阶段的产物：`tmp_code` 是给飞书自己消费的（拼在 `goto` 后），`code` 才是飞书回调给业务方的。
- **忘记在 message 监听里校验 `matchOrigin` 和 `matchData`** — postMessage 是跨域通信，不校验会被恶意页面注入。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 飞书扫码二维码生成与扫描状态轮询 | 自己调飞书开放 API 获取 qr_token → 轮询 | 飞书 QRLogin Web SDK (`LarkSSOSDKWebQRCode-1.0.3.js`) | SDK 内置扫码状态同步、iframe 隔离、CSRF，自写容易漏安全边界 |
| axios 请求重试/401 刷新 | 给飞书调用单独写 fetch + 重试逻辑 | 复用 `frontend/src/services/api.ts` 的 axios 实例 | 已有 JWT 拦截器 + 401 refresh 去重 + baseURL 配置 |
| localStorage 写入 + 跨标签同步 | 手动 `localStorage.setItem` + 自定义事件 | `storeAuthSession(authResponse)` from `services/auth.ts` | 已实现 `AUTH_SESSION_EVENT` 跨标签广播 |
| 角色路由跳转 | 手写 switch-case | `getRoleHomePath(profile.role)` from `utils/roleAccess.ts` | 已有且与 `Login.tsx` 逻辑一致 |
| 错误消息文案拼接 | 组件内硬编码中文字符串 | 新 `utils/feishuErrors.ts` 里的 `resolveFeishuError()` | D-11 明确要求集中管理；方便未来 i18n |
| 倒计时计时器 | `setInterval` 每秒渲染 | `setTimeout(fn, 180000)` 单次触发（D-08 明确不显示可见倒计时） | 省一次每秒渲染；与 D-08 一致 |

**Key insight:** Phase 27 的所有"自己造轮子"诱惑都已经被 CONTEXT.md 的 14 条决策拦截了。最大风险是"以为 CONTEXT.md 描述的 `onSuccess` / `onReady` / `onErr` 回调真实存在，然后发现 SDK 不是这样工作的"。

## Runtime State Inventory

本阶段为新增功能，不涉及 rename / refactor。对照五类状态检查：

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — 未改动任何数据库表或 localStorage 键名 | — |
| Live service config | **None** — 飞书应用配置已在 Phase 26 通过 `.env` 注入（`FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `FEISHU_REDIRECT_URI`），Phase 27 是纯前端消费 | — |
| OS-registered state | **None** | — |
| Secrets/env vars | 前端需要知道后端 base URL，已通过 `VITE_API_BASE_URL` 注入。**不需要**新增任何前端环境变量 | — |
| Build artifacts | **None** — 纯 TS/TSX 源码修改，`tsc -b && vite build` 自动产出 | 常规 `npm run build` |

**Nothing found in category:** 验证于 `grep -r feishu frontend/src/` 与 Phase 26 `.env.example` 差异审阅。

## Common Pitfalls

### Pitfall 1: `event.data` 结构在 SDK 不同版本间不一致

**What goes wrong:** 旧版 SDK (1.0.1) 的 `event.data` 直接是 tmp_code 字符串；新版 (1.0.3) 是对象 `{tmp_code: string}`。若按 1.0.1 的 `event.data` 做 string 拼接，会得到 `[object Object]` URL 并扫码失败。

**Why it happens:** 社区示例混杂，复制时没注意版本。

**How to avoid:** 锁定 CDN 版本为 1.0.3（constant 声明），用 `event.data.tmp_code` 取值。代码里加 `if (typeof event.data !== 'object' || !event.data.tmp_code) return;` 防御。

**Warning signs:** 扫码后 URL 变成 `...&tmp_code=[object%20Object]` 或 `...&tmp_code=undefined`。

`[CITED: CSDN/144227680 — 飞书二维码联合登录]`

### Pitfall 2: StrictMode 双挂载导致二维码叠加或监听器泄漏

**What goes wrong:** StrictMode 下 `useEffect` 执行两次，第一次挂载脚本 + QRLogin 实例 + message listener，第二次再挂一次，容器里叠两个二维码 iframe，`message` 事件触发两次回调，重定向竞态。

**Why it happens:** 忘记在 cleanup 里移除 message listener；不检查容器里是否已有内容。

**How to avoid:**
- Cleanup 里调 `window.removeEventListener('message', handler)`
- 挂载实例前先 `container.innerHTML = ''`
- 用 `ref` 或局部变量 hold 住 handler 引用，确保 cleanup 拿到的是同一个函数

**Warning signs:** 开发模式下扫码后看到两次跳转，或控制台看到重复的 `message` event。

**当前规避状态：** `main.tsx` 目前**没有** `<React.StrictMode>`，所以这个陷阱在当前项目**暂时不会触发**。但代码仍应写成幂等，因为：(a) 未来启用 StrictMode；(b) 用户手动点刷新就是真·重建周期。

`[VERIFIED: frontend/src/main.tsx 源码]` `[CITED: React 官方 + dev.to/jherr]`

### Pitfall 3: useEffect 依赖数组引用 `searchParams` 导致循环重登

**What goes wrong:** 有人把 `code = searchParams.get('code')` 作为依赖（而不是 `searchParams`），每次重渲染都触发 login。或把 `loginWithFeishu` 当依赖，`useAuth` 返回的函数没被 `useMemo`/`useCallback` 稳定化（现有实现 `useAuth` 内部用 `useMemo` 包了 value 但 `handleLogin` 本身没用 `useCallback`）。

**Why it happens:** `react-router-dom v7` 的 `searchParams` 是稳定引用 `[CITED: reactrouter.com/api/hooks/useSearchParams]`，**直接**放依赖安全。但 `useAuth` 暴露的函数每次 render 可能不是同一引用。

**How to avoid:**
- 依赖数组用 `[searchParams, loginWithFeishu, navigate]`。
- 加 `let cancelled = false;` flag（项目既有模式，见 `useAuth.tsx:38`）。
- 或者用 `useRef` 存 `hasRun` 标志，确保回调只执行一次。

**Warning signs:** `/auth/feishu/callback` 请求被后端拒绝"授权码已使用"（因为被调了两次）。

### Pitfall 4: CSP 阻塞外部脚本

**What goes wrong:** 若部署环境有 Content-Security-Policy header，没把 `lf-package-cn.feishucdn.com` 列入 `script-src`，脚本 load 失败。

**Why it happens:** 生产环境 CSP 常由 Nginx/CDN 注入，开发环境 Vite dev 没有 CSP。

**How to avoid:** `script.onerror` 捕获并显示"飞书登录组件加载失败"错误（D-11 的 `sdk_load_failed` 分类）。不要用 `try/catch` 包 `document.head.appendChild` — 脚本加载失败不会抛同步异常。

**Warning signs:** 生产环境 QR 面板显示加载失败，开发环境正常。

### Pitfall 5: 倒计时 + 路由导航的定时器泄漏

**What goes wrong:** 用户进 `/login` 看到 QR → 180s 还没到就切换到别的页面 → `setTimeout` 已经调度但组件已卸载 → 定时器回调触发 `setIsExpired(true)` → React 警告"state update on unmounted component"。

**Why it happens:** useEffect cleanup 忘记 `clearTimeout`。

**How to avoid:** 所有 `setTimeout` / `setInterval` 必须在 cleanup 里清理，这是项目已有模式 `[VERIFIED: frontend/src/hooks/usePolling.ts:57-63]`。

**Warning signs:** 控制台有 "Can't perform a React state update on an unmounted component"。

### Pitfall 6: localStorage 写入后 useAuth context 未同步

**What goes wrong:** `loginWithFeishu` 只写 localStorage 但忘了 `setUser(response.user) + setAccessToken(...)`，此时 ProtectedRoute 仍看到旧的 `isAuthenticated=false`，重定向回 `/login`。

**Why it happens:** 只抄 `storeAuthSession` 但漏抄 setState 两行。

**How to avoid:** 对照 `useAuth.tsx` 的 `handleLogin`（Line 112-129）实现 `loginWithFeishu`：必须同时调 `storeAuthSession()` + `setUser()` + `setAccessToken()`。这是项目既有模式的完整复用。

**Warning signs:** 扫码成功但停在 `/login`，或 F5 后才进工作区。

## Code Examples

### Example 1: resolveFeishuError 映射函数（D-11 签名）

```ts
// frontend/src/utils/feishuErrors.ts
// Source: D-11 签名 + backend/app/services/feishu_oauth_service.py 错误码
import axios from 'axios';

export type FeishuErrorCode =
  | 'authorization_cancelled'
  | 'employee_not_matched'
  | 'state_invalid_or_expired'
  | 'code_expired_or_replayed'
  | 'redis_unavailable'
  | 'network_error'
  | 'sdk_load_failed'
  | 'unknown_error';

export interface FeishuError {
  code: FeishuErrorCode;
  message: string;
}

const COPY: Record<FeishuErrorCode, string> = {
  authorization_cancelled: '你已取消飞书授权',
  employee_not_matched: '工号未匹配，请联系管理员开通',
  state_invalid_or_expired: '会话已过期，请刷新二维码重试',
  code_expired_or_replayed: '授权码已失效，请重新扫码',
  redis_unavailable: '登录服务暂不可用，请稍后重试',
  network_error: '网络错误，请检查连接',
  sdk_load_failed: '飞书登录组件加载失败，请刷新重试',
  unknown_error: '登录失败，请稍后重试',
};

function classifyBackend(err: unknown): FeishuErrorCode {
  if (!axios.isAxiosError(err)) return 'unknown_error';
  const status = err.response?.status;
  const detail = ((err.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
    (err.response?.data as { message?: string } | undefined)?.message ?? '') as string;

  if (!err.response) return 'network_error';
  if (status === 503) return 'redis_unavailable';
  if (status === 403) return 'authorization_cancelled';
  if (status === 400) {
    if (detail.includes('state')) return 'state_invalid_or_expired';
    if (detail.includes('工号')) return 'employee_not_matched';
    if (detail.includes('授权码')) return 'code_expired_or_replayed';
    return 'unknown_error';
  }
  return 'unknown_error';
}

function classifySdk(payload: unknown): FeishuErrorCode {
  // SDK 真实错误表面：脚本 load 事件失败 → new Error('sdk_load_failed')
  // 其它 SDK 运行时异常（罕见）统一归 unknown_error
  if (payload instanceof Error && payload.message === 'sdk_load_failed') {
    return 'sdk_load_failed';
  }
  return 'unknown_error';
}

export function resolveFeishuError(
  source: 'backend' | 'sdk',
  payload: unknown,
): FeishuError {
  const code = source === 'backend' ? classifyBackend(payload) : classifySdk(payload);
  return { code, message: COPY[code] };
}
```

### Example 2: authorizeFeishu + feishuCallback service

```ts
// frontend/src/services/auth.ts (additions)
import type { AuthResponse } from '../types/api';
import api from './api';

export interface FeishuAuthorizeResponse {
  authorize_url: string;
  state: string;
}

export async function authorizeFeishu(): Promise<FeishuAuthorizeResponse> {
  const response = await api.get<FeishuAuthorizeResponse>('/auth/feishu/authorize');
  return response.data;
}

export async function feishuCallback(code: string, state: string): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/feishu/callback', { code, state });
  return response.data;
}
```

### Example 3: useAuth.loginWithFeishu（补丁）

```tsx
// frontend/src/hooks/useAuth.tsx (additions)
// 在 AuthContextValue 加：
//   loginWithFeishu: (code: string, state: string) => Promise<UserProfile>;

async function handleLoginWithFeishu(code: string, state: string): Promise<UserProfile> {
  const response = await feishuCallback(code, state);  // import from '../services/auth'
  storeAuthSession(response);
  setUser(response.user);
  setAccessToken(response.tokens.access_token);
  return response.user;
}

// 加入 useMemo value：
//   loginWithFeishu: handleLoginWithFeishu,
// 并把依赖数组改为 [accessToken, isBootstrapping, user]（不变，因为 handleLoginWithFeishu 不闭包外部可变）
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SDK 1.0.1：手机扫 + 网页二次确认 | SDK 1.0.3：手机一次授权 | 2023+ | UX 显著提升，Phase 27 必须用 1.0.3 |
| `event.data` 为字符串 tmp_code | `event.data` 为 `{tmp_code: string}` 对象 | 1.0.3 引入 | 复制老代码会踩坑 |
| react-router v5 `useLocation().search` + 手解 URLSearchParams | react-router v6/v7 `useSearchParams()` | v6 | 项目已 v7.6.0；`searchParams` 是稳定引用，可直接入依赖数组 |
| React 17：`useEffect` 单次执行 | React 18 StrictMode：dev 双挂载 | React 18 | 项目 React 18.3.1 但 main.tsx 未启用 StrictMode — 仍应写成幂等 |

**Deprecated/outdated:**
- **SDK 1.0.1 CDN** `sf3-cn.feishucdn.com/obj/static/lark/passport/qrcode/LarkSSOSDKWebQRCode-1.0.1.js` — 不要用，UX 已落后。
- **网上流传的 `onSuccess` / `onReady` / `onErr` 回调写法** — **不存在于 1.0.2/1.0.3**，仅通过 postMessage 通信。若发现代码里写了这三个回调，一定是作者想当然照搬了微信 `WxLogin` 的 API。

## Assumptions Log

> 所有研究中未在 sandbox 内直接验证但依赖社区一致结论的陈述。Planner 与 Discuss 阶段应基于此表判断是否需要用户确认。

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 飞书 QRLogin SDK 1.0.3 是 2026-04 当前推荐稳定版本 | Standard Stack | LOW — 若已出 1.0.4/2.x 需要更新 constant；最坏情况是 UX 不如最新版 |
| A2 | `QRLogin({...})` 只接受 `id/goto/width/height/style` 五个参数，没有 `iframeStyle` 或 `onSuccess/onReady/onErr` 回调 | 飞书 QRLogin SDK 参考 / Pattern 2 | MEDIUM — 若官方新增了回调，我们的 postMessage 模式仍然工作，只是没用到新 API；若官方某天弃用了 postMessage，我们会坏 |
| A3 | 飞书 tmp_code 的有效期默认短（秒级），二维码本身无明确过期时间，依靠前端自己的 180s 倒计时 | Pattern 3 | LOW — 180s 是 UX 约定而非技术硬限制，即使 tmp_code 有效期更短，用户会看到"扫完了点授权但仍失败"，此时点刷新即可 |
| A4 | 后端 FastAPI 默认 HTTPException 格式 `{detail: string}` 未被 `main.py` 的 exception handler 改写 | Backend API Contract | MEDIUM — 若被改写成 `{error, message}`，`resolveFeishuError.classifyBackend` 需要看 `message` 字段。**Planner Task 必须先 grep `main.py` 验证** |
| A5 | 飞书 `redirect_uri` 配置为 `https://<domain>/auth/feishu/callback`（前端域名 + callback 路径） | 整体流程 | HIGH — 若 Phase 26 配置的 `FEISHU_REDIRECT_URI` 是后端域名路径（如 `/api/v1/auth/feishu/callback`），整个前端流程走不通。**Planner Task 0 必须验证 `.env.example` 和实际部署配置** |
| A6 | 前端无测试基础设施的现状不会在 Phase 27 中改变 | Testing | LOW — 仅影响"单元测试覆盖"条目可达性，可降级为手动验证 |
| A7 | `main.tsx` 无 StrictMode 的现状不会在 Phase 27 中改变 | Pitfalls | LOW — 即便改为启用，我们写的代码已经是幂等的 |

**如表为空：** 不适用 — 共 7 条 assumption 需要在实施前或实施中验证。A4 和 A5 在 planner 的 Wave 0 / Task 0 中**必须**验证，否则实现会在真实环境走不通。

## Open Questions (RESOLVED)

1. **飞书应用的 `FEISHU_REDIRECT_URI` 实际配置值是什么？** — **RESOLVED**
   - `.env.example:61` 确认 `FEISHU_REDIRECT_URI=http://localhost:5174/auth/feishu/callback` 指向前端路由，与 D-04/D-05 一致。
   - Plan 01 frontmatter 已记录该验证；若部署环境 `.env` 实际值不符，Plan 01 约定 executor BLOCK 并汇报。

2. **后端 exception handler 是否改写 FastAPI 默认 `{detail}` 格式？** — **RESOLVED**
   - `backend/app/main.py:132-142` 确认 `@app.exception_handler(HTTPException)` 经 `build_error_response` 改写为 `{error: 'http_error', message: <detail>}`。
   - Plan 01 Task 2 的 `resolveFeishuError.classifyBackend` 优先读 `message`，并对 `detail` 兜底（与 App.tsx:51 现有防御同款）。

3. **Vite dev server 会不会代理 `/api/v1/...` 到后端？飞书 redirect_uri 是否接受本地 dev 域名？** — **RESOLVED (deferred to Manual Test Plan)**
   - `vite.config.ts` 无 proxy 配置；前端用 `VITE_API_BASE_URL` 绝对地址直连后端 — 不需要代理。
   - 飞书 redirect_uri 对 `http://localhost:5174` 的接受取决于飞书应用后台登记，属运行环境前置条件。本 Phase 不解决；Manual Test Plan 中标记为前置条件（必要时用 ngrok HTTPS 隧道）。

## Environment Availability

| 依赖 | 用途 | Available | 版本 | Fallback |
|------|------|-----------|------|----------|
| Node.js + npm | 前端构建 | ✓（假设） | — | — |
| React 18.3.1 | UI | ✓ | 18.3.1 | — |
| react-router-dom 7.6.0 | 路由 | ✓ | 7.6.0 | — |
| axios 1.8.4 | HTTP | ✓ | 1.8.4 | — |
| TypeScript 5.8.3 | 类型 | ✓ | 5.8.3 | — |
| 飞书 QRLogin CDN (lf-package-cn.feishucdn.com) | QR SDK | ✓（网络可达前提下） | 1.0.3 | 无 — SDK 不可用时显示 `sdk_load_failed` 错误 banner + 提示改用邮箱登录 |
| 后端 `/api/v1/auth/feishu/authorize` | 取授权 URL | ✓（Phase 26 已交付） | — | 无 — 失败则显示错误 banner |
| 后端 `/api/v1/auth/feishu/callback` | 换 JWT | ✓（Phase 26 已交付） | — | 无 — 失败则回调页显示错误卡片 |
| Vitest / Jest / RTL | 单元测试 | ✗ | — | **手动浏览器验证**（Playwright 也没有）— 若决定引入，需 Wave 0 前置任务 |
| Playwright / Cypress | E2E 测试 | ✗ | — | 手动验证（REQUIREMENTS.md 已 defer E2E） |
| Redis（后端） | state/code 存储 | ✓（假设）| — | 503 降级已在 Phase 26 实现 |
| 飞书应用（app_id + app_secret + redirect_uri） | OAuth 凭证 | ? | — | 无 — 缺失则 `/feishu/authorize` 返回错或飞书 20002 |

**Missing dependencies with no fallback:**
- 飞书应用配置缺失或错误 → 阻塞（属于外部配置，不是 Phase 27 代码范围）。

**Missing dependencies with fallback:**
- 前端测试框架：降级为手动验证。

## Validation Architecture

> 本节按 `workflow.nyquist_validation: true` 执行。

### Test Framework

| Property | Value |
|----------|-------|
| Framework（当前） | **无** — 前端没有任何测试运行器 |
| Framework（建议 Wave 0 引入，可选） | Vitest 1.x + @testing-library/react 16.x + @testing-library/jest-dom 6.x + jsdom 或 happy-dom |
| Config file | 无；若引入需新增 `frontend/vitest.config.ts` |
| Quick run command（若引入） | `cd frontend && npm run test -- --run --reporter=basic` |
| Full suite command（若引入） | `cd frontend && npm run test -- --run --coverage` |
| 手动验证命令（现实路径） | 启动后端 `uvicorn backend.app.main:app --reload` + 前端 `cd frontend && npm run dev` + 浏览器访问 `http://localhost:5174/login` 按 Manual Test Plan 操作 |
| Lint 命令（两者皆适用） | `cd frontend && npm run lint`（即 `tsc --noEmit`） |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| **FUI-01** | `FeishuLoginPanel` 挂载时注入 SDK 脚本并调用 `QRLogin`；容器出现 iframe | **unit**（含 DOM） | `vitest frontend/src/components/auth/FeishuLoginPanel.test.tsx` （需 Wave 0）| ❌ Wave 0 |
| FUI-01（手动） | 真实浏览器扫真实二维码 | **manual** | 浏览器 + 飞书 App | 手动 |
| **FUI-02** | 访问 `/auth/feishu/callback?code=X&state=Y` 能解析 params 并调用 `loginWithFeishu` | **unit** | `vitest frontend/src/pages/FeishuCallbackPage.test.tsx` | ❌ Wave 0 |
| FUI-02 | service 层 `feishuCallback(code, state)` 调对后端端点 | **unit** | `vitest frontend/src/services/auth.test.ts` | ❌ Wave 0 |
| **FUI-03** | 180s 后面板显示过期蒙层 | **unit** | `vitest + vi.useFakeTimers()` | ❌ Wave 0 |
| FUI-03 | 点刷新按钮重新 fetch authorize_url 且重建 QRLogin | **unit** | 同上 | ❌ Wave 0 |
| **FUI-04** | `resolveFeishuError('backend', {...400 with state})` 返回 `state_invalid_or_expired` | **unit** | `vitest frontend/src/utils/feishuErrors.test.ts` | ❌ Wave 0 |
| FUI-04 | 回调页 failed 状态显示对应中文 + 「返回登录」按钮 | **unit** | `vitest frontend/src/pages/FeishuCallbackPage.test.tsx` | ❌ Wave 0 |
| **FUI-01~04 整体** | 端到端扫码成功回到 `/workspace` | **manual** | 浏览器 + 真实飞书 app | 手动 |
| **LOGIN-04**（保留约束）| 邮箱密码登录路径未损坏 | **manual**（+ 现有集成测试） | 浏览器回归 + `pytest backend/tests/test_api/test_auth.py` | ✅（后端侧） |
| **TypeScript 编译** | 所有代码类型检查通过 | automated | `cd frontend && npm run lint` | ✅ 无需新建 |

### Sampling Rate

- **Per task commit:** `cd frontend && npm run lint`（快速 tsc 检查；秒级）+ 手动刷新浏览器看无 console error。
- **Per wave merge:** `cd frontend && npm run build`（完整 tsc + vite 构建）+ 浏览器端到端手动验证登录 + 后端回归 `pytest backend/tests/test_api/test_feishu_oauth_integration.py`。
- **Phase gate:** Full manual test plan（见下）全绿 + `npm run lint` + `npm run build` + 后端 auth 相关 pytest 通过。

### Manual Test Plan（替代单元测试的实事求是方案）

| # | 操作 | 预期结果 | 覆盖 Req |
|---|------|---------|----------|
| 1 | 启动前后端，访问 `/login` | 右侧 section 下方出现飞书 QR 面板，二维码在 2-3s 内显示 | FUI-01 |
| 2 | 用飞书 App 扫描并授权 | 浏览器自动跳到 `/auth/feishu/callback?code=...&state=...` | FUI-01 |
| 3 | 观察回调页 | 处理中骨架卡片 → 成功短停 → 跳到角色首页（admin→/workspace, employee→/my-review） | FUI-02 |
| 4 | 首次用工号已匹配但未绑定的飞书账号登录 | `localStorage` 写入 auth session；下次刷新仍登录；数据库 `users.feishu_open_id` 被写 | FUI-02 |
| 5 | 在 QR 面板停留 3 分钟 | 面板显示毛玻璃蒙层 + 「二维码已过期，点击刷新」按钮 | FUI-03 |
| 6 | 点刷新 | 蒙层消失，二维码刷新，倒计时重置；旧 state 失效（后端日志看到删除） | FUI-03 |
| 7 | 在飞书 App 内点拒绝授权 | 回调页显示「你已取消飞书授权」+ 「返回登录」 | FUI-04 |
| 8 | 手动篡改 URL 的 `state` 再访问回调 | 回调页显示「会话已过期，请刷新二维码重试」 | FUI-04 |
| 9 | 用**未绑定**员工的飞书账号登录 | 回调页显示「工号未匹配，请联系管理员开通」 | FUI-04 (FAUTH-05 延伸) |
| 10 | 断网状态下点「账号登录」tab 的扫码刷新 | 面板内红色 banner「网络错误，请检查连接」+ 「重试」 | FUI-04 |
| 11 | 在 CSP 阻塞 feishucdn.com 的模拟场景（或修改 constant 到不存在域名） | 面板内「飞书登录组件加载失败」+ 重试 | FUI-04 |
| 12 | 用已绑定 feishu_open_id 的账号二次登录 | fast-path：跳过 employee_no 匹配直接 JWT | FUI-02 (FAUTH-04) |
| 13 | 保留邮箱密码登录回归 | 左/上方 LoginForm 功能完全不变，所有账号仍能用邮箱密码登录 | LOGIN-04 |
| 14 | `must_change_password=true` 账号扫码成功 | 跳到 `/settings` 并携带 `forcePasswordChange: true` state | D-05 / discretion |

### Wave 0 Gaps（if 决定引入 vitest）

- [ ] `frontend/vitest.config.ts` — Vitest 配置文件（使用 `environment: 'jsdom'`）
- [ ] `frontend/package.json` 加 `devDependencies`: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` 或 `happy-dom`, `@vitest/ui`（可选）
- [ ] `frontend/package.json` 加 script: `"test": "vitest"`
- [ ] `frontend/src/setupTests.ts` — 引入 `@testing-library/jest-dom/vitest`
- [ ] `frontend/tsconfig.json` 的 `include` 需要加 `"setupTests.ts"` 或新建 `tsconfig.test.json`
- [ ] 更新 `npm run lint` 脚本使其不 fail on test files（或保持分离）

*(若决定 **不** 引入 vitest：Wave 0 gaps 为空；Manual Test Plan 是唯一验证路径；降级符合 CLAUDE.md "完成任务前必须测试"的约束，因为"测试"涵盖手动验证 + `tsc --noEmit` + 后端 pytest。)*

**研究侧建议：** 由于 Phase 27 本身不大（估计 4-6 个文件），引入 vitest 的额外成本（引入 + 配置 + 写 6-8 个测试文件）会**翻倍**这一 phase 的工作量。**建议本 Phase 不引入 vitest**，改为在 v1.4 做专门的"前端测试基础设施"Phase。Phase 27 按 Manual Test Plan 验证即可。此决策由 planner 在 PLAN.md 中最终锁定。

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 复用 Phase 26 后端 OAuth2 流程；前端只负责展示与跳转，不做凭证校验 |
| V3 Session Management | yes | 复用 `storeAuthSession` / `updateStoredTokens`；不新增 session 机制；`feishu_open_id` 只读不改 |
| V4 Access Control | yes | 回调页是公开路由（`/auth/feishu/callback` 不在 ProtectedRoute 下），成功后写 localStorage + setState，后续 ProtectedRoute 自然 allowance |
| V5 Input Validation | yes | `code` / `state` 从 URL query 取，后端做最终校验（长度 + state Redis 比对）；前端只做"存在与否"检查 |
| V6 Cryptography | no | JWT 签名在后端；前端不做加解密 |
| V13.1 Generic API | yes | CORS 假定已由后端允许前端源（`allowed_origins` in Settings） |
| V14 Config | yes | CDN URL 作为 module constant，不接用户输入 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation | 本 Phase 处置 |
|---------|--------|---------------------|---------------|
| postMessage 来源伪造（任意页面嵌 iframe 发 `{tmp_code: "恶意值"}`）| Spoofing | `matchOrigin` + `matchData` 双校验 | Pattern 2 代码已覆盖，**必须**同时两者通过才使用 `tmp_code` |
| CSRF（攻击者构造带恶意 state 的回调 URL）| Tampering | state 随机 + Redis 一次性消费 | 后端已实现（Phase 26 D-02），前端只需把收到的 state 原样回传 |
| code replay | Replay | Redis 600s 防重放 | 后端已实现（Phase 26 D-03） |
| redirect_uri 篡改 | Tampering | 后端固定 redirect_uri 不接受请求参数 | 已实现（26 T-26-05） |
| localStorage 被 XSS 读取 | Info Disclosure | 前端不存 user_access_token（仅存 JWT） | 符合 — Phase 27 只写 `storeAuthSession(authResponse)`（JWT），`user_access_token` 不落前端 |
| CDN 脚本被污染（供应链攻击）| Tampering | 可选：加 SRI integrity hash 或 pin 版本 | 本 Phase 不做 SRI（飞书官方不发布 SRI hash）；风险由"信任飞书 CDN"承担 |
| 敏感信息记录到 console | Info Disclosure | 不要 `console.log(tmp_code / code / state)` | 实现注意项 — 未来接入真正的前端 telemetry 时不要把这些打到日志 |
| 跨域 CORS 被错误配置 | Info Disclosure | 后端 CORS 限白名单 | 不在 Phase 27 范围 |

## Sources

### Primary (HIGH confidence)

- `backend/app/api/v1/auth.py:269-297` — feishu OAuth 端点源码 `[VERIFIED]`
- `backend/app/services/feishu_oauth_service.py:21-26, 89-138` — 错误码映射与状态码 `[VERIFIED]`
- `backend/app/schemas/user.py:37, 92-95, 154-156` — AuthResponse / FeishuCallbackRequest `[VERIFIED]`
- `backend/tests/test_api/test_feishu_oauth_integration.py:164-269` — 实际 HTTP 响应 shape 验证 `[VERIFIED]`
- `frontend/src/hooks/useAuth.tsx` — handleLogin 参考模式 `[VERIFIED]`
- `frontend/src/services/auth.ts` — storeAuthSession 等复用 API `[VERIFIED]`
- `frontend/src/services/api.ts` — axios 实例 + 401 refresh 机制 `[VERIFIED]`
- `frontend/src/App.tsx:49-56, 415-468` — resolveError 模式、路由注册位置 `[VERIFIED]`
- `frontend/src/pages/Login.tsx:23-45` — 现有邮箱登录跳转逻辑与 must_change_password 处理 `[VERIFIED]`
- `frontend/src/hooks/usePolling.ts:56-65` — 本项目既有定时器 cleanup 模式 `[VERIFIED]`
- `frontend/src/main.tsx` — 确认**无** StrictMode 包裹 `[VERIFIED]`
- `frontend/package.json` — React 18.3.1 / react-router-dom 7.6.0 / 无测试框架 `[VERIFIED]`
- `.planning/phases/26-oauth2/26-02-SUMMARY.md` — AuthResponse 返回决策 `[VERIFIED]`

### Secondary (MEDIUM confidence)

- [飞书官方二维码 SDK 接入文档](https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/qr-sdk-documentation) — 官方页，sandbox 内网络受限未直连，内容经多个社区源交叉验证 `[CITED]`
- [飞书二维码联合登录实战 (CSDN 144227680)](https://blog.csdn.net/ZuiChuDeQiDian/article/details/144227680) — SDK 1.0.3 参数与 event.data 结构 `[CITED]`
- [飞书扫码登录全流程 (掘金 7501203502665891866)](https://aicoding.juejin.cn/post/7501203502665891866) — matchOrigin / matchData 最佳实践 `[CITED]`
- [飞书扫码登录网页 (博客园 xutongbao)](https://www.cnblogs.com/xutongbao/p/18161614) — QRLogin 基础参数验证 `[CITED]`
- [vue3 飞书扫码登录 (CSDN 133647799)](https://blog.csdn.net/qq_37656005/article/details/133647799) — postMessage 完整监听范式 `[CITED]`
- [飞书二维码登录注意点 (CSDN 145040888)](https://blog.csdn.net/qq_39099980/article/details/145040888) — 容器 innerHTML='' 防叠加 `[CITED]`
- [React Router v7 useSearchParams 文档](https://reactrouter.com/api/hooks/useSearchParams) — v7 API 契约 `[CITED]`
- [React 18 StrictMode 官方博文](https://dev.to/jherr/react-18-useeffect-double-call-for-apis-emergency-fix-27ee) — 双挂载 cleanup 模式 `[CITED]`
- [Why Your useEffect Is Firing Twice (UpgradeJS)](https://www.upgradejs.com/blog/javascript/react/updates-to-strict-mode-in-react-18.html) — StrictMode 正确 cleanup `[CITED]`
- [MDN: Window.postMessage()](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage) — postMessage 安全最佳实践 `[CITED]`

### Tertiary (LOW confidence — 标记为 ASSUMED)

- 见"Assumptions Log"表 A1-A7

## Metadata

**Confidence breakdown:**
- Backend API contract: **HIGH** — 代码/测试直接验证
- Frontend baseline (api.ts / useAuth / types): **HIGH** — 源码直接验证
- QRLogin SDK 契约: **MEDIUM** — 官方文档 sandbox 不可达，结论来自 5+ 独立社区实现交叉验证，一致性高；版本号和具体 config 字段 100% 交叉一致
- React 18 StrictMode 模式: **HIGH** — 官方推荐 + 社区共识
- react-router-dom v7 API: **HIGH** — 官方文档
- 错误码映射: **HIGH** — 后端源码直读；前端分类是新设计但合理
- Testing 现状: **HIGH** — 直接检查 package.json 和源码目录确认无测试框架

**Research date:** 2026-04-19
**Valid until:** ~2026-05-19（30 天；飞书 CDN 版本可能更新，每月重看一次 QR SDK 文档页；React/Router 稳定）

---

## RESEARCH COMPLETE

**Phase:** 27 - 飞书 OAuth2 前端集成
**Confidence:** HIGH (后端契约 / 项目基线) / MEDIUM (QRLogin SDK 细节)

### Key Findings
- **关键勘误：** CONTEXT.md D-10 提到的 `onSuccess` / `onReady` / `onErr` 回调在飞书 QRLogin 1.0.3 SDK 中**不存在** — SDK 通过 `window.postMessage` 传 `{tmp_code}`，前端必须手动 `addEventListener('message')` + `matchOrigin/matchData` 校验 + 手动 `window.location.href = goto + '&tmp_code=...'` 重定向。不影响 D-10 的"不轮询后端"结论，但影响具体实现代码。
- **前端无测试基础设施：** 没有 vitest/jest/RTL/Playwright。建议本 Phase 降级为 Manual Test Plan + `tsc --noEmit` + 后端 pytest 回归；引入 vitest 单独立项。
- **`main.tsx` 未启用 React.StrictMode：** 放松了双挂载约束，但代码仍应写幂等（未来可能启用；QR 刷新本身就是真·重建）。
- **后端响应 shape：** `GET /feishu/authorize` → `{authorize_url, state}`；`POST /feishu/callback` → `AuthResponse`（完整 user + tokens）；错误统一 `{detail: "中文"}`（FastAPI 默认，但 main.py 可能改写过 — Planner Task 0 需验证）。
- **两个必须验证的外部前提：** (A4) `main.py` exception handler 是否改写错误格式；(A5) `FEISHU_REDIRECT_URI` 是指向前端还是后端 callback URL — 后者若错了整个 D-04/D-05 流程需改写。

### File Created
- `.planning/phases/27-oauth2/27-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Backend API Contract | HIGH | 代码 + 集成测试直接验证 |
| Feishu QRLogin SDK | MEDIUM | 官方文档 sandbox 不可达；5+ 社区源一致验证；最新版本号存小风险 |
| React / Router / Axios 模式 | HIGH | 项目代码 + 官方文档 |
| Error code mapping | HIGH | 后端源码直读 |
| Testing 可行路径 | HIGH | 直接验证前端无测试框架 |
| StrictMode / Timer cleanup | HIGH | React 官方 + 项目既有模式 |

### Open Questions (RESOLVED)
1. **A5 – `FEISHU_REDIRECT_URI` 实际配置指向前端还是后端？** — **RESOLVED** `.env.example:61` 指向前端 `/auth/feishu/callback`；Plan 01 frontmatter 已记录验证，部署环境不符时 executor BLOCK。
2. **A4 – main.py exception_handler 是否改写 `{detail}` 格式？** — **RESOLVED** `backend/app/main.py:132-142` 改写为 `{error, message}`；Plan 01 Task 2 的 `resolveFeishuError.classifyBackend` 已按此格式实现并对 `detail` 兜底。
3. **Vitest 是否引入？** — **RESOLVED** 不引入；27-VALIDATION.md:20 锁定为 `tsc --noEmit` + Manual Test Plan + 后端 pytest 回归。
4. **Dev 环境飞书是否接受 `http://127.0.0.1:5174/auth/feishu/callback` 作为 redirect_uri？** — **RESOLVED (deferred)** 属运行环境前置条件，Manual Test Plan 中标记（必要时用 ngrok HTTPS 隧道），Phase 27 不解决。

### Ready for Planning
研究完成。Planner 可基于本文档创建 PLAN.md。建议 plan 结构：
- **Wave 0（Task 0）：** 验证 A4 / A5 两个假设；输出配置确认或阻塞。
- **Wave 1：** 添加类型（`types/api.ts`）+ service（`services/auth.ts`）+ utils（`feishuErrors.ts`）+ useAuth 补 `loginWithFeishu`。
- **Wave 2：** 实现 `FeishuCallbackPage` + 路由注册 + 手动验证 #2 #3 #7 #8 #9 #12 #14。
- **Wave 3：** 实现 `FeishuLoginPanel`（SDK 注入 + QR 渲染 + 倒计时 + 刷新 + 错误 banner）+ 插入 `Login.tsx`。手动验证 #1 #5 #6 #10 #11 #13。
- **Gate：** Manual Test Plan 14 项全绿 + `npm run lint` + `npm run build` + 后端 `pytest backend/tests/test_api/test_feishu_oauth_integration.py` 通过。
