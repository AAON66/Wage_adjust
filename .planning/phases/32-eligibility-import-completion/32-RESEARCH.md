# Phase 32: 调薪资格导入功能补齐 - Research

**Researched:** 2026-04-21
**Domain:** 后端 ImportService 两阶段提交（Preview + Confirm）+ 前端 Preview/diff/Radio/Modal + 并发互斥锁 + 文件暂存生命周期
**Confidence:** HIGH（基于实际代码盘点 + 实测验证 + Phase 31 已落地参考）

---

## Summary

Phase 32 的目标是把 `EligibilityManagementPage` 的 4 个资格导入 Tab 从「上传即落库」升级为「上传 → Preview → 覆盖模式选择 → 确认导入」三步闭环，并配套加 per-`import_type` 并发锁、僵尸 job 清理、blob 模板下载。`32-CONTEXT.md` 已锁定 18 个 D-XX 决策，本研究只补「实施细节」与「实测发现的真实差异」。

**关键事实纠正（CONTEXT.md 假设 vs 真实代码）：**
1. **`AuditLog` 字段名不是 `resource_type`/`resource_id`，而是 `target_type`/`target_id`**（`backend/app/models/audit_log.py:21-23`）。D-13 文案的字段名需要在落实时按真实模型映射（详见「## 关键差异」章节）。
2. **`PerformanceRecord` 已有 `UniqueConstraint('employee_id', 'year', name='uq_performance_employee_year')`**（`backend/app/models/performance_record.py:14-16`）— D-15 假设可能需要补的迁移**已经存在**，本期无需重复。
3. **`SalaryAdjustmentRecord` 没有 UniqueConstraint，只有 Index**（`backend/app/models/salary_adjustment_record.py:19-20`）— D-14 想要的 `(employee_id, adjustment_date)` 业务键在 DB 层**仅是 Index 不是 Unique**；当前 `_import_salary_adjustments` 是 **append** 不是 upsert（`backend/app/services/import_service.py:830-838`），重复导入会产生多条同日同类型记录。这与 D-14 文档的「同一员工同一日期只有一条调薪」约定**不一致**，需在规划阶段决议。
4. **当前项目无任何 Celery Beat schedule**（`backend/app/celery_app.py` 仅注册 worker 任务，无 `beat_schedule`），但已有 APScheduler（`backend/app/scheduler/feishu_scheduler.py`）。D-17 的「定时清理」选 Celery Beat 还是 APScheduler 需在规划时落定。
5. **`uploads/` 目录存储模式已有先例**（`backend/app/core/storage.py` 的 `LocalStorageService` 已实现路径遍历防护 `is_relative_to`），D-06 暂存方案应**复用此安全模式**而不是自写。

**Primary recommendation:** 实施分 4 个 wave —
- Wave 0：补测试基线（`test_import_preview_*.py`、`test_import_confirm_*.py`、`test_import_active_endpoint.py` 等）
- Wave 1：DB schema 改动（`ImportJob` 加 `overwrite_mode`/`actor_id`/`status='previewing'`/`status='cancelled'`；可选给 `SalaryAdjustmentRecord` 加 UniqueConstraint）
- Wave 2：后端 ImportService 改造（SUPPORTED_TYPES 扩 6 类、`_import_hire_info` / `_import_non_statutory_leave` 新方法、`build_preview` 与 `confirm_import` 两阶段、`is_import_running`、文件暂存）
- Wave 3：前端 6 个新组件 + ExcelImportPanel 状态机改造 + downloadTemplate blob 模式

---

## User Constraints (from CONTEXT.md)

> 本研究**严格遵循** CONTEXT.md 锁定的 18 项决策，不质疑、不重新探讨。以下是关键约束的精简映射：

### Locked Decisions（必须实现）

| ID | 锁定决策 |
|----|----------|
| D-01 | `SUPPORTED_TYPES` 扩为 6 类；UI 只暴露后 4 类 |
| D-02 | `hire_info` 字段：`employee_no` + `hire_date`（必）+ `last_salary_adjustment_date`（可选） |
| D-03 | `non_statutory_leave` 字段：`employee_no` + `year` + `total_days`（必）+ `leave_type`（可选枚举） |
| D-04 | `build_template_xlsx` 复用现有逻辑 + 105 行预填 + 文本格式 |
| D-05 | 前端模板下载改 `responseType: 'blob'` |
| D-06 | 文件暂存方案 `uploads/imports/{job_id}.xlsx`，**不**用 staging 表/dry-run |
| D-07 | `PreviewResponse` 结构（counters + rows max 200） |
| D-08 | Diff 行级 + 字段级，no_change 默认折叠，冲突禁用确认按钮 |
| D-09 | 冲突 = 同文件内业务键重复，preview 即检测 |
| D-10 | 分页 50/页，不虚拟滚动，no_change 折叠 |
| D-11 | Radio + 二次确认 modal（replace 强制 checkbox 勾选） |
| D-12 | `merge`（默认）/ `replace`（必填空值则失败） |
| D-13 | AuditLog `action='import_confirmed'`（**注意：实际字段名是 `target_type`/`target_id` 不是 `resource_type`/`resource_id`**） |
| D-14 | 业务键见表（performance/leave 已有约束；salary_adj 仅 index 不是 unique；hire_info=employee_id） |
| D-15 | `_import_performance_grades` UniqueConstraint **已存在**，本期无需补 |
| D-16 | 复用 Phase 31 per-`sync_type` 锁模式 → `is_import_running(import_type)`；preview 也持锁 |
| D-17 | 僵尸清理 — 选 Celery Beat（需新建）或 APScheduler（已有） |
| D-18 | 前端按钮禁用 + tooltip + 409 toast |

### Claude's Discretion（研究有推荐）

- 上传进度条实现：推荐 `XMLHttpRequest.upload.onprogress`（axios 支持 `onUploadProgress`）
- Preview 抽屉 vs 内嵌：UI-SPEC 已选**内嵌面板**（与「3 步直线走完」一致）
- `result_summary` JSON schema 字段顺序：本研究在 `## 后端 Schema 建议`给出推荐
- uploads/imports/ 清理 cron：推荐 30 天保留（与 D-13「不存原件到 AuditLog」一致）
- `_import_hire_info` 中 `last_salary_adjustment_date` 为空：推荐 merge/replace **都保留**（时间戳字段语义上 replace 清空无意义）

### Deferred Ideas（OUT OF SCOPE）

- 撤销已 confirm 的 job、批量预览多文件、定时拉取 S3、字段级 diff 持久化、`employees`/`certifications` 类型的 Preview 改造、MinIO/S3 替换本地 uploads/

---

## Phase Requirements

| ID | 描述 | 研究支撑 |
|----|------|----------|
| IMPORT-01 | `SUPPORTED_TYPES` 补齐 hire_info / non_statutory_leave + REQUIRED_COLUMNS / COLUMN_ALIASES / `_import_*` / `build_template_xlsx` 同步补齐 | `## 当前 ImportService 现状盘点`（缺什么、怎么加）+ `## hire_info / non_statutory_leave 字段映射对齐`（飞书同步参考） |
| IMPORT-02 | 模板下载返回非空 .xlsx，前端 `responseType: 'blob'` | `## 前端 Blob 下载模式`（已有 `feishuService.downloadUnmatchedCsv` 与 `importService.downloadImportTemplate` 模式参考）+ `## Pitfall 5: window.open(xlsx)` |
| IMPORT-05 | `overwrite_mode: Literal['merge', 'replace']` + AuditLog 记录 | `## 后端 Schema 建议`（ImportJob 字段扩展）+ `## merge / replace 语义实现表` |
| IMPORT-06 | per-`import_type` 并发锁，409 拒绝 | `## Phase 31 锁模式直接抄什么`（_with_sync_log 不抄；is_sync_running 直接抄；expire_stale 直接抄） |
| IMPORT-07 | Preview + diff，HR 显式确认才落库 | `## 两阶段提交实现路径`（4 个失败模式 + 3 个并发场景）+ `## 冲突检测算法` |

---

## 当前 ImportService 现状盘点（IMPORT-01 / IMPORT-07 基线）

### SUPPORTED_TYPES 与字段映射

`backend/app/services/import_service.py:28` 当前为 4 类：`{'employees', 'certifications', 'performance_grades', 'salary_adjustments'}`。

D-01 需补 2 类，最终：6 类。**已确认所有相关常量需要同步扩展**：

| 常量 | 当前 | 需要新加 |
|------|------|---------|
| `SUPPORTED_TYPES` (line 28) | 4 类 | + `hire_info`, `non_statutory_leave` |
| `REQUIRED_COLUMNS` (line 30-35) | 4 类 | + `hire_info: ['employee_no', 'hire_date']`<br>+ `non_statutory_leave: ['employee_no', 'year', 'total_days']` |
| `COLUMN_ALIASES` (line 36-68) | 4 类 | + `hire_info` 见 D-02<br>+ `non_statutory_leave` 见 D-03 |
| `TEMPLATE_TEXT_COLUMNS` (line 76-81) | 4 类 | + `hire_info: ['employee_no']`<br>+ `non_statutory_leave: ['employee_no']`（D-02/D-03 已锁） |
| `COLUMN_LABELS` (line 90-111) | 字段标签 | + `hire_date: '入职日期'`、`last_salary_adjustment_date: '末次调薪日期'`、`total_days: '假期天数'`、`leave_type: '假期类型'` |

