---
phase: 7
slug: dashboard-and-cache-layer
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-28
---

# Phase 7 — UI 设计契约 / UI Design Contract

> 看板与缓存层的视觉与交互契约。由 gsd-ui-researcher 生成，由 gsd-ui-checker 验证。
> Visual and interaction contract for the dashboard and cache layer phase.

---

## 设计系统 / Design System

| 属性 | 值 |
|------|---|
| 工具 | none（项目使用自定义 CSS 设计系统，无 shadcn） |
| 预设 | 不适用 |
| 组件库 | 无第三方组件库；使用项目自有 CSS 类（`.surface`、`.metric-tile`、`.table-shell` 等） |
| 图表库 | ECharts 6.0.0 + echarts-for-react 3.0.6（D-01 锁定决策） |
| 图标库 | 无专用图标库；KPI 卡片使用 emoji 或文字标识 |
| 字体 | "PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif（已在 `:root` 声明） |

---

## 间距比例 / Spacing Scale

已声明值（必须为 4 的倍数）：

| Token | 值 | 用途 |
|-------|----|------|
| xs | 4px | 图标间距、ECharts 内部 padding |
| sm | 8px | 紧凑元素间距、metric-note 上边距 |
| md | 16px | 默认元素间距、网格 gap、卡片内 padding |
| lg | 24px | 区域 padding（dashboard-hero 24px）、app-main 横向 padding |
| xl | 32px | 页面底部 padding |
| 2xl | 48px | 空状态区域垂直 padding |
| 3xl | 64px | 不使用（本阶段无需） |

例外：
- ECharts 图表容器高度固定 300px（非间距 token，为图表渲染区域）
- 部门下钻展开面板使用 `padding: 20px`（5 * 4px，保持 4 的倍数）

来源：现有 `index.css` 中 `.app-main { gap: 16px; padding: 20px 24px 32px; }` 和 `.metric-tile { padding: 16px 18px; }`。本契约中 18px 沿用现有不改动，新增组件严格使用 16px。

---

## 排版 / Typography

| 角色 | 尺寸 | 字重 | 行高 | 来源 |
|------|------|------|------|------|
| 正文 / Body | 13.5px | 400 (regular) | 1.5 | 现有 `.table-lite`、`.toolbar-input` |
| 标签 / Label | 12px | 500 (medium) | 1.5 | 现有 `.metric-label`、`.dashboard-signal-label` |
| 小标题 / Section Title | 15px | 600 (semibold) | 1.4 | 现有 `.section-title` |
| KPI 数值 / KPI Value | 26px | 600 (semibold) | 1.1 | 现有 `.metric-value` |

ECharts 内部排版规范：
- 坐标轴标签：12px，颜色 `#646A73`（--color-steel）
- 坐标轴名称：13px，颜色 `#646A73`
- 提示框标题：13px，颜色 `#1F2329`（--color-ink），weight 600
- 提示框正文：12px，颜色 `#646A73`
- 图例：12px，颜色 `#646A73`

---

## 色彩 / Color

| 角色 | 值 | 用途 |
|------|---|------|
| 主色调 60% / Dominant | `#F5F6F8`（--color-bg-page）| 页面背景 |
| 辅助色 30% / Secondary | `#FFFFFF`（--color-bg-surface）| 卡片、图表容器、表格背景 |
| 强调色 10% / Accent | `#1456F0`（--color-primary）| 见下方保留列表 |
| 破坏性 / Destructive | `#F53F3F`（--color-danger）| 仅用于错误状态文案 |

强调色保留元素（Accent reserved for）：
- 周期选择器 focus 边框
- "打开审批中心" 主按钮背景
- KPI 卡片中"待审批数"指标的数值颜色（当值 > 0 时使用 `--color-warning` `#FF7D00` 以示紧急）
- ECharts 图表中 AI 五级（最高等级）柱状图颜色
- 部门下钻展开按钮 hover 态

ECharts 图表色板（按 AI 等级从低到高）：

| AI 等级 | 中文标签 | 颜色 |
|---------|---------|------|
| Level 1 / AI 未入门 | 一级 | `#C9CDD4`（--color-border-strong）|
| Level 2 / AI 入门级 | 二级 | `#BAE6FD`（sky-200）|
| Level 3 / AI 应用级 | 三级 | `#38BDF8`（sky-400）|
| Level 4 / AI 专家级 | 四级 | `#1456F0`（--color-primary）|
| Level 5 / AI 大师级 | 五级 | `#00B42A`（--color-success）|

调薪幅度直方图：统一使用 `#1456F0`（--color-primary），alpha 从 0.4 到 1.0 按区间递增。

审批流水线状态色：

| 状态 | 颜色 |
|------|------|
| 草稿 draft | `#C9CDD4` |
| 已提交 submitted | `#38BDF8` |
| 经理审核中 manager_review | `#1456F0` |
| HR 审核中 hr_review | `#7C3AED`（purple-600）|
| 已批准 approved | `#00B42A` |
| 已拒绝 rejected | `#F53F3F` |

