# Feature Landscape

**Domain:** 企业调薪平台 v1.2 — 生产就绪与数据管理完善
**Researched:** 2026-04-07
**Confidence:** HIGH (基于已有代码库深度分析 + 行业最佳实践)

---

## Table Stakes

用户/运维人员期待的功能。缺失 = 系统无法进入生产环境或数据管理体验不完整。

| Feature | Why Expected | Complexity | Depends On |
|---------|--------------|------------|------------|
| Celery+Redis 异步任务基础架构 | 已有 celery==5.4.0, redis==5.2.1 依赖但未激活；生产环境长任务（AI评估、批量导入、飞书同步）会阻塞 API 请求，必须异步化 | Med | Redis 可用 |
| Python 3.9 兼容性 | 服务器部署环境为 Python 3.9；当前代码大量使用 `X \| None` 语法（PEP 604）需要 `from __future__ import annotations`（已有），但 `match` 语句（3.10+）、`tomllib`（3.11+）需排查 | Med | 无 |
| 员工所属公司字段 | 多公司集团场景下区分员工归属是基本的人事数据需求 | Low | Employee 模型 |
| 文件共享拒绝后清理 + 状态标签 | 当前拒绝后文件仍保留在申请方文件列表中，用户困惑；outgoing 方向缺少 "待同意"/"已拒绝" 状态标签 | Low | SharingRequest, FileService |
| 调薪资格数据统一导入管理页 | 当前 4 类资格数据（入职年限/调薪历史/假期记录/绩效等级）导入入口分散在不同页面，HR 操作效率低 | High | FeishuService, EligibilityService, 现有 bitable 集成模式 |

---

## Feature 1: Celery+Redis 异步任务架构

### 期望行为

**核心模式：** FastAPI 接收请求 -> 立即返回 task_id -> Celery worker 在后台执行 -> 前端轮询/回调获取结果。

**具体 UX 流程：**

1. **API 调用方发起请求** -> 后端立即返回 `{ task_id: "xxx", status: "queued" }`
2. **前端/调用方轮询** `GET /api/v1/tasks/{task_id}` -> 返回 `{ status: "running" | "success" | "failed", result: ... }`
3. **跨应用调用模式：** 外部系统通过 Public API 触发评估任务 -> 拿到 task_id -> 轮询直到完成

**应适用的场景（按现有代码分析）：**

| 场景 | 当前实现 | 改为 Celery 任务 |
|------|---------|-----------------|
| AI 评估（LLM 调用） | 同步 httpx 调用，120s 超时 | `evaluation.run_evaluation.delay(evaluation_id)` |
| 飞书数据同步 | 同步 `sync_attendance()`，阻塞请求 | `feishu.sync_attendance.delay(mode, triggered_by)` |
| 批量导入 | 同步处理，大文件会超时 | `import.process_batch.delay(job_id)` |
| 文件解析 | 同步，多文件串行 | `parse.parse_file.delay(file_id)` |

**Celery 配置建议（基于已有依赖版本）：**

```python
# backend/app/core/celery_app.py
from celery import Celery

celery_app = Celery('wage_adjust')
celery_app.config_from_object({
    'broker_url': settings.redis_url,           # redis://localhost:6379/0
    'result_backend': settings.redis_url,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'UTC',
    'enable_utc': True,
    'task_time_limit': 1800,          # 30 分钟硬限制
    'task_soft_time_limit': 1500,     # 25 分钟软限制
    'result_expires': 3600,           # 结果保留 1 小时
    'task_routes': {
        'backend.app.tasks.evaluation.*': {'queue': 'evaluation'},
        'backend.app.tasks.sync.*': {'queue': 'sync'},
        'backend.app.tasks.import.*': {'queue': 'default'},
    },
})
```

**任务状态 API 设计：**

