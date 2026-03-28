# Phase 6: 批量导入可靠性 - 上下文 / Batch Import Reliability - Context

**收集日期 / Gathered:** 2026-03-28
**状态 / Status:** 准备规划 / Ready for planning

<domain>
## 阶段边界 / Phase Boundary

HR 可以可靠地批量导入员工和认证记录，对成功和失败行获得清晰反馈。

HR can reliably import large batches of employee and certification records with clear feedback on exactly which rows succeeded and which failed.

范围内 / In scope:
- 部分成功导入（HTTP 207 Multi-Status） / Partial success import (HTTP 207)
- 逐行错误报告 + 可下载错误报告 / Per-row error reporting + downloadable error report
- 幂等性导入（按工号 upsert） / Idempotent import (upsert by employee_no)
- GBK/GB18030 编码兼容 / GBK/GB18030 encoding support
- Excel + CSV 双格式模板下载 / Excel + CSV dual-format template download
- 单次导入 5000 行限制 / 5000-row limit per import

范围外 / Out of scope:
- 异步导入任务队列（用同步处理） / Async import task queue (use synchronous)
- 部门组织架构导入 / Department hierarchy import
- 薪资历史导入 / Salary history import

</domain>

<decisions>
## 实施决策 / Implementation Decisions

### 错误处理与部分成功 / Error Handling & Partial Success
- **D-01:** 失败行**跳过并继续**，不回滚成功行。最终返回 HTTP 207 Multi-Status，包含 total、success_count、failure_count、per-row errors。
  Failed rows are **skipped and processing continues** — successful rows are committed. Returns HTTP 207 with total, success_count, failure_count, per-row errors.

- **D-02:** 失败行错误展示：**页面表格 + 可下载 Excel 报告**。页面上显示汇总统计和失败行表格，同时提供"下载错误报告"按钮生成 Excel 文件。
  Error display: **in-page table + downloadable Excel report**. Page shows summary stats and failed-row table; "Download Error Report" button generates Excel file.

### 幂等性 / Idempotency
- **D-03:** 重复导入按**工号 (employee_no)** 匹配已有记录。已存在则**覆盖更新**，不存在则创建。审计日志记录更新操作。
  Duplicate import matches by **employee_no**. Existing records are **overwritten**, new records created. Audit log records update operations.

### 编码与模板 / Encoding & Templates
- **D-04:** 模板同时提供 **Excel (.xlsx) 和 CSV (UTF-8 BOM)** 两种格式。Excel 模板自带列宽和示例行。
  Templates provided in **both Excel (.xlsx) and CSV (UTF-8 BOM)** formats. Excel template includes column widths and example rows.

- **D-05:** 上传文件自动检测编码：依次尝试 UTF-8-sig → UTF-8 → GB18030 → GBK。（已有代码实现）
  Upload file encoding auto-detection: try UTF-8-sig → UTF-8 → GB18030 → GBK in order. (Already implemented in code)

### 文件大小限制 / File Size Limits
- **D-06:** 单次导入最大 **5000 行**。超出时拒绝并提示"请分批导入，每批不超过 5000 行"。
  Maximum **5000 rows** per import. Exceeded → reject with "Please import in batches of 5000 rows or fewer".

### 进度反馈 / Progress Feedback
- **D-07:** **同步处理 + 前端 loading 状态**。API 同步执行导入，前端显示"导入中..."加载状态，完成后展示结果。
  **Synchronous processing + frontend loading state**. API processes import synchronously; frontend shows "Importing..." loading state, then displays results.

### 导入类型 / Import Types
- **D-08:** 当前阶段仅支持**员工 (employee) 和认证 (certification)** 两种导入类型。架构支持后续扩展。
  Current phase supports **employee and certification** import types only. Architecture supports future extension.

### Claude's Discretion / Claude 自行决定
- 错误报告 Excel 的具体列设计和格式化
- 前端导入结果页面的具体布局
- 认证导入的幂等键设计（employee_no + certification_name 或其他）

</decisions>

<canonical_refs>
## 规范引用 / Canonical References

**下游代理在规划或实施前必须阅读以下文件。**
**Downstream agents MUST read these before planning or implementing.**

### 导入服务 / Import Service
- `backend/app/services/import_service.py` — ImportService 类，含 `_import_employees`、`_import_certifications`、`_load_table`（已有编码检测）、`build_template`
- `backend/app/api/v1/imports.py` — 导入 API 端点
- `backend/app/schemas/import_job.py` — ImportJob schema
- `backend/app/models/import_job.py` — ImportJob 模型

### 前端 / Frontend
- `frontend/src/pages/ImportCenter.tsx` — 导入中心页面

### 先前决策 / Prior Decisions
- `.planning/phases/01-security-hardening-and-schema-integrity/01-CONTEXT.md` — D-11: Alembic-only migrations

</canonical_refs>

<code_context>
## 现有代码洞察 / Existing Code Insights

### 可复用资产 / Reusable Assets
- `ImportService._load_table` 已有 GBK/GB18030 编码检测逻辑
- `ImportService.build_template` 已有 CSV 模板生成
- `ImportService._import_employees` 和 `_import_certifications` 已有基础逻辑
- `ImportService.build_export_report` 已有导出报告框架
- `ImportCenter.tsx` 已有导入页面 UI

### 已建立模式 / Established Patterns
- 服务层逐行处理并收集结果列表
- `_dispatch_import` 方法根据 import_type 路由到具体处理方法
- ImportJob 模型记录导入任务元数据

### 集成点 / Integration Points
- `_import_employees` 需要改造为 upsert 逻辑
- API 层需要支持 207 Multi-Status 响应
- 前端需要展示部分成功结果和错误表格

</code_context>

<specifics>
## 具体要求 / Specific Ideas

- 207 响应体必须包含：total、success_count、failure_count 和 per-row error 数组
- 错误报告 Excel 需要包含原始行号、错误列、错误原因
- 模板同时提供 xlsx 和 csv 两种格式
- 5000 行限制在解析后、导入前检查

</specifics>

<deferred>
## 延后事项 / Deferred Ideas

- 异步导入 + 进度轮询（大文件场景，当 5000 行限制不够时） — 需要 Celery 任务队列
- 部门组织架构导入 — 新能力
- 薪资历史导入 — 新能力
- 导入任务的定时调度 — 新能力

</deferred>

---

*Phase: 06-batch-import-reliability*
*Context gathered: 2026-03-28*