---

## 文案契约 / Copywriting Contract

| 元素 | 文案 |
|------|------|
| 页面标题 | 组织洞察看板 |
| 页面描述 | 围绕评估周期查看 AI 等级分布、调薪幅度、审批进度与部门洞察，帮助管理者快速定位重点。 |
| 主操作按钮 | 打开审批中心 |
| 周期选择器标签 | 查看周期 |
| 周期选择器默认项 | 全部可见周期 |
| 空状态标题 | 暂无看板数据 |
| 空状态正文 | 当前周期尚未产生评估或调薪记录。请先在工作台发起评估流程。 |
| 加载态文案 | 正在加载组织洞察看板... |
| 错误状态 | 加载看板数据失败，请检查网络连接后刷新页面重试。 |
| Redis 不可用错误 | 缓存服务暂时不可用，数据加载可能较慢。请联系管理员检查 Redis 服务状态。 |
| 部门下钻展开按钮 | 查看详情（展开时变为"收起"） |
| KPI 卡片 — 待审批 | 待审批 |
| KPI 卡片 — 员工统计 | 已评估 / 总人数 |
| KPI 卡片 — 平均调薪 | 平均调薪幅度 |
| KPI 卡片 — 等级概览 | AI 等级概览 |
| 图表标题 — AI 等级分布 | AI 等级分布 |
| 图表标题 — 调薪幅度 | 调薪幅度分布 |
| 图表标题 — 审批流水线 | 审批流水线状态 |
| 图表标题 — 部门洞察 | 部门洞察 |
| 图表无数据 | 当前周期暂无数据 |
| 轮询指示器（隐藏文本） | 每 30 秒自动刷新 |

破坏性操作：本阶段无破坏性操作（纯只读看板，无删除、修改功能）。

---

## 布局契约 / Layout Contract

### 整体结构（D-09 锁定决策）

```
+------------------------------------------------------+
| AppShell (侧栏 240px + 主内容区)                       |
+------------------------------------------------------+
| 页面标题 + 操作按钮                                     |
+------------------------------------------------------+
| 周期选择器工具栏 (全宽)                                 |
+------------------------------------------------------+
| KPI 卡片横排 (4 列网格, 1280px+ 响应)                   |
| [待审批] [已评估/总数] [平均调薪] [等级概览]              |
+------------------------------------------------------+
| 双列网格 (900px+ 响应)                                 |
| [AI 等级分布 ECharts]  | [调薪幅度分布 ECharts]        |
+------------------------------------------------------+
| 审批流水线状态 ECharts (全宽)                           |
+------------------------------------------------------+
| 部门洞察表格 (全宽, 可展开行下钻)                       |
|   > 展开: 部门级 AI 等级分布 + 调薪平均值 ECharts       |
+------------------------------------------------------+
```

### 响应式断点

| 断点 | 行为 |
|------|------|
| < 768px | KPI 卡片单列堆叠；图表单列堆叠 |
| 768px - 1279px | KPI 卡片 2 列；图表单列 |
| >= 1280px | KPI 卡片 4 列；图表双列（D-09） |

### 网格间距

- KPI 卡片网格 gap：12px（沿用现有 `.metric-strip`）
- 图表双列网格 gap：16px（沿用现有 `.dashboard-analysis-grid`）
- 各 section 之间 gap：16px（沿用 `.app-main { gap: 16px; }`）

---

## 组件清单 / Component Inventory

### 删除组件

| 组件 | 原因 |
|------|------|
| `DistributionChart.tsx` | D-02：全部替换为 ECharts |
| `HeatmapChart.tsx` | D-02：全部替换为 ECharts |

### 新增组件

| 组件 | 用途 | 关键 Props |
|------|------|-----------|
| `AILevelChart.tsx` | AI 等级分布柱状图（ECharts） | `data: { label: string; value: number; percentage: number }[]` |
| `SalaryDistChart.tsx` | 调薪幅度分布直方图（ECharts） | `data: { label: string; value: number }[]` |
| `ApprovalPipelineChart.tsx` | 审批流水线状态柱状图（ECharts） | `data: { label: string; value: number }[]` |
| `DepartmentDrilldown.tsx` | 部门下钻展开面板（含 2 个 ECharts 迷你图表） | `department: string; levelData: ...; avgAdjustment: number` |
| `KpiCards.tsx` | 4 个 KPI 指标卡片，待审批数 30 秒轮询 | `cycleId: string \| undefined` |
| `usePolling.ts`（hooks） | 可复用轮询 hook | `fetcher: () => Promise<T>; intervalMs: number` |

### 改造组件