```
GET /api/v1/tasks/{task_id}
Response: {
  "task_id": "abc-123",
  "status": "pending" | "running" | "success" | "failed" | "retry",
  "progress": 0.75,        // 可选，百分比
  "result": { ... },       // status=success 时
  "error": "...",           // status=failed 时
  "created_at": "...",
  "updated_at": "..."
}
```

**跨应用 API 调用模式：**

外部系统发起评估 -> Public API 立即返回 task_id -> 外部系统按 task_id 轮询结果。这是 v1.2 "跨应用 API 调用基础" 的核心含义。

**关键实现要点：**

- Celery task 内部需要独立的 DB Session（不共享 FastAPI 的请求级 session）
- 使用 `bind=True` + `max_retries=3` + 指数退避
- 任务幂等性：同一 evaluation_id 不应并发执行两次
- 保留 fallback 路径：Redis 不可用时回退到 FastAPI BackgroundTasks（开发环境）

### Complexity: MEDIUM

已有依赖；主要工作在于：(1) 创建 celery_app 配置 (2) 将同步服务方法拆为 task (3) 添加 task 状态查询 API (4) DB Session 在 worker 中的生命周期管理。

---

## Feature 2: 员工所属公司字段

### 期望行为

- Employee 模型增加 `company: Mapped[str | None]` 字段
- 仅在员工档案详情页可见（不在列表、不在搜索筛选）
- 批量导入 Excel 支持该字段（可选列）
- 对外 API 包含该字段

**UX：** 管理员/HR 在员工详情页看到 "所属公司" 一行，显示为只读文本。无需前端编辑入口。

### Complexity: LOW

一个 Alembic migration + 模型字段 + schema 字段 + 前端详情页一行展示。

---

## Feature 3: Python 3.9 兼容 + 服务器部署优化

### 期望行为

**兼容性修复：**

| 语法/特性 | Python 3.9 状态 | 解决方案 |
|-----------|-----------------|---------|
| `X \| None` 类型注解 | 需要 `from __future__ import annotations`（已全量使用） | 已兼容，无需改动 |
| `match/case` 语句 | 3.10+ 才有 | 排查并替换为 if/elif |
| `tomllib` | 3.11+ 才有 | 如有使用，改用 `tomli` 包 |
| `str.removeprefix()` / `str.removesuffix()` | 3.9+ 已有 | 已兼容 |
| `dict \| dict` 合并运算符 | 3.9+ 已有 | 已兼容 |
| `typing.TypeAlias` | 3.10+ | 如有使用，改为普通赋值 |
| SQLAlchemy `Mapped[T]` | 需要 SQLAlchemy 2.0+（已有） + `from __future__ import annotations` | 已兼容 |

**部署优化：**

- uvicorn 启动参数优化（workers 数量、host 绑定）
- Gunicorn + Uvicorn worker 模式（生产推荐）
- 静态文件服务分离（Nginx 代理前端静态资源）
- 环境变量标准化（区分 dev/staging/prod）
- 健康检查端点 `/health`

### Complexity: MEDIUM

排查全代码库兼容性 + 部署脚本/配置编写。需逐文件扫描，但不涉及逻辑改动。

---

## Feature 4: 文件共享拒绝后处理

### 期望行为

**当前问题（根据代码分析）：**

1. `SharingService.reject_request()` 只设置 `status='rejected'` + `resolved_at`，但 **不删除** requester 方上传的文件副本
2. 前端 `SharingRequestCard` 已有 "已拒绝" 标签样式（`STATUS_STYLES.rejected`），但 **outgoing 方向不显示操作状态标签**——申请发出方看到的状态列只显示最终比例或 "-"
3. 拒绝后，requester 的文件列表中仍然保留那个被拒绝的文件，用户以为文件可用但实际无效

**目标 UX：**

