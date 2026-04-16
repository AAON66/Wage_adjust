# Feature Research

**Domain:** 企业 SSO 登录 — 飞书 OAuth2 登录 + 登录页重设计 (v1.3)
**Researched:** 2026-04-16
**Confidence:** HIGH (飞书官方文档 + 已有代码库核实)

---

## 背景与现有状态

本次研究聚焦 v1.3 里程碑新增功能，现有系统已完成：

- JWT 邮箱/密码登录（`LoginForm.tsx` + `useAuth` hook）
- 登录页：左侧角色说明卡 + 右侧登录表单（`Login.tsx` 两栏布局）
- `token_version` JWT 强制失效机制（绑定/解绑触发）
- `User.employee_id` FK 绑定 `Employee`；`employee_no` 通过 `user.employee.employee_no` 读取
- `FeishuService` 管理 `tenant_access_token` + bitable 考勤/绩效同步，**不处理用户 OAuth 登录**

新功能必须叠加在此基础上，不得破坏现有账号密码流程。

---

## 飞书 OAuth2 两种登录模式说明

飞书提供两套完全不同机制，适用于不同运行环境：

| 模式 | 运行环境 | 机制 | 依赖条件 |
|------|----------|------|----------|
| **扫码登录（QR Code）** | 普通浏览器（PC/外部 H5） | 飞书 QR SDK 嵌入二维码 → 用户用飞书 App 扫码 → 返回 `tmp_code` → 后端换 `user_access_token` | App ID、Redirect URI 预注册、QR SDK CDN |
| **网页授权免登（SSO）** | 飞书 App 内嵌 WebView（工作台） | `tt.requestAccess()` 自动获取授权码 → 后端换 `user_access_token` | App ID、可信域名配置、飞书客户端环境、JSSDK |

**本项目 v1.3 选用扫码登录。** 系统以独立浏览器 PC 端为主，不作为飞书工作台应用发布；扫码登录不依赖飞书客户端环境，兼容性更好。网页授权免登留作 v2 可选增强。

---

## 飞书 OAuth2 完整后端流程（HIGH confidence — 官方文档核实）

```
1. 前端构造授权 URL，通过 QR SDK 渲染二维码
   GET https://accounts.feishu.cn/open-apis/authen/v1/authorize
       ?client_id=APP_ID
       &redirect_uri=REDIRECT_URI        # 必须在飞书后台安全设置预注册，完全匹配
       &response_type=code
       &state=RANDOM_CSRF_TOKEN          # 存入 sessionStorage 用于回调验证

2. 用户用飞书 App 扫码确认授权
   → 飞书回调 redirect_uri?code=XXX&state=YYY
   （code 有效期 5 分钟，单次使用）

3. 后端验证 state 防 CSRF，用 code 换 user_access_token
   POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
   Body: { client_id, client_secret, code, grant_type: "authorization_code", redirect_uri }
   返回: { access_token, expires_in, refresh_token, ... }

4. 后端用 user_access_token 获取用户信息
   GET https://passport.feishu.cn/suite/passport/oauth/userinfo
   Authorization: Bearer {user_access_token}
   返回: { open_id, union_id, user_id, name, email, mobile, employee_no, avatar_url, ... }
   （employee_no 需飞书应用申请"获取用户受雇信息"权限）

5. 按 employee_no 匹配系统 Employee 记录 → 找到绑定的 User → 签发系统 JWT
   与现有账号密码登录共用相同的 JWT 生成逻辑（token_version 一致）

6. 前端收到系统 JWT，走与现有登录相同的 token 存储、角色跳转逻辑
```

**关键约束：** `user_access_token` 仅用于登录时换取用户信息，之后丢弃。不持久化存储，不与现有 `FeishuService` 的 `tenant_access_token` 混用。

---

## Feature Landscape