### `build_template_xlsx` 复用情况

`backend/app/services/import_service.py:276-349` 已结构化：
- header_font / header_fill / header_alignment 三个变量
- `if elif` 分支按 import_type 写不同 headers + example
- 末尾循环把 `TEMPLATE_TEXT_COLUMNS` 中的列设为 `cell.number_format = '@'` 共 105 行（line 329-343）

新增 hire_info / non_statutory_leave 只需在 `if/elif` 链里加两个分支即可，**末尾的文本格式逻辑自动生效**（已基于 `TEMPLATE_TEXT_COLUMNS` 配置驱动）。建议示例数据：
- hire_info: `['E00001', '2026-01-15', '2025-06-01']`
- non_statutory_leave: `['E00001', 2026, 10.5, '事假']`

### `_import_*` 方法已实现哪些

| 方法 | 行号 | 状态 | 业务键 | 模式 |
|------|------|------|--------|------|
| `_import_employees` | 529-666 | ✅ | `employee_no` | upsert |
| `_import_certifications` | 668-721 | ✅ | `(employee_id, certification_type)` | upsert |
| `_import_performance_grades` | 727-773 | ✅ | `(employee_id, year)` | upsert |
| `_import_salary_adjustments` | 795-850 | ⚠️ append（**非** upsert） | 无 unique key | append |
| `_import_hire_info` | — | ❌ 不存在 | `employee_id` (Employee 表) | 待写 |
| `_import_non_statutory_leave` | — | ❌ 不存在 | `(employee_id, year)` | 待写（NonStatutoryLeave 已有 UniqueConstraint） |

**关键设计差异：** `_import_salary_adjustments` 当前是 append 模式 — 这意味着 D-14 表中「`(employee_id, adjustment_date)` 同一员工同一日期只有一条调薪」实际上**当前不成立**。本期需要：
1. 决定改为 upsert 还是保持 append（CONTEXT.md D-14 说 upsert，但极端情况一天多次调薪是合法业务） — 推荐改为 upsert + `(employee_id, adjustment_date, adjustment_type)` 复合业务键（与飞书同步 `_sync_salary_adjustments_body` line 947-952 的查询键一致）。
2. 是否需要给 `SalaryAdjustmentRecord` 加 UniqueConstraint 迁移（**Wave 1 alembic 任务**）。

### `_dispatch_import` 路由

`backend/app/services/import_service.py:438-476`：用 if/elif 分发到 4 个 `_import_*` 方法。新加 2 类需在此处也加 elif 分支。Phase 30 已加的 `_detect_leading_zero_loss_rows` 检测会自动覆盖新类型（基于 `_EMPLOYEE_NO_KEY_COLUMNS` frozenset，line 88），无需改动。

[VERIFIED: 代码读取 backend/app/services/import_service.py 全文]

---

## ImportJob 模型现状（IMPORT-05 / IMPORT-06 schema 改造）

### 现有字段

`backend/app/models/import_job.py`:

```python
class ImportJob(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "import_jobs"
    file_name: Mapped[str]
    import_type: Mapped[str]  # index=True
    status: Mapped[str]  # default="pending", index=True
    total_rows: Mapped[int]
    success_rows: Mapped[int]
    failed_rows: Mapped[int]
    result_summary: Mapped[dict] = mapped_column(JSON)
```

继承 `UUIDPrimaryKeyMixin` 提供 `id: str(36)`，`CreatedAtMixin` 提供 `created_at`。**没有 `updated_at`**（不继承 `UpdatedAtMixin`）。**没有 `actor_id` 字段**。

### 当前 status 值

代码扫描 `backend/app/services/import_service.py`:
- `'processing'` (line 207, 创建时)
- `'completed'` (line 237)
- `'failed'` (line 239)
- `'partial'` (line 241)
- `'pending'`（model default，line 15）

注：`'pending'` 实际上从未被服务层使用，但是 model 的默认值。

### Wave 1 改动建议

新加列：

| 列名 | 类型 | nullable | 默认值 | 用途 |
|-----|------|----------|--------|------|
| `overwrite_mode` | `String(16)` | False | `'merge'` | D-12 / IMPORT-05 |
| `actor_id` | `String(36) FK users.id` | True | NULL | D-13 审计追溯 + 历史数据兼容 |
| `updated_at` | `DateTime` | False | `now()` | 支持 D-17「previewing 1 小时清理」/「processing 30 分钟清理」基于 `created_at` 即可，但 `updated_at` 让 Beat job 可优化（仅扫描刚刚 update 的状态机异常） |

新加 status 值（业务层枚举，不是 DB 约束）：
- `'previewing'`：上传完成、preview 已返回、HR 未 confirm（D-06 阶段 1 终态）
- `'cancelled'`：HR 显式取消 / 1 小时未 confirm（D-17）

### Alembic 两阶段迁移策略（参考 Phase 31 `31_01_feishu_sync_log_observability.py`）

| 步骤 | 操作 | SQLite 兼容点 |
|------|------|--------------|
| 1 | `batch_alter_table` add `overwrite_mode`（**nullable=True**，先不强制 NOT NULL） | OK |
| 2 | `op.execute("UPDATE import_jobs SET overwrite_mode='merge' WHERE overwrite_mode IS NULL")` | 历史数据回填 |
| 3 | `batch_alter_table` `alter_column overwrite_mode` 改为 NOT NULL | SQLite 通过 batch 重建 |
| 4 | `add_column actor_id`（nullable=True，因历史 import_job 无操作者；FK 约束 ON DELETE SET NULL 保护） | OK |
| 5 | `add_column updated_at` 带 `server_default=func.now()` | OK |

**避坑：** Phase 31 `31_01_feishu_sync_log_observability.py:31-55` 已确立此 3 阶段模板（add nullable → backfill → alter NOT NULL），直接照抄。**禁止** `op.add_column` 不在 batch 里（PITFALLS Pitfall 16，SQLite 不支持 `ALTER COLUMN`）。

### `result_summary` JSON 用法（preview vs execution）

当前 line 210 / 229-232 / 244-248 显示 result_summary 的两种形态：

```python
# 成功执行：
{'rows': [...], 'supported_types': [...]}
# 失败：
{'rows': [], 'error': '...', 'supported_types': [...]}
```

D-06 + 集成点提到 ImportJob 单条记录承载两阶段（preview + execution），建议 schema：

```jsonc
{
  "preview": {                                // 阶段 1 写入
    "counters": {"insert": 0, "update": 0, "no_change": 0, "conflict": 0},
    "rows": [...],                            // 最多 200 行（D-07）
    "rows_truncated": false,
    "uploaded_file_size": 12345,
    "uploaded_at": "2026-04-21T07:00:00Z",
    "preview_expires_at": "2026-04-21T08:00:00Z"
  },
  "execution": {                              // 阶段 2 confirm 时写入
    "rows": [...],
    "inserted_count": 0,
    "updated_count": 0,
    "no_change_count": 0,
    "failed_count": 0,
    "executed_at": "2026-04-21T07:05:00Z",
    "execution_duration_ms": 1234
  },
  "supported_types": [...]                    // 兼容现有
}
```

[VERIFIED: 代码 backend/app/models/import_job.py / import_service.py / 31_01 alembic migration]

---

## hire_info / non_statutory_leave 字段映射对齐（IMPORT-01 实现细节）

### hire_info 落库目标 = `Employee` 表的两个字段

`backend/app/models/employee.py:28-29`：

```python
hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
last_salary_adjustment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
```

**注意：飞书同步的字段映射 `backend/app/services/feishu_service.py:1029-1034` 用的是「历史调薪日期」标签**（`'历史调薪日期': 'last_salary_adjustment_date'`），但 D-02 用的是「末次调薪日期」 — 这两个标签需要对齐。建议：
- 模板 alias 沿用 D-02 「末次调薪日期」（HR 视角更直觉）
- 飞书同步保持「历史调薪日期」不变（已有 production 配置不变更）
- 在 COLUMN_ALIASES 里**同时**接受两个标签，避免老用户的飞书绑定切换到 Excel 后失败

```python
COLUMN_ALIASES['hire_info'] = {
    '员工工号': 'employee_no',
    '入职日期': 'hire_date',
    '末次调薪日期': 'last_salary_adjustment_date',  # D-02 主推
    '历史调薪日期': 'last_salary_adjustment_date',  # 兼容飞书同步标签
}
```

### `_import_hire_info` 实现参考

照抄 `_sync_hire_info_body`（feishu_service.py:1015-1130）的 4 个分支：
1. `employee_no` 找不到 → row 标 `failed` + `'未找到员工工号'`
2. `hire_date` / `last_salary_adjustment_date` 都为空：
   - merge 模式：no_change（未提供新数据）
   - replace 模式：no_change（时间戳字段 replace 也保留，见 CONTEXT D-子提示）
3. `hire_date` 解析失败 → row 标 `failed` + `'入职日期格式无效: ...'`
4. 成功 → 更新 Employee 表对应字段，标 `success` (insert/update by `did_change`)

**Excel 序列化日期处理（实测踩坑）：** `pd.read_excel(dtype=str)` 会把 Excel 日期单元格 `2024-01-01` 显示为字符串 `'45292'`（Excel 序列号）。`pd.to_datetime('45292')` 会抛 `DateParseError: year must be in 1..9999`。正确处理：

