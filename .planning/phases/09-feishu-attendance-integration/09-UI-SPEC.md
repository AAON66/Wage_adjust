---
phase: 9
slug: feishu-attendance-integration
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-29
---

# Phase 9 — UI 设计契约 / UI Design Contract

> 飞书考勤集成阶段的视觉与交互契约。由 gsd-ui-researcher 生成，由 gsd-ui-checker 验证。
> Visual and interaction contract for the Feishu Attendance Integration phase.

---

## 设计系统 / Design System

| 属性 | 值 |
|------|-----|
| 工具 | none（项目未使用 shadcn） |
| 预设 | 不适用 |
| 组件库 | 无第三方组件库；使用项目自建 CSS class 体系（`index.css` @layer components） |
| 图标库 | 无独立图标库；使用内联 SVG（与项目现有模式一致） |
| 字体 | "PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif（来源：`index.css :root`） |

---

## 间距规范 / Spacing Scale

沿用项目现有间距体系（基于 Tailwind 默认 4px 倍数 + `index.css` 自定义）：

| Token | 值 | 用途 |
|-------|-----|------|
| xs | 4px | 图标与文字间距、内联元素间距 |
| sm | 8px | 紧凑元素间距、metric-note margin-top |
| md | 12px | 卡片网格 gap、section-head gap |
| lg | 16px | 默认元素间距、app-main gap、卡片内 padding |
| xl | 20px | app-main 顶部 padding |
| 2xl | 24px | section padding、dashboard-hero padding |
| 3xl | 32px | app-main 底部 padding |
| 4xl | 40px | empty-state 上下 padding |

例外：考勤 KPI 卡片内部使用 `18px` padding（复用 `metric-tile` 的 `padding: 16px 18px`）。

---

## 排版规范 / Typography

沿用项目已有排版层级（来源：`index.css` @layer components）：

| 角色 | 尺寸 | 字重 | 行高 | CSS class |
|------|------|------|------|-----------|
| 正文 / Body | 13.5px | 400 (normal) | 1.5 | `table-lite td`、`toolbar-input` |
| 标签 / Label | 12px | 500 (medium) | 1.5 | `metric-label`、`metric-note` |
| 小标题 / Section Title | 15px | 600 (semibold) | 1.4 | `section-title` |
| 页面标题 / Page Title | 20px | 600 (semibold) | 1.3 | `page-title` |

本阶段新增元素的排版规则：

| 元素 | 尺寸 | 字重 | 行高 |
|------|------|------|------|
| 考勤 KPI 数值 | 26px | 600 | 1.1 |
| 考勤 KPI 标签 | 12px | 500 | 1.5 |
| 时间戳标注 | 12px | 400 | 1.5 |
| 同步状态文本 | 13.5px | 500 | 1.5 |
| 表单字段标签 | 13.5px | 500 | 1.4 |
| 表单帮助文本 | 12px | 400 | 1.6 |

---

## 颜色契约 / Color Contract

沿用项目已有 CSS 变量体系（来源：`index.css :root`）：

| 角色 | 值 | 用途 |
|------|-----|------|
| 主要表面 (60%) | `#F5F6F8` (`--color-bg-page`) | 页面背景 |
| 次要表面 (30%) | `#FFFFFF` (`--color-bg-surface`) | 卡片、表单、表格背景 |
| 强调色 (10%) | `#1456F0` (`--color-primary`) | 仅用于：同步按钮、配置保存按钮、活跃导航项、eyebrow 标签、focus ring |
| 危险色 | `#F53F3F` (`--color-danger`) | 仅用于：同步失败状态标记、错误消息文本 |

本阶段新增语义色用途：

| 语义 | 变量 | 用于本阶段的元素 |
|------|------|-----------------|
| 成功 | `--color-success` / `#00B42A` | 同步成功状态 pill |
| 成功背景 | `--color-success-bg` / `#E8FFEA` | 同步成功状态 pill 背景 |
| 警告 | `--color-warning` / `#FF7D00` | 数据过期提醒（超过 24 小时未同步） |
| 警告背景 | `--color-warning-bg` / `#FFF3E8` | 数据过期提醒背景 |
| 危险 | `--color-danger` / `#F53F3F` | 同步失败状态 pill |
| 危险背景 | `--color-danger-bg` / `#FFECE8` | 同步失败状态 pill 背景 |
| 信息 | `--color-info` / `#1456F0` | 同步进行中状态 pill |
| 信息背景 | `--color-info-bg` / `#EBF0FE` | 同步进行中状态 pill 背景 |

