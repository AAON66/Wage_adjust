# Phase 3: 审批流程正确性 - 讨论记录 / Discussion Log

> **仅供审计参考。** 不作为规划、研究或执行代理的输入。
> 决策记录在 CONTEXT.md 中 — 本日志保留讨论过程中考虑的备选方案。
>
> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**日期 / Date:** 2026-03-27
**阶段 / Phase:** 03-approval-workflow-correctness
**讨论区域 / Areas discussed:** 并发安全策略, 历史保留与重新提交, 审批队列视图, 审批步骤配置化, 审计日志可见性, 邮件/通知触发

---

## 并发安全策略 / Concurrency Safety

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 静默拒绝 + 提示刷新 | 第二个人看到"已被处理"提示，请刷新页面 | ✓ |
| 乐观锁 + 重试 | 返回 409 Conflict，前端自动重新加载 | |
| Claude 决定 | Claude 自行判断最佳方案 | |

**用户选择 / User's choice:** 静默拒绝 + 提示刷新

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 5 秒超时 | 等待最多 5 秒，超时返回 409 | ✓ |
| 无超时等待 | 一直等到前一个事务释放 | |
| Claude 决定 | Claude 自行判断 | |

**用户选择 / User's choice:** 5 秒超时

---

## 历史保留与重新提交 / History Preservation

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 时间线折叠 | 按 generation 分组，默认折叠旧轮次 | ✓ |
| 平铺显示 | 所有轮次全部平铺展示 | |
| Claude 决定 | Claude 自行判断 | |

**用户选择 / User's choice:** 时间线折叠

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 必填 | 驳回时必须填写原因 | ✓ |
| 可选 | 驳回原因可以留空 | |
| Claude 决定 | Claude 自行判断 | |

**用户选择 / User's choice:** 必填

---

## 审批队列视图 / Approval Queue View

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 按紧急度 | 等待时间最长的排在前面 | ✓ |
| 按提交时间 | 最新提交的排在前面 | |
| 按部门分组 | 先按部门分组，组内按时间排序 | |

**用户选择 / User's choice:** 按紧急度

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 表格对比 | 跨部门调薪比例并排显示，支持排序和筛选 | ✓ |
| 卡片布局 | 每个部门一张卡片，显示汇总统计 | ✓ |
| Claude 决定 | Claude 自行判断 | |

**用户选择 / User's choice:** 都做出来（表格 + 卡片两种模式）

---

## 审批步骤配置化 / Approval Step Configuration

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 可配置 | 管理员可配置审批链，不同部门可不同 | ✓ |
| 固定流程 | 统一主管→HR 两步审批 | |
| Claude 决定 | Claude 自行判断 | |

**用户选择 / User's choice:** 可配置

---

## 审计日志可见性 / Audit Log Visibility

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 仅 Admin | 只有系统管理员可查看 | ✓ |
| Admin + HR/HRBP | HR 也可查看所负责部门的审计记录 | |
| 所有角色 | 每个人可查看与自己相关的审计记录 | |

**用户选择 / User's choice:** 仅 Admin

---

## 通知触发 / Notification Triggers

| 选项 / Option | 描述 / Description | 选中 / Selected |
|--------|-------------|----------|
| 仅记录，不发通知 | 当前阶段不做通知 | |
| 邮件通知 | 审批/驳回时发邮件 | |
| 站内消息 + 邮件 | 同时在系统内推送和发邮件 | ✓ |

**用户选择 / User's choice:** 站内消息 + 邮件

---

## Claude's Discretion

- 审批 API 的分页参数设计
- 前端组件的具体 Tailwind 样式细节
- 测试用例的具体数据构造方式

## 延后事项 / Deferred Ideas

- 审批链配置化 UI — 后续阶段
- 通知发送实际实现 — 后续阶段
- 审批条件分支 — 属于新能力
