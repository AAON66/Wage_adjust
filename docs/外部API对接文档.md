# Wage Adjust Platform 外部 API 对接文档

本文档基于当前仓库代码整理，适用于外部系统、数据平台、HR 系统或中台服务对接本项目的公共接口能力。

更新时间：2026-04-01

## 1. 对接概览

当前项目对外集成采用两类能力：

- 公共只读 API：供外部系统主动拉取评估、调薪、审批和看板汇总数据
- Webhook 管理能力：用于登记回调地址和查看投递日志

从当前代码状态看，真正已经面向外部系统开放并可直接消费的是公共只读 API，统一前缀为：

```text
/api/v1/public
```

Webhook 相关接口也已经存在，但更偏平台管理能力，且当前业务事件投递链路尚未完全接通，详见本文末尾说明。

## 2. 基础信息

### 2.1 环境地址

本地开发默认地址：

- 后端根地址：`http://127.0.0.1:8011`
- API 前缀：`http://127.0.0.1:8011/api/v1`
- 公共 API 前缀：`http://127.0.0.1:8011/api/v1/public`

生产环境请替换为实际域名，例如：

```text
https://your-domain.example.com/api/v1/public
```

### 2.2 数据格式

- 协议：HTTPS / HTTP
- 风格：RESTful
- 请求体：JSON
- 返回体：JSON
- 时间字段：ISO 8601 时间字符串
- 金额字段：部分以字符串返回，避免精度问题

### 2.3 鉴权方式

公共 API 使用请求头 `X-API-Key` 鉴权：

```http
X-API-Key: <your-api-key>
```

说明：

- API Key 由平台管理员创建
- Key 支持失效时间、启用状态、使用记录和轮换
- Key 明文只会在创建或轮换时返回一次，之后无法再次查看

## 3. 接入流程建议

1. 由平台管理员在系统后台或管理接口中创建 API Key。
2. 调用方将 `X-API-Key` 写入所有公共 API 请求头。
3. 根据业务场景选择员工维度、周期维度或汇总维度接口拉取数据。
4. 如需批量同步周期结果，优先使用游标分页接口循环拉取。
5. 接入侧保存最近一次成功同步时间与游标，便于断点续拉。

## 4. 公共 API 清单

当前公共接口共有 4 个：

1. 获取员工最新评估结果
2. 获取某评估周期已审批调薪结果
3. 获取某评估周期审批状态
4. 获取组织看板汇总

## 5. 公共 API 详细说明

### 5.1 获取员工最新评估结果

用于按员工工号拉取该员工最近一条带 AI 评估结果的提交记录。

#### 请求

```http
GET /api/v1/public/employees/{employee_no}/latest-evaluation
```

#### 路径参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `employee_no` | string | 是 | 员工工号 |

#### 请求头

```http
X-API-Key: <your-api-key>
```

#### curl 示例

```bash
curl -X GET \
  'http://127.0.0.1:8011/api/v1/public/employees/EMP-CN-101/latest-evaluation' \
  -H 'X-API-Key: your-api-key'
```

#### 响应示例

