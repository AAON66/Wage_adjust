# Phase 20: 员工所属公司字段 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09T03:15:20Z
**Phase:** 20-员工所属公司字段
**Areas discussed:** 公司字段规则, 手动维护入口, 详情页展示位置, 导入覆盖语义

---

## 公司字段规则

| Option | Description | Selected |
|--------|-------------|----------|
| A | 可选自由文本，允许为空，保存前去首尾空格 | ✓ |
| B | 必填自由文本，每个员工都必须有所属公司 | |
| C | 下拉/预设公司列表 | |

**User's choice:** 全部按推荐（1A）
**Notes:** 用户接受推荐项，保持字段轻量，不在本阶段引入公司主数据或下拉枚举。

---

## 手动维护入口

| Option | Description | Selected |
|--------|-------------|----------|
| A | 只在管理端员工编辑表单里增加“所属公司”，右侧档案列表不显示 | ✓ |
| B | 编辑表单增加，同时右侧档案列表也显示公司 | |
| C | 不给手动编辑，只允许导入写入 | |

**User's choice:** 全部按推荐（2A）
**Notes:** 管理端需要支持手动设置/修改，但可见性仍然收敛，避免把公司信息扩散到员工档案列表。

---

## 详情页展示位置

| Option | Description | Selected |
|--------|-------------|----------|
| A | 放在 `/employees/:employeeId` 顶部资料卡区域，和“部门/岗位族/岗位级别”同级展示 | ✓ |
| B | 放在员工编号下面，作为一行次级文本 | |
| C | 单独新增一个“员工档案信息”区块 | |

**User's choice:** 全部按推荐（3A）
**Notes:** “档案详情页”已明确对应现有 `/employees/:employeeId` 页面，不新增独立详情页结构。

---

## 导入覆盖语义

| Option | Description | Selected |
|--------|-------------|----------|
| A | `company` 列存在时：有值就更新，空白就清空；列不存在时保持原值 | ✓ |
| B | `company` 列存在但为空时：保留原值，不清空 | |
| C | 导入模板把 `company` 作为必填列 | |

**User's choice:** 全部按推荐（4A）
**Notes:** 继续沿用现有员工导入 upsert 思路，显式列值优先，空白允许清空，可选列缺失则不触碰旧值。

---

## the agent's Discretion

- 详情卡片中 `company` 与现有卡片/周期选择器的最终排版
- 表单占位提示文案
- 迁移文件命名和 revision id
- 共享 employee read contract 是否直接携带 `company`，前提是列表页不渲染

## Deferred Ideas

None
