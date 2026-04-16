# Phase 26: 飞书 OAuth2 后端接入 - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

后端完整支持飞书授权码登录流程：接收飞书授权码 → 换取 user_access_token → 获取用户信息 → 匹配员工 → 绑定/识别用户 → 签发 JWT。不涉及前端 UI 改动（Phase 27 负责）。

</domain>

<decisions>
## Implementation Decisions

### OAuth 流程设计
- **D-01:** 新增 `POST /api/v1/auth/feishu/callback` 端点接收授权码，后端完成 code→token→userinfo 全流程
- **D-02:** state 参数使用 `secrets.token_urlsafe(32)` 生成，存入 Redis（TTL 5 分钟），回调时校验后立即删除（一次性使用）
- **D-03:** authorization code 一次性使用：通过飞书 API 自身保证（同一 code 二次请求返回错误），后端记录已使用的 code 到 Redis（TTL 10 分钟）防重放
- **D-04:** 新增 `GET /api/v1/auth/feishu/authorize` 端点返回飞书授权 URL（含 state），前端重定向或用于 QR SDK 初始化

### 用户匹配绑定
- **D-05:** 飞书登录后通过 user_access_token 调用飞书 API 获取 employee_no，复用 FeishuService 已有的 leading-zero 容差匹配逻辑
- **D-06:** 匹配成功后：若 User 不存在则查找对应 Employee，找到已绑定的 User 直接使用；若无 User 则返回错误（不自动创建）
- **D-07:** User 模型新增 `feishu_open_id: Mapped[str | None]`（唯一约束），通过 Alembic 迁移添加
- **D-08:** 已绑定 feishu_open_id 的用户后续登录：先查 feishu_open_id → 直接识别，跳过 employee_no 匹配
- **D-09:** 匹配失败时返回 HTTP 400 + 中文错误提示"工号未匹配，请联系管理员开通"

### 配置与安全
- **D-10:** OAuth 配置通过 .env 管理：新增 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_REDIRECT_URI` 到 Settings（pydantic-settings）
- **D-11:** 复用现有 `feishu_encryption_key` 加密 app_secret 存储（与 FeishuConfig 模式一致）
- **D-12:** OAuth 回调端点不需要 JWT 认证（公开端点），但有 state CSRF 校验保护
- **D-13:** 飞书 API 调用复用 FeishuService 的 httpx 客户端和 rate limiter

### Claude's Discretion
- OAuth service 的具体类设计（独立 FeishuOAuthService 或扩展 FeishuService）
- 飞书 API 调用的具体错误码映射
- Alembic 迁移脚本的具体实现细节
- 单元测试的 mock 策略和覆盖范围

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 认证系统
- `backend/app/core/security.py` — JWT 创建/验证逻辑，HS256 算法，token_version 校验
- `backend/app/api/v1/auth.py` — 现有登录/注册/刷新端点，rate limiting 模式
- `backend/app/models/user.py` — User 模型字段定义，employee_id 外键关系

### 飞书集成
- `backend/app/services/feishu_service.py` — 现有飞书 API 集成，tenant_access_token 管理，employee_no 匹配逻辑（leading-zero 容差）
- `backend/app/core/config.py` — Settings 类，已有 feishu_encryption_key 等配置

### 身份绑定
- `backend/app/services/identity_binding_service.py` — 用户-员工绑定模式参考

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FeishuService.get_tenant_access_token()`: 已有飞书 API 认证逻辑，可复用 httpx 客户端
- `FeishuService._match_employee_no()`: 已有 employee_no leading-zero 容差匹配
- `create_access_token()` / `create_refresh_token()`: 现有 JWT 签发函数直接复用
- `IdentityBindingService`: 用户-员工绑定模式参考（但 OAuth 绑定逻辑更简单）

### Established Patterns
- 所有 Settings 通过 pydantic-settings 从 .env 加载，`get_settings()` LRU 缓存
- 服务层通过构造函数注入 Session 和依赖（testability）
- 错误处理统一使用 `build_error_response()` 格式

### Integration Points
- `backend/app/api/v1/auth.py`: 新增飞书 OAuth 端点与现有认证端点并列
- `backend/app/models/user.py`: 新增 feishu_open_id 字段
- `backend/app/main.py`: 路由已通过 `include_router` 统一注册

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-oauth2*
*Context gathered: 2026-04-16*