### Table Stakes（用户期望存在，缺失则感觉残缺）

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 飞书扫码登录区域（QR SDK 嵌入） | 企业内部系统标配入口；员工期望不用记密码直接扫码进入 | MEDIUM | 引入飞书 QR SDK（`LarkSSOSDKWebQRCode-1.0.3.js` CDN），在 `<div id="feishu-qr-container">` 渲染二维码；监听 `window.message` 事件获取 `tmp_code` |
| OAuth 回调处理路由 `/auth/feishu/callback` | 飞书扫码后跳转到此，必须有前端路由处理 code → 系统 JWT 转换 | LOW | 新 React 路由页：从 URL 解析 `?code=&state=`，验证 state，POST 后端，成功后按角色跳转；失败显示中文错误 |
| 后端 OAuth callback 接口 `POST /api/v1/auth/feishu/callback` | 前后端协议边界 | MEDIUM | 接收 `{code, state}`，验证 state，换 `user_access_token`，调用飞书 userinfo，按 `employee_no` 匹配 `Employee`→`User`，签发系统 JWT |
| 按 employee_no 自动匹配绑定 | 企业员工 `employee_no` 唯一且系统内已存在，无需额外人工绑定步骤 | LOW | 查 `Employee.employee_no`→`User.employee_id`；匹配失败返回明确错误"飞书账号未与系统账号绑定，请联系管理员" |
| CSRF state 参数校验 | OAuth 2.0 基础安全要求，防授权码劫持 | LOW | 前端生成随机 state 存 `sessionStorage`，回调时比对；后端不需要额外存储 |
| 登录页双栏重设计（左侧账号密码 + 右侧飞书扫码） | v1.3 明确目标；与同类企业系统视觉预期一致 | LOW | 重写 `Login.tsx`；左侧保留现有 `LoginForm` 组件；右侧新增飞书扫码面板 |
| Canvas 粒子动态背景 | 登录页视觉现代感；避免空白背景感；产品定位为技术型企业平台 | LOW | 原生 Canvas + `requestAnimationFrame`；不引入 `particles.js` 外部库；参数硬编码即可（粒子数约 80，连线距离 150px） |
| 登录失败分类错误提示 | 飞书登录失败原因多样，笼统提示"登录失败"是高频体验痛点 | LOW | 三类错误：(1) `employee_no` 未匹配：提示"飞书账号未绑定系统账号"；(2) 飞书授权失败（`error=access_denied`）：提示"授权被取消"；(3) 网络/超时：提示"网络错误，请重试" |
| 保持现有邮箱/密码登录不变 | 管理员和初始化账号可能无飞书账号；不能断掉现有入口 | LOW | `LoginForm.tsx` 不改动；仅调整在页面中的布局位置 |

### Differentiators（加分项，非必须但有价值）

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 二维码自动刷新（过期重新生成） | 飞书 QR 码有效期约 3 分钟；页面长时间停留后不刷新用户会困惑 | LOW | 前端设 3 分钟 timer 重新初始化 QR SDK；QR SDK 自身可能内置刷新（需验证） |
| 粒子背景鼠标跟随交互（连线/排斥） | 提升视觉品质感，增加科技感 | LOW | Canvas `mousemove` 监听 + 粒子引力/斥力算法；纯原生实现约 50 行 |
| `feishu_open_id` 存储到 User 模型 | 飞书登录后记录 `open_id`，后续可通过 `open_id` 快速识别而无需每次查 `employee_no` | LOW | `User` 模型加 `feishu_open_id: Mapped[str | None]` 字段；Alembic migration；P2 优先级，v1.3 可跳过 |
| 登录页暗色模式适配 | 与系统整体 CSS 变量体系一致 | LOW | 粒子背景颜色使用 CSS 变量而非硬编码；无需额外工作量 |