```json
{
  "employee_id": "emp_123",
  "employee_no": "EMP-CN-101",
  "employee_name": "陈曦",
  "department": "研发中心",
  "job_family": "平台研发",
  "job_level": "P6",
  "cycle_id": "cycle_001",
  "cycle_name": "2026 年春季调薪评估",
  "cycle_status": "published",
  "submission_id": "sub_001",
  "evaluation_id": "eval_001",
  "evaluation_status": "confirmed",
  "ai_level": "Level 5",
  "overall_score": 91,
  "confidence_score": 0.93,
  "explanation": "员工在 AI 工具使用深度、业务落地和团队分享方面表现突出。",
  "evaluated_at": "2026-03-25T09:30:00Z",
  "dimension_scores": [
    {
      "dimension_code": "TOOL",
      "display_score": 94,
      "raw_score": 94,
      "weighted_contribution": 23.5,
      "weighted_score": 23.5,
      "rationale": "熟练使用多类 AI 工具构建日常工作流。"
    }
  ],
  "salary_recommendation": {
    "recommendation_id": "rec_001",
    "status": "approved",
    "current_salary": "52000.00",
    "recommended_salary": "60320.00",
    "final_adjustment_ratio": 0.16
  }
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `employee_id` | string | 平台内员工 ID |
| `employee_no` | string | 员工工号 |
| `employee_name` | string | 员工姓名 |
| `department` | string | 所属部门 |
| `job_family` | string | 岗位族 |
| `job_level` | string | 岗位级别 |
| `cycle_id` | string | 评估周期 ID |
| `cycle_name` | string | 评估周期名称 |
| `cycle_status` | string | 周期状态 |
| `submission_id` | string | 员工提交记录 ID |
| `evaluation_id` | string | AI 评估记录 ID |
| `evaluation_status` | string | 评估状态 |
| `ai_level` | string | AI 等级，如 `Level 1` ~ `Level 5` |
| `overall_score` | number | 综合评分 |
| `confidence_score` | number | 置信度 |
| `explanation` | string | 评估说明 |
| `evaluated_at` | datetime | 评估更新时间 |
| `dimension_scores` | array | 五维评分明细 |
| `salary_recommendation` | object/null | 若已生成调薪建议则返回，否则为 `null` |

### 5.2 获取某周期已审批调薪结果

用于批量同步某个评估周期下已经审批通过的调薪结果。

#### 请求

```http
GET /api/v1/public/cycles/{cycle_id}/salary-results
```

#### 查询参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `cursor` | string | 否 | 无 | 分页游标 |
| `page_size` | integer | 否 | `20` | 每页条数，最大 `100` |
| `department` | string | 否 | 无 | 部门过滤 |

#### curl 示例

```bash
curl -X GET \
  'http://127.0.0.1:8011/api/v1/public/cycles/cycle_001/salary-results?page_size=20' \
  -H 'X-API-Key: your-api-key'
```

#### 响应示例

```json
{
  "cycle_id": "cycle_001",
  "cycle_name": "2026 年春季调薪评估",
  "cycle_status": "published",
  "items": [
    {
      "employee_id": "emp_123",
      "employee_no": "EMP-CN-101",
      "employee_name": "陈曦",
      "department": "研发中心",
      "job_family": "平台研发",
      "job_level": "P6",
      "evaluation_id": "eval_001",
      "ai_level": "Level 5",
      "evaluation_status": "confirmed",
      "recommendation_id": "rec_001",
      "recommendation_status": "approved",
      "current_salary": "52000.00",
      "recommended_salary": "60320.00",
      "final_adjustment_ratio": 0.16
    }
  ],
  "next_cursor": "eyJpZCI6InN1Yl8wMDEifQ==",
  "has_more": true,
  "total": 1
}
```

#### 分页说明

- 本接口采用游标分页，不使用传统 `page/page_size`
- 首次请求不传 `cursor`
- 若响应中 `has_more=true` 且 `next_cursor` 非空，则继续携带该值请求下一页
- `total` 当前表示“本页条数”，不表示全量总数

#### 适用场景

- 对接薪酬系统批量同步审批通过结果
- 对接数据平台做周期级分析
- 对接 BI 或离线数仓做增量抽取

### 5.3 获取某周期审批状态

用于查看某个周期下各员工调薪建议的审批进度，不返回完整调薪金额明细。

#### 请求

```http
GET /api/v1/public/cycles/{cycle_id}/approval-status
```

#### curl 示例

```bash
curl -X GET \
  'http://127.0.0.1:8011/api/v1/public/cycles/cycle_001/approval-status' \
  -H 'X-API-Key: your-api-key'
```

#### 响应示例

```json
{
  "cycle_id": "cycle_001",
  "cycle_name": "2026 年春季调薪评估",
  "cycle_status": "published",
  "items": [
    {
      "recommendation_id": "rec_001",
      "employee_no": "EMP-CN-101",
      "employee_name": "陈曦",
      "recommendation_status": "approved",
      "total_steps": 2,
      "approved_steps": 2,
      "pending_steps": 0,
      "rejected_steps": 0,
      "latest_decision_at": "2026-03-26T10:30:00Z"
    }
  ],
  "total": 1
}
```

#### 典型用途

- 外部审批系统做状态对账
- 管理后台展示审批进度
- 周期执行日报或同步校验

### 5.4 获取组织看板汇总

用于拉取平台级汇总指标，适合外部看板、中台分析或简单展示页。

#### 请求

```http
GET /api/v1/public/dashboard/summary
```

#### curl 示例

```bash
curl -X GET \
  'http://127.0.0.1:8011/api/v1/public/dashboard/summary' \
  -H 'X-API-Key: your-api-key'
