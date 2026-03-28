---
phase: 6
slug: batch-import-reliability
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-28
---

# Phase 6 -- UI 设计契约 / UI Design Contract

> 批量导入可靠性阶段的视觉与交互契约。由 gsd-ui-researcher 生成，gsd-ui-checker 验证。
> Visual and interaction contract for the batch import reliability phase.

---

## 设计系统 / Design System

| 属性 | 值 |
|------|-----|
| 工具 | none (自定义 CSS + Tailwind utilities) |
| 预设 | 不适用 |
| 组件库 | 无第三方组件库；使用项目自定义 CSS 类（`surface`, `table-shell`, `action-primary` 等） |
| 图标库 | 无（当前项目未使用图标库；本阶段不新增） |
| 字体 | "PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif |

**来源：** `frontend/src/index.css` `:root` 声明、`frontend/tailwind.config.js`

---

## 间距规范 / Spacing Scale

沿用项目已有间距体系（基于 Tailwind 默认 4px 基数）：

| Token | 值 | 用途 |
|-------|-----|------|
| xs | 4px | 图标间隔、行内微距 |
| sm | 8px | 紧凑元素间距、按钮组 gap |
| md | 12px | metric-strip gap、section-head gap |
| lg | 16px | 卡片内边距、app-main gap、section-head margin-bottom |
| xl | 20px | app-main 水平 padding、表格 section-head padding |
| 2xl | 24px | app-main 侧边距、section 大间距 |
| 3xl | 32px | app-main 底部 padding |

例外：
- `metric-tile` 使用 `16px 18px` padding（沿用现有）
- `table-lite th` 使用 `9px 14px` padding（沿用现有）
- `table-lite td` 使用 `11px 14px` padding（沿用现有）

**来源：** `frontend/src/index.css` 中 `.app-main`, `.metric-tile`, `.table-lite` 等已有定义

---

## 排版 / Typography

沿用项目已建立的排版体系：

| 角色 | 尺寸 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| 正文 Body | 13.5px | 400 | 1.5 | 表格单元格、表单文字、描述文案 |
| 标签 Label | 12px | 500 | 1.5 | metric-label、表格表头、辅助说明 |
| 区域标题 Section Title | 15px | 600 | 1.4 | 卡片区域标题（如"批量导入记录"） |
| 页面标题 Page Title | 20px | 600 | 1.3 | AppShell 页面主标题 |

附加角色（仅本阶段新增组件使用）：
- **eyebrow**：11px / 600 / uppercase / letter-spacing 0.10em / `--color-primary`
- **metric-value**：26px / 600 / letter-spacing -0.02em / 仅用于汇总统计数字

**来源：** `frontend/src/index.css` 中 `.page-title`, `.section-title`, `.table-lite`, `.eyebrow`, `.metric-value`

---

## 颜色 / Color

沿用项目已有 CSS 自定义属性色板：

| 角色 | 值 | 用途 |
|------|-----|------|
| 主色面 Dominant (60%) | `#F5F6F8` (`--color-bg-page`) | 页面背景 |
| 辅助色面 Secondary (30%) | `#FFFFFF` (`--color-bg-surface`) | 卡片、表格、面板背景 |
| 主题色 Accent (10%) | `#1456F0` (`--color-primary`) | 见下方"主题色使用范围" |
| 危险色 Destructive | `#F53F3F` (`--color-danger`) | 失败行数字、错误提示文字、删除按钮 |

**主题色使用范围（本阶段）：**
- "开始导入" 主操作按钮背景色
- "下载模板" 操作的 eyebrow 标签文字色
- 表格聚焦态边框
- 导入成功时的标题高亮（不适用——成功用 `--color-success`）

**语义色（本阶段新增交互需使用）：**

| 语义 | 值 | 背景色 | 边框色 | 用途 |
|------|-----|--------|--------|------|
| 成功 | `#00B42A` | `#E8FFEA` | `#AFF0B5` | 成功行数、导入完成提示 |
| 警告 | `#FF7D00` | `#FFF3E8` | `#FFD8A8` | 处理中状态、部分成功提示横幅 |
| 危险 | `#F53F3F` | `#FFECE8` | `#FFCDD0` | 失败行数、错误行表格高亮、行数超限提示 |
| 信息 | `#1456F0` | `#EBF0FE` | -- | 模板下载提示 |

**来源：** `frontend/src/index.css` `:root` CSS 自定义属性

---

## 组件清单 / Component Inventory

### 已有组件（复用，无需新建）

| 组件 | 文件 | 本阶段用途 |
|------|------|-----------|
| `AppShell` | `components/layout/AppShell.tsx` | 页面布局容器 |
| `ImportJobTable` | `components/import/ImportJobTable.tsx` | 导入任务列表（需扩展） |

### 需要扩展的组件

#### `ImportJobTable` 扩展

