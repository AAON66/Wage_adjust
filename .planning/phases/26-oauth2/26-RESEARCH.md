# Phase 26: 飞书 OAuth2 后端接入 - Research

**Researched:** 2026-04-16
**Domain:** OAuth2 授权码登录 / 飞书开放平台 API / 用户身份绑定
**Confidence:** HIGH

## Summary

本阶段需要在后端实现完整的飞书 OAuth2 授权码登录流程。核心链路为：生成授权 URL（含 state CSRF token）-> 接收回调授权码 -> 调用飞书 API 换取 user_access_token -> 获取用户信息（open_id + employee_no）-> 匹配系统 Employee -> 绑定 User -> 签发 JWT。

项目已有完善的飞书 API 集成基础设施（`FeishuService`、httpx 客户端、rate limiter、employee_no 容差匹配），以及成熟的 JWT 签发和身份绑定模式。本阶段的核心工作是新增 OAuth 相关端点、User 模型 feishu_open_id 字段（含 Alembic 迁移），以及一个封装 OAuth 流程的服务层。飞书 OAuth API 文档清晰，v2 token 端点稳定，无重大技术风险。

**Primary recommendation:** 新建独立的 `FeishuOAuthService` 服务类处理 OAuth 流程，复用 `FeishuService` 的 httpx 客户端和 employee_no 匹配逻辑，在 `auth.py` 路由文件中新增两个飞书端点。

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 新增 `POST /api/v1/auth/feishu/callback` 端点接收授权码，后端完成 code->token->userinfo 全流程
- **D-02:** state 参数使用 `secrets.token_urlsafe(32)` 生成，存入 Redis（TTL 5 分钟），回调时校验后立即删除（一次性使用）
- **D-03:** authorization code 一次性使用：通过飞书 API 自身保证（同一 code 二次请求返回错误），后端记录已使用的 code 到 Redis（TTL 10 分钟）防重放
- **D-04:** 新增 `GET /api/v1/auth/feishu/authorize` 端点返回飞书授权 URL（含 state），前端重定向或用于 QR SDK 初始化
- **D-05:** 飞书登录后通过 user_access_token 调用飞书 API 获取 employee_no，复用 FeishuService 已有的 leading-zero 容差匹配逻辑
- **D-06:** 匹配成功后：若 User 不存在则查找对应 Employee，找到已绑定的 User 直接使用；若无 User 则返回错误（不自动创建）
- **D-07:** User 模型新增 `feishu_open_id: Mapped[str | None]`（唯一约束），通过 Alembic 迁移添加
- **D-08:** 已绑定 feishu_open_id 的用户后续登录：先查 feishu_open_id -> 直接识别，跳过 employee_no 匹配
- **D-09:** 匹配失败时返回 HTTP 400 + 中文错误提示"工号未匹配，请联系管理员开通"
- **D-10:** OAuth 配置通过 .env 管理：新增 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_REDIRECT_URI` 到 Settings（pydantic-settings）
- **D-11:** 复用现有 `feishu_encryption_key` 加密 app_secret 存储（与 FeishuConfig 模式一致）
- **D-12:** OAuth 回调端点不需要 JWT 认证（公开端点），但有 state CSRF 校验保护
- **D-13:** 飞书 API 调用复用 FeishuService 的 httpx 客户端和 rate limiter

### Claude's Discretion
- OAuth service 的具体类设计（独立 FeishuOAuthService 或扩展 FeishuService）
- 飞书 API 调用的具体错误码映射
- Alembic 迁移脚本的具体实现细节
- 单元测试的 mock 策略和覆盖范围

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FAUTH-01 | 后端 OAuth callback 端点接收飞书授权码，换取 user_access_token 并获取用户信息 | 飞书 v2 token API + user_info API 完整规格已文档化 |
| FAUTH-02 | 飞书用户的 employee_no 与系统 Employee 记录自动匹配，匹配成功后绑定对应 User 账号并签发 JWT | 复用 FeishuService._build_employee_map() 和 _lookup_employee() 方法 |
| FAUTH-03 | OAuth 回调包含 state 参数 CSRF 校验，authorization code 一次性使用防重放 | state 存 Redis TTL 5min + code 存 Redis TTL 10min |
| FAUTH-04 | User 模型新增 feishu_open_id 字段（唯一约束），已绑定用户后续登录直接识别无需重复匹配 | Alembic 迁移添加 nullable unique column |
| FAUTH-05 | 飞书登录找不到匹配员工时返回中文错误提示"工号未匹配，请联系管理员开通" | HTTP 400 + 中文 detail，与现有错误处理模式一致 |

</phase_requirements>

## Standard Stack

### Core（已有依赖，无需新增安装）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | 调用飞书 OAuth API（token exchange、user info） | 项目已用于所有飞书/DeepSeek API 调用 [VERIFIED: codebase] |
| redis | 7.4.0 | 存储 OAuth state 和已使用 code（防 CSRF + 防重放） | 项目已用于登录 rate limiting [VERIFIED: codebase] |
| python-jose | 3.3.0 | JWT 签发（access_token + refresh_token） | 项目认证基础设施 [VERIFIED: codebase] |
| SQLAlchemy | 2.0.36 | User 模型扩展 feishu_open_id 字段 | 项目 ORM 层 [VERIFIED: codebase] |
| Alembic | 1.14.0 | 数据库迁移：添加 feishu_open_id 列 | 项目唯一迁移工具 [VERIFIED: codebase] |
| pydantic-settings | 2.6.1 | 新增 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_REDIRECT_URI 配置 | 项目配置管理方式 [VERIFIED: codebase] |

**Installation:** 无需安装新依赖，所有所需库已在 `requirements.txt` 中。

## Architecture Patterns

### 推荐项目结构变更

```
backend/app/
├── api/v1/
│   └── auth.py              # 新增 feishu/authorize + feishu/callback 端点
├── core/
│   └── config.py            # 新增 3 个飞书 OAuth 配置项
├── models/
│   └── user.py              # 新增 feishu_open_id 字段
├── schemas/
│   └── user.py              # 新增 FeishuCallbackRequest schema
├── services/
│   └── feishu_oauth_service.py  # 新增 OAuth 流程服务（独立文件）
└── ...
alembic/versions/
    └── xxx_add_feishu_open_id.py  # 新增迁移脚本
