# Phase 14: Eligibility Visibility & Overrides - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-04-03
**Phase:** 14-eligibility-visibility-overrides
**Areas discussed:** 资格列表页面设计, 特殊申请审批流程, 权限隔离实现方式, 前端页面入口

---

## 资格列表页面设计

| Option | Description | Selected |
|--------|-------------|----------|
| 部门 + 状态筛选 | 简洁实用 | |
| 多维度筛选 | 部门+状态+具体规则+岗位族+职级 | ✓ |
| Claude 决定 | | |

**User's choice:** 多维度筛选

| Option | Description | Selected |
|--------|-------------|----------|
| 不需要 | 后续再加 | |
| 需要 Excel 导出 | 筛选结果导出 | ✓ |
| Claude 决定 | | |

**User's choice:** 需要 Excel 导出

---

## 特殊申请审批流程

| Option | Description | Selected |
|--------|-------------|----------|
| 主管/HRBP | 为下属发起 | ✓ |
| 仅 HR/Admin | 只有 HR 可发起 | |

**User's choice:** 主管/HRBP

| Option | Description | Selected |
|--------|-------------|----------|
| 两级审批 | HRBP → Admin | ✓ |
| 单级 Admin | 只需 Admin 审批 | |

**User's choice:** 两级审批

| Option | Description | Selected |
|--------|-------------|----------|
| 理由 + 覆盖规则 | 文本理由 + 选择具体规则 | ✓ |
| 理由 + 规则 + 附件 | 额外支持证明材料 | |

**User's choice:** 理由 + 覆盖规则

---

## 权限隔离实现方式

| Option | Description | Selected |
|--------|-------------|----------|
| 后端不返回 + 前端不显示 | 双重保障 | ✓ |
| 仅前端隐藏 | 简单但不安全 | |

**User's choice:** 后端不返回 + 前端不显示

| Option | Description | Selected |
|--------|-------------|----------|
| 本部门员工 | 复用 AccessScopeService | ✓ |
| 下属员工 | 通过 manager_id | |

**User's choice:** 本部门员工

---

## 前端页面入口

| Option | Description | Selected |
|--------|-------------|----------|
| 运营管理组 | 与员工评估并列 | ✓ |
| 新建调薪管理组 | 专门分组 | |

**User's choice:** 运营管理组

| Option | Description | Selected |
|--------|-------------|----------|
| 同一页面分 Tab | 资格列表 + 特殊申请 | ✓ |
| 两个独立页面 | 分别独立 | |

**User's choice:** 同一页面分 Tab

---

## Claude's Discretion

- 特殊申请数据模型设计
- 资格列表分页策略和排序
- Excel 导出格式
- 前端组件拆分

## Deferred Ideas

None