```

#### 响应结构

```json
{
  "generated_at": "2026-04-01T08:00:00Z",
  "overview": [
    {
      "label": "纳入范围员工数",
      "value": "4",
      "note": "当前提交范围内去重后的员工总数。"
    }
  ],
  "ai_level_distribution": [
    { "label": "Level 1", "value": 0 },
    { "label": "Level 2", "value": 0 },
    { "label": "Level 3", "value": 1 },
    { "label": "Level 4", "value": 1 },
    { "label": "Level 5", "value": 2 }
  ],
  "roi_distribution": [
    { "label": "Under 1.0x", "value": 0 },
    { "label": "1.0x - 1.5x", "value": 1 },
    { "label": "1.5x - 2.0x", "value": 2 },
    { "label": "2.0x+", "value": 1 }
  ],
  "heatmap": [
    {
      "department": "研发中心",
      "level": "Level 5",
      "intensity": 91
    }
  ]
}
```

#### 说明

- `overview`：核心指标摘要
- `ai_level_distribution`：AI 等级分布
- `roi_distribution`：ROI 区间分布
- `heatmap`：部门热力数据

## 6. 公共 API 通用错误码

| HTTP 状态码 | 含义 | 说明 |
| --- | --- | --- |
| `401` | 未认证 | 缺少 `X-API-Key` 或 Key 无效/已吊销/已过期 |
| `404` | 资源不存在 | 如员工、周期或对应结果不存在 |
| `429` | 触发限流 | 请求频率超过限制 |
| `500` | 服务异常 | 服务端发生未预期错误 |

### 6.1 典型错误响应

缺少 API Key：

```json
{
  "detail": "X-API-Key header is required."
}
```

API Key 无效：

```json
{
  "detail": "Invalid, revoked, or expired API key."
}
```

资源不存在：

```json
{
  "detail": "Cycle not found."
}
```

## 7. 限流与审计

### 7.1 限流

公共 API 当前使用按 API Key 维度的限流策略。

默认实现特征：

- 默认限流值：`1000/hour`
- 识别维度：优先按 API Key，缺失时回退到 IP
- 开发环境下 Redis 不可用时会降级为内存限流
- 生产环境要求 Redis 可用

### 7.2 审计

每次公共 API 调用都会记录审计日志，包含：

- API Key ID
- API Key 名称
- 请求来源 IP
- 请求路径
- 响应耗时
- 目标资源标识

因此该项目适合接入对审计追踪有要求的内部系统。

## 8. 数据字段与建模约定

### 8.1 时间

所有时间字段建议按 UTC 处理，接入方在展示层再转换本地时区。

### 8.2 金额与比例

- 金额字段如 `current_salary`、`recommended_salary` 使用字符串返回
- 比例字段如 `final_adjustment_ratio` 使用小数返回
- 例如 `0.16` 表示 `16%`

### 8.3 状态字段

常见状态值来源于业务流程，接入时建议按“枚举容忍新增值”的方式处理，不要写死为固定列表。

常见示例：

- 周期状态：`draft`、`published`、`archived`
- 评估状态：`generated`、`reviewed`、`confirmed`、`needs_review`
- 调薪建议状态：`recommended`、`pending_approval`、`approved`、`locked`

## 9. API Key 管理接口

以下接口不属于公共读取接口，而是平台管理员用于管理 API Key 的后台接口。

统一前缀：

```text
/api/v1/api-keys
```

鉴权方式：

- `Authorization: Bearer <access_token>`
- 角色要求：`admin`

### 9.1 创建 API Key

```http
POST /api/v1/api-keys/
```

请求体：

```json
{
  "name": "hr-sync-prod",
  "rate_limit": 1000,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

响应说明：

- 会返回 `plain_key`
- 该字段只会返回一次，务必在创建当下安全保存

### 9.2 查询 API Key 列表

```http
GET /api/v1/api-keys/
```

### 9.3 查询单个 API Key

```http
GET /api/v1/api-keys/{key_id}
```

### 9.4 轮换 API Key

```http
POST /api/v1/api-keys/{key_id}/rotate
```

说明：

- 原 Key 会失效
- 会返回新的 `plain_key`

### 9.5 吊销 API Key

```http
POST /api/v1/api-keys/{key_id}/revoke
```

说明：

- 吊销后旧 Key 立即失效

## 10. Webhook 管理接口

以下接口用于登记回调地址、查看状态和投递日志，统一前缀为：

```text
/api/v1/webhooks
```

鉴权方式：

- `Authorization: Bearer <access_token>`
- 角色要求：`admin`

### 10.1 注册 Webhook

```http
POST /api/v1/webhooks/
```

请求体：

```json
{
  "url": "https://example.com/webhook/wage-adjust",
  "description": "薪酬系统回调地址",
  "events": ["recommendation.approved"]
}
```

当前已知事件名：

- `recommendation.approved`

### 10.2 查询 Webhook 列表

```http
GET /api/v1/webhooks/?active_only=true
```

### 10.3 查询单个 Webhook

```http
GET /api/v1/webhooks/{webhook_id}
```

### 10.4 注销 Webhook

```http
DELETE /api/v1/webhooks/{webhook_id}
```

### 10.5 查询投递日志

```http
GET /api/v1/webhooks/{webhook_id}/logs?limit=50
```

日志字段包括：

- `event_type`
- `payload`
- `response_status`
- `response_body`
- `attempt`
- `success`
- `error_message`
- `created_at`

## 11. Webhook 投递设计说明

从当前代码实现看，Webhook 投递设计如下：

- 请求方法：`POST`
- Content-Type：`application/json`
- 超时：10 秒
- 重试：最多 3 次
- 重试间隔：1 秒、5 秒、30 秒
- 签名算法：HMAC-SHA256

投递请求头设计如下：

```http
Content-Type: application/json
X-Webhook-Event: recommendation.approved
X-Signature-256: sha256=<hmac-signature>
```

签名计算方式：

```text
HMAC-SHA256(secret, 原始 JSON body)
```

## 12. 当前 Webhook 状态说明

基于 2026-04-01 当前仓库代码，Webhook 能力需要注意以下几点：

1. Webhook 管理接口已经存在，支持注册、查询、注销和日志查看。
2. 系统会为每个 Webhook 自动生成签名密钥 `secret`。
3. 但当前注册接口响应不会返回该 `secret` 明文，因此仅靠现有管理接口，接收方暂时无法独立完成验签配置。
4. 代码中已存在通用投递实现，但当前业务代码里尚未检索到实际调用 `deliver()` 的地方。

这意味着：

- Webhook 更适合作为“预留中的对外推送能力”
- 当前稳定可用的对外集成方式仍应以公共只读 API 拉取为主

如果后续要正式启用 Webhook，建议补齐两点：

1. 在注册或轮换时安全返回一次性 `secret`
2. 在审批通过、结果发布等业务节点接通事件投递

## 13. 推荐对接方案

### 方案 A：定时拉取

适用于大多数内部系统，推荐优先采用。

建议方式：

1. 定时调用周期调薪结果接口同步审批通过结果
2. 定时调用审批状态接口做过程对账
3. 对单个员工详情场景，按需调用最新评估接口
4. 对 BI 或大屏场景，调用看板汇总接口

优点：

- 实现简单
- 当前项目已稳定支持
- 不依赖事件投递接通状态

### 方案 B：拉取为主，Webhook 为辅

适用于后续计划增强实时性的场景。

建议方式：

1. 先按方案 A 完成主链路
2. 等 Webhook 事件正式接通后，再追加事件驱动同步

## 14. 联调建议

### 14.1 建议先验证这 4 个点

1. API Key 是否可正常创建并保存
2. 公共接口是否能返回 200
3. 周期调薪结果分页是否能正确翻页
4. 金额字符串和比例字段在接入侧是否按预期解析

### 14.2 建议重点关注

- `final_adjustment_ratio` 为小数，不是百分数字符串
- `total` 在分页接口中表示当前页条数，不是总记录数
- 状态字段后续可能扩展，接入方不要写死
- 当前 Webhook 不应当作为唯一同步渠道

## 15. 文档适用范围

本文档整理的是“仓库当前代码已经体现出来的对外集成能力”，不是未来规划文档。如果后续项目补充了更多公共接口、事件类型或 OpenAPI 导出，建议同步更新本文件。
