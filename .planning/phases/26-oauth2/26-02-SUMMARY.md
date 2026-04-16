---
phase: 26-oauth2
plan: "02"
subsystem: auth
tags: [feishu, oauth2, jwt, redis, csrf]
dependency_graph:
  requires: [26-01]
  provides: [feishu-oauth-service, feishu-oauth-endpoints]
  affects: [backend/app/api/v1/auth.py]
tech_stack:
  added: []
  patterns: [TDD, service-layer, dependency-injection]
key_files:
  created:
    - backend/app/services/feishu_oauth_service.py
    - backend/tests/test_services/test_feishu_oauth_service.py
    - backend/tests/test_api/test_feishu_oauth_integration.py
  modified:
    - backend/app/api/v1/auth.py
decisions:
  - "callback endpoint returns AuthResponse (user + tokens) instead of bare TokenPair for consistency with existing login endpoint"
  - "integration test uses StaticPool for thread-safe in-memory SQLite with TestClient"
metrics:
  duration: "1010s"
  completed: "2026-04-16"
  tasks_completed: 2
  files_changed: 4
---

# Phase 26 Plan 02: 飞书 OAuth 服务层与 API 端点 Summary

飞书 OAuth2 授权码登录完整实现：FeishuOAuthService 处理 code→token→userinfo→match→bind→JWT 全流程，两个公开 API 端点，14 个单元+集成测试全部通过。

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 (RED) | 编写 10 个 FeishuOAuthService 单元测试（TDD RED） | 3e1b561 |
| 1 (GREEN) | 实现 FeishuOAuthService 完整服务类 | 244e16c |
| 2 | 注册 GET /feishu/authorize 和 POST /feishu/callback 端点 | 38801d5 |
| 3 | 添加 4 个端到端集成测试 | 53a62f0 |

## What Was Built

### FeishuOAuthService (`backend/app/services/feishu_oauth_service.py`)

- `generate_authorize_url(redis_client)` — 生成 CSRF state（`secrets.token_urlsafe(32)`），存入 Redis TTL 300s，返回飞书授权 URL
- `handle_callback(code, state, redis_client)` — 完整回调处理：state 校验 → code 防重放 → token 换取 → 用户信息获取 → 用户匹配绑定
- `require_redis()` — Redis 不可用时返回 503（区别于登录限流的 graceful degradation）
- `_validate_state()` — 校验并立即删除 state（一次性使用）
- `_check_code_replay()` — 检查 code 是否已使用（Redis TTL 600s）
- `_exchange_code_for_token()` — 飞书 token API 调用，错误码映射（20002/20003/20004/20010）
- `_get_user_info()` — 获取 open_id 和 employee_no
- `_find_or_bind_user()` — Fast path（feishu_open_id 直查）+ Slow path（employee_no 匹配 + 绑定）

### API 端点 (`backend/app/api/v1/auth.py`)

- `GET /api/v1/auth/feishu/authorize` — 无需 JWT，返回 `{authorize_url, state}`
- `POST /api/v1/auth/feishu/callback` — 无需 JWT，接收 `{code, state}`，返回 `AuthResponse`（user + tokens）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] load_model_modules() 调用**
- **Found during:** Task 1 GREEN 测试运行
- **Issue:** SQLAlchemy 关系解析失败（`EmployeeHandbook` 未注册），因为测试文件未导入所有模型
- **Fix:** 在测试文件顶层调用 `load_model_modules()`
- **Files modified:** `backend/tests/test_services/test_feishu_oauth_service.py`

**2. [Rule 1 - Bug] Redis 不可用测试需要真实不可达端口**
- **Found during:** Task 1 GREEN 测试运行
- **Issue:** 本地 Redis 实际运行，`require_redis()` 不抛出异常
- **Fix:** 测试使用端口 19999（保证不可达）的 Settings 实例
- **Files modified:** `backend/tests/test_services/test_feishu_oauth_service.py`

**3. [Rule 1 - Bug] 集成测试 SQLite 线程问题**
- **Found during:** Task 3 集成测试
- **Issue:** TestClient 在独立线程运行，`sqlite://` 内存 DB 不跨线程共享
- **Fix:** 使用 `StaticPool` 确保所有线程共享同一连接
- **Files modified:** `backend/tests/test_api/test_feishu_oauth_integration.py`

**4. [Rule 1 - Bug] callback 端点返回 AuthResponse 而非 TokenPair**
- **Found during:** Task 2 实现
- **Issue:** 计划要求返回 TokenPair，但现有 login 端点返回 AuthResponse（含 user 信息），集成测试也验证了 user 字段
- **Fix:** 返回 `AuthResponse`（与 `/auth/register` 一致），前端可直接获取用户信息
- **Commit:** 38801d5

## Known Stubs

无。所有功能均已完整实现。

## Threat Flags

所有威胁均已按 threat_model 中的 mitigate 处置实现：

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-26-03 CSRF | state Redis TTL 300s + 一次性删除 | ✓ 已实现 |
| T-26-04 Code Replay | code Redis TTL 600s 防重放 | ✓ 已实现 |
| T-26-05 redirect_uri | 从 .env 固定配置，不接受请求参数 | ✓ 已实现 |
| T-26-06 user_access_token | 仅在方法内使用，不持久化不记录日志 | ✓ 已实现 |
| T-26-08 Privilege Escalation | 不自动创建 User，只绑定已存在账号 | ✓ 已实现 |
| T-26-09 Redis 不可用 | require_redis() 返回 503 | ✓ 已实现 |

## Self-Check: PASSED

| Item | Status |
|------|--------|
| backend/app/services/feishu_oauth_service.py | FOUND |
| backend/tests/test_services/test_feishu_oauth_service.py | FOUND |
| backend/tests/test_api/test_feishu_oauth_integration.py | FOUND |
| commit 3e1b561 (RED tests) | FOUND |
| commit 244e16c (GREEN implementation) | FOUND |
| commit 38801d5 (API endpoints) | FOUND |
| commit 53a62f0 (integration tests) | FOUND |