```

### Pattern 1: 独立 FeishuOAuthService 服务类

**What:** 创建独立的 `FeishuOAuthService` 而非扩展现有 `FeishuService`
**When to use:** OAuth 流程与数据同步在职责、依赖和生命周期上完全不同
**Why:** 现有 `FeishuService` 已有 1000+ 行，聚焦于 bitable 数据同步。OAuth 是认证域的关注点，应独立于数据同步域。 [VERIFIED: codebase]

```python
# backend/app/services/feishu_oauth_service.py
class FeishuOAuthService:
    """飞书 OAuth2 授权码登录服务。"""

    FEISHU_AUTHORIZE_URL = 'https://accounts.feishu.cn/open-apis/authen/v1/authorize'
    FEISHU_TOKEN_URL = 'https://open.feishu.cn/open-apis/authen/v2/oauth/token'
    FEISHU_USER_INFO_URL = 'https://open.feishu.cn/open-apis/authen/v1/user_info'

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self._settings = settings or get_settings()

    def generate_authorize_url(self, redis_client: redis.Redis) -> str:
        """生成飞书授权 URL，state 存入 Redis（TTL 5 分钟）。"""
        ...

    def handle_callback(self, code: str, state: str, redis_client: redis.Redis) -> User:
        """处理 OAuth 回调：校验 state -> 换取 token -> 获取用户信息 -> 匹配/绑定 -> 返回 User。"""
        ...