强调色保留列表：同步按钮（`action-primary`）、飞书配置保存按钮（`action-primary`）、侧边栏活跃导航（`nav-link-active`）、eyebrow 文字。

---

## 组件清单 / Component Inventory

### 新页面

| 页面 | 路径 | 权限 | 布局 |
|------|------|------|------|
| 考勤管理 AttendanceManagement | `/attendance` | admin, hrbp | AppShell + eyebrow + page-title + 三区布局 |
| 飞书配置 FeishuConfig | `/feishu-config` | admin | AppShell + eyebrow + page-title + 单页表单 |

### 新组件

| 组件 | 路径 | 复用位置 | 描述 |
|------|------|----------|------|
| AttendanceKpiCard | `components/attendance/AttendanceKpiCard.tsx` | 考勤管理页 + SalarySimulator 内嵌 | 单员工考勤 KPI 卡片，展示 5 项指标 + 时间戳 |
| SyncStatusCard | `components/attendance/SyncStatusCard.tsx` | 考勤管理页顶部 | 同步状态 + 上次同步时间 + 记录数 + 手动同步按钮 |
| FieldMappingTable | `components/attendance/FieldMappingTable.tsx` | 飞书配置页 | 双列字段映射表（飞书字段名 - 系统字段名） |

### 组件交互规格

#### AttendanceKpiCard

```
+-----------------------------------------------+
| [eyebrow] 考勤概览                              |
| +---------+ +---------+ +---------+            |
| | 出勤率  | | 缺勤天数 | | 加班时长 |            |
| | 95.2%   | | 3 天    | | 24.5 h  |            |
| +---------+ +---------+ +---------+            |
| +---------+ +---------+                        |
| | 迟到次数 | | 早退次数 |                        |
| | 2 次    | | 0 次    |                        |
| +---------+ +---------+                        |
| 数据截至：2026-03-28 06:00                      |
+-----------------------------------------------+
```

- 使用 `surface` class 作为外层容器
- KPI 指标使用 `metric-tile` 布局模式
- 数值使用 `metric-value` 样式（26px / 600 weight）
- 标签使用 `metric-label` 样式（12px / 500 weight）
- 时间戳标注使用 `metric-note` 样式（12px / `--color-placeholder`）
- 无数据时展示 `--`（不是 0）
- 响应式：>=768px 3 列，<768px 2 列

#### SyncStatusCard

```
+-----------------------------------------------------+
| 同步状态                                              |
| 上次同步：2026-03-28 06:00 | [成功] 同步 326 条记录    |
| [增量同步]  [全量同步]                                 |
+-----------------------------------------------------+
```

- 使用 `surface` class 作为外层容器
- 同步状态使用 `status-pill` class + 语义色
- 状态值枚举：`成功`（success）、`进行中`（info）、`失败`（danger）、`未配置`（placeholder 灰色）
- 「增量同步」使用 `action-primary` class
- 「全量同步」使用 `action-secondary` class
- 按钮在同步进行中状态禁用（`disabled`），文案变为「同步中...」
- 同步进行中按钮显示旋转 spinner（CSS animation）

#### FieldMappingTable

```
+--------------------------------------------------+
| 字段映射                                           |
| +-----------------------+-----------------------+ |
| | 飞书字段名            | 系统字段               | |
| +-----------------------+-----------------------+ |
| | [输入框: 工号]        | employee_no (关联键)   | |
| | [输入框: 出勤率]       | attendance_rate       | |
| | [输入框: 缺勤天数]     | absence_days          | |
| | [输入框: 加班时长]     | overtime_hours         | |
| | [输入框: 迟到次数]     | late_count            | |
| | [输入框: 早退次数]     | early_leave_count     | |
| +-----------------------+-----------------------+ |
+--------------------------------------------------+
```