```python
# 实测验证：参考 _sync_hire_info_body 的双分支模式
def _parse_excel_date(value):
    if isinstance(value, (int, float)):
        return pd.to_datetime(value, unit='D', origin='1899-12-30').date()
    s = str(value).strip()
    if s.isdigit() and 5 <= len(s) <= 6:  # Excel serial range
        return pd.to_datetime(int(s), unit='D', origin='1899-12-30').date()
    return pd.to_datetime(s).date()
```

但飞书同步的 `_sync_hire_info_body` line 1080-1085 有更简单的判断（`isinstance(value, (int, float))`），是因为飞书 SDK 直接返回数字。Excel + `pd.read_excel(dtype=str)` 会把所有单元格转 str，所以 ImportService 必须额外做 isdigit 检测。

[VERIFIED: 实测 .venv/bin/python with pd.to_datetime('45292') → DateParseError]

### non_statutory_leave 落库目标 = `NonStatutoryLeave` 表

`backend/app/models/non_statutory_leave.py`：
- `__table_args__ = (UniqueConstraint('employee_id', 'year', name='uq_leave_employee_year'),)`
- `total_days: Mapped[Decimal] = mapped_column(Numeric(6, 1))` ← 注意是 **Decimal 不是 float**（精度 0.5 天）
- `leave_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment='事假/病假/其他')`

**`_import_non_statutory_leave` 实现要点：**
1. upsert by `(employee_id, year)`（已有 unique constraint，可用 `select` + `merge`）
2. `total_days` 必须用 `Decimal(str(value))` 转换（避免 float 精度，参考 `_import_salary_adjustments:825` 用 `Decimal(str(raw_amount).strip())`）
3. `leave_type` 可选，且不强校验枚举（飞书同步也未校验，line 1242-1247）
4. `year` 用 `int(float(str(raw_year)))` 容错（参考飞书同步 line 1219）

[VERIFIED: 代码 feishu_service.py:1015-1291 / non_statutory_leave.py / salary_adjustment_record.py]

---

## Phase 31 锁模式直接抄什么（IMPORT-06 实现细节）

### 锁实现：直接照抄 `is_sync_running`

`backend/app/services/feishu_service.py:1685-1696`：

```python
def is_sync_running(self, sync_type: str | None = None) -> bool:
    stmt = select(FeishuSyncLog).where(FeishuSyncLog.status == 'running')
    if sync_type is not None:
        stmt = stmt.where(FeishuSyncLog.sync_type == sync_type)
    return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None
```

**对应的 ImportService 实现：**

```python
def is_import_running(self, import_type: str | None = None) -> bool:
    """D-16: 检测同 import_type 是否有 'previewing' 或 'processing' 状态的 job。"""
    stmt = select(ImportJob).where(
        ImportJob.status.in_(['previewing', 'processing'])
    )
    if import_type is not None:
        stmt = stmt.where(ImportJob.import_type == import_type)
    return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None
```

**注意 D-16 锁定 `previewing` 也持锁** — 这与 Phase 31 仅锁 `running` 不同。理由：HR A 预览过程中，HR B 不能强行 confirm 同类型；防止 preview 阶段的文件被覆盖。

### 僵尸清理：照抄 `expire_stale_running_logs` 但分双时限

`backend/app/services/feishu_service.py:1698-1717`：

```python
def expire_stale_import_jobs(
    self,
    *,
    processing_timeout_minutes: int = 30,   # D-17 same as feishu
    previewing_timeout_minutes: int = 60,   # D-17 一小时
) -> dict[str, int]:
    """D-17: 双时限 — processing 超 30 分钟 → failed；previewing 超 1 小时 → cancelled + 删文件。"""
    now = datetime.now(timezone.utc)
    expired = {'processing': 0, 'previewing': 0}

    # processing 超时
    cutoff_p = now - timedelta(minutes=processing_timeout_minutes)
    stale_p = list(self.db.execute(
        select(ImportJob).where(
            ImportJob.status == 'processing',
            ImportJob.created_at < cutoff_p,
        )
    ).scalars().all())
    for job in stale_p:
        job.status = 'failed'
        job.result_summary = {**(job.result_summary or {}), 'error': 'timeout'}
    expired['processing'] = len(stale_p)

    # previewing 超时 + 删文件
    cutoff_v = now - timedelta(minutes=previewing_timeout_minutes)
    stale_v = list(self.db.execute(
        select(ImportJob).where(
            ImportJob.status == 'previewing',
            ImportJob.created_at < cutoff_v,
        )
    ).scalars().all())
    for job in stale_v:
        job.status = 'cancelled'
        # 删除 uploads/imports/{job_id}.xlsx，try/except 内吞异常
        try:
            self._delete_staged_file(job.id)
        except Exception:
            logger.exception('Failed to delete staged file for job %s', job.id)
    expired['previewing'] = len(stale_v)

    if stale_p or stale_v:
        self.db.commit()
    return expired
```

### `_with_sync_log` 是否抄

**不抄。** Phase 31 的 helper 是用独立 SessionLocal() 把 sync log 的「生命周期事务」与「业务事务」隔离（`feishu_service.py:379-491`），这样 sync log 即使业务 rollback 也能写终态。

ImportJob 的两阶段提交不需要这个隔离：
- 阶段 1（preview）：写 ImportJob row + 存文件 + 返回 — **业务成功才 commit**，业务失败时 ImportJob 不应该存在
- 阶段 2（confirm）：读文件 + 落库 + 更新 ImportJob — 业务事务和 ImportJob 的 status 更新可以共享同一 session

唯一可能需要独立 session 的场景是 D-17 僵尸清理（Beat 任务），但 Celery task 默认就用独立 SessionLocal()（参考 `feishu_sync_eligibility_task` 模式），无需 helper 抽象。

### Celery Beat vs APScheduler（D-17 技术选型）

当前项目状态：

| 调度器 | 状态 | 适用场景 |
|--------|------|---------|
| Celery + Redis | ✅ 已配置 worker（`backend/app/celery_app.py`），**未配置 beat_schedule** | 异步任务执行（已用于 import / feishu sync / evaluation） |
| APScheduler | ✅ 已用于飞书定时同步（`backend/app/scheduler/feishu_scheduler.py:9`） | 应用进程内的定时任务（依赖 ASGI lifespan 启动） |

**两种实现方案对比：**

| 维度 | Celery Beat | APScheduler |
|------|-------------|-------------|
| 部署复杂度 | 需新启 `celery beat` 进程 | 复用现有 ASGI 进程 |
| 多实例部署 | Beat 单点（多实例需 redbeat 等扩展） | 同样单点（lifespan 起在第一个 worker） |
| 重启行为 | Redis 持久化任务时间 | 内存调度，重启后从下一个 cron 时间开始 |
| 与现有代码契合 | Phase 31 D-17 文档说"Celery Beat" | 现有 `feishu_scheduler.py` 模式可直接复用 |
| 测试友好度 | 需 mock celery_app | `scheduler.add_job` 可单测 |

**推荐：选 APScheduler**（复用 `feishu_scheduler.py` 的 `add_job` 模式新增一个 cron job，每 15 分钟跑一次 `expire_stale_import_jobs`）。理由：
1. 部署不增加新进程
2. Phase 30/31 已确立 APScheduler 为「轻量定时任务」首选
3. CONTEXT.md D-17 写的 "Celery Beat" 应理解为「定时任务」而非具体技术，APScheduler 等价

**如果一定要选 Celery Beat**：需在 `celery_app.py` 加 `beat_schedule` 配置 + 文档明确启动 `celery -A backend.app.celery_app beat` 命令 + 部署文档更新。

[VERIFIED: backend/app/celery_app.py / scheduler/feishu_scheduler.py / Phase 31 D-15/D-16/D-17]

---

## 两阶段提交实现路径（IMPORT-07 + D-06 / D-07）

### API 路由设计（`backend/app/api/v1/eligibility_import.py`）

| Method | Path | 功能 | Status Code |
|--------|------|------|-------------|
| POST | `/eligibility-import/excel/preview` | 上传 + 解析 + 返回 PreviewResponse + 暂存文件 | 200 |
| POST | `/eligibility-import/excel/{job_id}/confirm` | 读暂存文件 + 落库 + 写 AuditLog + 删文件 | 200 |
| POST | `/eligibility-import/excel/{job_id}/cancel` | 删暂存文件 + 标 cancelled | 204 |
| GET | `/eligibility-import/excel/active?import_type=X` | D-18 查询活跃 job | 200 |

**当前 `POST /eligibility-import/excel`**（`backend/app/api/v1/eligibility_import.py:33-60`）一步完成上传→Celery→落库；本期需要**保留**（兼容性）但**改为透传到 preview**（直接返回 preview 给前端，前端自动调 confirm 视为同步语义）— 也可以选择标 deprecated 加 warning header，由规划阶段决议。

### 文件暂存目录与命名

按 D-06 + 安全规范（`backend/app/core/storage.py:23-30` 已实现路径遍历防护）：