| 组件 | 改动 |
|------|------|
| `DepartmentInsightTable.tsx` | 添加行展开/收起按钮，展开时渲染 `DepartmentDrilldown`（D-06） |
| `Dashboard.tsx` | 双列网格布局（D-09）、周期选择器（D-10）、替换所有旧图表为 ECharts 组件、移除 hero 区域的信号卡片（由 KpiCards 替代） |
| `OverviewCards.tsx` | 删除，功能由 `KpiCards.tsx` 替代（D-07：固定 4 个指标） |

---

## ECharts 视觉规范 / ECharts Visual Spec

### 通用配置

```typescript
// 所有 ECharts 组件共享的基础 option
const BASE_CHART_OPTION = {
  textStyle: {
    fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif',
    color: '#646A73',
  },
  tooltip: {
    trigger: 'axis' as const,
    backgroundColor: '#FFFFFF',
    borderColor: '#E0E4EA',
    borderWidth: 1,
    textStyle: { color: '#1F2329', fontSize: 13 },
    padding: [8, 12],
    extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.10);',
  },
  grid: {
    left: 16,
    right: 16,
    top: 24,
    bottom: 8,
    containLabel: true,
  },
};
```

### 柱状图（AI 等级分布、审批流水线）

- 柱体圆角：`borderRadius: [4, 4, 0, 0]`
- 柱体宽度：自适应（`barMaxWidth: 48`）
- Y 轴名称位置：`nameLocation: 'end'`，文案"人数"
- X 轴标签旋转：0 度（中文标签简短无需旋转）
- 无图例（单系列不需要图例）

### 直方图（调薪幅度分布）

- 柱体圆角：`borderRadius: [4, 4, 0, 0]`
- X 轴标签：区间标签（"0-5%"、"5-10%"、"10-15%"、"15-20%"、"20%+"）
- Y 轴名称："人数"
- 单色渐变：`#1456F0` alpha 递增

### 部门下钻迷你图表

- 容器高度：200px（比标准图表矮）
- grid padding 缩小：`{ left: 8, right: 8, top: 16, bottom: 4, containLabel: true }`
- 不显示图例

---

## 交互契约 / Interaction Contract

### 周期选择器（D-10）

- 位置：页面顶部工具栏区域
- 控件类型：`<select>` 下拉框（沿用现有 `.toolbar-input` 样式）
- 默认值：最新周期（优先 `published` 状态，其次 `collecting`，最后第一个）
- 切换行为：所有图表和 KPI 卡片联动刷新
- 加载态：切换时显示"正在加载组织洞察看板..."

### KPI 卡片轮询（D-07、D-08）

- 待审批数：每 30 秒静默轮询独立 API（`GET /dashboard/kpi-summary`）
- 轮询失败：静默忽略，下次重试（不弹 toast、不显示错误）
- 组件卸载时：`clearInterval` 清理定时器
- 其他 3 个指标：随页面初始加载和周期切换时刷新，不独立轮询

### 部门下钻（D-06）

- 触发：点击部门表格行的"查看详情"按钮
- 展开方式：当前行下方页内展开（不弹模态框，不跳转）
- 再次点击：收起展开区域
- 同时只能展开一个部门（点击其他部门自动收起前一个）
- 展开时异步加载该部门数据（`GET /dashboard/department-drilldown?department=xxx`）
- 加载态：展开区域内显示"加载中..."占位

### 权限可见性（D-11、D-12）

- admin/hrbp：看到全部部门数据
- manager：仅看到自己管理部门的数据（后端 AccessScopeService 过滤）
- employee：不显示看板导航入口（前端 roleAccess 配置）

---

## 状态契约 / State Contract

| 状态 | 视觉表现 |
|------|---------|
| 初始加载中 | 全页显示"正在加载组织洞察看板..."文案 |
| 加载成功 | 所有图表和卡片正常渲染 |
| 加载失败 | 错误消息卡片（`.surface` + `--color-danger` 文本） |
| 空数据 | 空状态区域（`.empty-state`），标题 + 正文 + 引导前往工作台 |
| 周期切换中 | 保留旧数据渲染，新数据到达后替换（避免闪烁） |
| 下钻加载中 | 展开区域内 "加载中..." 文本占位 |
| 轮询更新 | KPI 待审批数值静默替换，无动画 |

---

## 注册表安全 / Registry Safety

| 注册表 | 使用的包 | 安全门 |
|--------|---------|--------|
| npm (echarts) | echarts@6.0.0 | Apache 2.0 开源，npm 官方包，无需额外审查 |
| npm (echarts-for-react) | echarts-for-react@3.0.6 | MIT 开源，npm 官方包，无需额外审查 |
| shadcn official | 不适用 | 项目未使用 shadcn |

---

## 检查清单签署 / Checker Sign-Off

- [ ] 维度 1 文案 / Copywriting: PASS
- [ ] 维度 2 视觉 / Visuals: PASS
- [ ] 维度 3 色彩 / Color: PASS
- [ ] 维度 4 排版 / Typography: PASS
- [ ] 维度 5 间距 / Spacing: PASS
- [ ] 维度 6 注册表安全 / Registry Safety: PASS

**审批状态:** pending
