# Project Research Summary

**Project:** v1.3 - 飞书 OAuth2 登录与登录页重设计
**Domain:** 企业 SSO 登录集成 + 登录页视觉升级
**Researched:** 2026-04-16
**Confidence:** HIGH

## Executive Summary

v1.3 里程碑的核心目标是为企业调薪平台新增飞书扫码登录能力，并重设计登录页为左右分栏布局（左侧账号密码、右侧飞书扫码）+ Canvas 粒子动态背景。这是一个边界清晰、风险可控的增量功能——后端零新 Python 依赖（复用现有 `httpx`），前端仅新增两个 npm 包（`@tsparticles/react` + `@tsparticles/slim`），外加飞书 QR SDK CDN 脚本。飞书 OAuth2 的完整流程只涉及 2 个 HTTP 调用（code 换 token、token 取用户信息），技术复杂度低，但配置和安全细节是主要风险点。

推荐方案：新建独立的 `FeishuOAuthService`（与现有 bitable 同步的 `FeishuService` 完全分离），通过 `employee_no` 匹配系统内员工完成自动绑定，复用现有 JWT 基础设施（`create_access_token`、`token_version`）签发系统令牌。前端通过飞书 QR SDK 在登录页嵌入扫码区域，回调页面独立处理 OAuth code 交换后走与密码登录相同的 session 存储路径。Canvas 粒子背景作为纯视觉层，与 OAuth 逻辑完全解耦，可并行开发。

关键风险集中在三个方面：(1) 飞书开放平台配置（redirect URI 注册、权限申请、应用发布审批）是硬性前置阻塞，必须在写代码前完成；(2) OAuth 安全性（state CSRF 防护、code 一次性校验、飞书 token 不持久化）不可推迟实现；(3) 工号绑定冲突场景（员工未导入、已被其他账号绑定）必须返回明确的中文错误提示而非 500。

## Key Findings

### Recommended Stack

后端无需新增任何 Python 包。飞书 OAuth2 的两个 HTTP 调用由已有的 `httpx 0.28.1` 处理。前端新增粒子动画库用于登录页背景效果。

**Core technologies (new additions only):**
- `@tsparticles/react ^3.0.0`: React 18 粒子动画组件 -- TypeScript 原生，官方维护，40KB gzipped
- `@tsparticles/slim ^3.x`: 粒子引擎精简包 -- 只含 particles + links + mouse 交互，无多余预设
- Feishu QR SDK 1.0.3 (CDN): 扫码二维码渲染 -- `window.QRLogin` API，动态 script 加载

**明确不用:**
- `lark-oapi` Python SDK（6MB+ 仅为 2 个 HTTP 调用）
- `particles.js`（2018 年停更，无 TypeScript 支持）
- `python-social-auth` / `allauth`（Django 生态，不适配 FastAPI）

**新增配置项:** `feishu_oauth_app_id`、`feishu_oauth_app_secret`、`feishu_oauth_redirect_uri`（后端 `.env`）；`VITE_FEISHU_APP_ID`、`VITE_FEISHU_REDIRECT_URI`（前端 `.env`）

### Expected Features

**Must have (table stakes):**
- 飞书 QR SDK 扫码登录区域 -- 企业内部系统标配，员工期望不用记密码
- 后端 OAuth callback 接口（code 换 token、取用户信息、匹配绑定、签发 JWT）
- 前端 OAuth 回调路由 `/auth/feishu/callback`
- 按 `employee_no` 自动匹配绑定 -- 无需额外人工步骤
- CSRF state 参数校验 -- OAuth2 基础安全要求
- 登录页双栏重设计（左密码 + 右扫码）
- Canvas 粒子动态背景
- 登录失败分类错误提示（中文，区分未绑定/授权取消/网络错误）
- 现有邮箱/密码登录完整保留

**Should have (differentiators):**
- `feishu_open_id` 存储到 User 模型 -- 加速后续登录识别
- 二维码自动刷新（3 分钟 timer）
- 粒子背景鼠标跟随交互

**Defer (v2+):**
- 飞书工作台免登（`tt.requestAccess`）-- 需要应用上架工作台，独立里程碑

**Anti-features (明确不做):**
- 首次飞书登录自动创建系统账号 -- 绕过 RBAC，产生无角色灰色状态
- 扫码/密码 Tab 切换 -- QR SDK 容器销毁重建会闪烁，行业标准为并列
- 持久化存储飞书 `user_access_token` -- 不必要的安全风险

### Architecture Approach

架构遵循现有分层模式（router -> service -> model），新增独立的 `FeishuOAuthService` 处理 OAuth 登录，与现有 `FeishuService`（bitable 同步）完全分离。两种登录模式（扫码 + 网页授权）共用同一后端 callback 端点。前端 `FeishuOAuthCallback` 作为独立页面路由处理回调，不修改 `useAuth` context，而是直接调用已有的 `storeAuthSession` + `AUTH_SESSION_EVENT` 完成 session 写入。

