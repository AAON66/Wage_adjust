# Phase 17: Salary Display Simplification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 17-salary-display-simplification
**Areas discussed:** 摘要卡片内容, 展开/折叠交互, 资格徽章设计, 人工调整区域处理, 历史走势图处理, 无建议空状态, 维度明细展示格式

---

## 摘要卡片内容

| Option | Description | Selected |
|--------|-------------|----------|
| 三指标摘要（推荐） | 考勤概况 + 资格徽章 + AI 评分/等级 + 最终调薪比例，其余折叠 | ✓ |
| 四指标摘要 | 多加薪资对比（当前→建议），比三指标多一个卡片 | |
| 极简摘要 | 只保留资格徽章 + 最终调薪比例 | |

**User's choice:** 三指标摘要
**Notes:** 无

### 考勤卡片处理

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有卡片（推荐） | AttendanceKpiCard 直接保留，不做改动 | ✓ |
| 精简为单行摘要 | 只显示关键数字，需拆分或新建组件 | |
| Claude 决定 | 根据组件复杂度决定 | |

**User's choice:** 复用现有卡片

## 展开/折叠交互

| Option | Description | Selected |
|--------|-------------|----------|
| 单按钮全展开（推荐） | 一个按钮展开全部详情，简单直接 | ✓ |
| 分组手风琴 | 调薪计算/AI 维度/联动预览各自独立展开 | |
| Claude 决定 | 根据数据量决定 | |

**User's choice:** 单按钮全展开

## 资格徽章设计

| Option | Description | Selected |
|--------|-------------|----------|
| 彩色状态徽章（推荐） | 绿/红/黄三色，复用 status-pill 样式 | ✓ |
| 图标+文字标签 | 大图标（盾牌/警告/禁止）+ 文字 | |
| Claude 决定 | 根据设计系统决定 | |

**User's choice:** 彩色状态徽章

### 规则展开位置

| Option | Description | Selected |
|--------|-------------|----------|
| 徽章下方内联展开（推荐） | 点击后在徽章下方展开 4 条规则 | ✓ |
| 弹出气泡/Popover | 浮层显示规则明细 | |
| Claude 决定 | 根据页面空间决定 | |

**User's choice:** 徽章下方内联展开

## 人工调整区域处理

| Option | Description | Selected |
|--------|-------------|----------|
| 摘要层保留操作按钮（推荐） | 人工调整和审批按钮始终可见在摘要层底部 | ✓ |
| 详情层内部 | 必须展开详情才能操作 | |
| Claude 决定 | 根据布局复杂度决定 | |

**User's choice:** 摘要层保留操作按钮

## 历史走势图处理

| Option | Description | Selected |
|--------|-------------|----------|
| 移入详情层（推荐） | 走势图和历史明细折叠到详情层 | ✓ |
| 保留在摘要层底部 | 继续像现在一样总是可见 | |
| Claude 决定 | 根据页面长度决定 | |

**User's choice:** 移入详情层

## 无建议空状态

| Option | Description | Selected |
|--------|-------------|----------|
| 精简提示+生成按钮（推荐） | 提示文字 + 生成调薪建议按钮 | ✓ |
| 保持现有虚线框 | 沿用当前虚线框设计 | |
| Claude 决定 | 根据整体布局决定 | |

**User's choice:** 精简提示+生成按钮

## 维度明细展示格式

| Option | Description | Selected |
|--------|-------------|----------|
| 简单表格（推荐） | 一行一维度，维度名+得分+权重+加权分 | ✓ |
| 横向柱状图 | 5 条进度条可视化 | |
| Claude 决定 | 根据现有组件决定 | |

**User's choice:** 简单表格

## Claude's Discretion

- 展开/收起动画效果
- 摘要层卡片间距和排列
- 详情层内部区块排列顺序
- 资格徽章无数据时的占位展示

## Deferred Ideas

None
