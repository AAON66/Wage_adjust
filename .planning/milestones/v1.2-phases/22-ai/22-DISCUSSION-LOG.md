# Phase 22: AI 评估与批量导入异步迁移 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 22-ai
**Areas discussed:** 前端进度展示, API 契约设计, 任务粒度与进度计算, 失败处理与重试

---

## 前端进度展示

### 进度 UI 形态

| Option | Description | Selected |
|--------|-------------|----------|
| 状态文字 + Spinner | "AI 评估中..." / "导入中 45/120 行" + loading 动画。简单可靠 | ✓ |
| 进度条 + 百分比 | 导入显示进度条，AI 评估显示步骤进度条。更直观但需要更细的进度上报 | |
| 你来决定 | Claude 根据场景分别选择 | |

**User's choice:** 状态文字 + Spinner
**Notes:** 无

### 完成通知方式

| Option | Description | Selected |
|--------|-------------|----------|
| 轮询自动刷新 | 前端轮询发现完成后直接刷新页面数据，无额外通知 | ✓ |
| Toast 提示 + 自动刷新 | 轮询发现完成后弹 Toast 同时刷新数据 | |
| 你来决定 | Claude 根据场景选择 | |

**User's choice:** 轮询自动刷新
**Notes:** 无

### 轮询间隔

| Option | Description | Selected |
|--------|-------------|----------|
| 2秒固定间隔 | 简单可靠，对 Redis 压力小 | ✓ |
| 递增退避 | 前 30 秒每 2 秒，之后逐渐拉长到 5-10 秒 | |
| 你来决定 | Claude 根据任务类型选择 | |

**User's choice:** 2秒固定间隔
**Notes:** 无

---

## API 契约设计

### 端点组织方式

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有端点 | POST /evaluations/generate 改为返回 {task_id, status}。破坏性但更简洁 | ✓ |
| 新增异步端点 | 保留现有同步端点，新增 /generate-async。非破坏性但端点增多 | |
| 你来决定 | Claude 根据代码现状选择 | |

**User's choice:** 复用现有端点
**Notes:** 无

### 轮询端点位置

| Option | Description | Selected |
|--------|-------------|----------|
| GET /tasks/{task_id} | 新建 tasks.py，通用任务查询端点。AI 评估和导入共用 | ✓ |
| 分别在各自路由下 | GET /evaluations/tasks/{id} 和 GET /imports/tasks/{id}。逻辑分离但代码重复 | |

**User's choice:** GET /tasks/{task_id}
**Notes:** 无

### 响应格式

| Option | Description | Selected |
|--------|-------------|----------|
| 嵌入结果 | 完成时 result 字段包含业务数据，前端一次轮询拿到全部数据 | ✓ |
| 只返回状态+资源ID | 完成时返回 resource_id，前端再调现有端点获取详细数据。解耦但多一次请求 | |

**User's choice:** 嵌入结果
**Notes:** 无

---

## 任务粒度与进度计算

### AI 评估进度

| Option | Description | Selected |
|--------|-------------|----------|
| 粗粒度状态 | pending → running → completed/failed。不报告子步骤 | ✓ |
| 分步骤状态 | pending → loading_evidence → calling_llm → scoring → completed/failed | |

**User's choice:** 粗粒度状态
**Notes:** LLM 调用本身无法量化进度

### 批量导入进度

| Option | Description | Selected |
|--------|-------------|----------|
| 按行报告 | 定期更新 meta {processed, total, errors}，每批 50 行更新一次 | ✓ |
| 粗粒度状态 | 和 AI 评估一样只报告 pending/running/completed/failed | |

**User's choice:** 按行报告
**Notes:** 无

---

## 失败处理与重试

### AI 评估重试策略

| Option | Description | Selected |
|--------|-------------|----------|
| 自动重试 2 次 | autoretry_for + retry_backoff，2 次失败后标记 failed | ✓ |
| 不自动重试 | 失败直接标记 failed，用户手动重新触发 | |
| 你来决定 | Claude 根据场景选择 | |

**User's choice:** 自动重试 2 次
**Notes:** 无

### 批量导入部分行失败

| Option | Description | Selected |
|--------|-------------|----------|
| 继续处理 + 汇总错误 | 单行失败不中断，最终返回 {success, failed, errors} | ✓ |
| 失败超阈值时中断 | 失败行超过 10% 时停止导入 | |

**User's choice:** 继续处理 + 汇总错误
**Notes:** 与现有 ImportService per-row 错误记录逻辑一致

---

## Claude's Discretion

- DB session 管理细节
- 前端轮询 hook 实现方式
- task meta 更新批次大小
- 任务超时设置

## Deferred Ideas

None
