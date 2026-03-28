# Phase 7: 看板与缓存层 - 上下文

**收集日期:** 2026-03-28
**状态:** 准备规划

<domain>
## 阶段边界

看板加载速度优化、多维度图表展示（AI 等级分布、调薪幅度分布、审批流水线状态）、部门下钻、KPI 实时刷新、Redis 缓存层、角色权限数据隔离。

范围内:
- SQL 侧聚合替换全表扫描（DASH-01）
- Redis 缓存 + TTL 策略（DASH-02）
- AI 等级分布图表（DASH-03）
- 调薪幅度分布直方图（DASH-04）
- 审批流水线状态图（DASH-05）
- 部门下钻（DASH-06）
- KPI 卡片实时刷新（DASH-07）

范围外:
- Docker 一键部署（用户明确延后到单独阶段）
- 员工自助看板（员工角色不可见看板）
- 导出看板数据为 PDF/Excel

</domain>

<decisions>
## 实施决策

### 图表库与可视化
- **D-01:** 使用 **ECharts** 作为图表库。安装 `echarts` + `echarts-for-react`。
- **D-02:** **全部替换**现有纯 CSS 图表组件（DistributionChart、HeatmapChart 等）为 ECharts 实现。统一技术栈，不保留混合风格。

### 缓存策略
- **D-03:** Redis 为**必须依赖**，开发环境也使用 Redis。不提供内存缓存回退。
- **D-04:** 缓存 key 包含 `cycle_id` + 用户角色，防止跨角色数据泄漏。TTL 按图表类型 5-15 分钟。
- **D-05:** 要保证后续部署上服务器的方便程度。本阶段确保 Redis 配置清晰，但 Docker 一键部署延后。

### 部门下钻
- **D-06:** 部门下钻使用**页内展开**方式。点击部门行后在当前页面下方展开该部门的等级分布和调薪平均值图表。不弹出模态框，不跳转新页面。

### KPI 卡片
- **D-07:** KPI 卡片展示 4 个指标：待审批数（实时 30 秒刷新）、员工总数/已评估数、平均调薪幅度、AI 等级分布概览。
- **D-08:** 待审批数每 30 秒轮询刷新（`setInterval`），不需要 WebSocket。其他图表使用 Redis TTL 自然过期刷新。

### 页面布局
- **D-09:** 看板页面使用**双列网格**布局。KPI 卡片横排顶部，下方图表双列排列（AI等级分布 | 调薪幅度分布），审批流水线和部门表格占满宽。
- **D-10:** 顶部包含**周期选择器**下拉框，切换评估周期后所有图表刷新。默认显示最新周期。

### 权限
- **D-11:** 看板仅对 **admin/hrbp/manager** 可见。员工角色不显示看板入口。
- **D-12:** manager 只能看到自己管理的部门数据，admin/hrbp 看全量。沿用已有 AccessScopeService 权限模型。

### Claude's Discretion
- ECharts 主题色和图表样式细节
- SQL 聚合查询的具体写法
- Redis key 命名规范和过期策略细节
- KPI 卡片的具体视觉样式

</decisions>

<canonical_refs>
## 规范引用

**下游代理在规划或实施前必须阅读以下文件。**

### 看板服务
- `backend/app/services/dashboard_service.py` — 现有 DashboardService，全表扫描模式需改造为 SQL 聚合
- `backend/app/api/v1/dashboard.py` — 现有看板 API 端点（如存在）

### 前端看板
- `frontend/src/pages/Dashboard.tsx` — 现有看板页面
- `frontend/src/components/dashboard/DistributionChart.tsx` — 待替换为 ECharts
- `frontend/src/components/dashboard/HeatmapChart.tsx` — 待替换为 ECharts
- `frontend/src/components/dashboard/ActionSummaryPanel.tsx` — 审批摘要面板
- `frontend/src/components/dashboard/DepartmentInsightTable.tsx` — 部门表格（下钻基础）
- `frontend/src/services/dashboardService.ts` — 前端看板服务层

### 权限
- `backend/app/services/access_scope_service.py` — 角色权限隔离服务
- `frontend/src/utils/roleAccess.ts` — 前端角色模块配置

### 先前决策
- `.planning/phases/01-security-hardening-and-schema-integrity/01-CONTEXT.md` — 角色权限模型

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- `DashboardService` 已有 `_submissions()`、`_evaluations()` 等数据加载方法，需改为 SQL 聚合
- `OverviewCards` 组件已有 KPI 卡片基础结构
- `DepartmentInsightTable` 已有部门表格，可作为下钻入口
- `AccessScopeService` 提供完整的角色权限过滤

### 已建立模式
- 前端使用 `useEffect` + `useState` 获取数据（无 React Query/SWR）
- 后端 API 通过 `Depends(get_current_user)` 获取当前用户
- 图表组件在 `frontend/src/components/dashboard/` 目录下

### 集成点
- 看板 API 端点在 `backend/app/api/v1/` 下
- Redis 配置需添加到 `backend/app/core/config.py` 的 Settings 中
- `requirements.txt` 已有 `redis==5.2.1` 和 `hiredis==3.1.0`

</code_context>

<specifics>
## 具体要求

- ECharts 图表需要中文标签（"一级"/"二级"等，而非 "Level 1"/"Level 2"）
- Redis 配置要清晰，便于后续 Docker 部署
- 看板页面已有入口（`/dashboard`），在工作区侧栏已配置

</specifics>

<deferred>
## 延后事项

- **Docker 一键部署** — 用户明确要求延后到单独阶段，包含完整 docker-compose（前端 + 后端 + Redis + DB）
- **员工自助看板** — 员工角色不可见看板，如需提供简版需新阶段
- **看板数据导出** — 导出 PDF/Excel 功能不在当前范围

</deferred>

---

*Phase: 07-dashboard-and-cache-layer*
*Context gathered: 2026-03-28*