**Major components:**
1. `FeishuOAuthService` (backend) -- code 换 token、获取用户信息、employee_no 匹配绑定、JWT 签发
2. `feishu_auth.py` router (backend) -- `POST /auth/feishu/callback` + `GET /auth/feishu/web-url`
3. `FeishuQRPanel.tsx` (frontend) -- 动态加载 QR SDK、渲染二维码、监听 postMessage
4. `FeishuOAuthCallback.tsx` (frontend) -- 独立路由页，解析 code/state、调用后端、存储 JWT、角色跳转
5. `ParticleCanvas.tsx` (frontend) -- Canvas 粒子动画组件，自包含 rAF 循环 + cleanup

**Key patterns:**
- Client secret 永远不离开后端
- 飞书 `user_access_token` 用后即弃，不持久化
- 复用 `_build_auth_response` 生成 JWT（包含 `token_version`）
- 回调页不使用 `useAuth.login()`，走 `storeAuthSession` + event 模式

### Critical Pitfalls

1. **飞书 OAuth code 重复使用竞态** -- 用 Redis `SET NX EX 300` 原子标记 code 已使用，前端回调页立即禁用重复提交
2. **state CSRF 防护缺失** -- 前端生成随机 state 存 sessionStorage，回调时比对后立即删除；不可推迟实现
3. **工号绑定冲突场景未覆盖** -- 穷举所有场景（员工不存在、已被他人绑定、重复登录），返回明确中文错误
4. **飞书 QR SDK iframe 被 CSP 拦截** -- 生产 Nginx CSP 需添加 `frame-src https://open.feishu.cn`，或优先用重定向方式
5. **token_version 与飞书登录路径不兼容** -- 必须复用 `_build_auth_response`，飞书解绑时必须递增 token_version
6. **Canvas rAF 僵尸循环** -- 用 `useRef` 存 rAF ID，`useEffect` cleanup 调用 `cancelAnimationFrame`
7. **飞书应用配置缺失静默失败** -- 完整配置 checklist 必须在写代码前全部完成（redirect URI、权限、版本发布）

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: 飞书开放平台前置配置
**Rationale:** P7（飞书配置缺失）是硬性 blocker，平台未配置则无法联调任何代码。这是外部依赖，需人工操作，必须最先完成。
**Delivers:** 飞书应用 App ID/Secret、redirect URI 注册、权限申请、版本发布审批
**Addresses:** 外部依赖解除阻塞
**Avoids:** P7 飞书应用配置缺失静默失败
**Needs research:** NO -- 纯操作性任务，按 checklist 执行

### Phase 2: 飞书 OAuth2 后端接入
**Rationale:** 后端接口是前端所有飞书功能的依赖，且安全性 pitfalls (P1/P2/P3/P5) 必须在此阶段同步解决，不可后补。可用 curl 独立测试，不依赖前端。
**Delivers:** `FeishuOAuthService` + `POST /auth/feishu/callback` + `GET /auth/feishu/web-url` + config 新增 + Alembic migration（feishu_open_id）
**Addresses:** 飞书 QR SDK 扫码登录、OAuth callback、employee_no 匹配绑定、CSRF state 校验、JWT 签发
**Avoids:** P1 code 重复使用、P2 CSRF 劫持、P3 绑定冲突、P5 token_version 不兼容、P11 飞书 token 持久化
**Needs research:** NO -- 飞书 API 已完整文档化，代码模式已明确

### Phase 3: 飞书 OAuth2 前端集成
**Rationale:** 依赖 Phase 2 后端接口稳定。包含 QR SDK 嵌入、回调路由、前端 service 层。
**Delivers:** `FeishuQRPanel.tsx` + `FeishuOAuthCallback.tsx` + `feishuAuthService.ts` + `App.tsx` 路由注册
**Addresses:** 飞书扫码区域、前端 OAuth 回调、登录失败分类错误提示
**Avoids:** P4 CSP 阻断 iframe、P8 两种 OAuth 回调差异、P12 破坏 AuthContext
**Needs research:** NO -- QR SDK API 已验证，前端模式已明确

### Phase 4: 登录页粒子背景
**Rationale:** 纯视觉组件，与 OAuth 逻辑完全解耦。可与 Phase 3 并行开发，但建议排在后面以避免分散注意力。
**Delivers:** `ParticleCanvas.tsx` -- 全屏 Canvas 粒子背景 + HiDPI 适配 + 性能分级 + prefers-reduced-motion 响应
**Addresses:** Canvas 粒子动态背景、鼠标跟随交互
**Avoids:** P6 rAF 僵尸循环、P9 HiDPI 模糊、P10 无障碍、P13 低端设备性能
**Needs research:** NO -- Canvas 动画是成熟模式