| 视角 | 当前行为 | 目标行为 |
|------|---------|---------|
| 原上传者（incoming） | 可以"拒绝"，状态显示"已拒绝" | 不变，保持现状 |
| 申请方（outgoing） | 状态列只显示"-"或最终比例 | 显示 "待同意" / "已拒绝" 状态标签 |
| 申请方文件列表 | 拒绝后文件仍在列表中 | 拒绝后自动软删除 requester_file，文件从列表消失 |

**具体改动点：**

1. **后端 `reject_request()` 增加文件清理逻辑：**
   - 拒绝时对 `requester_file` 执行软删除（标记 `is_deleted=True`）或硬删除
   - 同时删除磁盘上的物理文件（通过 `LocalStorageService`）
   - 推荐软删除 + 定期清理，避免误操作不可恢复

2. **前端 outgoing 方向状态显示：**
   - 当前 `SharingRequestCard` 在 outgoing 时最后一列只展示 `finalRatio` 或 "-"
   - 改为：outgoing 方向也展示 `statusPill`（待审批/已审批/已拒绝/已超时）
   - 特别是 "待同意" (pending) 和 "已拒绝" (rejected) 要醒目

3. **文件列表过滤：**
   - `EvaluationDetail` 页面的文件列表查询需过滤掉 `is_deleted` 的文件
   - 或在前端过滤掉关联的 sharing_request 状态为 rejected 的文件

### Complexity: LOW

后端改动约 10-20 行（reject 时清理文件）；前端改动约 5-10 行（outgoing 展示 statusPill）。

---

## Feature 5: 调薪资格数据统一导入管理页

### 期望行为

**核心问题：** 当前调薪资格检查依赖 4 类数据，但导入入口分散：

| 数据类型 | 当前入口 | 对应模型 |
|---------|---------|---------|
| 入职年限（tenure） | Employee.hire_date，批量导入员工时携带 | Employee |
| 调薪历史 | 无独立入口，零散在 eligibility API | SalaryAdjustmentRecord |
| 假期记录 | 飞书考勤同步页面 | AttendanceRecord |
| 绩效等级 | `FeishuService.sync_performance_records()` 或手动单条创建 | PerformanceRecord |

**目标 UX — 统一管理页：**

```
页面标题：调薪资格数据管理

+-----------------------------------------------------+
|  [入职年限]  [调薪历史]  [假期记录]  [绩效等级]     |  <- Tab 切换
+-----------------------------------------------------+
|                                                     |
|  当前数据概览                                        |
|  +----------------------------------------------+   |
|  | 已导入: 352 条  |  最近更新: 2026-04-01       |   |
|  | 覆盖率: 89%（352/396 名活跃员工）              |   |
|  +----------------------------------------------+   |
|                                                     |
|  导入方式                                            |
|  +--------------+  +------------------+             |
|  |  飞书导入     |  |  Excel 上传      |             |
|  |  (推荐)      |  |                  |              |
|  +--------------+  +------------------+             |
|                                                     |
|  [飞书导入] 展开：                                    |
|  +----------------------------------------------+   |
|  | 多维表格 App Token: [____________]             |   |
|  | 数据表 Table ID:    [____________]             |   |
|  |                                               |   |
|  | 字段映射:                                      |   |
|  | +--------------+----------------+             |   |
|  | | 飞书字段名   | 系统字段        |             |   |
|  | +--------------+----------------+             |   |
|  | | 员工工号     | employee_no    |             |   |
|  | | 绩效等级     | grade          |             |   |
|  | | 年度         | year           |             |   |
|  | +--------------+----------------+             |   |
|  | [+ 添加映射]                                   |   |
|  |                                               |   |
|  | [开始同步]                                     |   |
|  +----------------------------------------------+   |
|                                                     |
|  [Excel 上传] 展开：                                  |
|  +----------------------------------------------+   |
|  | [下载模板]  [选择文件]  [开始导入]              |   |
|  +----------------------------------------------+   |
|                                                     |
|  导入历史记录                                        |
|  +------+--------+-------+------+----------+       |
|  | 时间 | 方式   | 总数  | 成功 | 失败/跳过 |       |
|  +------+--------+-------+------+----------+       |
|  | 4/1  | 飞书   | 352   | 340  | 12       |       |
|  | 3/15 | Excel  | 50    | 50   | 0        |       |
|  +------+--------+-------+------+----------+       |
+-----------------------------------------------------+
```

