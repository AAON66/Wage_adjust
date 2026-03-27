# Phase 3: 审批流程正确性 - 上下文 / Approval Workflow Correctness - Context

**收集日期 / Gathered:** 2026-03-27
**状态 / Status:** 已完成规划 / Ready for planning

<domain>
## 阶段边界 / Phase Boundary

修复审批流程中的并发竞态条件和历史丢失问题，确保审批人拥有做出决策所需的全部信息。

Fix race conditions and history-reset bugs in the approval workflow; give reviewers all the information they need to make decisions.

范围内 / In scope:
- 悲观锁防并发（`SELECT ... FOR UPDATE`） / Pessimistic locking for concurrency
- generation 机制防历史丢失 / Generation mechanism to preserve history
- 审计日志事务内写入 / Audit log writes within same transaction
- 审批队列按部门筛选 + 维度评分展示 / Department-filtered approval queue with dimension scores
- HR 跨部门对比视图 / Cross-department comparison for HR/HRBP

范围外 / Out of scope:
- 通知系统的实际实现（仅记录触发点） / Actual notification system implementation (record trigger points only)
- 审批流程配置化 UI（记录设计意图，后续阶段实现） / Approval chain configuration UI (record design intent, implement later)

</domain>

<decisions>
## 实施决策 / Implementation Decisions

### 并发安全 / Concurrency Safety
- **D-01:** 两个审批人同时操作同一记录时，使用**悲观锁**（`SELECT ... FOR UPDATE`），第二个人收到"已被处理"提示并请求刷新页面。不返回 409，而是静默拒绝 + 前端提示。
  When two approvers act on the same record simultaneously, use **pessimistic locking** (`SELECT ... FOR UPDATE`). The second person sees an "already processed" message and is asked to refresh. Silent rejection + frontend prompt, not a 409 error.

- **D-02:** 悲观锁等待**超时 5 秒**，超时后返回提示。
  Pessimistic lock wait **timeout: 5 seconds**, return a prompt on timeout.

### 历史保留与重新提交 / History Preservation & Resubmission
- **D-03:** 驳回后重新提交时，旧 generation 的审批记录**全部保留**，新 generation 创建新记录。前端按 generation 分组，**默认折叠旧轮次**，点击展开查看历史。
  After rejection and resubmission, old generation approval records are **fully preserved**. New generation creates new records. Frontend groups by generation, **old rounds collapsed by default**, click to expand.

- **D-04:** 驳回原因**必填**，保证可追溯性。
  Rejection reason is **mandatory** to ensure traceability.

### 审批队列视图 / Approval Queue View
- **D-05:** 审批列表默认按**紧急度排序**（等待时间最长的排在前面）。
  Approval list default sort: **urgency** (longest waiting time first).

- **D-06:** HR/HRBP 跨部门对比视图**同时提供表格对比和卡片布局**两种模式。表格支持排序和筛选，卡片显示部门汇总统计。
  HR/HRBP cross-department comparison provides **both table comparison and card layout** modes. Table supports sorting and filtering; cards show department summary stats.

### 审批步骤配置化 / Approval Step Configuration
- **D-07:** 审批链**可配置**。管理员可在后台配置审批流程步骤（如主管→HR→总监），不同部门可以有不同审批链。当前阶段用代码 `build_default_steps()` 硬编码默认链，但架构需支持后续配置化扩展。
  Approval chain is **configurable**. Admin can configure approval flow steps (e.g., Manager→HR→Director), different departments can have different chains. Current phase hardcodes defaults in `build_default_steps()`, but architecture must support future configuration.

### 审计日志可见性 / Audit Log Visibility
- **D-08:** 审计日志**仅 Admin 可见**。HR/HRBP 和其他角色不能查看。
  Audit logs **visible to Admin only**. HR/HRBP and other roles cannot access.

### 通知触发 / Notification Triggers
- **D-09:** 审批状态变更时触发**站内消息 + 邮件**双通道通知。当前阶段记录触发点和通知内容模板设计，实际发送机制可在后续阶段实现。
  Approval status changes trigger **in-app message + email** dual-channel notifications. Current phase records trigger points and notification content template design; actual sending mechanism can be implemented in a later phase.

### Claude's Discretion / Claude 自行决定
- 审批 API 的分页参数设计（page_size、cursor vs offset）
- 前端组件的具体 Tailwind 样式细节
- 测试用例的具体数据构造方式

</decisions>

<canonical_refs>
## 规范引用 / Canonical References

**下游代理在规划或实施前必须阅读以下文件。**
**Downstream agents MUST read these before planning or implementing.**

### 审批服务 / Approval Service
- `backend/app/services/approval_service.py` — 核心审批逻辑，悲观锁、generation 机制、审计日志写入
- `backend/app/models/approval.py` — ApprovalRecord 模型，含 generation 和 step_order 字段
- `backend/app/api/v1/approvals.py` — 审批 API 端点，含 dimension_scores 序列化

### 审计日志 / Audit Log
- `backend/app/services/audit_service.py` — 审计服务
- `backend/app/models/audit_log.py` — AuditLog 模型

### 前端 / Frontend
- `frontend/src/pages/Approvals.tsx` — 审批页面，含维度评分面板

### Phase 1 决策 / Phase 1 Decisions
- `.planning/phases/01-security-hardening-and-schema-integrity/01-CONTEXT.md` — D-13/D-14 角色权限过滤

</canonical_refs>

<code_context>
## 现有代码洞察 / Existing Code Insights

### 可复用资产 / Reusable Assets
- `ApprovalService` 已实现悲观锁 (`with_for_update()`) 和 generation 机制
- `AuditLog` 模型和 `AuditService` 已就位
- `Approvals.tsx` 已有维度评分面板（dimension_scores 展示）
- Phase 2 的 `EvaluationDetail.tsx` 维度面板组件模式可复用

### 已建立模式 / Established Patterns
- 事务内审计日志写入（`self.db.add(audit_entry)` 在同一 session 中）
- `generation` 字段区分提交轮次
- `_is_current_step()` 方法判断当前审批步骤

### 集成点 / Integration Points
- `build_default_steps()` 是未来配置化审批链的入口点
- `decide_approval()` 中的悲观锁是并发保护的核心位置
- 前端 `Approvals.tsx` 的 `selectedApproval.dimension_scores` 已接入

</code_context>

<specifics>
## 具体要求 / Specific Ideas

- HR 跨部门视图需同时支持表格和卡片两种布局，不是二选一
- 驳回历史使用时间线折叠模式，默认只看当前轮次
- 通知系统采用站内消息+邮件双通道，但当前阶段仅设计触发点

</specifics>

<deferred>
## 延后事项 / Deferred Ideas

- 审批链配置化 UI（管理员界面） — 当前用代码默认值，后续阶段提供可视化配置
- 通知发送的实际实现（SMTP / 企业微信 / 站内消息存储） — 当前只记录触发点
- 审批流程的条件分支（如金额超过阈值时增加审批层级） — 属于新能力

</deferred>

---

*Phase: 03-approval-workflow-correctness*
*Context gathered: 2026-03-27*