### Phase 5: 登录页重设计整合
**Rationale:** 最后将所有新组件（FeishuQRPanel + ParticleCanvas + 现有 LoginForm）整合到统一的双栏布局。此阶段改动面最广但风险最低（纯布局）。
**Delivers:** 重写 `Login.tsx` -- 左侧密码登录 + 右侧飞书扫码 + 粒子背景层
**Addresses:** 登录页双栏重设计、保持现有密码登录不变
**Avoids:** P12 破坏 AuthContext（两种登录路径一致性验证）

### Phase Ordering Rationale

- **配置先于代码:** 飞书平台配置是外部阻塞，无法通过代码解决，必须最先完成
- **后端先于前端:** 后端 API 可独立测试（curl），前端依赖后端接口，先稳定后端减少联调成本
- **安全与功能同步:** OAuth 安全机制（state、code 一次性、token_version）不可作为"后续优化"推迟
- **视觉与逻辑分离:** Canvas 粒子背景与 OAuth 无耦合，可并行但建议串行以保持专注
- **整合放最后:** 登录页布局重写依赖所有子组件就绪，放在最后降低返工风险

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (飞书配置):** 需确认飞书应用类型（企业自建 vs 商店）、权限审批周期、redirect URI 是否支持 localhost

Phases with standard patterns (skip research-phase):
- **Phase 2 (后端 OAuth):** 飞书 API 完整文档化，代码模式在研究中已给出伪代码
- **Phase 3 (前端集成):** QR SDK API 已验证，TypeScript 声明模式已明确
- **Phase 4 (粒子背景):** Canvas + rAF + React useEffect 是成熟模式
- **Phase 5 (页面整合):** 纯布局工作，无技术风险

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 零新后端依赖；前端包已确认版本兼容；飞书 QR SDK CDN URL 需生产前再次验证 |
| Features | HIGH | 飞书官方文档 + 现有代码库直接审计；feature 边界清晰 |
| Architecture | HIGH | 完全基于现有代码结构推导；所有集成点已标注文件路径和函数名 |
| Pitfalls | HIGH | 基于飞书文档 + OAuth2 RFC + 社区 issue + 代码审计；13 个 pitfall 均有具体预防方案 |

**Overall confidence:** HIGH

### Gaps to Address

- **QR SDK CDN URL 稳定性:** 1.0.3 版本 URL 来自社区文章，需在飞书官方文档确认最新 CDN 地址
- **飞书应用审批周期:** 版本发布后企业管理员审批时长不确定（通常 1 个工作日），可能阻塞 Phase 1
- **STACK vs FEATURES 分歧 -- 粒子实现方式:** STACK.md 推荐 `@tsparticles/slim`，FEATURES.md 推荐原生 Canvas（零依赖）。**建议采用 tsParticles:** JSON 配置式调参优于手写动画循环，40KB gzipped 对登录页可接受，且 STACK 研究的论证更充分
- **`feishu_open_id` 优先级:** FEATURES.md 列为 P2（可跳过），ARCHITECTURE.md 建议可选 migration，PITFALLS.md 要求唯一约束。**建议 v1.3 就实现:** 低成本（一个字段 + 一次 migration），高收益（重复登录加速 + 唯一约束防并发绑定）

## Sources

### Primary (HIGH confidence)
- [飞书 OAuth2 授权码获取](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code)
- [飞书 user_access_token 获取](https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token)
- [飞书用户信息接口](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get)
- [飞书 QR SDK 文档](https://open.feishu.cn/document/common-capabilities/sso/web-application-sso/qr-sdk-documentation)
- [OAuth2 RFC 6749 Section 10.12 (state CSRF)](https://www.rfc-editor.org/rfc/rfc6749#section-10.12)
- [@tsparticles/react npm](https://www.npmjs.com/package/@tsparticles/react)
- [MDN Canvas Optimization](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)
- 项目代码直接审计: `auth.py`, `feishu_service.py`, `user.py`, `Login.tsx`, `useAuth.tsx`

### Secondary (MEDIUM confidence)
- [飞书扫码登录避坑指南 (CSDN)](https://blog.csdn.net/weixin_28049429/article/details/158673318)
- [Enterprise SSO UI/UX Best Practices](https://www.scalekit.com/blog/ui-ux-considerations-for-streamlining-sso-in-b2b-applications)
- [Canvas Particle Background 实现参考](https://techhub.iodigital.com/articles/particle-background-effect-with-canvas)
- QR SDK CDN URL 1.0.3 (社区文章来源，需官方确认)

---
*Research completed: 2026-04-16*
*Ready for roadmap: yes*