当前组件已有：文件名、类型、状态、总行数、成功数、失败数、导出报告按钮。

新增需求：
- 当 `failedRows > 0` 时，"导出报告" 按钮文案改为 "下载错误报告"，并添加导出 xlsx 格式的能力
- 状态列新增 `partial`（部分成功）状态展示，使用 `--color-warning` / `--color-warning-bg` 样式

#### `ImportCenter.tsx` 页面扩展

新增以下 UI 区域：

### 需要新建的组件 / 区域

#### 1. 导入结果面板 `ImportResultPanel`

**位置：** 导入操作完成后，在"创建导入任务"区域下方展示
**触发条件：** `createImportJob` 返回响应后（无论成功或部分失败）

**布局结构：**
```
+--------------------------------------------------+
| [eyebrow] 导入结果                                 |
| [section-title] 本次导入完成                        |
|                                                    |
| +----------+ +----------+ +----------+             |
| | 总行数    | | 成功     | | 失败     |             |
| | 100      | | 90       | | 10       |             |
| +----------+ +----------+ +----------+             |
|                                                    |
| [部分成功提示横幅 — 仅当 failed > 0 时显示]          |
|                                                    |
| [错误行表格 — 仅当 failed > 0 时显示]               |
|                                         [下载错误报告] |
+--------------------------------------------------+
```

**汇总统计卡片样式：**
- 使用 3 列 `metric-strip` 布局
- "总行数" 卡片：`metric-value` 使用 `--color-ink`
- "成功" 卡片：`metric-value` 使用 `--color-success`
- "失败" 卡片：`metric-value` 使用 `--color-danger`

**部分成功提示横幅：**
- 仅当 `failedRows > 0 && successRows > 0` 时展示
- 背景 `--color-warning-bg`，边框 `1px solid --color-warning-border`，圆角 8px
- 文案见"文案契约"章节
- padding: `12px 16px`

**全部失败提示横幅：**
- 仅当 `failedRows > 0 && successRows === 0` 时展示
- 背景 `--color-danger-bg`，边框 `1px solid --color-danger-border`，圆角 8px
- 文案见"文案契约"章节

#### 2. 错误行表格 `ImportErrorTable`

**位置：** `ImportResultPanel` 内部，部分成功提示横幅下方
**触发条件：** 仅当 `failedRows > 0`

**表格结构：**

| 列 | 宽度 | 对齐 | 说明 |
|----|------|------|------|
| 行号 | 80px | 居中 | 原始 Excel/CSV 中的行号（从 1 开始，不含表头行） |
| 状态 | 80px | 居中 | `status-pill`，失败行使用 `--color-danger` / `--color-danger-bg` |
| 错误字段 | 120px | 左对齐 | 导致失败的具体字段名（如"身份证号"），无则显示 "--" |
| 错误原因 | 自适应 | 左对齐 | 具体错误描述 |

**样式：**
- 使用 `table-shell` + `table-lite` 已有样式
- 仅展示失败行（不展示成功行），减少信息噪声
- 最多展示前 50 行错误，超过 50 行时在表格底部显示提示："还有 N 条错误未显示，请下载完整错误报告查看。"
- 截断提示样式：`padding: 12px 14px`，`font-size: 13px`，`color: --color-steel`，`text-align: center`，`background: --color-bg-subtle`

#### 3. 模板下载区域改造

当前状态：metric-strip 中的"员工模板 CSV"和"认证模板 CSV"仅支持 CSV。

改造为：
- metric-tile 内的 `metric-value` 改为同时展示 "Excel" 和 "CSV"（两种格式）
- 每个 metric-tile 底部添加两个并排的 `chip-button`："下载 Excel" 和 "下载 CSV"
- chip-button gap: 8px

#### 4. 行数超限提示

**触发条件：** 后端返回包含"5000 行"相关错误信息时
**展示位置：** 与普通错误提示相同位置（页面顶部 `errorMessage` 区域）
**样式：** 沿用现有 `surface px-5 py-4 text-sm` + `color: var(--color-danger)` 样式

#### 5. 导入中加载状态

**触发条件：** `isUploading === true`
**展示方式：**
- "开始导入" 按钮变为 disabled 状态，文案改为 "导入中..."
- 按钮上方或旁边无需添加进度条（同步处理，无进度数据）
- 已有实现满足需求，无需改动

---

## 交互流程 / Interaction Flow

### 完整导入流程