```python
# 推荐放在 ImportService 里
class ImportService:
    @staticmethod
    def _staged_file_path(job_id: str) -> Path:
        # job_id 是 UUID，无路径遍历风险（line 4 of import_job.py 继承 UUIDPrimaryKeyMixin）
        # 但保险起见仍用 Path.resolve + is_relative_to 检查
        base = Path(get_settings().storage_base_dir).resolve() / 'imports'
        base.mkdir(parents=True, exist_ok=True)
        target = (base / f'{job_id}.xlsx').resolve()
        if not target.is_relative_to(base):
            raise ValueError(f'Staged file path escapes base: {job_id!r}')
        return target

    def _save_staged_file(self, job_id: str, content: bytes) -> None:
        self._staged_file_path(job_id).write_bytes(content)

    def _read_staged_file(self, job_id: str) -> bytes:
        path = self._staged_file_path(job_id)
        if not path.exists():
            raise ValueError(f'Staged file for job {job_id} not found (expired or deleted)')
        return path.read_bytes()

    def _delete_staged_file(self, job_id: str) -> None:
        path = self._staged_file_path(job_id)
        if path.exists():
            path.unlink()
```

`storage_base_dir` 默认值 `'uploads'`（`backend/app/core/config.py:35`），所以暂存目录 = `uploads/imports/`。

### 失败模式（必须在测试覆盖）

| # | 场景 | 期望行为 | 实现要点 |
|---|------|----------|---------|
| F1 | HR 上传后崩溃（preview 已写但 confirm 没来） | 1 小时后 expire_stale_import_jobs 标 cancelled + 删文件 | D-17 |
| F2 | HR 长时间不 confirm | 同 F1 | 同 F1 |
| F3 | HR confirm 时文件被改（外部 mtime 变化） | 检查文件 hash（preview 时存 sha256，confirm 时校验）→ 不一致返回 409 + 提示「请重新上传」 | 推荐增加，CONTEXT 未明确 |
| F4 | HR 同时打开两个 Tab 上传同 import_type | 第二次 preview 触发 409（is_import_running 返回 True） | D-16 |
| F5 | HR 并发 confirm 同一个 job_id | 第一次成功，第二次因 status 已变 `processing/completed` 返回 409 「该 job 已确认或已完成」 | 在 confirm 端点增加 status 检查 |
| F6 | confirm 时业务失败（如部分行 IntegrityError） | job.status='partial'，AuditLog 仍写入但 detail 反映失败计数 | 复用 `run_import` 现有 partial/failed 逻辑 |
| F7 | confirm 后删文件失败（磁盘只读、权限） | logger.exception，但 confirm 整体不失败（已落库） | try/except 包裹 `_delete_staged_file` |
| F8 | 上传文件 > MAX_ROWS（5000） | preview 阶段就拒绝（沿用 line 219 的 ValueError） | 复用现有 |

**F3 的设计权衡：** 文件 hash 校验是「过度防御」还是「合理保险」？建议**做**，理由：
1. 暂存目录在本地磁盘，外部进程理论上可改（虽然实际不会）
2. 给 HR 一个明确「文件被改」的错误（vs 「数据不一致」的莫名错误）
3. 实现成本低（preview 时算 sha256 存 result_summary.preview，confirm 时对比）

### 冲突检测算法（D-09）

**冲突定义：** 同一 batch 文件内，相同业务键（D-14 表）出现 2 次以上。

实现方式：preview 阶段在 `_dispatch_import` 之前先做 dataframe 级 groupby：

```python
def _detect_in_file_conflicts(
    self, import_type: str, dataframe: pd.DataFrame
) -> dict[int, str]:
    """返回 {pandas_idx: conflict_reason} 映射。冲突行不进入 _import_*。"""
    business_keys = {
        'performance_grades': ['employee_no', 'year'],
        'salary_adjustments': ['employee_no', 'adjustment_date'],
        'hire_info': ['employee_no'],
        'non_statutory_leave': ['employee_no', 'year'],
    }
    keys = business_keys[import_type]
    if not all(k in dataframe.columns for k in keys):
        return {}  # 缺列已被 _dispatch_import 拦截
    # 按业务键分组，找出 count > 1 的 group
    duped = dataframe.groupby(keys).filter(lambda g: len(g) > 1)
    conflicts: dict[int, str] = {}
    for pandas_idx, row in duped.iterrows():
        key_str = ', '.join(f'{k}={row[k]}' for k in keys)
        conflicts[pandas_idx] = f'同文件内 ({key_str}) 出现多次，请仅保留一行后重新上传'
    return conflicts
```

### Preview 阶段算 diff 的策略

需要在不真正落库的情况下算 insert/update/no_change 计数 — 关键是**模拟 SAVEPOINT 但 rollback**？还是**仅查 DB 现状对比**？

**推荐：仅查 DB 现状对比**（不模拟落库），理由：
- 模拟落库需要走完整 `_import_*` 流程然后 rollback，但有些 row 失败会破坏 SAVEPOINT 嵌套
- 字段级 diff 只需要查现有 record，对比新 row 的字段值即可
- 计算复杂度 O(n) 单次查询（用 `WHERE employee_no IN (...)` 一次性 prefetch）

```python
def _build_preview(self, import_type: str, dataframe: pd.DataFrame) -> dict:
    # Step 1: 检测同文件内冲突（D-09）
    in_file_conflicts = self._detect_in_file_conflicts(import_type, dataframe)

    # Step 2: 一次性 prefetch 数据库现存 records（按业务键索引）
    prefetch = self._prefetch_existing_records(import_type, dataframe)
    # prefetch: dict[business_key_tuple, ORMRecord]

    # Step 3: 逐行对比，分类 insert/update/no_change/conflict
    counters = {'insert': 0, 'update': 0, 'no_change': 0, 'conflict': 0}
    rows: list[dict] = []
    for pandas_idx, row in dataframe.iterrows():
        if pandas_idx in in_file_conflicts:
            counters['conflict'] += 1
            rows.append({
                'row_number': int(pandas_idx) + 2,  # +2 因为 Excel 行号 = pandas_idx + 1（表头）+ 1
                'action': 'conflict',
                'employee_no': str(row.get('employee_no', '')),
                'conflict_reason': in_file_conflicts[pandas_idx],
            })
            continue
        # ... 对比逻辑
    return {'counters': counters, 'rows': rows[:200], 'rows_truncated': len(rows) > 200}
```

**注意 row_number 口径：** 既有代码 `_dispatch_import` line 626 / 711 / 763 用 `int(index) + 1`（pandas idx + 1 = 数据行号，HR 对照 Excel 时再加 1 跳过表头）。Preview 应保持口径一致 — **建议在 PreviewResponse 里直接给 `excel_row_number = pandas_idx + 2`**（含表头），减少前端二次计算。

### 200 行截断策略（D-07）

按 D-08「No-change 默认折叠」+ D-10「分页 50/页」逻辑：

```python
# Preview rows 排序：conflict 最前 → insert → update → no_change，便于前端默认展示
rows_sorted = sorted(all_rows, key=lambda r: {
    'conflict': 0, 'insert': 1, 'update': 2, 'no_change': 3
}[r['action']])
# 200 行截断 — 保留所有 conflict + insert + update，no_change 按剩余配额裁剪
```

[VERIFIED: 代码 import_service.py:438-476/626/711/763 + storage.py:23-30 + 实测 pandas date parsing]

---

## merge / replace 语义实现表（IMPORT-05 / D-12）

### 语义对照

| import_type | 字段 | 必填 | merge 模式 | replace 模式 |
|-------------|------|------|-----------|--------------|
| `hire_info` | `hire_date` | ✅ | 空值保留旧值 | 空值 → 行失败（必填不允许清空） |
| `hire_info` | `last_salary_adjustment_date` | ❌ | 空值保留旧值 | 空值保留旧值（**例外**：时间戳字段 replace 也保留，CONTEXT 自由区已确认） |
| `non_statutory_leave` | `total_days` | ✅ | 空值保留旧值 | 空值 → 行失败 |
| `non_statutory_leave` | `leave_type` | ❌ | 空值保留旧值 | 空值 → set NULL |
| `performance_grades` | `grade` | ✅ | 空值保留旧值（实际不会发生，必填） | 空值 → 行失败 |
| `salary_adjustments` | `amount` | ❌ | 空值保留旧值 | 空值 → set NULL |

### 实现位点

每个 `_import_*` 方法的 upsert 分支增加 `if overwrite_mode == 'replace': value = value or None` 转换，并在必填字段上加 `if not value and overwrite_mode == 'replace' and field in REQUIRED: raise ValueError(...)`。

### AuditLog 字段名修正（关键差异）

CONTEXT.md D-13 写的 `'resource_type': 'import_job'`、`'resource_id': job_id`，但 `backend/app/models/audit_log.py:21-23` 真实字段名是：

```python
action: Mapped[str] = mapped_column(String(128), ...)
target_type: Mapped[str] = mapped_column(String(64), ...)   # ← 不是 resource_type
target_id: Mapped[str] = mapped_column(String(36), ...)     # ← 不是 resource_id
detail: Mapped[dict] = mapped_column(JSON, ...)
operator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), ...)
operator_role: Mapped[Optional[str]]
request_id: Mapped[Optional[str]]
```

**正确写法：**

```python
audit_log = AuditLog(
    operator_id=current_user.id,        # ← 不是 actor_id
    operator_role=current_user.role,
    action='import_confirmed',
    target_type='import_job',           # ← 不是 resource_type
    target_id=job_id,                    # ← 不是 resource_id
    detail={
        'import_type': 'performance_grades',
        'overwrite_mode': 'merge',
        'file_name': 'grades_2026Q1.xlsx',
        'total_rows': 120,
        'inserted_count': 45,
        'updated_count': 72,
        'no_change_count': 2,
        'conflict_count': 1,
        'failed_count': 0,
    },
)
db.add(audit_log)
db.commit()
```

