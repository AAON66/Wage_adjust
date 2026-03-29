# Phase 9: 飞书考勤集成 - 上下文

**收集日期:** 2026-03-29
**状态:** 准备规划

<domain>
## 阶段边界

从飞书多维表格同步员工考勤数据，在调薪审批页面展示考勤概览，独立考勤管理页面，支持手动/定时同步，飞书连接配置可视化管理。

范围内:
- 飞书多维表格 API 对接（ATT-01）
- 手动触发同步（ATT-02）
- 定时自动同步（ATT-03）
- 飞书连接配置 UI（ATT-04）
- 调薪页面考勤概览（ATT-05）
- 考勤数据时间戳标注（ATT-06）
- 同步失败处理与展示（ATT-07）
- 独立考勤管理页面（卡片面板 + 同步状态 + 配置入口）

范围外:
- 考勤数据自动影响调薪计算（仅作参考展示）
- 考勤数据导出
- 飞书审批流对接（仅多维表格）

</domain>

<decisions>
## 实施决策

### 飞书 API 认证与安全
- **D-01:** App ID/Secret **数据库加密存储**。复用项目已有的加密方案，管理员通过 UI 配置。
- **D-02:** Token 自动刷新——tenant_access_token 有效期 2 小时，系统在调用前检查过期时间，过期时自动重新获取。

### 字段映射
- **D-03:** **UI 可配置映射**。管理员在配置页面设置「飞书字段名 → 系统字段名」映射关系。系统固定字段：employee_no（关联键）、attendance_rate、absence_days、overtime_hours、late_count、early_leave_count。飞书字段名可自定义。
- **D-04:** 按 employee_no 匹配员工，飞书表格中必须有一个字段映射到员工工号。

### 定时同步
- **D-05:** 使用 **APScheduler**（内嵌 FastAPI 进程），不依赖额外 Celery worker。配置定时同步时间（如每天 06:00）。
- **D-06:** 定时同步使用增量拉取（基于上次同步时间）。

### 同步策略
- **D-07:** 默认**增量拉取**（基于上次同步时间，仅获取新增/修改记录）。
- **D-08:** 手动提供两个按钮：「全量同步」（拉取全部 + upsert）和「增量同步」（仅新增/修改）。
- **D-09:** 同步失败**自动重试 3 次**（间隔递增），全部失败后记录错误日志，在管理页面展示错误状态。不影响调薪流程。

### 考勤展示
- **D-10:** 考勤概览在**两个位置**展示：
  1. 人工调薪窗口内嵌（该员工的考勤 KPI 卡片）
  2. 独立考勤管理页面（所有员工的卡片面板，支持搜索筛选）
- **D-11:** 展示字段：出勤率、缺勤天数、加班时长、迟到次数、早退次数。底部标注「数据截至：YYYY-MM-DD HH:mm」时间戳。

### 考勤管理页面
- **D-12:** 页面包含：员工考勤卡片面板（搜索+筛选）、同步状态卡片（上次同步时间/状态/记录数）、手动同步按钮（全量+增量）、飞书配置入口按钮。
- **D-13:** 页面权限：**admin + hrbp** 可见。飞书配置修改权限仅 admin。

### 飞书配置页面
- **D-14:** **单页表单**布局。分两个区域：「连接配置」（App ID / App Secret / 多维表格 ID / 定时同步时间）和「字段映射」（双列映射表：左飞书字段名、右系统字段名）。底部保存按钮。
- **D-15:** 飞书配置页面**仅 admin** 可访问。

### Claude's Discretion
- APScheduler 的具体调度配置
- 考勤卡片和配置页面的视觉样式
- 飞书 API 错误码到中文错误消息的映射
- 增量同步的「修改时间」字段检测逻辑

</decisions>

<canonical_refs>
## 规范引用

### 调薪审批页面
- `frontend/src/pages/SalaryDetail.tsx` — 调薪详情页（内嵌考勤概览的位置）
- `frontend/src/components/salary/` — 现有调薪组件

### 后端服务
- `backend/app/services/` — 服务层模式
- `backend/app/core/config.py` — 配置管理（新增飞书相关配置项）
- `backend/app/core/security.py` — 加密方案复用
- `backend/app/models/` — ORM 模型模式

### 权限
- `backend/app/dependencies.py` — require_roles 权限工厂
- `frontend/src/utils/roleAccess.ts` — 角色模块配置

### 先前决策
- Phase 1: 加密方案
- Phase 3: 审批工作流页面布局
- Phase 7: Redis（APScheduler 可能用于状态存储）

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- `backend/app/core/security.py` 已有加密/解密方法
- `backend/app/dependencies.py` 已有 `require_roles` 工厂
- `frontend/src/utils/roleAccess.ts` 已有角色模块管理
- Celery + Redis 基础设施已就绪（虽然不用 Celery 但 Redis 可用）
- `requirements.txt` 已有 `httpx`（可用于飞书 API 调用）

### 需要新建
- `FeishuConfig` 模型（存储加密后的 App Secret + 字段映射 JSON）
- `AttendanceRecord` 模型（员工考勤快照）
- `FeishuSyncLog` 模型（同步日志）
- `FeishuService`（API 调用 + Token 管理 + 数据同步）
- `AttendanceService`（考勤查询 + 管理）
- 前端：考勤管理页面、飞书配置页面、考勤概览组件

</code_context>

<deferred>
## 延后事项

- **考勤数据影响调薪计算** — 本阶段考勤仅作参考展示，不自动影响调薪
- **考勤数据导出** — 不在当前范围
- **飞书审批流对接** — 仅对接多维表格
- **Mock 数据** — 用户明确不需要开发环境 Mock

</deferred>

---

*Phase: 09-feishu-attendance-integration*
*Context gathered: 2026-03-29*