```
1. 用户选择导入类型（员工/认证）
2. 用户选择文件（.csv / .xlsx / .xls）
3. 用户点击"开始导入"
   -> 按钮变为"导入中..." + disabled
   -> 文件上传区域不可操作
4a. 全部成功（HTTP 201）：
   -> ImportResultPanel 展示汇总统计（全绿）
   -> 无错误表格
   -> 刷新 ImportJobTable
4b. 部分成功（HTTP 207, failed > 0, success > 0）：
   -> ImportResultPanel 展示汇总统计
   -> 展示部分成功提示横幅（橙色）
   -> 展示错误行表格
   -> 展示"下载错误报告"按钮
   -> 刷新 ImportJobTable
4c. 全部失败（HTTP 207, success === 0）：
   -> ImportResultPanel 展示汇总统计（全红）
   -> 展示全部失败提示横幅（红色）
   -> 展示错误行表格
   -> 展示"下载错误报告"按钮
   -> 刷新 ImportJobTable
4d. 请求失败（HTTP 4xx/5xx）：
   -> 顶部 errorMessage 展示错误详情
   -> 不展示 ImportResultPanel
```

### 模板下载流程

```
1. 用户点击"下载 Excel"或"下载 CSV"
   -> 浏览器直接下载对应格式文件
   -> 文件名：{import_type}_template.xlsx 或 {import_type}_template.csv
```

### 错误报告下载流程

```
1. 用户在 ImportResultPanel 中点击"下载错误报告"
   -> 浏览器下载 xlsx 格式的错误报告
   -> 文件名：{import_type}_{job_id}_report.xlsx
2. 或在 ImportJobTable 中点击"导出报告"
   -> 同上
```

---

## 文案契约 / Copywriting Contract

| 元素 | 中文文案 |
|------|---------|
| 主操作按钮（CTA） | 开始导入 |
| 主操作按钮（加载态） | 导入中... |
| 页面标题 | 批量导入中心 |
| 页面描述 | 下载模板、导入文件、查看结果。 |
| 空状态标题 | 暂无导入记录 |
| 空状态正文 | 请先下载导入模板，按要求填写数据后上传文件开始导入。 |
| 全部成功提示 | 导入完成，{success_count} 条记录全部成功。 |
| 部分成功提示横幅 | 导入已完成，共 {total} 条记录：{success_count} 条成功，{failure_count} 条失败。请查看下方错误明细或下载错误报告。 |
| 全部失败提示横幅 | 导入失败，{total} 条记录全部未通过校验。请检查文件格式是否与模板一致，修正后重新导入。 |
| 行数超限错误 | 单次导入不能超过 5000 行，请分批导入。 |
| 文件未选择错误 | 请先选择需要上传的文件。 |
| 网络/服务器错误 | 导入操作失败，请稍后重试。如问题持续，请联系管理员。 |
| 错误表格截断提示 | 还有 {remaining} 条错误未显示，请下载完整错误报告查看。 |
| 下载错误报告按钮 | 下载错误报告 |
| 下载 Excel 模板按钮 | 下载 Excel |
| 下载 CSV 模板按钮 | 下载 CSV |
| 导出报告按钮（任务列表） | 导出报告 |
| 无失败行时的结果面板关闭提示 | （不展示关闭按钮，面板在下次导入时自动替换） |

### 破坏性操作

本阶段无破坏性操作。导入是追加/更新操作（upsert），不删除现有数据。"删除所选"功能已存在于 ImportJobTable 但本阶段不涉及改动。

---

## 响应式行为 / Responsive Behavior

| 断点 | 布局变化 |
|------|---------|
| < 768px | 汇总统计卡片单列堆叠；错误表格横向滚动 |
| 768px - 1279px | 汇总统计卡片 2 列；表格正常宽度 |
| >= 1280px | 汇总统计卡片 3 列（总行数/成功/失败）；表格正常宽度 |

模板下载区域的 metric-strip 保持现有响应式行为（4 列 -> 2 列 -> 1 列）。

---

## 可访问性 / Accessibility

- 所有按钮使用语义化 `<button>` 元素，disabled 态使用 `disabled` 属性
- 表格使用语义化 `<table>` / `<thead>` / `<tbody>` 结构
- 错误提示横幅使用 `role="alert"` 属性，确保屏幕阅读器即时播报
- 文件输入使用 `<label>` 关联
- 颜色不作为传达信息的唯一方式——状态同时使用文字标签（"成功"/"失败"）
- 焦点可见态沿用项目全局 `:focus-visible` 样式（`2px solid --color-primary`，offset 2px）

---

## 注册表安全 / Registry Safety

| 注册表 | 使用的组件 | 安全门 |
|--------|-----------|--------|
| 不适用 | 无第三方注册表 | 不适用 |

本项目未使用 shadcn 或任何第三方组件注册表。所有 UI 组件均为项目内部自定义。

---

## 检查清单 / Checker Sign-Off

- [ ] 维度 1 文案：PASS
- [ ] 维度 2 视觉：PASS
- [ ] 维度 3 颜色：PASS
- [ ] 维度 4 排版：PASS
- [ ] 维度 5 间距：PASS
- [ ] 维度 6 注册表安全：PASS

**审批状态：** pending