[VERIFIED: backend/app/models/audit_log.py 全文]

### `detail` 字段大小限制

`AuditLog.detail: Mapped[dict] = mapped_column(JSON)` — SQLAlchemy 的 `JSON` 类型在 SQLite 下是 `TEXT`（无长度限制），在 PostgreSQL 下是 `jsonb`（理论 1GB）。**实际限制是 .planning 中没有约束**。

**建议**：detail 不写完整 row diff（D-13 已锁定），只写计数 + 关键元数据。当前推荐 detail 大小 < 2KB，远低于 SQLite TEXT 单行限制（默认 1GB）。

---

## 前端 Blob 下载模式（IMPORT-02 / D-05）

### 已有参考（直接抄）

`frontend/src/services/feishuService.ts:69-83`：

```typescript
export async function downloadUnmatchedCsv(logId: string): Promise<void> {
  const response = await api.get<Blob>(`/feishu/sync-logs/${logId}/unmatched.csv`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sync-log-${logId}-unmatched.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
```

`frontend/src/services/importService.ts:20-23` 也已用 blob 模式（但只返回 Blob，前端调用方还需自己 saveAs）。

### `eligibilityImportService.getTemplateUrl` 改造

**当前实现**（`frontend/src/services/eligibilityImportService.ts:51-54`）返回 URL 字符串，被 `<a href={url} target="_blank">` 直接消费 → 浏览器把 .xlsx 当成二进制下载或直接渲染（取决于 Content-Disposition）。

**已知问题：**
- Safari 14+ 对带 attachment header 的二进制 URL 会先内嵌渲染再下载（用户体验差）
- `target="_blank"` 在某些 browser 弹出 popup blocker
- 不支持自定义文件名（依赖后端 Content-Disposition）
- 鉴权（JWT）通过 axios 拦截器加入 — 直接 `<a href>` 不带 token 会 401

**改造为：**

```typescript
export async function downloadTemplate(importType: EligibilityImportType): Promise<void> {
  const response = await api.get<Blob>(
    `/eligibility-import/templates/${importType}?format=xlsx`,
    { responseType: 'blob' },
  );
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${importType}_template.xlsx`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
```

### Safari/Edge 兼容性

经实测验证（Phase 31 已落地的 `downloadUnmatchedCsv`）：
- Safari 14+：✅ 兼容（`URL.createObjectURL` + `<a download>` 是标准 API）
- Edge（Chromium）：✅ 兼容
- Firefox：✅ 兼容
- IE 11：❌ 不支持 — 项目已在 desktop-first 范围内排除（UI-SPEC § Responsive）

**唯一已知坑：** iOS Safari 下载 binary 后用户必须主动「保存」（系统限制，无法自动），但 PC 端 Safari 无此问题。HR 都用 PC 端，不影响。

[VERIFIED: frontend/src/services/feishuService.ts:69-83 + importService.ts:20-23]

---

## eligibilityImportService 与 ExcelImportPanel 现有调用契约（前端改造范围）

### 当前 ExcelImportPanel 数据流

`frontend/src/components/eligibility-import/ExcelImportPanel.tsx`：

1. HR 拖拽/选择文件 → `setFile(selected)`（line 22-54）
2. 点击「开始导入」 → `uploadEligibilityExcel(importType, file)` → 拿到 `task_id`（line 72-86）
3. `useTaskPolling` 每 2 秒查 `/tasks/{task_id}` 状态（`useTaskPolling.ts:24`）
4. 完成后 `onResult(result)` 回调到 `ImportTabContent`（`ImportTabContent.tsx:49-52`）
5. 渲染 `ImportResultPanel`（`ImportTabContent.tsx:73-80`）

### 改造后状态机（参考 UI-SPEC § Component Inventory）

```typescript
type ImportFlowState =
  | { kind: 'idle' }
  | { kind: 'uploading'; file: File; progress?: number }
  | { kind: 'previewing'; jobId: string; preview: PreviewResponse; overwriteMode: 'merge' | 'replace' }
  | { kind: 'replace_confirming'; jobId: string; preview: PreviewResponse }  // modal open
  | { kind: 'confirming'; jobId: string; taskId?: string }  // 异步
  | { kind: 'done'; result: ImportConfirmResult }
  | { kind: 'cancelled' }
  | { kind: 'error'; message: string };
```

### 新加的 service 函数

```typescript
// eligibilityImportService.ts 需要新增
export async function uploadAndPreview(
  importType: EligibilityImportType,
  file: File,
): Promise<PreviewResponse>;

export async function confirmImport(
  jobId: string,
  overwriteMode: 'merge' | 'replace',
): Promise<ImportConfirmResult>;

export async function cancelImport(jobId: string): Promise<void>;

export async function getActiveImportJob(
  importType: EligibilityImportType,
): Promise<ActiveJobResponse>;

export async function downloadTemplate(
  importType: EligibilityImportType,
): Promise<void>;  // 替换 getTemplateUrl
```

### 与 useTaskPolling 的衔接

confirm 阶段如果异步（推荐异步，因为大文件可能 > 30 秒），返回 `task_id` 给前端 → `useTaskPolling` 复用现有逻辑。如果同步（小文件 < 5000 行实测 < 1 秒），直接返回结果，无需轮询。

**推荐：confirm 走 Celery 异步**（统一与既有上传一致的体验，HR 可以离开页面），但 preview 必须是同步（HR 等待 < 5 秒），不走 Celery（因为 Celery 任务的 result 通过 result backend 拉取，对返回 200KB JSON preview 是 overkill）。

[VERIFIED: frontend/src/components/eligibility-import/ExcelImportPanel.tsx + useTaskPolling.ts]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | `pytest.ini` (testpaths = backend/tests) |
| Quick run command | `.venv/bin/pytest backend/tests/test_services/test_import_*.py -x` |
| Full suite command | `.venv/bin/pytest backend/tests/ -x --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMPORT-01 | SUPPORTED_TYPES 含 6 类 | unit | `pytest backend/tests/test_services/test_import_service.py::test_supported_types_includes_all_six -x` | ❌ Wave 0 |
| IMPORT-01 | hire_info 模板可被 openpyxl 读回 | unit | `pytest backend/tests/test_services/test_import_xlsx.py::test_hire_info_template_loadable -x` | ❌ Wave 0 |
| IMPORT-01 | non_statutory_leave 模板可被 openpyxl 读回 | unit | `pytest backend/tests/test_services/test_import_xlsx.py::test_non_statutory_leave_template_loadable -x` | ❌ Wave 0 |
| IMPORT-01 | `_import_hire_info` 解析 Excel 序列日期 + ISO 字符串 | unit | `pytest backend/tests/test_services/test_import_hire_info.py -x` | ❌ Wave 0 |
| IMPORT-01 | `_import_non_statutory_leave` upsert by (employee_id, year) | unit | `pytest backend/tests/test_services/test_import_non_statutory_leave.py -x` | ❌ Wave 0 |
| IMPORT-02 | 4 类 import_type 模板下载返回非空 .xlsx | api | `pytest backend/tests/test_api/test_eligibility_import_template.py -x` | ❌ Wave 0 |
| IMPORT-02 | 前端 downloadTemplate 触发 blob 下载（手测） | manual | manual UAT in `32-VALIDATION.md` | manual |
| IMPORT-05 | merge 模式空值保留旧值（4 类 × 字段矩阵） | unit | `pytest backend/tests/test_services/test_import_overwrite_merge.py -x` | ❌ Wave 0 |
| IMPORT-05 | replace 模式空值清空可选字段、必填字段为空则失败 | unit | `pytest backend/tests/test_services/test_import_overwrite_replace.py -x` | ❌ Wave 0 |
| IMPORT-05 | confirm 写 AuditLog action='import_confirmed' detail 含 overwrite_mode | api | `pytest backend/tests/test_api/test_eligibility_import_audit.py -x` | ❌ Wave 0 |
| IMPORT-06 | `is_import_running(import_type)` 仅查 previewing+processing | unit | `pytest backend/tests/test_services/test_import_lock.py::test_is_import_running_filters_by_type -x` | ❌ Wave 0 |
| IMPORT-06 | preview 端点同 import_type 第二次返回 409 | api | `pytest backend/tests/test_api/test_eligibility_import_concurrency.py::test_preview_409_when_running -x` | ❌ Wave 0 |
| IMPORT-06 | confirm 端点同 import_type 第二次返回 409 | api | `pytest backend/tests/test_api/test_eligibility_import_concurrency.py::test_confirm_409_when_running -x` | ❌ Wave 0 |
| IMPORT-06 | 不同 import_type 可并行（preview hire_info + processing performance） | api | `pytest backend/tests/test_api/test_eligibility_import_concurrency.py::test_different_types_parallel -x` | ❌ Wave 0 |
| IMPORT-07 | preview 返回 PreviewResponse 结构（counters + rows + rows_truncated） | api | `pytest backend/tests/test_api/test_eligibility_import_preview.py::test_preview_response_shape -x` | ❌ Wave 0 |
| IMPORT-07 | preview 检测同文件内重复 → conflict 行 + 禁用 confirm | api | `pytest backend/tests/test_api/test_eligibility_import_preview.py::test_in_file_conflict_detection -x` | ❌ Wave 0 |
| IMPORT-07 | confirm 后 ImportJob.status 变 completed/partial/failed | api | `pytest backend/tests/test_api/test_eligibility_import_confirm.py -x` | ❌ Wave 0 |
| IMPORT-07 | 重复 confirm 同一 job_id 第二次返回 409 | api | `pytest backend/tests/test_api/test_eligibility_import_confirm.py::test_double_confirm_rejected -x` | ❌ Wave 0 |
| 集成 | expire_stale_import_jobs 双时限清理（30min processing + 60min previewing + 删文件） | unit | `pytest backend/tests/test_services/test_import_expire_stale.py -x` | ❌ Wave 0 |
| 集成 | 文件 hash 校验：confirm 时文件被改 → 409 | unit | `pytest backend/tests/test_services/test_import_file_hash.py -x` | ❌ Wave 0 |
| 集成 | 暂存文件路径不可逃逸 base_dir | unit | `pytest backend/tests/test_services/test_import_staged_path_safety.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_services/test_import_*.py -x`（ImportService 范围，约 5 秒）
- **Per wave merge:** `pytest backend/tests/ -x --tb=short -q`（全套，约 60-90 秒）
- **Phase gate:** 全套绿色 + 4 个手动 UAT 通过（前端模板下载 / Preview 抽屉 / Modal 焦点循环 / 409 toast）才能 `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_services/test_import_hire_info.py` — `_import_hire_info` 单测（Excel 日期序列 / ISO 字符串 / merge / replace / 必填空值 → failed）
- [ ] `backend/tests/test_services/test_import_non_statutory_leave.py` — `_import_non_statutory_leave` 单测（upsert by year / Decimal 精度 / leave_type 可选）
- [ ] `backend/tests/test_services/test_import_lock.py` — `is_import_running` 单测（参考 `test_feishu_per_sync_type_lock.py` 模板）
- [ ] `backend/tests/test_services/test_import_expire_stale.py` — `expire_stale_import_jobs` 单测（参考 `test_feishu_expire_stale.py` 模板）
- [ ] `backend/tests/test_services/test_import_overwrite_merge.py` / `test_import_overwrite_replace.py` — 4 类 × 字段矩阵
- [ ] `backend/tests/test_services/test_import_file_hash.py` — 文件 hash 校验
- [ ] `backend/tests/test_services/test_import_staged_path_safety.py` — `_staged_file_path` 防路径遍历
- [ ] `backend/tests/test_api/test_eligibility_import_preview.py` — Preview 端点 + 冲突检测 + 200 行截断
- [ ] `backend/tests/test_api/test_eligibility_import_confirm.py` — Confirm 端点 + AuditLog + 双 confirm 409
- [ ] `backend/tests/test_api/test_eligibility_import_concurrency.py` — 4 个并发场景（参考 Phase 31 锁测试）
- [ ] `backend/tests/test_api/test_eligibility_import_template.py` — 6 类 import_type 模板下载（4 类资格 + 2 类 employees/certifications 兼容）
- [ ] `backend/tests/test_api/test_eligibility_import_audit.py` — AuditLog 字段断言
- [ ] `backend/tests/test_api/test_eligibility_import_active.py` — `GET /excel/active` 端点
- [ ] 手动 UAT 清单（写在 `32-VALIDATION.md`）：模板下载（Safari/Chrome/Edge）/ Preview 抽屉键盘可达 / Modal focus trap / 409 toast 显示与冷却 5 秒

