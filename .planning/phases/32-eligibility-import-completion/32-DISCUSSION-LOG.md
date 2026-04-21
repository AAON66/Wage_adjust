# Phase 32: 调薪资格导入功能补齐 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-21
**Phase:** 32-eligibility-import-completion
**Mode:** assumptions (user delegated all gray areas with "这些你自己去判断")

## 背景

用户在被问到想讨论哪几组灰色地带时，回答「这些你自己去判断」。切入 assumptions 模式：Claude 基于代码证据 + Phase 23/31 先例 + 行业默认直接拍板，生成 CONTEXT.md 供 planner 消费。

## 6 个识别出的灰色地带（合并为 4 组）

### 1. 模板字段定义 (IMPORT-01 / IMPORT-02)

**Assumption:** hire_info / non_statutory_leave 模板字段沿用 `FeishuService._sync_hire_info_body` 和 `_sync_non_statutory_leave_body` 已建立的字段映射 + NonStatutoryLeave 模型字段。
- Confidence: Confident
- Evidence: `backend/app/services/feishu_service.py:1032, 1174` 已有明确的 `field_mapping` 默认值
- If wrong: 模板字段与飞书同步不一致 → HR 从飞书和 Excel 两条路径导入同一数据会格式分歧

**Decision: D-01~D-05（见 CONTEXT.md）**
- `ImportService.SUPPORTED_TYPES` 扩 6 类；资格导入 UI 暴露后 4 类
- hire_info 必填 `employee_no + hire_date`，可选 `last_salary_adjustment_date`
- non_statutory_leave 必填 `employee_no + year + total_days`，可选 `leave_type`
- 前端 `responseType: 'blob'`（复用 Phase 31 CSV 下载模式）

### 2. Preview + Diff 形态 (IMPORT-07)

**Alternatives considered:**
| 方案 | Pros | Cons |
|------|------|------|
| A. Staging 表 | 原子性好，支持大文件，SQL join 做 diff | 需额外表，清理策略复杂 |
| B. 文件暂存（选中） | 无额外 schema，原件可审计 | 解析两次（可忽略，同份二进制必然一致） |
| C. Dry-run 不落文件 | 最轻 | 用户需重新上传，UX 差 |

**Decision: D-06~D-10** — 方案 B 文件暂存
- 上传 → 存 `uploads/imports/{job_id}.xlsx` → `ImportJob.status='previewing'` → HR confirm → 重新读同份文件执行
- Diff 粒度：4 色计数卡片 + 行级字段级表格（`old→new` 并排，类 GitHub PR 风格）
- `no_change` 默认折叠；前 200 行展示；分页 50 行一页
- 冲突定义只包含「同文件内重复业务键」；跨 job 冲突由并发锁 D-16 拦截

### 3. 覆盖模式与 AuditLog (IMPORT-05)

**Alternatives considered:**
| 控件 | Pros | Cons |
|------|------|------|
| 复选框 "清空空值" | 简洁 | 语义不直观 |
| Radio `merge / replace`（选中） | 语义明确，破坏性操作显眼 | 多占 UI 空间 |
| 下拉选择 | 统一选择器风格 | 破坏性操作不够显眼 |

**Decision: D-11~D-13** — Radio + inline 警告 + 二次确认 modal
- 默认 merge（安全）
- replace 选中 → inline 警告 + 二次确认 modal（要求勾选「我已理解并确认」才能继续）
- 不记忆每次选择（防误用）
- AuditLog 只存计数 + metadata，不存原文件内容（隐私 + 空间）

### 4. 并发锁 + 业务键 (IMPORT-06 + SC5)

**Assumption:** 直接复用 Phase 31 `is_sync_running(sync_type)` + `_with_sync_log` + `expire_stale_running_logs` 模式，无需重新设计。
- Confidence: Confident
- Evidence: `backend/app/services/feishu_service.py` Phase 31 实现已经过 UAT 验证
- If wrong: 锁语义不一致会导致两套不同的互斥行为，HR 体验混乱

**Decision: D-14~D-18**
- 幂等业务键：performance_grades `(employee_id, year)` / salary_adjustments `(employee_id, adjustment_date)` / hire_info `employee_id` / non_statutory_leave `(employee_id, year)`
- 用 SQLAlchemy `merge()` / 显式 `select+update/insert` 实现 upsert，不靠 `try/except IntegrityError`
- 锁状态：`processing` + `previewing` 都持锁（避免 preview 和 confirm 之间被抢）
- 僵尸清理：processing 30min / previewing 1 hour
- 前端：按钮禁用 + tooltip + 409 toast

## 研究补充

没有用外部研究 — 所有决策都基于项目内代码证据和先前阶段决策。

## 未决（交给 planner）

- Alembic 迁移文件命名（32_01_...）
- Celery Beat 任务的 CronSchedule 具体小时数
- `_import_hire_info` 中 `last_salary_adjustment_date` 空值在 replace 模式的处理（Claude 倾向保留而非清空，因为「最后一次调薪时间」类字段语义上不该被「空」清掉；但交给 planner 最终决策）
- Preview 抽屉 vs 内嵌展开的视觉选择（倾向抽屉，与 Phase 31 风格一致）

## 验证方式

用户后续可通过 `/gsd-plan-phase 32` 进入计划阶段时复核所有 D-XX 决策；如有分歧可在计划前修改 CONTEXT.md。

## Scope Creep 已拒绝

- 「导入撤销（rollback）」→ Deferred
- 「employees / certifications 类型的 Preview 改造」→ 不在 4 类资格导入范围，Deferred
- 「批量多文件预览」→ Deferred
- 「字段级 diff 持久化」→ 不做，原件在 uploads/ 保留
