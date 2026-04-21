# Phase 32: 调薪资格导入功能补齐 - Context

**Gathered:** 2026-04-21 (assumptions mode — user delegated all gray areas to Claude)
**Status:** Ready for planning

<domain>
## Phase Boundary

HR 通过「调薪资格导入」页面（现有 `EligibilityManagementPage` 的 Tab）对 4 种 import_type 做完整闭环：模板下载（真 xlsx）→ 上传预览（Preview + diff）→ 覆盖模式选择（merge/replace）→ 并发互斥（409）→ 幂等落库。4 种 import_type：`performance_grades` / `salary_adjustments` / `hire_info` / `non_statutory_leave`。

**不在本期:** 飞书同步补齐（Phase 23 + 31 已覆盖）、`ImportCenter.tsx`（历史页面不动）、批量删除/撤销导入（未来阶段）、`employees` / `certifications` 类型的 diff 改造（非资格导入，不在 4 类范围）。

</domain>

<decisions>
## Implementation Decisions

### 模板字段定义 (IMPORT-01 / IMPORT-02)

**D-01:** `ImportService.SUPPORTED_TYPES` 扩为 6 类：`{'employees', 'certifications', 'performance_grades', 'salary_adjustments', 'hire_info', 'non_statutory_leave'}`；但资格导入 UI 只暴露后 4 类（前两类留给 `ImportCenter` 历史页面）。

**D-02:** `hire_info` 模板字段（对齐 `FeishuService._sync_hire_info_body` 字段映射）：
- `REQUIRED_COLUMNS['hire_info'] = ['employee_no', 'hire_date']`
- `COLUMN_ALIASES['hire_info'] = {'员工工号': 'employee_no', '入职日期': 'hire_date', '末次调薪日期': 'last_salary_adjustment_date'}`
- `last_salary_adjustment_date` 为可选（为空不覆盖已有值，跟飞书同步保持一致）
- `hire_date` 接受三种输入：`YYYY-MM-DD` 字符串 / Excel 日期单元格 / Excel 序列号（复用 `sync_hire_info` 里的 `pd.to_datetime` 兼容逻辑）
- `TEMPLATE_TEXT_COLUMNS['hire_info'] = ['employee_no']`（防前导零丢失，复用 D-09 模式）

**D-03:** `non_statutory_leave` 模板字段（对齐 `NonStatutoryLeave` 模型 + `_sync_non_statutory_leave_body` 默认映射）：
- `REQUIRED_COLUMNS['non_statutory_leave'] = ['employee_no', 'year', 'total_days']`
- `COLUMN_ALIASES['non_statutory_leave'] = {'员工工号': 'employee_no', '年度': 'year', '假期天数': 'total_days', '假期类型': 'leave_type'}`
- `leave_type` 可选（枚举：`事假 / 病假 / 其他`，与模型 comment 一致）
- `year` 为 4 位整数（如 `2026`）；`total_days` 为 Decimal(6,1)（允许 0.5 天）
- `TEMPLATE_TEXT_COLUMNS['non_statutory_leave'] = ['employee_no']`

**D-04:** `build_template_xlsx(import_type)` 复用现有 openpyxl 逻辑，预填 1 行表头 + 1 行示例 + 105 行空白（`TEMPLATE_TEXT_PREFILL_ROWS`）；hire_info/non_statutory_leave 的示例行用 `E00001` 工号 + `2026-01-15` / `2026 / 10.5 / 事假` 占位。

**D-05:** 前端下载模板：`eligibilityImportService.getTemplateUrl(type)` 改用 `axios.get(url, {responseType: 'blob'})` 拉取 → 通过 `URL.createObjectURL` + 临时 `<a>` 触发浏览器下载（复用 Phase 31 CSV 下载 Safari 兼容模式）；删除 `window.open(url)` 的旧实现（否则 xlsx 在浏览器里被渲染为乱码）。

### Preview + Diff 机制 (IMPORT-07)

