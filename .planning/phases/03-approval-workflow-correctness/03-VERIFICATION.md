---
phase: 03-approval-workflow-correctness
verified: 2026-03-27T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
human_verification:
  - test: "在浏览器中打开审批中心，选择一条有维度评分的审批记录，确认右侧面板显示「评估维度明细」表格"
    expected: "显示 5 列表格（维度代码、权重、原始得分、加权得分、AI说明），无维度数据时显示「暂无维度评分数据」"
    why_human: "前端渲染逻辑已验证，但实际 UI 展示效果需浏览器确认"
  - test: "以 HRBP 身份登录，勾选「查看可见范围内全部审批记录」，确认跨部门过滤行为"
    expected: "HRBP 只能看到自己所属部门的审批记录，不能看到其他部门"
    why_human: "include_all 的部门过滤逻辑已通过测试，但实际 UI 交互体验需人工确认"
---

# Phase 3: Approval Workflow Correctness Verification Report

**Phase Goal:** The approval workflow correctly tracks multi-step decisions without race conditions or lost history, and gives reviewers all the information they need
**Verified:** 2026-03-27
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 两个 manager 同时审批同一评估，只产生一个 approved 决定（无并发重复） | ✓ VERIFIED | `decide_approval` 使用 `.with_for_update()` + `decision != 'pending'` 应用层守卫；`test_concurrent_decide_rejected` PASS |
| 2 | 评估被拒绝并重新提交后，完整拒绝历史保留并可见 | ✓ VERIFIED | `generation` 列 + resubmit 路径保留旧记录；`test_resubmit_preserves_history` PASS（history len > 2） |
| 3 | Manager 审批队列按部门过滤，且同屏显示维度评分 | ✓ VERIFIED | `_approval_query` selectinload `AIEvaluation.dimension_scores`；`ApprovalRecordRead.dimension_scores` 字段存在；`test_manager_queue_has_dimension_scores` PASS |
| 4 | HR/HRBP 可跨部门查看待审批评估，并对比调薪比例 | ✓ VERIFIED | `list_approvals` 中 `include_all=True` 路径对 admin/hrbp 开放；`test_hrbp_cross_department_queue` PASS |
| 5 | 每个审批动作（approve/reject/override）在同一事务中写入审计日志 | ✓ VERIFIED | `decide_approval` 在 `db.commit()` 前写 `AuditLog(action='approval_decided')`；`update_recommendation` 写 `AuditLog(action='salary_updated')`；`test_audit_log_written_on_decide/reject/salary_change` 全部 PASS |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/approval.py` | ApprovalRecord with generation column | ✓ VERIFIED | `generation: Mapped[int]`，UniqueConstraint 已更新为 3 列 |
| `alembic/versions/0d80f22f388f_add_generation_to_approval_records.py` | Migration adding generation column | ✓ VERIFIED | 文件存在，drop 旧约束，创建新 3 列约束 |
| `backend/app/services/approval_service.py` | Pessimistic lock + history preservation + audit log | ✓ VERIFIED | `.with_for_update()`、generation-aware resubmit、`AuditLog` 写入均存在，实质性实现 |
| `backend/app/services/salary_service.py` | AuditLog write in update_recommendation | ✓ VERIFIED | `old_ratio`/`old_status` 捕获 + `AuditLog(action='salary_updated')` 在同一事务中写入 |
| `backend/app/schemas/approval.py` | dimension_scores field in ApprovalRecordRead | ✓ VERIFIED | `dimension_scores: list[DimensionScoreRead] = []` 存在 |
| `backend/app/api/v1/approvals.py` | dimension_scores populated in serialize function | ✓ VERIFIED | `serialize_approval_with_service` 通过 `model_validate` 填充 `dimension_scores` |
| `frontend/src/types/api.ts` | ApprovalRecord interface with dimension_scores | ✓ VERIFIED | `dimension_scores: DimensionScoreRecord[]` 在第 267 行 |
| `frontend/src/pages/Approvals.tsx` | Dimension score table in detail panel | ✓ VERIFIED | 「评估维度明细」section 存在，含 5 列表格和空状态文案 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `decide_approval` | `approval.decision != 'pending'` guard | second call raises ValueError | ✓ WIRED | 第 347 行：`if approval.decision != 'pending': raise ValueError(...)` |
| `decide_approval` | `AuditLog` table | same-transaction write before commit | ✓ WIRED | 第 384-399 行：`db.add(audit_entry)` 在 `db.commit()` 之前 |
| `submit_for_approval` resubmit | old `ApprovalRecord` rows | generation increment, no delete | ✓ WIRED | `new_generation = current_generation + 1`；resubmit 路径 `existing_by_step_current = {}` 不删除旧记录 |
| `_approval_query` | `AIEvaluation.dimension_scores` | selectinload chain | ✓ WIRED | 第 36 行：`.selectinload(AIEvaluation.dimension_scores)` |
| `serialize_approval_with_service` | `ApprovalRecordRead.dimension_scores` | model_validate loop | ✓ WIRED | 第 33-36 行：list comprehension + `DimensionScoreRead.model_validate(ds)` |
| `Approvals.tsx` | `selectedApproval.dimension_scores` | JSX render | ✓ WIRED | 第 677-706 行：条件渲染表格，空状态兜底 |
| `update_recommendation` | `AuditLog` table | same-transaction write | ✓ WIRED | `AuditLog(action='salary_updated')` 在 `db.commit()` 之前 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `Approvals.tsx` | `selectedApproval.dimension_scores` | `fetchApprovals` → `/api/v1/approvals` → `serialize_approval_with_service` → `evaluation.dimension_scores` (DB) | 是，selectinload 从 `dimension_scores` 表加载 | ✓ FLOWING |
| `approval_service.list_approvals` | `ApprovalRecord` list | `_approval_query()` selectinload chain → SQLAlchemy ORM → DB | 是，真实 DB 查询 | ✓ FLOWING |
| `decide_approval` | `AuditLog` row | `AuditLog(...)` 构造 + `db.add` + `db.commit` | 是，写入真实 DB | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| APPR-01: 双重审批被拒绝 | `pytest test_concurrent_decide_rejected` | PASSED | ✓ PASS |
| APPR-02: 拒绝后重提交历史保留 | `pytest test_resubmit_preserves_history` | PASSED | ✓ PASS |
| APPR-03: 审批动作写审计日志 | `pytest test_audit_log_written_on_decide test_audit_log_written_on_reject` | PASSED | ✓ PASS |
| APPR-04: 调薪更新写审计日志 | `pytest test_audit_log_written_on_salary_change` | PASSED | ✓ PASS |
| APPR-05: 审批队列含维度评分 | `pytest test_manager_queue_has_dimension_scores` | PASSED | ✓ PASS |
| APPR-06: HRBP 跨部门队列 | `pytest test_hrbp_cross_department_queue` | PASSED | ✓ PASS |

完整测试运行：15 passed, 1 pre-existing failure (`test_submit_decide_and_list_workflow` — HRBP 未绑定部门，Phase 3 范围外的已知问题，已记录在 deferred-items.md)

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| APPR-01 | 03-02 | 并发双重审批守卫 | ✓ SATISFIED | `.with_for_update()` + `decision != 'pending'` 守卫；测试 PASS |
| APPR-02 | 03-02 | 拒绝后重提交保留历史 | ✓ SATISFIED | `generation` 列 + resubmit 路径不删除旧记录；测试 PASS |
| APPR-03 | 03-02 | 审批动作同事务写审计日志 | ✓ SATISFIED | `decide_approval` 中 `AuditLog` 写入；测试 PASS |
| APPR-04 | 03-02 | 调薪更新同事务写审计日志 | ✓ SATISFIED | `update_recommendation` 中 `AuditLog` 写入；测试 PASS |
| APPR-05 | 03-03 | 审批队列含维度评分 | ✓ SATISFIED | `ApprovalRecordRead.dimension_scores` + selectinload；测试 PASS |
| APPR-06 | 03-01/03-03 | HRBP 跨部门查看待审批 | ✓ SATISFIED | `include_all=True` 路径 + 部门过滤；测试 PASS |
| APPR-07 | 03-03 | 前端审批队列展示维度评分 | ? NEEDS HUMAN | `Approvals.tsx` 维度表格代码已实现并 wired，需浏览器确认渲染效果 |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `approval_service.py` | 313 | SQLite 忽略 FOR UPDATE 注释 | ℹ️ Info | 已在注释中说明；PostgreSQL 生产环境有效，不影响目标 |
| `salary_service.py` | 368 | `operator_id=None` in AuditLog | ℹ️ Info | 已在注释中说明（salary service 无 auth context），可追溯性略有损失但不阻塞目标 |

无 Blocker 或 Warning 级别的反模式。

---

### Human Verification Required

#### 1. 维度评分表格渲染

**Test:** 以 manager 身份登录，进入审批中心，选择一条有维度评分数据的审批记录
**Expected:** 右侧面板「评估维度明细」区域显示 5 列表格（维度代码、权重、原始得分、加权得分、AI说明）；若无数据则显示「暂无维度评分数据」
**Why human:** 前端代码和数据流已全部验证，但实际浏览器渲染效果无法通过静态分析确认

#### 2. HRBP include_all 交互体验

**Test:** 以 HRBP 身份登录，勾选「查看可见范围内全部审批记录」复选框
**Expected:** 列表更新为显示该 HRBP 所属部门的全部审批记录，调薪比例列可见
**Why human:** 复选框状态切换触发 `useEffect` 重新 fetch，需浏览器确认 UI 响应正确

---

### Gaps Summary

无 gap。所有 5 个可观测目标均已验证，7 个需求中 6 个通过自动化测试确认，1 个（APPR-07 前端渲染）路由至人工验证。

唯一的测试失败（`test_submit_decide_and_list_workflow`）是 Phase 3 开始前就存在的预存问题（HRBP 用户未绑定部门），已在 03-01-SUMMARY 中记录，不属于本 Phase 范围。

---

_Verified: 2026-03-27_
_Verifier: Claude (gsd-verifier)_