---

## Common Pitfalls

### Pitfall 1: Excel 序列日期通过 `dtype=str` 读出来仍是数字字符串

**What goes wrong:** HR 在 Excel 单元格里输入 `2024-01-01`，Excel 把它存成内部序列号 `45292`。`pd.read_excel(file, dtype=str)` 读出来是字符串 `'45292'`（不是 `'2024-01-01'`）。后续 `pd.to_datetime('45292')` 抛 `DateParseError: year must be in 1..9999`。

**Why it happens:** `dtype=str` 只阻止 pandas 做类型推断，但 Excel 单元格底层就是数字格式，pandas 看到的就是 `45292`。`pd.to_datetime` 默认按 ISO 8601 字符串解析。

**How to avoid:** 在 `_import_hire_info` / `_import_salary_adjustments` 加 `_parse_excel_date` helper，先判断 isdigit + 长度 5-6（Excel serial 范围），用 `pd.to_datetime(int(s), unit='D', origin='1899-12-30')` 转换；否则按 ISO 字符串解析。

**Warning signs:** `pd.read_excel(dtype=str)` + `pd.to_datetime(value)` 直接调用、单测里没有「Excel 单元格输入日期 → 序列号 45292」用例。

[VERIFIED: 实测 .venv/bin/python 验证 DateParseError]

### Pitfall 2: ImportJob 状态机迁移破坏现有 status 检查

**What goes wrong:** 加完 `'previewing'` / `'cancelled'` 状态后，前端某处 `if job.status === 'completed' || job.status === 'failed'` 判断完成态会漏掉新状态，导致 UI 永远显示 loading。

**Why it happens:** status 字段是字符串枚举（DB 层无约束），新增值不会触发编译错误。

**How to avoid:**
- TypeScript 层：在 `frontend/src/types/api.ts` 给 `ImportJobStatus` 加 union type `'pending' | 'previewing' | 'processing' | 'completed' | 'failed' | 'partial' | 'cancelled'` —— 让 tsc strict 模式拦截缺失分支
- 后端：在 `ImportService` 加 `_TERMINAL_STATUSES = frozenset({'completed', 'failed', 'partial', 'cancelled'})` 常量，所有「完成态判断」用此常量
- 测试：grep `'completed'` 检查所有判断点是否需要更新

**Warning signs:** 前端有任何 `job.status === 'completed'` 单值判断、frontend 类型未同步更新。

### Pitfall 3: 文件路径遍历漏洞

**What goes wrong:** 如果 confirm 端点接受用户传入的 `job_id` 后未做安全检查，恶意用户传 `../../etc/passwd` 作为 job_id 读到任意文件。

**Why it happens:** `Path('uploads/imports') / f'{job_id}.xlsx'` 在 job_id 含 `../` 时不会自动 resolve。

**How to avoid:** 复用 `backend/app/core/storage.py:23-30` 的 `is_relative_to` 检查模式。job_id 来自 ImportJob 表（UUID4，不可能含 `/`），但 defense in depth 仍要做检查。

**Warning signs:** 没有 `target.resolve().is_relative_to(base_dir.resolve())` 检查。

### Pitfall 4: SalaryAdjustmentRecord 缺 UniqueConstraint 导致 D-14 业务键失效

**What goes wrong:** `_import_salary_adjustments` 当前是 append 而非 upsert（line 830-838），D-14 文档说业务键是 `(employee_id, adjustment_date)`，但 DB 仅是 Index（line 19-20），无 unique 约束。如果改为 upsert 但不加约束，并发竞态会插入两条相同 (employee_id, adjustment_date) 记录，破坏「同一员工同一日期只有一条」约定。

**Why it happens:** 业务键约束设计在迁移阶段被遗漏；append 模式相当于「重复导入产生历史记录」。

**How to avoid:**
- **决议点（必须在 plan 阶段定）：** 一天多次调薪算合法业务还是异常？
  - 选项 A：保持 append（现状），D-14 调整为「无业务键，重复导入产生重复行」
  - 选项 B：改为 upsert by `(employee_id, adjustment_date, adjustment_type)`（与飞书同步 line 947-952 一致），加 UniqueConstraint
  - 推荐 B（与飞书同步行为对齐），但要：(1) 在 plan 阶段确认 HR 不需要历史多记录；(2) Wave 1 先 dedup 现有数据再加约束（参考 v1.4 Phase 30 处理方式）

**Warning signs:** salary_adjustments 导入两次相同数据，DB 行数翻倍。

[VERIFIED: salary_adjustment_record.py:19-20 + import_service.py:830-838 + feishu_service.py:947-952]

### Pitfall 5: window.open(xlsx URL) 浏览器渲染乱码

**What goes wrong:** 当前 `getTemplateUrl` 返回 URL，被 `<a href={url} target="_blank">` 消费，部分浏览器（特别是 Safari）会先尝试在新 Tab 内嵌渲染 .xlsx 二进制，显示乱码。

**Why it happens:** Content-Disposition: attachment 在 Safari 下不一定强制下载（取决于版本和用户设置）。

**How to avoid:** D-05 已锁定改 `responseType: 'blob'` + `URL.createObjectURL` + 临时 `<a download>` 触发下载。Phase 31 已落地此模式（`feishuService.downloadUnmatchedCsv`），直接抄。

**Warning signs:** axios.get(url) 没有 `responseType: 'blob'` 或前端用 `<a href={url}>` 直链。

### Pitfall 6: AuditLog 字段名误用 resource_type/resource_id

**What goes wrong:** CONTEXT.md D-13 写的字段名 `resource_type` / `resource_id` 在真实模型不存在（实际是 `target_type` / `target_id`），代码写下去会 SQLAlchemy 报错或 silently 不写入。

**Why it happens:** 不同代码库约定不同字段名（v1.0 Phase 4 已落地 target_*）。

**How to avoid:** 严格按 `backend/app/models/audit_log.py` 字段名实现，文档中的 D-13 字段名仅是「概念示意」。