**D-06:** 两阶段提交用 **文件暂存方案**：
1. HR 上传 xlsx → 后端解析 + 存 `uploads/imports/{job_id}.xlsx` + 返回 `{job_id, preview}`
2. `ImportJob` 初始 status = `'previewing'`（新增状态）
3. HR 点击「确认导入」→ POST `/imports/{job_id}/confirm` → 从 `uploads/imports/{job_id}.xlsx` 重新读取同一份二进制 → 执行落库 → status 变 `'processing'` → `'completed'`/`'failed'`
4. HR 点击「取消」或超过 1 小时未 confirm → status 变 `'cancelled'`，定时任务清理文件

不用 staging 表（简单、避免额外 schema）、不用 dry-run（避免重复上传体验差）。

**D-07:** Preview 返回结构（`PreviewResponse`）：
```json
{
  "job_id": "uuid",
  "import_type": "performance_grades",
  "total_rows": 120,
  "counters": {"insert": 45, "update": 72, "no_change": 2, "conflict": 1},
  "rows": [
    {"row_number": 2, "action": "insert", "employee_no": "E0001", "fields": {"grade": {"old": null, "new": "A"}}},
    {"row_number": 3, "action": "update", "employee_no": "E0002", "fields": {"grade": {"old": "B", "new": "A"}, "comment": {"old": "x", "new": "y"}}},
    {"row_number": 4, "action": "conflict", "employee_no": "E0003", "conflict_reason": "同文件内 (employee_no=E0003, year=2026) 出现 2 次"}
  ],
  "rows_truncated": false
}
```
- `rows` 最多返回 200 行（`insert` 优先展示，`no_change` 默认折叠在前端）
- 超过 200 行时 `rows_truncated=true`，前端显示「已省略 {N} 行 no-change」

**D-08:** Diff 粒度 = **行级 + 字段级**：
- 计数卡片（顶部）：4 色 badge `Insert(绿) / Update(蓝) / No-change(灰) / 冲突(红)`
- 详细表格（可展开）：每行显示 `行号 / 员工工号 / action / 变化字段 old→new 并排`
- No-change 行默认折叠（点击「显示未变化 {N} 行」展开）
- 冲突行高亮红色 + 显示冲突原因；只要有 1 条冲突 → 禁用「确认导入」按钮，HR 必须修正 Excel 后重新上传

**D-09:** 冲突定义：
- 同一批文件内，相同「业务键」（见 D-14）出现 2 次以上 → `conflict`
- 上传时即检测，不在 confirm 阶段重新算（preview 返回时冲突已知）
- 不检测「跨 job 的时间竞争冲突」（由并发锁 D-12 在 confirm 时拦截）

**D-10:** 前端展示大批量策略（> 200 行）：
- 表格用原生分页（每页 50 行，上一页/下一页）— 不用虚拟滚动（复杂度过高）
- Preview 默认展开 Insert + Update + Conflict 三类；No-change 折叠

### 覆盖模式与 AuditLog (IMPORT-05)

**D-11:** UI 控件 = **Radio（互斥）**：
- 选项：「合并模式（空值保留旧值，推荐）」/「替换模式（空值清空字段）」
- 默认：`merge`（安全选项）
- 位置：在 Preview 确认页面底部，紧邻「确认导入」按钮
- 不记忆每次选择（每次手动选，防止误用）
- 选中 `replace` 时：显示 inline 警告 `⚠ 替换模式会清空你未填的字段，这是破坏性操作。确认要继续吗？`
- 点击「确认导入」时：若 `replace` 被选中，弹二次确认 modal「确认以替换模式导入 {N} 行？此操作会清空未填字段，已入库数据无法自动恢复」，HR 必须勾选「我已理解并确认」才能点「继续」

**D-12:** `overwrite_mode` 语义：
- `merge`（默认）：只更新 Excel 中「有值」的字段；Excel 单元格为空 → 保留数据库旧值
- `replace`：Excel 中有值的字段更新；**可选字段** 为空 → 设为 NULL（清空）；**必填字段** 为空 → 直接 `failed`（不允许清空必填）