- 使用 `table-shell` + `table-lite` 样式
- 左列为 `toolbar-input` 可编辑输入框
- 右列为只读文本（系统固定字段名），使用 `--color-steel` 色
- `employee_no` 行标注 `(关联键)` 后缀，使用 `--color-primary` 色

### 页面布局规格

#### 考勤管理页 AttendanceManagement

```
AppShell
+-- eyebrow: "ATTENDANCE"
+-- page-title: "考勤管理"
+-- page-desc: "查看员工考勤数据，手动或定时从飞书同步最新记录。"
+-- section 1: SyncStatusCard（全宽）
+-- section 2: 工具栏
|   +-- toolbar-input 搜索框（按姓名/工号搜索）
|   +-- chip-button 筛选器（部门）
|   +-- action-secondary 飞书配置（仅 admin 可见）
+-- section 3: 员工考勤卡片网格
|   +-- 响应式 grid：>=1280px 4 列，>=768px 2 列，<768px 1 列
|   +-- 每张卡片 = AttendanceKpiCard（附带员工姓名 + 工号标题行）
|   +-- 空状态（见 Copywriting）
+-- section 4: 分页（offset/limit，复用现有分页样式）
```

#### 飞书配置页 FeishuConfig

```
AppShell
+-- eyebrow: "SETTINGS"
+-- page-title: "飞书考勤配置"
+-- page-desc: "配置飞书应用凭证和字段映射，系统将据此从飞书多维表格同步考勤数据。"
+-- surface 容器
|   +-- section-head: "连接配置"
|   +-- 表单字段（垂直堆叠，间距 16px）：
|   |   +-- App ID [toolbar-input, 全宽]
|   |   +-- App Secret [toolbar-input, type=password, 全宽]
|   |   +-- 多维表格 App Token [toolbar-input, 全宽]
|   |   +-- 多维表格 Table ID [toolbar-input, 全宽]
|   |   +-- 定时同步时间 [两个 toolbar-input 并排: 时 + 分]
|   +-- divider
|   +-- section-head: "字段映射"
|   +-- FieldMappingTable
|   +-- 底部按钮栏（右对齐，间距 8px）：
|   |   +-- [action-secondary] 测试连接
|   |   +-- [action-primary] 保存配置
```

#### SalarySimulator 内嵌考勤概览（ATT-05）

在 `SalarySimulator.tsx` 的员工详情区域，当选中某位员工时，在调薪卡片下方插入 `AttendanceKpiCard` 组件。

- 如果该员工无考勤数据，不显示该区域（不展示空卡片）
- 组件通过 `employee_id` 从 `GET /api/v1/attendance/{employee_id}` 获取数据

---

## 文案契约 / Copywriting Contract

| 元素 | 中文文案 |
|------|---------|
| **考勤管理页 CTA（增量同步）** | 增量同步 |
| **考勤管理页 CTA（全量同步）** | 全量同步 |
| **飞书配置页 CTA** | 保存配置 |
| **飞书配置页次要 CTA** | 测试连接 |
| **考勤管理页空状态标题** | 暂无考勤数据 |
| **考勤管理页空状态正文** | 请先完成飞书配置，然后点击「增量同步」或「全量同步」拉取考勤记录。 |
| **飞书未配置空状态标题** | 飞书考勤未配置 |
| **飞书未配置空状态正文** | 请前往飞书配置页面填写应用凭证和字段映射。 |
| **飞书未配置空状态链接** | 前往配置 |
| **同步成功提示** | 同步完成，共更新 {n} 条记录。 |
| **同步失败提示** | 同步失败：{error_message}。系统将自动重试，如持续失败请检查飞书配置。 |
| **同步进行中提示** | 正在从飞书同步考勤数据... |
| **测试连接成功** | 连接成功，已验证飞书应用凭证有效。 |
| **测试连接失败** | 连接失败：{error_message}。请检查 App ID 和 App Secret 是否正确。 |
| **时间戳标注** | 数据截至：{YYYY-MM-DD HH:mm} |
| **数据过期警告** | 考勤数据已超过 24 小时未更新，建议手动同步。 |
| **未匹配工号提示** | 本次同步有 {n} 条记录因工号不匹配被跳过。 |
| **并发同步拒绝** | 同步任务正在进行中，请稍后再试。 |
| **飞书配置权限提示** | 仅管理员可修改飞书配置。 |

