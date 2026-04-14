# Phase 23: 调薪资格统一导入管理 - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

在现有"调薪资格管理"页面（EligibilityManagementPage）中增加 4 个 Tab（绩效等级、调薪历史、入职信息、非法定假期），每个 Tab 支持本地 Excel 导入和飞书多维表格同步。侧边栏新增菜单入口。不修改现有 ImportCenter 页面。

</domain>

<decisions>
## Implementation Decisions

### 页面结构与导航
- **D-01:** 在现有 EligibilityManagementPage 中扩展，新增 4 个 Tab：绩效等级、调薪历史、入职信息、非法定假期。与 ImportCenter 分开，不复用 ImportCenter
- **D-02:** 每个 Tab 内同时提供"Excel 导入"和"飞书同步"两个功能区域
- **D-03:** 侧边栏菜单新增"调薪资格管理"入口，HR/admin 角色可见

### 飞书多维表格集成
- **D-04:** 手动触发同步，HR 配置字段映射后点击"开始同步"，通过 Celery task 后台执行
- **D-05:** 复用现有 FeishuConfig 的 app_id/app_secret 凭证（Settings 页面配置），每个 Tab 只需配置多维表格 URL 和字段映射
- **D-06:** 字段映射 UI 使用左右两栏拖拽连线设计（左侧飞书字段列表，右侧系统字段列表，拖拽建立连接）。不复用 FieldMappingTable 下拉选择模式
- **D-07:** HR 输入多维表格 URL 后，后端调用飞书 API 自动获取字段列表，前端展示供拖拽映射
- **D-08:** 飞书 API 限流使用固定 RPM（如 60 RPM）+ 指数退避重试。复用 LLM 服务已有的 InMemoryRateLimiter 模式

### 导入结果展示
- **D-09:** 顶部 3 个统计卡片（成功/失败/跳过），下方可展开的错误明细表格。复用现有 ImportResultPanel 模式
- **D-10:** 提供"导出错误报告"按钮，下载 CSV 包含失败行号 + 原因，方便 HR 修正后重新导入

### 数据模型
- **D-11:** 入职信息导入复用 Employee 模型的 hire_date 等字段，通过现有 ImportService 的 employees 类型处理，不新建模型
- **D-12:** 非法定假期新建 NonStatutoryLeave 模型：employee_no, year, total_days, leave_type（可选）。与 Employee 一对多关系。EligibilityEngine 已读取 max_non_statutory_leave_days 配置

### Claude's Discretion
- 拖拽连线的具体前端库选择（如 react-dnd、自研 SVG 连线等）
- Tab 内 Excel 导入和飞书同步的布局排列（上下分区还是左右分区）
- 飞书多维表格 URL 的解析方式和 app_token/table_id 提取逻辑
- NonStatutoryLeave 模型的 leave_type 枚举值定义
- 导入时数据冲突处理策略（覆盖/跳过/追加）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 现有导入基础设施
- `backend/app/services/import_service.py` — ImportService 类，已支持 employees/certifications/performance_grades/salary_adjustments。COLUMN_ALIASES 中文列名映射、MAX_ROWS 限制、per-row 错误处理模式
- `backend/app/tasks/import_tasks.py` — Phase 22 新建的 Celery import task，含进度上报和自动重试
- `backend/app/api/v1/imports.py` — 导入 API 端点，已支持异步触发

### 飞书集成
- `backend/app/services/feishu_service.py` — FeishuService，已有 token 获取和 API 调用逻辑
- `backend/app/models/feishu_config.py` — FeishuConfig 模型，存储 app_id/app_secret
- `backend/app/scheduler/feishu_scheduler.py` — 飞书定时同步模式参考
- `frontend/src/components/attendance/FieldMappingTable.tsx` — 现有字段映射组件（参考但不复用，新设计拖拽连线）

### 资格管理页面
- `frontend/src/pages/EligibilityManagementPage.tsx` — 现有调薪资格管理页面，需在此基础上扩展 Tab
- `frontend/src/services/eligibilityService.ts` — 资格相关前端服务
- `backend/app/engines/eligibility_engine.py` — EligibilityEngine，读取 max_non_statutory_leave_days 配置

### 导入结果展示
- `frontend/src/components/import/ImportResultPanel.tsx` — 现有导入结果面板组件，复用此模式
- `frontend/src/components/import/ImportErrorTable.tsx` — 错误表格组件

### 需求定义
- `.planning/REQUIREMENTS.md` §ELIGIMP-01 至 §ELIGIMP-04 — 调薪资格导入管理需求
- `.planning/REQUIREMENTS.md` §FEISHU-01 — 飞书 API 限流和重试

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ImportService`: 已支持 4 种数据类型的 Excel 导入，含中文列名映射和 per-row 错误记录
- `import_tasks.py`: Celery task 包装，含进度上报（PROGRESS meta）和自动重试
- `FeishuService`: 飞书 API 客户端，token 管理和 API 调用
- `ImportResultPanel` + `ImportErrorTable`: 导入结果展示组件
- `useTaskPolling`: Phase 22 新建的 2 秒轮询 hook，可用于飞书同步进度
- `InMemoryRateLimiter`（LlmService 中）: RPM 限流模式参考

### Established Patterns
- ImportService 通过 COLUMN_ALIASES 字典支持中文列名，REQUIRED_COLUMNS 定义必填字段
- Celery task 通过 `self.update_state(state='PROGRESS', meta={...})` 上报进度
- 前端 Tab 用 chip-button 样式切换（见 SharingRequestsPage）
- 飞书配置通过 Settings 页面统一管理

### Integration Points
- `frontend/src/pages/EligibilityManagementPage.tsx` — 主页面扩展点
- `frontend/src/App.tsx` — 路由注册
- `frontend/src/components/layout/AppShell.tsx` — 侧边栏菜单配置
- `backend/app/services/import_service.py` — SUPPORTED_TYPES 扩展（如需新增 hire_info 类型）
- `backend/app/models/` — NonStatutoryLeave 新模型
- `backend/app/tasks/` — 飞书同步 Celery task

</code_context>

<specifics>
## Specific Ideas

- 飞书字段映射使用左右两栏拖拽连线（类似 ETL 工具的映射界面），不用下拉选择
- 导入错误报告支持 CSV 导出，包含行号和具体原因

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-eligibility-import*
*Context gathered: 2026-04-14*