**D-13:** AuditLog 字段（新增 `AuditLog(action='import_confirmed')` 一条/job）：
```python
{
  'action': 'import_confirmed',
  'resource_type': 'import_job',
  'resource_id': job_id,
  'actor_id': user_id,
  'detail': {
    'import_type': 'performance_grades',
    'overwrite_mode': 'merge',
    'file_name': 'grades_2026Q1.xlsx',
    'total_rows': 120,
    'inserted_count': 45,
    'updated_count': 72,
    'no_change_count': 2,
    'conflict_count': 1,
    'failed_count': 0
  }
}
```
- 不保存 Excel 原件到 AuditLog（GDPR / 存储考虑），原件已在 `uploads/imports/{job_id}.xlsx` 保留 30 天后定时清理
- 不记录 field-level diff（太大；需要审计时直接查 AuditLog 关联的 `ImportJob.result_summary`）

### 并发锁与业务键 (IMPORT-06 + SC5)

**D-14:** 幂等业务键（upsert key）：
| import_type | 业务键 | 说明 |
|-------------|-------|------|
| `performance_grades` | `(employee_id, year)` | 同一员工同一年度只有一条绩效（已有模型约束或待加） |
| `salary_adjustments` | `(employee_id, adjustment_date)` | 同一员工同一日期只有一条调薪（极端情况一天多次调薪由 business 约束） |
| `hire_info` | `employee_id` | 更新 `Employee` 主表的 `hire_date` / `last_salary_adjustment_date` |
| `non_statutory_leave` | `(employee_id, year)` | 已有 `UniqueConstraint('employee_id', 'year')` |

实现方式：`_import_xxx` 方法内用 `ON CONFLICT DO UPDATE`（SQLAlchemy `merge()` 或显式 `select() + update()/insert()`），不用 `try/except IntegrityError` 抓重试。

**D-15:** `_import_performance_grades` 需要补 `UniqueConstraint('employee_id', 'year')` 迁移（如果尚无）— Wave 1 Alembic migration 检查。

**D-16:** 并发锁复用 Phase 31 `is_sync_running(sync_type)` 模式：
- 新增 `ImportService.is_import_running(import_type) -> bool`：查 `ImportJob` 有无 `status in ('processing', 'previewing')` 且 `import_type == ?` 的记录
- `previewing` 也算持锁（HR 在 preview 和 confirm 之间，其他并发提交 409）— 避免 HR A 预览 / HR B 强行导入导致数据覆盖
- `POST /imports/upload` 和 `POST /imports/{job_id}/confirm` 都过锁检查；409 不写 AuditLog（与 Phase 31 D-16 一致）
- 锁粒度：per `import_type`（4 类各一把锁，不互相阻塞）

**D-17:** 僵尸 job 清理：
- Celery Beat 定时任务 `expire_stale_import_jobs`，每 15 分钟跑一次
- 扫 `status='processing' AND created_at < now - 30min` → 标记 `status='failed'` + `result_summary={'error': 'timeout'}`
- 扫 `status='previewing' AND created_at < now - 1hour` → 标记 `status='cancelled'` + 删除 `uploads/imports/{job_id}.xlsx`
- 复用 Phase 31 `expire_stale_running_logs` 独立 session 模式

**D-18:** 前端 UX（按钮禁用）：
- 进入 Tab 时：`GET /imports/active?import_type=X` 返回 `{active: true/false, job: {...} | null}`
- 有活跃 job → 「选择文件」按钮禁用 + tooltip「该类型导入正在进行中（job_id=xxx，状态=previewing）」
- 409 响应 → toast 「该类型导入正在进行中，请等待当前任务完成或在「同步日志」查看状态」 + 禁用按钮 5 秒（防误点）

### Claude's Discretion
- 上传进度条实现细节（可以用 `XMLHttpRequest.upload.onprogress`）
- Preview 抽屉 vs 内嵌展开的视觉选择（倾向抽屉，与 Phase 31 风格一致）
- `ImportJob.result_summary` JSON schema 具体字段顺序
- uploads/imports/ 目录的清理 cron 具体小时数（7/30 天都合理）
- `_import_hire_info` 中 `last_salary_adjustment_date` 为空时的行为（merge 模式必然保留；replace 模式也保留，因为对「时间戳类」字段 replace 清空没语义）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 导入基础设施
- `backend/app/services/import_service.py` — `ImportService` 全文，尤其 `SUPPORTED_TYPES` / `REQUIRED_COLUMNS` / `COLUMN_ALIASES` / `build_template_xlsx` / `_import_*` / `_dispatch_import` / `TEMPLATE_TEXT_COLUMNS` (D-07 前导零防御)
- `backend/app/models/import_job.py` — `ImportJob` 模型，需加 `overwrite_mode` / `actor_id` 字段
- `backend/app/api/v1/imports.py` — 旧导入 API
- `backend/app/api/v1/eligibility_import.py` — 资格导入 API（本期主战场）
- `backend/app/schemas/eligibility_import.py` — `ELIGIBILITY_IMPORT_TYPES = {'performance_grades', 'salary_adjustments', 'hire_info', 'non_statutory_leave'}`
- `backend/app/tasks/import_tasks.py` — Celery 异步 import 任务