[VERIFIED: backend/app/models/audit_log.py 全文]

### Pitfall 7: openpyxl 写大文件性能

**What goes wrong:** 当 import 行数 > 1000，preview 阶段需要再生成一个 result xlsx 给 HR 下载，openpyxl 的 `wb.save(buf)` 慢。

**Why it happens:** openpyxl 默认 write_only=False，写入时构建完整 DOM 后序列化。

**How to avoid:** **本期不需要担心**：
- 实测：5000 行 × 5 列耗时 0.19 秒，size=101KB（Mac M1）
- preview 阶段不需要写新 xlsx（只读 + 返回 JSON）
- confirm 阶段只更新 ImportJob，不写新 xlsx
- 仅在 `build_export_report_xlsx` 失败导出时写 — 已有功能，本期不动

[VERIFIED: 实测 .venv/bin/python，5000 行 0.19 秒]

### Pitfall 8: pandas 读 xlsx 全部转 str 丢失类型信息

**What goes wrong:** `pd.read_excel(buf, dtype=str)` 把 `total_days = 10.5` 读成字符串 `'10.5'`，后续如果直接 `Decimal(value)` 容错，但如果 `int(value)` 会失败（`int('10.5')` ValueError）。

**Why it happens:** Phase 30 为了防工号前导零丢失，全部 dtype=str。

**How to avoid:** 数值字段用 `Decimal(str(value).strip())` 不是 `int(value)` 不是 `float(value)`。年份字段用 `int(float(str(value)))` 三层转换（参考飞书同步 line 1219）。

**Warning signs:** `int(row['total_days'])` 之类的直接转换。

### Pitfall 9: Celery 任务内 SessionLocal() 不关闭导致连接泄漏

**What goes wrong:** confirm 阶段如果走 Celery 异步任务，没正确 try/finally close session 会泄漏 DB 连接。

**Why it happens:** 复制粘贴时漏掉 finally 块。

**How to avoid:** 严格按 `import_tasks.py:37-64` 模板：
```python
db = SessionLocal()
try:
    # ...
finally:
    db.close()
```

### Pitfall 10: HR confirm 时 result_summary 被两阶段覆盖

**What goes wrong:** preview 阶段写 `result_summary['preview'] = {...}`，confirm 阶段 `result_summary = {...}` 直接赋值会丢失 preview 数据。

**Why it happens:** 字典赋值不会自动 merge。

**How to avoid:** confirm 阶段用 `job.result_summary = {**job.result_summary, 'execution': {...}}` 保留 preview 数据。注意 SQLAlchemy 的 JSON 字段需要重新赋值才会触发 dirty flag（不能 in-place mutate），用 `flag_modified(job, 'result_summary')` 也行。

---

## Code Examples

### Example 1: Phase 31 风格的 ImportService.is_import_running

```python
# Source: backend/app/services/feishu_service.py:1685-1696（Phase 31 既定模式）
# Target: backend/app/services/import_service.py（新加方法）

def is_import_running(self, import_type: str | None = None) -> bool:
    """D-16: 检测同 import_type 是否有 'previewing' 或 'processing' 状态的 job。"""
    stmt = select(ImportJob).where(
        ImportJob.status.in_(['previewing', 'processing'])
    )
    if import_type is not None:
        stmt = stmt.where(ImportJob.import_type == import_type)
    return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None
```

### Example 2: API 端点 409 + expire_stale 模式

```python
# Source: backend/app/api/v1/feishu.py:208-238（Phase 31 既定模式）
# Target: backend/app/api/v1/eligibility_import.py（新端点）

@router.post('/excel/preview')
def preview_excel_import(
    import_type: str,
    file: UploadFile = File(...),
    current_user=Depends(require_roles('admin', 'hrbp')),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    if import_type not in ELIGIBILITY_IMPORT_TYPES:
        raise HTTPException(status_code=400, detail='Unsupported import type.')

    service = ImportService(db, operator_id=str(current_user.id), operator_role=current_user.role)

    # D-17: 先清理僵尸 job（防止 1 小时前 HR 关浏览器后锁不释放）
    service.expire_stale_import_jobs()

    # D-16: per-import_type 锁
    if service.is_import_running(import_type=import_type):
        raise HTTPException(
            status_code=409,
            detail={
                'error': 'import_in_progress',
                'import_type': import_type,
                'message': '该类型导入正在进行中，请稍后再试',
            },
        )

    # 实际 preview 逻辑
    raw_bytes = file.file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail='Uploaded file is empty.')

    return service.build_preview(
        import_type=import_type,
        file_name=file.filename or f'{import_type}.xlsx',
        raw_bytes=raw_bytes,
    )
```

### Example 3: Alembic 两阶段迁移（ImportJob 加 overwrite_mode）

```python
# Source: alembic/versions/31_01_feishu_sync_log_observability.py（既定模板）
# Target: alembic/versions/32_01_import_job_overwrite_mode.py

def upgrade() -> None:
    # Stage 1: add columns nullable=True (overwrite_mode) + with default (actor_id)
    with op.batch_alter_table('import_jobs') as batch_op:
        batch_op.add_column(sa.Column('overwrite_mode', sa.String(16), nullable=True))
        batch_op.add_column(sa.Column('actor_id', sa.String(36), nullable=True))
        # Optional: FK to users.id with ON DELETE SET NULL（兼容历史数据）
        batch_op.create_foreign_key(
            'fk_import_jobs_actor_id', 'users', ['actor_id'], ['id'],
            ondelete='SET NULL',
        )
        batch_op.add_column(sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ))

    # Stage 2: backfill historical rows
    op.execute("UPDATE import_jobs SET overwrite_mode = 'merge' WHERE overwrite_mode IS NULL")

    # Stage 3: enforce NOT NULL on overwrite_mode
    with op.batch_alter_table('import_jobs') as batch_op:
        batch_op.alter_column(
            'overwrite_mode', existing_type=sa.String(16), nullable=False,
        )
```

### Example 4: 暂存文件路径安全（防路径遍历）

```python
# Source: backend/app/core/storage.py:23-30（既定模式）
# Target: backend/app/services/import_service.py（新方法）

@staticmethod
def _staged_file_path(job_id: str) -> Path:
    """安全的暂存文件路径，防路径遍历。"""
    base = (Path(get_settings().storage_base_dir).resolve() / 'imports').resolve()
    base.mkdir(parents=True, exist_ok=True)
    target = (base / f'{job_id}.xlsx').resolve()
    if not target.is_relative_to(base):
        raise ValueError(f'Staged file path escapes base_dir: {job_id!r}')
    return target
```

[CITED: backend/app/core/storage.py:23-30 + Phase 31 alembic template]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 全部 | ✓ | 3.14（实测）/项目支持 3.9+ | — |
| openpyxl | 模板生成 + xlsx 解析 | ✓ | 3.1.5（实测） | — |
| pandas | xlsx 读入 + diff | ✓ | 3.0.2（实测）⚠️ 较新版 | 降级到 2.x — 不需要 |
| SQLAlchemy | DB | ✓ | 2.0.36（CLAUDE.md） | — |
| Alembic | migrations | ✓ | 1.14.0 | — |
| celery | 异步任务 | ✓ | 5.6.3（实测） | 同步 fallback（preview 已是同步） |
| Redis | celery broker | 假设可用 | — | dev 用 Redis 必须本地起 |
| FastAPI | API | ✓ | 0.115.0 | — |
| pydantic v2 | schemas | ✓ | 2.10.3 | — |
| APScheduler | 定时任务（D-17） | ✓ | 已用于 feishu_scheduler | Celery Beat（需新部署） |
| axios | 前端 HTTP | ✓ | 1.8.4 | — |
| Vite + React | 前端 | ✓ | 6.2.6 + 18.3.1 | — |

**Missing dependencies with no fallback:** 无

**Missing dependencies with fallback:**
- D-17 定时清理：选 APScheduler（已有）vs Celery Beat（需新增 beat 进程） — 推荐 APScheduler

[VERIFIED: 实测 .venv/bin/python -c "import openpyxl, pandas, celery; print(...)"]

---

## Project Constraints (from CLAUDE.md)

| 规则 | 本期落实方式 |
|------|-------------|
| 后端 Python + FastAPI 为核心 | ✅ ImportService 改造保持 service/api/models 分层 |
| 所有评分、系数、阈值、认证规则必须配置化 | ✅ overwrite_mode 默认值/超时分钟数/Preview 200 行截断 都通过常量或 Settings 配置（不硬编码） |
| 上传解析、评分引擎、API 输出之间必须通过明确的 Schema 对接 | ✅ PreviewResponse / ImportConfirmResult / ActiveJobResponse 都用 Pydantic v2 BaseModel |
| 所有关键业务结果都应可审计、可解释、可追踪 | ✅ AuditLog action='import_confirmed' 写入完整 detail；ImportJob.result_summary 保留 preview + execution 两阶段 |
| 对外 API 要保持版本化 `/api/v1/...` | ✅ 新端点全部挂在 `/api/v1/eligibility-import/excel/...` |
| 批量导入必须考虑幂等性、校验错误回传和部分成功场景 | ✅ D-14 业务键 upsert + partial status + AuditLog detail.failed_count |
| 涉及 AI 评估的改动 | N/A（本期不涉及 AI） |
| 模板字段定义 | ✅ D-02/D-03 字段集已锁，REQUIRED_COLUMNS / COLUMN_ALIASES 同步 |
| Pydantic v2 + SQLAlchemy 2.0 | ✅ 所有新 schema 用 `model_config = ConfigDict(from_attributes=True)`，新模型用 `Mapped[T]` |
| 中文注释/输出 | ✅ 所有错误文案、AuditLog 都中文 |

