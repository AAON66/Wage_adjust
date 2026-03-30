# Phase 10: External API Hardening - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

让外部 HR 系统通过安全、可靠、有文档的公开 API 拉取已审批的调薪建议。包括多 Key 管理（创建/轮换/撤销/过期）、游标分页、数据过滤（仅 approved）、OpenAPI 文档增强、Webhook 通知和审计日志。

</domain>

<decisions>
## Implementation Decisions

### API Key 管理模型
- **D-01:** 使用 DB 表存储 API Key（新建 `api_keys` 表），支持多 Key 并存、轮换、撤销、过期、last_used 记录
- **D-02:** Key 哈希存储（SHA-256），创建时仅显示一次明文，关闭后不可再查看
- **D-03:** 每个 Key 拥有全局读取权限，可访问所有 `/api/v1/public/` 端点，不做端点级授权
- **D-04:** 按 Key 独立限流，每个 Key 有自己的 rate limit（默认 1000/小时），互不影响

### 游标分页设计
- **D-05:** 使用 Base64 编码不透明游标，内部结构为 `(sort_field, last_id)`，外部系统无法篡改
- **D-06:** 默认每页 20 条，最大 100 条/页

### 数据过滤策略
- **D-07:** 公开 API 仅返回 `recommendation.status == 'approved'` 的记录，草稿和审核中的记录不对外暴露
- **D-08:** 支持可选 query 参数筛选：`cycle_id`、`department`。不传则返回全部已审批记录

### OpenAPI 文档增强
- **D-09:** Schema 内联 example 字段 + 每个端点的 responses 文档（401/403/404/429 错误码）
- **D-10:** 前端新增独立「API 使用指南」页面，包含认证说明、分页教程、快速开始步骤

### Key 管理 UI
- **D-11:** Key 管理页面放在系统设置内的子页（与飞书配置等管理功能平级）
- **D-12:** Key 创建后弹窗一次性显示完整 Key，提示「关闭后无法再查看」，提供复制按钮

### Webhook 通知
- **D-13:** 同时支持 Pull 模式（外部系统定时拉取）和 Webhook 模式（审批通过时主动 POST 到注册 URL）
- **D-14:** Webhook 需要基础能力：URL 注册、签名验证、重试机制、发送日志

### 审计日志
- **D-15:** 公开 API 访问全量记录：Key ID、Key 名称、请求 IP、请求路径、响应状态码、耗时、时间戳。复用现有 audit_log 表

### Claude's Discretion
- Webhook 签名算法选择（HMAC-SHA256 等）
- Webhook 重试策略（次数、间隔）
- API 使用指南页面的具体布局和样式
- 游标内部编码的具体字段组合

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 现有公开 API 实现
- `backend/app/api/v1/public.py` — 当前 4 个公开端点实现，需要改造
- `backend/app/schemas/public.py` — 公开 API 的 Pydantic Schema
- `backend/app/services/integration_service.py` — 公开 API 业务逻辑层
- `backend/app/dependencies.py` — `get_public_api_key` 依赖（当前单一静态 Key）

### 安全与限流
- `backend/app/core/config.py` — `public_api_key` 和 `public_api_rate_limit` 配置
- `backend/app/core/rate_limit.py` — slowapi limiter 配置
- `.planning/phases/01-security-hardening-and-schema-integrity/01-CONTEXT.md` — Phase 1 安全决策（D-04~D-07 速率限制）

### 数据模型
- `backend/app/models/` — 现有 ORM 模型目录
- `backend/app/models/mixins.py` — UUID PK + timestamp mixins

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `require_public_api_key` 依赖 — 需要替换为多 Key 版本
- `slowapi` limiter — 已集成，需要扩展为按 Key 限流
- `IntegrationService` — 现有公开 API 业务层，需要扩展
- `audit_log` 表 — 现有审计日志表可复用
- 前端飞书配置页面模式 — Key 管理 UI 可参考 FeishuConfig.tsx 的表单模式

### Established Patterns
- API 路由：`backend/app/api/v1/` 下按域名一个文件
- 服务层：`backend/app/services/` 下按域名一个类
- 前端服务层：`frontend/src/services/` 下按域名一个文件
- Schema 设计：Request/Response/Read 三类

### Integration Points
- `backend/app/api/v1/router.py` — 注册新路由
- `frontend/src/App.tsx` — 注册新前端路由
- `frontend/src/utils/roleAccess.ts` — 配置角色权限
- `backend/app/main.py` — 生命周期钩子（Webhook 后台任务）

</code_context>

<specifics>
## Specific Ideas

- 无外部系统已对接，按通用 RESTful 标准设计
- Webhook 和 Pull 两种模式都需要支持，给对接方灵活选择

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-external-api-hardening*
*Context gathered: 2026-03-30*