### 数据模型
- `backend/app/models/employee.py` §`hire_date: Mapped[Optional[date]]` — `hire_info` 落库目标
- `backend/app/models/non_statutory_leave.py` — 字段 `(employee_id, year, total_days, leave_type, source)` + `UniqueConstraint('employee_id', 'year', name='uq_leave_employee_year')`
- `backend/app/models/performance_record.py` — 检查是否有 `UniqueConstraint('employee_id', 'year')`（D-15 依赖）
- `backend/app/models/salary_adjustment_record.py` — 检查是否有 `(employee_id, adjustment_date)` 约束
- `backend/app/models/audit_log.py` — `action` / `resource_type` / `resource_id` / `detail` 字段约定

### 飞书同步（字段映射参考）
- `backend/app/services/feishu_service.py:994-1134` — `sync_hire_info` + `_sync_hire_info_body`，字段映射 `{'员工工号': 'employee_no', '入职日期': 'hire_date', '末次调薪日期': 'last_salary_adjustment_date'}`
- `backend/app/services/feishu_service.py:1135-1200` — `sync_non_statutory_leave` + `_sync_non_statutory_leave_body`，字段映射 `{'员工工号': 'employee_no', '年度': 'year', '假期天数': 'total_days', '假期类型': 'leave_type'}`
- `backend/app/services/feishu_service.py:_with_sync_log / is_sync_running` — 并发锁模式参考（D-16）
- `backend/app/services/feishu_service.py:expire_stale_running_logs` — 僵尸清理模式参考（D-17）

### 前端
- `frontend/src/pages/EligibilityManagementPage.tsx` — 4 Tab 容器
- `frontend/src/components/eligibility-import/ExcelImportPanel.tsx` — 本期主要改造目标（加 Preview + diff + 覆盖模式 Radio）
- `frontend/src/components/eligibility-import/ImportTabContent.tsx` — Tab 内容组装
- `frontend/src/components/eligibility-import/FeishuSyncPanel.tsx` — 不改，只作视觉参考
- `frontend/src/services/eligibilityImportService.ts` — `getTemplateUrl` 改 `responseType: 'blob'` (D-05)
- `frontend/src/hooks/useTaskPolling.tsx` — 异步 import 进度轮询

### 先前阶段参考
- `.planning/phases/23-eligibility-import/23-CONTEXT.md` — Phase 23 导入基础决策（D-11 hire_info 复用 Employee, D-12 NonStatutoryLeave 模型）
- `.planning/phases/31-feishu-sync-observability/31-CONTEXT.md` — per-sync_type 锁模式（D-15 / D-16 / D-17）可直接抄