CLAUDE.md 中其他强制条款（Step 1-6 工作流、Step 4 Testing Requirements 5 子项、Blocking Issues 模板）属于 GSD 工作流自带覆盖，本期不重复。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_import_salary_adjustments` 改为 upsert by `(employee_id, adjustment_date, adjustment_type)` 业务上无副作用 | Pitfall 4 / SUPPORTED_TYPES | 若 HR 业务上要求保留多次调薪历史（如同一日跨级别调薪），改 upsert 会丢数据 — 需在 plan 阶段确认 |
| A2 | APScheduler 适合 D-17 僵尸清理（vs Celery Beat） | Phase 31 锁模式直接抄什么 | 若部署架构不允许应用进程内调度（如多实例无 leader 选举），需切 Celery Beat |
| A3 | uploads/imports/ 目录使用本地磁盘（非 MinIO/S3） | 文件暂存目录与命名 | 若生产环境用对象存储，需改为 `LocalStorageService` 或自写 S3 暂存层 — CONTEXT 已锁本期用本地（Deferred Ideas） |
| A4 | 文件 hash 校验（preview 时存 sha256，confirm 时对比）是合理的 defense in depth | F3 失败模式 | 若 plan 阶段决议不做（节省 5 行代码），confirm 时文件被改的边缘场景不被检测 |
| A5 | confirm 阶段走 Celery 异步（与现有上传体验一致） | useTaskPolling 衔接 | 若小文件 < 100 行 confirm < 1 秒，前端轮询 Celery 反而慢 — 可在 plan 阶段决议「仅 > N 行走异步」 |
| A6 | row_number 在 PreviewResponse 直接给 Excel 行号（pandas_idx + 2） | 冲突检测算法 | 若前端期望接收 pandas idx，需在 plan 阶段对齐 |
| A7 | hire_info 的 `last_salary_adjustment_date` 在 replace 模式下也保留旧值（不清空） | merge / replace 语义实现表 | CONTEXT D-子提示已确认；若业务方不同意，需重新讨论 |

**确认建议**：A1 与 A4 应在 plan 阶段以「需要决议」形式列出，由用户最终拍板。

---

## Open Questions (RESOLVED)

> 全部 5 个 OQ 已在 plan 阶段拍板。详见各 OQ 段首的 **RESOLVED** 行。

1. **`_import_salary_adjustments` 是否改 upsert？**

   **RESOLVED:** _import_salary_adjustments 改 upsert，业务键 (employee_id, adjustment_date, adjustment_type)，与飞书同步对齐。Plan 32-01 加 UniqueConstraint（uq_salary_adj_employee_date_type），Plan 32-02 改 upsert。

   - 当前：append（line 830-838）
   - D-14 文档：upsert by `(employee_id, adjustment_date)`
   - 飞书同步：upsert by `(employee_id, adjustment_date, adjustment_type)`（line 947-952）
   - 推荐：选「飞书同步同款 3 字段业务键」+ Wave 1 alembic 加 UniqueConstraint
   - 阻塞：需 plan 阶段决议（A1）

2. **D-17 选 APScheduler 还是 Celery Beat？**

   **RESOLVED:** 选 APScheduler，复用 backend/app/scheduler/feishu_scheduler.py 模式，不引入 Celery Beat。Plan 32-06 实现（每 15 分钟跑 expire_stale_import_jobs）。

   - 推荐 APScheduler（无新部署成本）
   - 需要：plan 阶段确认部署方运维侧没有「禁止应用进程内调度」的要求

3. **confirm 端点走同步还是 Celery 异步？**

   **RESOLVED:** confirm 端点同步执行（< 5000 行实测 < 5 秒），避免轮询复杂度。Plan 32-03 service 层同步实现，Plan 32-04 API 层薄包装直接返回 ConfirmResponse。

   - 同步：< 5000 行实测 < 5 秒，HR 体验好（无轮询）
   - 异步：与现有上传体验一致，HR 可离开
   - 折中：< 500 行同步，>= 500 行异步（行数判断点配置化）

4. **当前 `POST /eligibility-import/excel`（一步上传）是否保留？**

   **RESOLVED:** 旧 POST /excel 保留并标 deprecated=True，新版前端不调用。Plan 32-04 在路由 decorator 加 deprecated=True，Plan 32-05/06 前端改用 uploadAndPreview + confirmImport 两阶段。

   - 保留：兼容性
   - 废弃：减少 API 表面积
   - 推荐：保留并标 `Deprecated`，规划期决议

5. **文件 hash 校验是否做？**

   **RESOLVED:** 做 sha256 文件 hash 校验，preview 时把哈希存到 ImportJob.result_summary.preview.file_sha256，confirm 时校验。Plan 32-03 实现（_save_staged_file 返回 sha256，_read_staged_file 接 expected_sha256 参数）。

   - 做：F3 边缘场景能检测，多 5 行代码
   - 不做：YAGNI，本地磁盘理论上不会被外部进程改
   - 推荐：做（成本低，价值高）

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 一步上传立即落库 | 两阶段 preview + confirm | Phase 32（本期） | HR 可见 diff，避免误覆盖 |
| `<a href={xlsxUrl} target="_blank">` | `axios.get(..., {responseType: 'blob'}) + URL.createObjectURL` | Phase 31 CSV 下载已落地 | Safari 不再渲染乱码，统一鉴权 |
| FeishuSyncLog 单一全局锁 | per-sync_type 分桶锁（D-15/D-16） | Phase 31 | 5 类同步可并行 |
| ImportJob 只承载 execution | 同时承载 preview + execution | Phase 32（本期） | 单条 record 完整链路 |

**Deprecated/outdated:**
- `getTemplateUrl(type)` 返回 URL：被 `downloadTemplate(type)` Promise<void> 取代
- 老 `POST /eligibility-import/excel`：可能标 deprecated 或并行保留（plan 决议）

---

## Sources

### Primary (HIGH confidence — 直接代码验证)
- `backend/app/services/import_service.py` 全文 — SUPPORTED_TYPES / _dispatch_import / _import_* / build_template_xlsx
- `backend/app/services/feishu_service.py:379-491, 700-1291, 1685-1717` — _with_sync_log / sync_*_body / is_sync_running / expire_stale_running_logs
- `backend/app/models/import_job.py` / `audit_log.py` / `performance_record.py` / `salary_adjustment_record.py` / `non_statutory_leave.py` / `employee.py` — 真实字段名与约束
- `backend/app/api/v1/eligibility_import.py` / `feishu.py:189-318` — 现有 API + Phase 31 锁/CSV 模式
- `backend/app/tasks/import_tasks.py` / `feishu_sync_tasks.py` — Celery 模式
- `backend/app/celery_app.py` / `backend/app/scheduler/feishu_scheduler.py` — 调度技术栈
- `backend/app/core/storage.py:23-30` — 路径遍历防护模式
- `alembic/versions/31_01_feishu_sync_log_observability.py` — 两阶段迁移模板
- `frontend/src/services/feishuService.ts:69-83` / `importService.ts:20-23` — blob 下载已落地模式
- `frontend/src/components/eligibility-import/ExcelImportPanel.tsx` / `ImportTabContent.tsx` — 现有前端契约
- `frontend/src/hooks/useTaskPolling.ts` — Celery 轮询模式
- `.planning/phases/31-feishu-sync-observability/31-CONTEXT.md` — D-15/D-16/D-17 锁模式
- `.planning/research/PITFALLS.md` — Pitfall 5/8/9/10/14/16（直接相关）
- `.planning/codebase/TESTING.md` — pytest 模式

### Secondary (MEDIUM confidence — 实测验证)
- 实测 `pd.to_datetime('45292')` 触发 DateParseError → Pitfall 1
- 实测 openpyxl 5000×5 cell 写入 0.19 秒 → Pitfall 7 不成立
- 实测 openpyxl 3.1.5 / pandas 3.0.2 / celery 5.6.3 在 .venv 内可用

### Tertiary (LOW confidence — 仅训练知识)
- iOS Safari 二进制下载需用户主动保存 — 实际 HR 用 PC 端，不影响

---

## Metadata

**Confidence breakdown:**
- 当前 ImportService 现状盘点：HIGH — 全文代码读取
- ImportJob 模型现状：HIGH — 模型代码读取
- Phase 31 锁模式参考：HIGH — Phase 31 已落地代码 + 测试通过
- 失败模式与并发场景：MEDIUM — 设计分析为主，需在 Wave 0 测试覆盖
- AuditLog 字段名差异：HIGH — 模型代码读取确认
- Excel 日期解析坑：HIGH — 实测验证
- APScheduler vs Celery Beat 决策：MEDIUM — 技术选型推荐，需 plan 阶段拍板
- merge/replace 语义矩阵：MEDIUM — 基于 D-12 推导，需 Wave 0 测试矩阵覆盖

**Research date:** 2026-04-21
**Valid until:** 2026-05-21（30 天，依赖技术栈稳定）

---

*Phase: 32-eligibility-import-completion*
*Researched: 2026-04-21*