**每个 Tab 的具体数据与映射：**

| Tab | 飞书默认字段映射 | Excel 模板列 | 目标模型 | Upsert 键 |
|-----|----------------|-------------|---------|-----------|
| 入职年限 | 员工工号->employee_no, 入职日期->hire_date | 工号, 入职日期 | Employee.hire_date | employee_no |
| 调薪历史 | 员工工号->employee_no, 调薪日期->adjustment_date, 调薪类型->adjustment_type, 金额->amount | 工号, 调薪日期, 类型, 金额 | SalaryAdjustmentRecord | employee_no + adjustment_date |
| 假期记录 | 员工工号->employee_no, 月份->period, 非法定假天数->non_statutory_leave_days | 工号, 月份, 非法定假天数 | AttendanceRecord.non_statutory_leave_days | employee_no + period |
| 绩效等级 | 员工工号->employee_no, 年度->year, 等级->grade | 工号, 年度, 等级 | PerformanceRecord | employee_no + year |

**飞书多维表格映射 UX 关键设计（复用现有模式）：**

当前 `FieldMappingTable` 组件已有成熟的映射 UX：
- 左列输入飞书字段名（文本输入）
- 右列选择系统字段（下拉选择）
- 支持添加/删除行
- employee_no 为必填校验

v1.2 需要做的是：**让 FieldMappingTable 组件可配置不同的 SYSTEM_FIELDS 列表**，每个 Tab 对应不同的系统字段选项。

当前组件硬编码了考勤字段（`attendance_rate`, `absence_days` 等），需要改为通过 props 传入可用字段列表。

**飞书配置复用：** 所有 Tab 共享同一个飞书 App 配置（app_id/app_secret），但 bitable_app_token 和 table_id 可以不同（不同数据在不同表中）。因此每个数据类型需要独立的 bitable 连接配置。

**Excel 导入行为：**

- 提供每种数据类型的 Excel 模板下载
- 上传后后端解析、校验、upsert
- 返回处理结果摘要：成功数/失败数/跳过数 + 错误详情
- 复用现有 `import_service.py` 的批量导入模式

**导入历史：**

- 统一的 ImportLog 表，记录每次导入的方式、数据类型、结果统计
- 现有 `FeishuSyncLog` 模式可扩展为通用导入日志

### Complexity: HIGH

- 前端：新页面 + Tab 组件 + 4 套字段映射配置 + Excel 上传 + 导入历史表格
- 后端：4 种数据类型的 Feishu sync 方法 + 4 种 Excel 解析器 + 通用 ImportLog 模型
- 需要泛化 `FieldMappingTable` 组件 + 泛化 `FeishuService` 的同步方法

---

## Differentiators

不是用户期待的，但提供后会显著提升体验的功能。

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Celery 任务进度条 | 批量导入/同步时前端显示实时进度百分比 | Med | 通过 Redis pub/sub 或轮询 task meta |
| 导入数据预览 + 确认 | Excel/飞书导入前先展示将要导入的数据预览，用户确认后再执行 | Med | 防止误操作，但增加交互复杂度 |
| 导入冲突检测 | 导入前检测与现有数据的冲突，显示 "将更新 X 条 / 新增 Y 条 / 跳过 Z 条" | Low | 用户体验显著提升 |
| Flower 任务监控面板 | 独立的 Celery 监控 Web UI | Low | 仅运维可见，`pip install flower` 即可 |
| 数据覆盖率告警 | 导入后自动检测覆盖率，低于阈值时告警 HR | Low | 防止遗漏数据 |

