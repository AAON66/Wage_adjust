# Phase 27: 飞书 OAuth2 前端集成 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 27-oauth2
**Areas discussed:** QR SDK 加载与初始化, 回调路由形态, 二维码过期与刷新, 错误分类与展示

---

## Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| QR SDK 加载与初始化 | 官方 CDN 脚本 vs npm 包 vs 自实现；authorize_url 获取时机 | ✓ |
| 回调路由形态 | 独立页面 vs 透明重定向 vs 复用现有路由；useAuth 衔接方式 | ✓ |
| 二维码过期与刷新 | 手动刷新 vs 自动静默 vs 倒计时 + 手动；扫码状态反馈来源 | ✓ |
| 错误分类与展示 | 文案映射位置、展示位置与方式、登录页布局边界 | ✓ |

**User's choice:** 全部四个领域。

---

## QR SDK 加载与初始化

### Q1: 飞书 QR SDK 如何集成？

| Option | Description | Selected |
|--------|-------------|----------|
| 官方 CDN 脚本动态注入 (Recommended) | useEffect 内 inject `<script src="https://lf-package-cn.feishucdn.com/...QRLogin.js"/>`，调用 window.QRLogin(...)。版本始终跟随官方、不增大 bundle | ✓ |
| npm 包 @larksuiteoapi/lark-js-sdk | 可离线打包、TypeScript 类型支持；但需确认该包确实暴露 QRLogin、增加 bundle | |
| 后端代理或自实现二维码 | 不用 SDK，纯后端 + 前端轮询；改造量大，Phase 26 未规划端点 | |

**User's choice:** 官方 CDN 脚本动态注入

### Q2: authorize_url (含 state) 什么时候请求后端？

| Option | Description | Selected |
|--------|-------------|----------|
| QR 面板挂载时调用 (Recommended) | 用户打开登录页就调用一次 /auth/feishu/authorize，过期前不重复；与 300s TTL 匹配 | ✓ |
| 用户点击标签才加载 | 默认不初始化 SDK，切换 Tab 时再请求；节省 Redis 写入，但引入额外 loading | |
| 页面挂载预拉取 + 自动刷新 | 挂载立即调用 + 启动定时器 2:55 主动刷新；完全自动化 | |

**User's choice:** QR 面板挂载时调用

---

## 回调路由形态

### Q1: /auth/feishu/callback 路由做成什么形态？

| Option | Description | Selected |
|--------|-------------|----------|
| 独立页面组件有 loading/error UI (Recommended) | FeishuCallbackPage 组件：解析 URL 的 code/state → 调用 callback → 写入 localStorage → useNavigate。显示 loading 骨架和错误卡片 | ✓ |
| 轻量透明路由 | 不渲染可见内容，useEffect 处理后立即重定向；错误需回跳 /login 显示 | |
| 不新增路由，在现有页面判断 | 对 redirect_uri 回到 / 或 /login，根据 query 参数处理；需改后端固定 redirect_uri，耦合升高 | |

**User's choice:** 独立页面组件有 loading/error UI

### Q2: 回调成功后用户应用状态如何衔接 useAuth？

| Option | Description | Selected |
|--------|-------------|----------|
| 为 useAuth 新增 loginWithFeishu(code, state) 方法 (Recommended) | 保持与现有 login(payload) 相同模式；FeishuCallbackPage 只需调 loginWithFeishu | ✓ |
| 回调页面直接调用 service + storeAuthSession | 不改 useAuth，页面 import storeAuthSession；可能忽略 bootstrap 的 fetchCurrentUser 刷新 | |
| 调用后 window.location.href 重新 bootstrap | 硬刷新触发 AuthProvider bootstrap；最小代码改动但闪白重载 | |

**User's choice:** 为 useAuth 新增 loginWithFeishu(code, state) 方法

---

## 二维码过期与刷新

### Q1: 二维码过期后如何处理？

| Option | Description | Selected |
|--------|-------------|----------|
| 过期后显示「点击刷新」蒙层 (Recommended) | 180s 到期后 QR 上覆盖毛玻璃蒙层 + 刷新按钮；用户点击时重新调 authorize + 重建 QRLogin | ✓ |
| 过期时点静默自动刷新 | 2:55 自动调 authorize + 重建，用户无感；但会不停占用后端 Redis | |
| 倒计时 + 手动确认刷新 | 显示剩余时间，到期后显示刷新按钮；更透明但占用视觉面积 | |