```

### Pattern 2: Redis state 管理模式（复用现有 auth.py 的 Redis 模式）

**What:** 使用与登录 rate limiting 相同的 Redis 客户端获取模式
**When to use:** state CSRF 校验和 code 防重放

```python
# 复用现有模式：_get_redis_client(settings)
# state key: 'feishu_oauth_state:{state_value}' -> TTL 300s
# code key:  'feishu_oauth_code:{code_value}'  -> TTL 600s
```

### Pattern 3: 两阶段用户查找（fast path + slow path）

**What:** 已绑定用户走 feishu_open_id 快速路径，未绑定用户走 employee_no 匹配路径
**When to use:** FAUTH-04 要求的「已绑定直接识别」

```python
def _find_or_bind_user(self, open_id: str, employee_no: str) -> User:
    # Fast path: 已绑定 feishu_open_id 的用户
    user = self.db.scalar(select(User).where(User.feishu_open_id == open_id))
    if user is not None:
        return user

    # Slow path: employee_no -> Employee -> User，然后绑定 feishu_open_id
    emp_map = FeishuService._build_employee_map_static(self.db)  # 或内联实现
    employee_id = FeishuService._lookup_employee(emp_map, employee_no)
    if employee_id is None:
        raise HTTPException(status_code=400, detail='工号未匹配，请联系管理员开通')

    user = self.db.scalar(select(User).where(User.employee_id == employee_id))
    if user is None:
        raise HTTPException(status_code=400, detail='工号未匹配，请联系管理员开通')

    user.feishu_open_id = open_id
    self.db.flush()
    return user
```

### Anti-Patterns to Avoid
- **将 user_access_token 持久化存储：** 已明确列为 Out of Scope，用后即弃 [VERIFIED: REQUIREMENTS.md]
- **在 OAuth 回调中自动创建 User：** 已明确 Out of Scope，绕过 RBAC 产生无角色灰色状态 [VERIFIED: REQUIREMENTS.md]
- **在 FeishuService 中添加 OAuth 逻辑：** 违反单一职责，FeishuService 已 1000+ 行聚焦数据同步 [VERIFIED: codebase]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSRF state 生成 | 自定义随机字符串 | `secrets.token_urlsafe(32)` | 标准库，密码学安全随机 [VERIFIED: D-02] |
| state/code 临时存储 | 内存 dict 或数据库表 | Redis SET + TTL | 项目已有 Redis 基础设施，自动过期 [VERIFIED: codebase] |
| employee_no 容差匹配 | 新的匹配逻辑 | `FeishuService._build_employee_map()` + `_lookup_employee()` | 已有 leading-zero 处理逻辑 [VERIFIED: codebase] |
| JWT 签发 | 新的 token 生成 | `create_access_token()` + `create_refresh_token()` | 已有完整实现含 token_version [VERIFIED: codebase] |
| URL 编码 | 手动拼接 | `urllib.parse.urlencode` | 标准库，正确处理特殊字符 [ASSUMED] |

## Common Pitfalls

### Pitfall 1: Redis 不可用时 OAuth 完全失败
**What goes wrong:** 开发环境 Redis 未启动，state 校验和 code 防重放均失效
**Why it happens:** 现有 auth.py 的 `_get_redis_client` 在 Redis 不可用时返回 None 并跳过 rate limiting（graceful degradation）
**How to avoid:** OAuth 的 state 校验是安全关键路径，Redis 不可用时应直接返回 503 错误，而非静默跳过。与登录 rate limiting 的 graceful degradation 策略不同
**Warning signs:** 开发环境中 OAuth 登录"总是成功"但 state 参数被忽略

### Pitfall 2: employee_no 字段需要特定权限
**What goes wrong:** 飞书 user_info API 返回的 employee_no 为空
**Why it happens:** 获取 employee_no 需要飞书应用开启 `contact:user.employee_id:readonly` 或 `contact:user.employee:readonly` 权限 [CITED: open.feishu.cn/document/server-docs/authentication-management/login-state-management/get]
**How to avoid:** 在飞书开放平台应用配置中确认已开启对应权限；代码中对 employee_no 为空的情况返回明确错误提示
**Warning signs:** 测试账号 employee_no 返回 null

### Pitfall 3: 飞书 code 已由 API 保证一次性使用，额外防重放是 defense-in-depth
**What goes wrong:** 过度依赖飞书 API 的 code 一次性保证，在飞书 API 响应异常时未能拦截重放
**Why it happens:** 飞书 API 错误码 20003 表示 code 已使用，但网络超时等情况下后端可能未收到该错误
**How to avoid:** D-03 要求的 Redis code 记录（TTL 10 分钟）是正确的 defense-in-depth 策略
**Warning signs:** 极端情况下同一 code 被处理两次

### Pitfall 4: Alembic 迁移中 unique constraint 在有数据的表上
**What goes wrong:** 添加 unique constraint 的迁移在有大量数据时失败
**Why it happens:** nullable unique column 在 SQLite 中行为与 PostgreSQL 不同（SQLite 允许多个 NULL，PostgreSQL 也允许）
**How to avoid:** `feishu_open_id` 是 nullable，多个 NULL 值在 unique constraint 下不冲突（SQL 标准行为）。迁移脚本直接 `add_column` 即可
**Warning signs:** 无需特殊处理

### Pitfall 5: _build_employee_map 是实例方法而非静态方法
**What goes wrong:** 新的 FeishuOAuthService 无法直接调用 `FeishuService._build_employee_map()`
**Why it happens:** 该方法依赖 `self.db`（Session 实例）
**How to avoid:** 在 FeishuOAuthService 中内联实现相同逻辑（或提取为接受 db 参数的静态函数）。`_lookup_employee` 已经是 `@staticmethod`，可直接复用
**Warning signs:** 尝试从 FeishuService 复用方法时发现无法传递 Session

## Code Examples

### 飞书 OAuth2 Token Exchange

```python
# Source: https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token
# [CITED: open.feishu.cn]
def _exchange_code_for_token(self, code: str) -> dict:
    """用授权码换取 user_access_token。"""
    resp = httpx.post(
        self.FEISHU_TOKEN_URL,
        json={
            'grant_type': 'authorization_code',
            'client_id': self._settings.feishu_app_id,
            'client_secret': self._settings.feishu_app_secret,
            'code': code,
            'redirect_uri': self._settings.feishu_redirect_uri,
        },
        timeout=10,
    )
    data = resp.json()
    if data.get('code') != 0:
        # 错误码映射
        error_code = data.get('code')
        if error_code == 20003:
            raise HTTPException(status_code=400, detail='授权码已使用或已过期')
        if error_code == 20004:
            raise HTTPException(status_code=400, detail='授权码已过期，请重新扫码')
        if error_code == 20002:
            raise HTTPException(status_code=500, detail='飞书应用凭证配置错误')
        raise HTTPException(status_code=502, detail=f'飞书授权失败: {data.get("error_description", "unknown")}')
    return data