---

## Anti-Features

明确不应构建的功能。

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| 飞书字段自动发现（从 bitable API 拉取字段列表） | 增加 API 权限要求和调用复杂度；当前手动输入字段名已够用 | 保持手动输入飞书字段名 + 文档说明 |
| WebSocket 实时任务推送 | 过度工程化；Celery 任务轮询已满足需求，WebSocket 增加连接管理复杂度 | 前端 3-5 秒轮询 task 状态端点 |
| 动态数据类型配置（让 HR 自定义新的资格数据类型） | 4 种数据类型已覆盖业务需求；动态类型需要 schema-on-read 模型，过度复杂 | 固定 4 种数据类型 + 可配置阈值 |
| 共享拒绝后的申诉流程 | 增加审批链条复杂度；已有"撤销拒绝"机制 | 保持现有的撤销拒绝功能 |
| 自动文件回收站（带恢复） | 拒绝后的文件只是副本（requester 上传的副本），无业务数据价值 | 直接软删除，不提供恢复 UI |
| Celery Beat 定时任务调度 | 当前飞书同步已有 sync_hour/sync_minute 配置但通过 cron/手动触发；引入 Beat 增加部署组件 | 使用系统 cron 或 supervisord 触发 |

---

## Feature Dependencies

```
Feature 1 (Celery) --- 无前置依赖，但为 Feature 5 提供异步基础
                    +-- Feature 5 的飞书同步可选通过 Celery task 执行

Feature 2 (Company) --- 无依赖
Feature 3 (Py3.9)  --- 无依赖，但应最先完成（确保后续开发在兼容环境下验证）

Feature 4 (Sharing) --- 依赖现有 SharingService, FileService
                    +-- 不依赖 Celery（同步操作，无需异步）

Feature 5 (Import)  --- 依赖现有 FeishuService, EligibilityService
                    +-- 复用 FieldMappingTable 组件（需泛化）
                    +-- 复用 FeishuConfig 的 app_id/app_secret（共享凭证）
                    +-- 可选依赖 Feature 1（大批量导入通过 Celery 异步执行）
```

---

## MVP Recommendation

### Phase 1 — 优先完成（无阻塞、低风险）

1. **Python 3.9 兼容性**（Feature 3） — 最先完成，确保后续所有开发在目标环境兼容
2. **员工所属公司字段**（Feature 2） — 改动最小，一个 migration + 几行代码
3. **文件共享拒绝处理**（Feature 4） — 改动小，直接修复用户困惑点

### Phase 2 — 核心基础设施

4. **Celery+Redis 异步任务架构**（Feature 1） — 为后续异步场景打基础

### Phase 3 — 大功能交付

5. **统一导入管理页**（Feature 5） — 工作量最大，依赖前端新页面 + 后端 4 种数据类型泛化

### Defer（本期可不做的差异化功能）

- 任务进度条 — 可以后续 milestone 补充
- 导入数据预览 — 先做导入，后续加预览
- Flower 监控 — 运维工具，按需部署

---

## Sources

- 项目代码库深度分析：`backend/app/services/sharing_service.py`, `eligibility_service.py`, `feishu_service.py`, `file_service.py`
- 前端组件分析：`SharingRequestCard.tsx`, `SharingRequests.tsx`, `FieldMappingTable.tsx`, `FeishuConfig.tsx`
- 数据模型分析：`Employee`, `SharingRequest`, `FeishuConfig`, `PerformanceRecord`, `SalaryAdjustmentRecord`, `AttendanceRecord`
- [Celery + FastAPI 集成最佳实践 2025](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7)
- [FastAPI + Celery 入门指南](https://derlin.github.io/introduction-to-fastapi-and-celery/03-celery/)
- [Feishu Bitable API 概览](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/bitable-overview)
- [Feishu 字段编辑开发指南](https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/guide)