**User's choice:** 过期后显示「点击刷新」蒙层

### Q2: 扫码过程中如何处理状态反馈？

| Option | Description | Selected |
|--------|-------------|----------|
| 依赖飞书 SDK 的 onSuccess/onReady/onErr 回调 (Recommended) | QRLogin 自带回调；onSuccess 会自动重定向到 redirect_uri；无需额外轮询后端 | ✓ |
| 额外轮询后端检查扫码状态 | 除 SDK 回调外再用 setInterval 查后端；Phase 26 未提供此端点 | |

**User's choice:** 依赖飞书 SDK 的 onSuccess/onReady/onErr 回调

---

## 错误分类与展示

### Q1: 错误文案映射逻辑放在哪里？

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 feishuErrorMessages 常量集中映射 (Recommended) | frontend/src/utils/feishuErrors.ts 集中：后端 error code/message + SDK onErr 码 → 中文文案 | ✓ |
| 在回调页面内联 switch 处理 | FeishuCallbackPage 内部 switch；难复用到 Login 页的 SDK 错误（onErr） | |
| 直接使用后端返回的 message 字段 | 依赖后端文案稳定；onErr 前端错误维度仍需自写 | |

**User's choice:** 新建 feishuErrorMessages 常量集中映射

### Q2: 错误展示位置和方式？

| Option | Description | Selected |
|--------|-------------|----------|
| 回调页错误卡片 + QR 面板内 inline banner (Recommended) | 双场景：(1) 回调页失败居中错误卡片 + 返回登录按钮；(2) Login 页 SDK / authorize 失败面板内红色 banner + 重试 | ✓ |
| 全局 Toast 通知 | 项目无现有 Toast，新建会偏离风格 | |
| 回调失败自动跳回 /login 并在登录页展示 | 回调页不展示错误，带 error query 跳回 /login | |

**User's choice:** 回调页错误卡片 + QR 面板内 inline banner

### Q3: 登录页 QR 面板与现有「左右双栏」如何共存？（Phase 29 才做完整重设计）

| Option | Description | Selected |
|--------|-------------|----------|
| 新增独立 FeishuLoginPanel 组件，放在右侧 section (Recommended) | 现有 Login.tsx 的第二 section（访问入口）内部：LoginForm 上方或下方添加 FeishuLoginPanel；Phase 29 重设计时只需搬移组件，不需重写 QR 逻辑 | ✓ |
| 插入在登录表单上方 + 分割线 | LoginForm 上方添加 FeishuLoginPanel + 「或使用账号密码登录」分割线；与 Phase 29 目标方向不一致 | |
| 预先重构为左右双栏，提前实现 Phase 29 | 把 Phase 29 的左右布局提前在 Phase 27 做（不动粒子背景）；范围蔓延 | |

**User's choice:** 新增独立 FeishuLoginPanel 组件，放在右侧 section

---

## Claude's Discretion

- CDN 脚本 URL 具体版本（跟随飞书官方最新稳定版）
- QRLogin 配置项细节（width/height/iframeStyle 等视觉参数）
- 骨架屏与错误卡片精确视觉细节（遵循现有 surface / action-primary 类）
- 倒计时实现（setTimeout + cleanup）
- 跳转目标（复用 getRoleHomePath）
- must_change_password 场景处理（与 Login.tsx 对齐）
- 测试策略（单元测试覆盖映射表 + 组件；SDK 集成手动验证）

## Deferred Ideas

- 粒子动态背景（LOGIN-02, LOGIN-03）→ Phase 28
- 登录页完整左右双栏重设计（LOGIN-01）→ Phase 29
- 飞书工作台免登（tt.requestAccess）→ 未来里程碑
- 扫码/密码 Tab 切换模式 → REQUIREMENTS Out of Scope
- 持久化 user_access_token → REQUIREMENTS Out of Scope
- E2E 集成测试套件 → REQUIREMENTS deferred