```

### 飞书获取用户信息

```python
# Source: https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get
# [CITED: open.feishu.cn]
def _get_user_info(self, access_token: str) -> dict:
    """通过 user_access_token 获取用户信息（open_id, employee_no）。"""
    resp = httpx.get(
        self.FEISHU_USER_INFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    data = resp.json()
    if data.get('code') != 0:
        raise HTTPException(status_code=502, detail='获取飞书用户信息失败')
    return data.get('data', {})
```

### 授权 URL 生成

```python
# Source: https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code
# [CITED: open.feishu.cn]
def generate_authorize_url(self, redis_client: redis.Redis) -> dict:
    state = secrets.token_urlsafe(32)
    redis_client.setex(f'feishu_oauth_state:{state}', 300, '1')  # TTL 5 min

    params = {
        'client_id': self._settings.feishu_app_id,
        'response_type': 'code',
        'redirect_uri': self._settings.feishu_redirect_uri,
        'state': state,
    }
    url = f'{self.FEISHU_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}'
    return {'authorize_url': url, 'state': state}
```

### State CSRF 校验

```python
def _validate_state(self, state: str, redis_client: redis.Redis) -> None:
    key = f'feishu_oauth_state:{state}'
    if not redis_client.get(key):
        raise HTTPException(status_code=400, detail='无效的 state 参数，请重新发起授权')
    redis_client.delete(key)  # 一次性使用
```

### Alembic 迁移模板

```python
# alembic/versions/xxx_add_feishu_open_id_to_users.py
def upgrade() -> None:
    op.add_column('users', sa.Column('feishu_open_id', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_users_feishu_open_id', 'users', ['feishu_open_id'])
    op.create_index('ix_users_feishu_open_id', 'users', ['feishu_open_id'])

def downgrade() -> None:
    op.drop_index('ix_users_feishu_open_id', table_name='users')
    op.drop_constraint('uq_users_feishu_open_id', 'users', type_='unique')
    op.drop_column('users', 'feishu_open_id')
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 飞书 authen/v1/access_token | authen/v2/oauth/token | 2024 | v2 使用标准 OAuth2 参数命名（client_id 替代 app_id），更规范 |
| passport.feishu.cn 授权页 | accounts.feishu.cn 授权页 | 2024 | 授权 URL 域名更新 |

**Deprecated/outdated:**
- `POST /open-apis/authen/v1/access_token`：旧版 token 端点，参数命名非标准 OAuth2（使用 app_id 而非 client_id），v2 已取代 [CITED: open.feishu.cn]

## 飞书 API 关键规格

### 授权 URL

| Property | Value |
|----------|-------|
| URL | `https://accounts.feishu.cn/open-apis/authen/v1/authorize` |
| Method | GET |
| 必需参数 | `client_id`, `response_type=code`, `redirect_uri` |
| 可选参数 | `state`, `scope`, `prompt` |
| 回调格式 | `{redirect_uri}?code={code}&state={state}` |

[CITED: open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code]

### Token Exchange

| Property | Value |
|----------|-------|
| URL | `https://open.feishu.cn/open-apis/authen/v2/oauth/token` |
| Method | POST |
| Content-Type | `application/json; charset=utf-8` |
| 必需参数 | `grant_type=authorization_code`, `client_id`, `client_secret`, `code` |
| Rate Limit | 1000/min, 50/sec |

[CITED: open.feishu.cn/document/authentication-management/access-token/get-user-access-token]

### 关键错误码

| Code | 含义 | 后端处理 |
|------|------|----------|
| 20002 | client 凭证无效 | 500 - 飞书配置错误 |
| 20003 | code 已使用 | 400 - 授权码已使用 |
| 20004 | code 已过期 | 400 - 授权码已过期 |
| 20010 | 用户无应用权限 | 403 - 用户未获得应用授权 |

[CITED: open.feishu.cn/document/authentication-management/access-token/get-user-access-token]

### User Info API

| Property | Value |
|----------|-------|
| URL | `https://open.feishu.cn/open-apis/authen/v1/user_info` |
| Method | GET |
| Authorization | `Bearer {user_access_token}` |
| 返回字段 | `open_id`, `union_id`, `user_id`, `name`, `employee_no`, `email`, `mobile` |
| 所需权限 | `contact:user.employee_id:readonly`（获取 employee_no 必需） |

[CITED: open.feishu.cn/document/server-docs/authentication-management/login-state-management/get]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `urllib.parse.urlencode` 用于授权 URL 拼接 | Don't Hand-Roll | 低风险，标准库用法 |
| A2 | Redis SET + TTL 在高并发下无 race condition | Architecture Patterns | 低风险，Redis SET 是原子操作 |
| A3 | 飞书应用需要 contact:user.employee_id:readonly 权限才能获取 employee_no | Pitfall 2 | 中风险，若权限未配置则 employee_no 为空，登录流程中断 |

## Open Questions

1. **飞书 app_secret 存储方式**
   - What we know: D-11 要求复用 `feishu_encryption_key` 加密存储，与 FeishuConfig 模式一致
   - What's unclear: D-10 同时要求通过 .env 管理 `FEISHU_APP_SECRET`。两者是否冲突？
   - Recommendation: .env 中的 `FEISHU_APP_SECRET` 以明文形式存在于环境变量中，运行时从 Settings 直接读取。这与 FeishuConfig 在数据库中加密存储 app_secret 是不同的场景。OAuth 使用 .env 中的值即可，无需二次加密。D-11 可能指的是「如果未来将 OAuth 配置也存入数据库，则使用相同加密方式」。当前阶段直接从 Settings 读取明文即可。

2. **employee_no 匹配的 _build_employee_map 复用方式**
   - What we know: 该方法是 FeishuService 的实例方法，依赖 self.db
   - What's unclear: 是直接在 FeishuOAuthService 中重新实现，还是提取为共享函数？
   - Recommendation: 在 FeishuOAuthService 中内联实现一个简化版本（只需 employee_no -> Employee 查找），同时将 `_lookup_employee` 静态方法直接通过类引用调用。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Redis | state CSRF + code 防重放 | 需运行时检查 | -- | 无 fallback（安全关键路径） |
| Alembic | 数据库迁移 | Yes | 1.14.0 | -- |
| httpx | 飞书 API 调用 | Yes | 0.28.1 | -- |
| redis (Python) | Redis 客户端 | Yes | 7.4.0 | -- |

**Missing dependencies with no fallback:**
- Redis 服务需要在运行时可用。OAuth state 校验是安全关键路径，不可 graceful degrade。

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | 无独立配置文件，使用默认配置 |
| Quick run command | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py -x` |
| Full suite command | `python -m pytest backend/tests/ -x` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FAUTH-01 | code->token->userinfo 全流程 | unit (mock httpx) | `pytest backend/tests/test_services/test_feishu_oauth_service.py::test_handle_callback_success -x` | No - Wave 0 |
| FAUTH-02 | employee_no 匹配 + User 绑定 + JWT 签发 | unit | `pytest backend/tests/test_services/test_feishu_oauth_service.py::test_employee_match_and_bind -x` | No - Wave 0 |
| FAUTH-03 | state CSRF 校验 + code 防重放 | unit (mock Redis) | `pytest backend/tests/test_services/test_feishu_oauth_service.py::test_state_csrf_validation -x` | No - Wave 0 |
| FAUTH-04 | feishu_open_id 已绑定快速识别 | unit | `pytest backend/tests/test_services/test_feishu_oauth_service.py::test_bound_user_fast_path -x` | No - Wave 0 |
| FAUTH-05 | 匹配失败返回中文错误 | unit | `pytest backend/tests/test_services/test_feishu_oauth_service.py::test_unmatched_employee_error -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py -x`
- **Per wave merge:** `python -m pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_services/test_feishu_oauth_service.py` -- covers FAUTH-01 through FAUTH-05
- [ ] `backend/tests/test_api/test_feishu_auth_api.py` -- covers API 端点集成测试（可选）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | OAuth2 授权码流程 + JWT 签发（复用现有 security.py） |
| V3 Session Management | Yes | JWT access/refresh token 模式（复用现有实现） |
| V4 Access Control | No | OAuth 端点为公开端点，无 RBAC |
| V5 Input Validation | Yes | Pydantic schema 验证 code/state 参数 |
| V6 Cryptography | No | 无自定义加密（JWT 使用 HS256，已有实现） |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| CSRF via OAuth callback | Spoofing | state 参数存 Redis，回调时校验后删除 |
| Authorization code 重放 | Repudiation | 飞书 API 保证一次性 + Redis 记录已用 code |
| Open redirect via redirect_uri | Tampering | redirect_uri 在 .env 固定配置，不接受动态值 |
| Token theft via logging | Info Disclosure | user_access_token 用后即弃，不持久化不记录 |

## Sources

### Primary (HIGH confidence)
- [飞书 OAuth Token API](https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token) - v2 token 端点完整规格
- [飞书授权码获取](https://open.feishu.cn/document/authentication-management/access-token/obtain-oauth-code) - 授权 URL 格式和参数
- [飞书用户信息 API](https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/get) - user_info 端点和所需权限
- Codebase 直接验证 - security.py, auth.py, user.py, feishu_service.py, config.py, dependencies.py

### Secondary (MEDIUM confidence)
- [飞书 refresh token](https://open.feishu.cn/document/authentication-management/access-token/refresh-user-access-token) - 刷新机制（本阶段不使用）

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 全部已有依赖，无需新增
- Architecture: HIGH - 复用现有模式，飞书 API 文档清晰
- Pitfalls: HIGH - 基于官方文档和现有代码分析

**Research date:** 2026-04-16
**Valid until:** 2026-05-16（飞书 API 稳定，30 天有效）
