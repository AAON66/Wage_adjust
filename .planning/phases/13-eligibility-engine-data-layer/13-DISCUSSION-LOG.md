# Phase 13: Eligibility Engine & Data Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 13-eligibility-engine-data-layer
**Areas discussed:** 数据模型设计, 资格规则引擎, 数据导入通道, 缺失数据处理

---

## 数据模型设计

| Option | Description | Selected |
|--------|-------------|----------|
| 加到 Employee 模型 | hire_date、last_salary_date 直接加为 Employee 字段 | ✓ |
| 独立人事数据表 | 新建 EmployeeHRData 表与 Employee 1:1 关联 | |
| Claude 决定 | Claude 根据代码结构自行判断 | |

**User's choice:** 加到 Employee 模型
**Notes:** 查询简单，复用现有 employee 导入流程

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 PerformanceRecord 模型 | 每条记录 = 一个员工某年度绩效等级，支持多年历史 | ✓ |
| 加到 Employee 字段 | 只存当年绩效，不保留历史 | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 新建 PerformanceRecord 模型

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 SalaryAdjustmentRecord | 每次调薪一条记录（日期、类型、金额） | ✓ |
| 复用 SalaryRecommendation | 现有模型加 approved_at 字段 | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 新建 SalaryAdjustmentRecord

---

## 资格规则引擎

| Option | Description | Selected |
|--------|-------------|----------|
| 配置化 | 阈值放在配置文件或数据库，HR 可调整 | ✓ |
| 硬编码常量 | 写在引擎代码里作为常量 | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 配置化

| Option | Description | Selected |
|--------|-------------|----------|
| 实时计算不存储 | 每次查询时实时计算 4 条规则 | ✓ |
| 存到数据库 | 计算结果存为快照 | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 实时计算不存储

---

## 数据导入通道

| Option | Description | Selected |
|--------|-------------|----------|
| Excel + 手动录入优先 | 本阶段做 Excel 和手动，飞书延后 | |
| 三种全做 | Excel、飞书、手动录入全部实现 | ✓ |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 三种全做

| Option | Description | Selected |
|--------|-------------|----------|
| 分开两个模板 | 绩效模板和调薪历史模板分别导入 | ✓ |
| 合并一个模板 | 一个文件多个 Sheet | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 分开两个模板

---

## 缺失数据处理

| Option | Description | Selected |
|--------|-------------|----------|
| 缺失视为"待定" | 已有规则正常判定，缺失显示"数据缺失" | ✓ |
| 缺失视为"不合格" | 缺数据直接判不合格 | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 缺失视为"待定"

| Option | Description | Selected |
|--------|-------------|----------|
| 不需要，仅显示状态 | 列表中显示"数据缺失"即可 | ✓ |
| 需要催办通知 | 系统内或飞书提醒 HR 导入 | |
| Claude 决定 | Claude 自行判断 | |

**User's choice:** 不需要，仅显示状态

---

## Claude's Discretion

- Alembic 迁移脚本结构
- EligibilityEngine 内部方法拆分
- API 端点路径和返回结构
- 飞书同步具体字段映射

## Deferred Ideas

None