### Anti-Features（看似合理但应明确不做）

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 飞书工作台免登（`tt.requestAccess`） | "从飞书工作台点进去不用扫码" | 依赖飞书客户端 WebView 环境和 JSSDK 鉴权；需要配置可信域名；应用需上架飞书工作台；当前系统不作为工作台应用发布，实现复杂度与优先级不匹配 | 扫码登录已覆盖主要场景；工作台集成可作独立 v2 里程碑 |
| 首次飞书登录自动创建系统账号 | "扫码就能用，不需要管理员预建账号" | 新建账号无角色、无员工绑定，进不了任何功能页面；绕过现有角色分配和 RBAC 流程；引入"飞书存在但系统无角色"的灰色状态 | 保持"管理员预建账号 + employee_no 绑定"流程；飞书登录匹配失败时显示"请联系管理员开通账号" |
| 扫码/密码同一面板 Tab 切换 | 视觉上更紧凑 | Tab 切换时 QR SDK 容器销毁/重建会触发二维码闪烁；行业标准（企业微信、钉钉登录页）均采用双栏或并列而非 Tab | 左右分栏：左侧账号密码，右侧飞书扫码，两种方式视觉并列 |
| 后端持久化存储飞书 `user_access_token` | "后续可直接调用飞书用户 API" | 飞书 token 有效期短（2h），存储带来安全风险；本系统登录后不需要持续调用飞书用户 API；`tenant_access_token`（机器人权限）已由 `FeishuService` 管理 | 仅用于登录时换取用户信息后丢弃；如需标识可存 `feishu_open_id`（字符串，无安全风险） |
| 引入 `particles.js` / `tsparticles` 库 | "成熟库效果更好" | 压缩后仍约 50KB+，登录页是首次加载性能最关键的页面；外部 CDN 引入增加故障点；原生 Canvas 200 行以内可实现相同效果 | 原生 Canvas + `requestAnimationFrame` 实现，零外部依赖 |
| 飞书扫码状态实时轮询（已扫码/确认中） | "扫码后让用户知道状态" | 需要后端维护扫码状态或 SSE 连接，复杂度高；飞书 QR SDK 的 `message` 事件本身就是确认信号，确认后立即发起 OAuth 回调即可 | 扫码成功 → 立即重定向回调页，回调页展示"登录中..."loading 状态即可 |

---

## Feature Dependencies

```
飞书 QR SDK 扫码区域（前端）
    └──requires──> 飞书开放平台应用（App ID + App Secret）[外部依赖，需人工配置]
    └──requires──> Redirect URI 在飞书后台安全设置中预注册（完全字符串匹配）
    └──requires──> QR SDK 脚本加载（CDN script tag 在 public/index.html）
    └──triggers──> 前端 OAuth 回调路由

前端 OAuth 回调路由 /auth/feishu/callback
    └──requires──> 后端 OAuth callback 接口
    └──requires──> sessionStorage 中的 state 值（CSRF 验证）
    └──on-success──> 走与现有账号密码登录相同的 JWT 存储 + 角色跳转逻辑

后端 OAuth callback 接口 POST /api/v1/auth/feishu/callback
    └──requires──> 飞书 userinfo API（外部调用）
    └──requires──> Employee.employee_no 索引（数据库）
    └──requires──> Employee 已绑定 User（employee_id FK，v1.1 已建立）
    └──reuses──> 现有 create_access_token() / create_refresh_token() 函数

登录页双栏重设计
    └──requires──> 飞书扫码区域组件（右侧面板）
    └──reuses──> 现有 LoginForm 组件（左侧面板，不改动）
    └──replaces──> 现有 Login.tsx 布局（原角色介绍卡压缩为背景层文字）

Canvas 粒子背景
    └──requires──> 新版登录页组件（作为全屏背景层）
    └──independent-of──> 飞书 OAuth2 逻辑（纯视觉）
```

### Dependency Notes

- **飞书 OAuth2 requires employee_no 绑定已建立：** v1.1 账号绑定流程已完成此依赖。`User.employee_no` 通过 `user.employee.employee_no` 属性读取，无需改 User 模型。
- **飞书 OAuth2 requires 外部配置（硬性阻塞）：** `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_REDIRECT_URI` 必须在 `.env` 中配置；`FEISHU_REDIRECT_URI` 必须与飞书后台安全设置完全一致（含协议、域名、路径）。缺失则整条链路无法工作。
- **QR SDK 与现有 FeishuService 完全分离：** 现有 `FeishuService` 管理 `tenant_access_token`（机器人权限），OAuth2 用户登录走 `user_access_token`（用户权限）。两个 token 体系不同，不共用服务类，需新建 `FeishuAuthService` 或在 `auth.py` 内联实现。
- **前端 QR SDK 加载方式：** 官方 SDK 通过 `<script>` 标签引入，暴露全局 `window.QRLogin`。在 React+TypeScript 项目中需在 `public/index.html` 中加 CDN script，在 TypeScript 组件中声明 `declare global { interface Window { QRLogin: ... } }`。

---

## MVP Definition

### Launch With (v1.3 — 必须交付)

- [ ] 飞书 QR SDK 嵌入 — 右侧面板渲染扫码二维码，监听 `window.message` 授权结果
- [ ] 后端 OAuth callback 接口 — code 换 token、取用户信息、按 `employee_no` 匹配 User、签发 JWT
- [ ] 前端 OAuth 回调路由 `/auth/feishu/callback` — 解析 code/state，调用后端，成功跳转，失败显示分类中文错误
- [ ] 登录页双栏重设计 — 左侧账号密码，右侧飞书扫码
- [ ] Canvas 粒子动态背景 — 全屏背景层，原生 Canvas 实现
- [ ] CSRF state 参数校验 — `sessionStorage` 存储 + 回调验证