### 需求定义
- `.planning/REQUIREMENTS.md` §IMPORT-01 — SUPPORTED_TYPES 补齐
- `.planning/REQUIREMENTS.md` §IMPORT-02 — 模板下载 blob
- `.planning/REQUIREMENTS.md` §IMPORT-05 — overwrite_mode Literal['merge','replace']
- `.planning/REQUIREMENTS.md` §IMPORT-06 — 409 并发锁
- `.planning/REQUIREMENTS.md` §IMPORT-07 — Preview + diff

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ImportService._normalize_columns` + `COLUMN_ALIASES`**：中文列名 → 系统字段名的映射逻辑已就绪，加 2 条 entry 就能复用
- **`build_template_xlsx` + `TEMPLATE_TEXT_PREFILL_ROWS` + `TEMPLATE_TEXT_COLUMNS`**：openpyxl 模板生成 + 工号列强制文本格式已抽象，新类型只需注册 REQUIRED_COLUMNS 即可自动支持
- **`FeishuService.is_sync_running` + `_with_sync_log` + `expire_stale_running_logs`**：Phase 31 已建立 per-bucket 锁模式，`ImportService` 照抄即可（D-16 / D-17）
- **`NonStatutoryLeave` 模型**：已有 `UniqueConstraint('employee_id', 'year')`，`_import_non_statutory_leave` 直接 SQLAlchemy upsert
- **`useTaskPolling` hook**：Celery task 进度轮询已就绪
- **`AuditLog` 模型**：`action` + `detail: JSON` 字段已就绪，`import_confirmed` 作为新 action 即可
- **`ImportJob` 模型**：`import_type` + `status` + `result_summary` 已就绪，加 `overwrite_mode` + `actor_id` 两列即可

### Established Patterns
- **两阶段 Alembic 迁移（Phase 30 / 31 已确立）**：`op.batch_alter_table` + `add_column(nullable=True)` → `UPDATE 回填` → `alter_column(nullable=False)`，本期加 `ImportJob.overwrite_mode` 按此走
- **Per-sync_type 独立 session 锁（Phase 31 D-13）**：`SessionLocal()` 独立 session 写锁终态，避免业务 rollback 带走锁释放
- **文本格式防前导零（Phase 30 + ImportService D-07）**：hire_info / non_statutory_leave 的 `employee_no` 列继续走 `TEMPLATE_TEXT_COLUMNS`
- **Radio + 二次确认弹窗**：破坏性操作的标准 UX（仿 Phase 21 拒绝重新上传确认）
- **CSV 下载 Safari 兼容（Phase 31 D-08）**：`Blob + URL.createObjectURL + <a>` 模式可迁移到 xlsx 模板下载

### Integration Points
- **`ImportService.SUPPORTED_TYPES` → 所有导入 API 的校验入口**：加 2 个 type 后，现有的 `POST /imports/upload` / `GET /imports/template/{type}` / `GET /imports/{job_id}/report.xlsx` 自动支持
- **`EligibilityManagementPage.tsx` 4 个 Tab → `ExcelImportPanel` 组件**：改造单一组件即可覆盖全部 4 类
- **`ImportJob.result_summary` JSON 承载 diff 结果**：preview 阶段写入 `{preview: {...}}`，confirm 阶段覆盖为 `{execution: {...}}`（单条 ImportJob 记录）
- **侧边栏菜单 `/eligibility` 路由**：Phase 23 已加，本期不改

</code_context>

<specifics>
## Specific Ideas

- **"类似 GitHub PR 的 diff 视图"**：字段级新旧并排（`"old_value" → "new_value"`），而不是 unified diff。
- **"不要太多步骤"**：上传 → Preview（单页含 diff + radio + 按钮）→ Confirm，3 步走完。
- **Phase 31 紫色 `mapping_failed` 概念在本期不适用**：import 没有「映射失败」一说，映射错的直接是行级 `failed` + 错误信息（不引入新色）。
- **冲突定义收窄**：只检测「同文件内重复」这一种冲突；跨 job 的时间竞争冲突由并发锁拦截，不作为 conflict 类目。

</specifics>

<deferred>
## Deferred Ideas

- **撤销导入（rollback a confirmed job）**：未来阶段（需要完整 audit trail + 反向操作）
- **批量预览多个文件**：单次只一个文件
- **导入调度 / 定时任务（如每周一自动从 S3 拉取）**：不在资格导入场景
- **Diff 的审计查询 UI**：管理员想看历史 diff 要从 `AuditLog.detail` + `ImportJob.result_summary` 查 — 不做专门页面，CLI / DB 查询即可
- **字段级 diff 持久化**：`result_summary` 只存计数 + 前 200 行，完整 diff 查原文件 `uploads/imports/{job_id}.xlsx`
- **`employees` / `certifications` 类型的 Preview + diff 改造**：不在 4 类资格导入范围；若未来要，另开 phase
- **文件存到 MinIO/S3 代替本地 uploads/**：当前 dev 用本地路径够用，部署时切换存储后端属于运维任务

</deferred>

---

*Phase: 32-eligibility-import-completion*
*Context gathered: 2026-04-21 (assumptions mode)*