### 破坏性操作

| 操作 | 确认文案 | 确认方式 |
|------|---------|---------|
| 全量同步 | 全量同步将拉取飞书表格中的全部数据并覆盖现有记录，确定执行？ | 浏览器 `window.confirm()` 弹窗 |

---

## 交互状态 / Interaction States

### 同步按钮状态机

```
[空闲] --点击增量同步--> [同步中] --成功--> [空闲 + 成功 toast]
                                  --失败--> [空闲 + 失败 toast]
[空闲] --点击全量同步--> [确认弹窗] --确认--> [同步中]
                                   --取消--> [空闲]
[同步中] --再次点击--> [按钮 disabled, 无响应]
```

### SyncStatusCard 状态枚举

| 状态 | pill 样式 | 文案 | 附加信息 |
|------|----------|------|---------|
| 未配置 | `bg: --color-bg-subtle`, `color: --color-placeholder` | 未配置 | 显示配置入口链接 |
| 同步中 | `bg: --color-info-bg`, `color: --color-info` | 同步中 | 显示 spinner |
| 成功 | `bg: --color-success-bg`, `color: --color-success` | 成功 | 显示记录数 + 时间 |
| 失败 | `bg: --color-danger-bg`, `color: --color-danger` | 失败 | 显示错误摘要 + 时间 |

### 飞书配置表单验证

| 字段 | 验证规则 | 错误提示 |
|------|---------|---------|
| App ID | 必填 | 请输入飞书 App ID |
| App Secret | 必填 | 请输入飞书 App Secret |
| 多维表格 App Token | 必填 | 请输入多维表格 App Token |
| 多维表格 Table ID | 必填 | 请输入多维表格 Table ID |
| 定时同步 - 时 | 0-23 整数 | 请输入 0~23 之间的整数 |
| 定时同步 - 分 | 0-59 整数 | 请输入 0~59 之间的整数 |
| 字段映射 - employee_no | 必填 | 员工工号映射为必填项 |

验证时机：点击「保存配置」时统一校验，错误字段下方显示红色提示文本（13px, `--color-danger`）。

### 考勤 KPI 卡片数据状态

| 状态 | 展示 |
|------|------|
| 正常加载 | 5 项 KPI 数值 + 时间戳 |
| 加载中 | 5 个 metric-tile 显示 `--` 占位 |
| 无数据 | 整个 AttendanceKpiCard 不渲染（在 SalarySimulator 中）；在考勤管理页显示空状态 |
| 数据过期（>24h） | KPI 正常展示，时间戳行使用 `--color-warning` 色并附加过期警告文案 |

---

## 注册表安全 / Registry Safety

| 注册表 | 使用的组件 | 安全门 |
|--------|-----------|--------|
| 不适用 | 不适用 | 项目未使用 shadcn 或第三方组件注册表 |

---

## 可访问性要点 / Accessibility Notes

- 所有表单输入框必须关联 `<label>` 元素（`htmlFor` + `id`）
- 同步按钮在 disabled 状态设置 `aria-disabled="true"`
- SyncStatusCard 的状态变化使用 `aria-live="polite"` 区域通知屏幕阅读器
- 考勤 KPI 数值使用 `aria-label` 标注完整含义（如 `aria-label="出勤率 95.2%"`）
- 颜色对比度：所有文本颜色与背景的对比度符合 WCAG 2.1 AA（4.5:1）
- focus-visible 样式复用现有 `2px solid var(--color-primary)` outline

---

## 审核签章 / Checker Sign-Off

- [ ] 维度 1 文案 / Copywriting: PASS
- [ ] 维度 2 视觉 / Visuals: PASS
- [ ] 维度 3 颜色 / Color: PASS
- [ ] 维度 4 排版 / Typography: PASS
- [ ] 维度 5 间距 / Spacing: PASS
- [ ] 维度 6 注册表安全 / Registry Safety: PASS

**审批状态:** pending