### Add After Validation (v1.x — 验证后补充)

- [ ] `feishu_open_id` 存储到 User 模型 — 首次飞书登录写入，加快后续识别（P2）
- [ ] 二维码自动刷新 timer — 3 分钟重新初始化 QR SDK（验证 SDK 是否内置后决定）

### Future Consideration (v2+)

- [ ] 飞书工作台免登（`tt.requestAccess`）— 需要应用正式上架工作台后才有价值；另立里程碑

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 飞书 QR SDK 扫码区域 | HIGH | MEDIUM | P1 |
| 后端 OAuth callback 接口 | HIGH | MEDIUM | P1 |
| 前端 OAuth 回调路由页 | HIGH | LOW | P1 |
| `employee_no` 自动匹配绑定 | HIGH | LOW（现有绑定体系已就绪）| P1 |
| CSRF state 校验 | HIGH | LOW | P1 |
| 登录失败分类错误提示 | MEDIUM | LOW | P1 |
| 登录页双栏重设计 | MEDIUM | LOW | P1 |
| Canvas 粒子背景 | MEDIUM | LOW | P1 |
| `feishu_open_id` 存储到 User | LOW | LOW | P2 |
| 二维码自动刷新 | LOW | LOW | P2 |
| 飞书工作台免登 | LOW | HIGH | P3 |

---

## Existing Code Impact Analysis

| 现有文件 | 操作 | 说明 |
|----------|------|------|
| `frontend/src/pages/Login.tsx` | **重写** | 整体布局改为双栏 + Canvas 粒子背景；左侧保留 `LoginForm`，右侧新增飞书扫码面板 |
| `frontend/src/components/auth/LoginForm.tsx` | **不改** | 现有邮箱密码表单完整复用，仅移入左侧面板 |
| `frontend/src/App.tsx` | **小改** | 注册 `/auth/feishu/callback` 路由（无需鉴权的 public 路由） |
| `backend/app/services/feishu_service.py` | **不改** | 现有服务仅处理 bitable/考勤同步，OAuth 用户登录是独立能力 |
| `backend/app/api/v1/auth.py`（或新文件） | **扩展** | 新增 `POST /api/v1/auth/feishu/callback` endpoint；可新建 `feishu_auth.py` 保持清晰 |
| `backend/app/models/user.py` | **可选小改** | 如存储 `feishu_open_id` 需加字段（P2 功能，v1.3 可跳过） |
| `frontend/src/services/authService.ts` | **扩展** | 新增 `feishuOAuthCallback(code: string, state: string)` 函数 |
| `public/index.html` | **小改** | 添加飞书 QR SDK CDN script tag |

---

## Sources

- [飞书开放平台 — 获取 OAuth 授权码](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code) — HIGH confidence
- [飞书开放平台 — 获取 user_access_token](https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token) — HIGH confidence
- [飞书扫码登录解决方案 + QR SDK](https://open.feishu.cn/solutions/detail/qrcode) — HIGH confidence
- [飞书 Web 应用 SSO 登录概览](https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/web-app-overview) — HIGH confidence
- 飞书 userinfo 接口返回 `employee_no` 字段（多篇独立文章印证）— HIGH confidence
- 扫码登录 vs 网页授权免登 vs JSSDK 三种模式区别整理 — MEDIUM confidence（社区文章）
- [通过飞书登录 Web 应用开发实战指南](https://open.feishu.cn/community/articles/7317091221654224898) — MEDIUM confidence
- [Enterprise SSO UI/UX Best Practices](https://www.scalekit.com/blog/ui-ux-considerations-for-streamlining-sso-in-b2b-applications) — MEDIUM confidence
- [Canvas Particle Background 实现参考](https://techhub.iodigital.com/articles/particle-background-effect-with-canvas) — MEDIUM confidence
- 项目现有代码核实（`Login.tsx`, `LoginForm.tsx`, `user.py`, `feishu_service.py`）— HIGH confidence

---
*Feature research for: 飞书 OAuth2 登录 + 登录页重设计 (v1.3 milestone)*
*Researched: 2026-04-16*
