# Phase 6: 批量导入可靠性 - 研究 / Batch Import Reliability - Research

**研究日期 / Researched:** 2026-03-28
**领域 / Domain:** 批量数据导入、部分成功处理、编码兼容、Excel 模板生成
**置信度 / Confidence:** HIGH

## 摘要 / Summary

Phase 6 的核心目标是将现有的批量导入功能从"全成功或全失败"模式改造为**部分成功 + 逐行错误报告**模式。当前代码库（`ImportService`）已具备基础的逐行处理框架和编码检测逻辑，但缺少以下关键能力：(1) 每行独立 savepoint 以实现部分失败时有效行仍提交；(2) HTTP 207 Multi-Status 响应；(3) Excel (.xlsx) 文件读写支持（当前拒绝 xlsx）；(4) 5000 行限制校验；(5) 可下载的 Excel 错误报告。

现有代码已经实现了 employee_no upsert（员工导入的幂等性）和 certification 的 upsert（按 employee_id + certification_type），但员工导入在遇到行级异常时使用单一 `db.commit()` 在末尾提交——如果中途抛出未捕获异常，所有行都会回滚。需要改造为每行使用 `db.begin_nested()`（SAVEPOINT）包裹，确保单行失败不影响其他行。

**核心建议 / Primary recommendation:** 使用 SQLAlchemy `db.begin_nested()` 实现每行 SAVEPOINT，用 openpyxl（已安装 3.1.5）支持 xlsx 读写，API 层返回 HTTP 207 + 标准化响应体。

<user_constraints>
## 用户约束（来自 CONTEXT.md）/ User Constraints (from CONTEXT.md)

### 锁定决策 / Locked Decisions
- **D-01:** 失败行跳过并继续，不回滚成功行。最终返回 HTTP 207 Multi-Status，包含 total、success_count、failure_count、per-row errors。
- **D-02:** 失败行错误展示：页面表格 + 可下载 Excel 报告。页面上显示汇总统计和失败行表格，同时提供"下载错误报告"按钮生成 Excel 文件。
- **D-03:** 重复导入按工号 (employee_no) 匹配已有记录。已存在则覆盖更新，不存在则创建。审计日志记录更新操作。
- **D-04:** 模板同时提供 Excel (.xlsx) 和 CSV (UTF-8 BOM) 两种格式。Excel 模板自带列宽和示例行。
- **D-05:** 上传文件自动检测编码：依次尝试 UTF-8-sig -> UTF-8 -> GB18030 -> GBK。（已有代码实现）
- **D-06:** 单次导入最大 5000 行。超出时拒绝并提示"请分批导入，每批不超过 5000 行"。
- **D-07:** 同步处理 + 前端 loading 状态。API 同步执行导入，前端显示"导入中..."加载状态。
- **D-08:** 当前阶段仅支持员工 (employee) 和认证 (certification) 两种导入类型。

### Claude 自行决定 / Claude's Discretion
- 错误报告 Excel 的具体列设计和格式化
- 前端导入结果页面的具体布局
- 认证导入的幂等键设计（employee_no + certification_name 或其他）

### 延后事项（不在范围内）/ Deferred Ideas (OUT OF SCOPE)
- 异步导入 + 进度轮询（大文件场景，当 5000 行限制不够时）— 需要 Celery 任务队列
- 部门组织架构导入 — 新能力
- 薪资历史导入 — 新能力
- 导入任务的定时调度 — 新能力
</user_constraints>

<phase_requirements>
## 阶段需求 / Phase Requirements

| ID | 描述 / Description | 研究支持 / Research Support |
|----|---------------------|----------------------------|
| IMP-01 | 批量导入使用惰性验证，收集所有行级错误后一次性返回，不在第一个错误时中断 | 现有代码已逐行处理并 append 到 results 列表；需确保异常被 try/except 捕获而非冒泡 |
| IMP-02 | 批量导入使用每行独立 savepoint，有效行在部分失败时仍然提交，返回 HTTP 207 | 使用 SQLAlchemy `db.begin_nested()` 实现 SAVEPOINT；API 层改为 JSONResponse(status_code=207) |
| IMP-03 | 导入响应包含汇总信息：总行数、成功行数、失败行数，以及每条失败行的具体错误原因 | 现有 ImportJobRead schema 已有 total_rows/success_rows/failed_rows；result_summary.rows 已有逐行结构 |
| IMP-04 | 批量导入正确处理中文字符编码，支持 UTF-8 和 GBK/GB2312 格式的 Excel 文件 | CSV 编码检测已实现；需添加 openpyxl 读取 xlsx（openpyxl 3.1.5 已安装）|
| IMP-05 | 员工导入幂等——对 employee_no 进行 upsert，重复导入不产生重复数据 | 现有 `_import_employees` 已按 employee_no 查询并更新；需添加审计日志记录 |
| IMP-06 | 前端提供导入模板文件下载（包含必填列和示例数据的 Excel 格式）| 当前只有 CSV 模板；需用 openpyxl 生成 xlsx 模板带列宽和示例行 |
</phase_requirements>

## 标准技术栈 / Standard Stack

### 核心 / Core
| 库 / Library | 版本 / Version | 用途 / Purpose | 为何标准 / Why Standard |
|---------|---------|---------|--------------|
| openpyxl | 3.1.5（已安装） | Excel (.xlsx) 读写 | pandas 默认 Excel 引擎，已是项目依赖 |
| pandas | 2.2.3（已安装） | DataFrame 操作、CSV/Excel 解析 | 项目已用于导入流程 |
| SQLAlchemy | 2.0.36（已安装） | ORM、SAVEPOINT (begin_nested) | 项目核心 ORM |

### 辅助 / Supporting
| 库 / Library | 版本 / Version | 用途 / Purpose | 使用场景 / When to Use |
|---------|---------|---------|-------------|
| FastAPI JSONResponse | 0.115.0（已安装） | 返回自定义 HTTP 207 状态码 | API 层部分成功响应 |

### 无需新增依赖 / No New Dependencies Needed

所有需要的库均已安装。openpyxl 3.1.5 已在环境中但未列入 `requirements.txt`——需要添加。

**安装命令 / Installation:**
```bash
# openpyxl 已安装但需加入 requirements.txt
echo "openpyxl==3.1.5" >> requirements.txt
```

## 架构模式 / Architecture Patterns

### 现有代码结构 / Existing Code Structure
```
backend/app/
├── api/v1/imports.py          # API 路由层（需改造：207 响应）
├── services/import_service.py # 核心导入逻辑（需改造：savepoint、xlsx、5000行限制）
├── schemas/import_job.py      # Pydantic schema（需扩展：207 响应体）
├── models/import_job.py       # ImportJob ORM 模型（无需改动）
frontend/src/
├── pages/ImportCenter.tsx     # 导入中心页面（需改造：结果展示、错误表格）
├── components/import/ImportJobTable.tsx  # 任务列表组件（可能需扩展）
├── services/importService.ts  # API 调用层（需适配 207 响应）
```

### 模式 1: 每行 SAVEPOINT 部分成功 / Per-Row SAVEPOINT Partial Success
**概述:** 每行导入逻辑用 `db.begin_nested()` 包裹，失败时 rollback 到 savepoint，不影响其他行。
**使用场景:** `_import_employees` 和 `_import_certifications` 的逐行处理循环。
**示例:**
```python
for index, row in dataframe.iterrows():
    try:
        with db.begin_nested():  # SAVEPOINT
            # 解析 + 校验 + 写入
            employee = self._process_employee_row(row, index)
            db.add(employee)
        results.append({'row_index': int(index) + 1, 'status': 'success', 'message': '导入成功。'})
    except Exception as exc:
        results.append({'row_index': int(index) + 1, 'status': 'failed', 'message': str(exc)})
db.commit()  # 提交所有成功的行
```

### 模式 2: HTTP 207 Multi-Status 响应 / HTTP 207 Multi-Status Response
**概述:** 当有部分行失败时返回 207 而非 201。全部成功返回 201，全部失败返回 422 或 201（按 D-01 设计用 207）。
**示例:**
```python
from fastapi.responses import JSONResponse

# 在 API 层
job = service.run_import(import_type=import_type, upload=file)
response_data = ImportJobRead.model_validate(job).model_dump(mode='json')
if job.failed_rows > 0 and job.success_rows > 0:
    return JSONResponse(content=response_data, status_code=207)
elif job.failed_rows > 0 and job.success_rows == 0:
    return JSONResponse(content=response_data, status_code=207)
return JSONResponse(content=response_data, status_code=201)
```

### 模式 3: Excel 模板生成 / Excel Template Generation
**概述:** 用 openpyxl 生成带列宽、表头样式和示例行的 xlsx 模板。
**示例:**
```python
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

wb = Workbook()
ws = wb.active
ws.title = '员工导入模板'
headers = ['员工工号', '员工姓名', '身份证号', ...]
for col_idx, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_idx, value=header)
    cell.font = Font(bold=True)
    ws.column_dimensions[cell.column_letter].width = 18
# 示例行
ws.append(['EMP-1001', '张小明', '310101199001010123', ...])
output = io.BytesIO()
wb.save(output)
return output.getvalue()
```

### 反模式 / Anti-Patterns to Avoid
- **一次性 commit 所有行:** 任何一行异常会导致全部回滚——必须用 SAVEPOINT
- **在 API 层捕获 ValueError 返回 400:** 部分成功场景下不应整体失败，错误应在服务层逐行收集
- **用 CSV 代替 Excel 作为错误报告:** D-02 明确要求可下载 Excel 报告
- **硬编码 5000 行限制:** 应作为配置常量，但本阶段可用类级别常量

## 不要自行实现 / Don't Hand-Roll

| 问题 / Problem | 不要自建 / Don't Build | 使用替代 / Use Instead | 原因 / Why |
|---------|-------------|-------------|-----|
| Excel 读写 | 自定义 XML 解析 | openpyxl（已安装） | xlsx 是复杂的 ZIP/XML 格式 |
| CSV 编码检测 | 逐字节分析 | pandas + 编码回退链（已实现） | 边界情况极多 |
| SAVEPOINT 管理 | 原始 SQL | SQLAlchemy `begin_nested()` | 自动管理嵌套事务生命周期 |
| HTTP 207 响应 | 自定义中间件 | FastAPI `JSONResponse(status_code=207)` | 标准用法 |

## 常见陷阱 / Common Pitfalls

### 陷阱 1: SQLite SAVEPOINT 兼容性 / SQLite SAVEPOINT Compatibility
**问题:** SQLite 支持 SAVEPOINT，但 SQLAlchemy 的 `begin_nested()` 在 SQLite 上需要注意 autocommit 模式。
**原因:** SQLAlchemy 2.0 默认使用 AUTOBEGIN，`begin_nested()` 在活跃事务内工作正常。
**避免方式:** 确保在 `begin_nested()` 调用前已有活跃的外层事务（即已调用过 `db.begin()` 或处于 AUTOBEGIN 状态），在 commit 前不要关闭 session。
**警告信号:** `InvalidRequestError: This session is in 'inactive' state` 提示事务已结束。

### 陷阱 2: pandas read_excel 编码 / pandas read_excel Encoding
**问题:** `pd.read_excel()` 读取 xlsx 时不涉及编码问题（xlsx 内部是 UTF-8 XML），但读取旧版 xls 或 CSV 时需要编码处理。
**原因:** xlsx 是标准 UTF-8，编码检测只需应用于 CSV。
**避免方式:** xlsx 文件直接用 `pd.read_excel(io.BytesIO(raw_bytes), engine='openpyxl')`，仅对 CSV 走编码回退链。

### 陷阱 3: 大 DataFrame 内存 / Large DataFrame Memory
**问题:** 5000 行的 Excel 文件在内存中完全合理，但如果用户上传的行数远超 5000，DataFrame 仍会全部加载到内存。
**原因:** pandas 一次性读取整个文件。
**避免方式:** 先读取再检查行数，超过 5000 行时立即拒绝并释放 DataFrame。不要试图流式处理——同步模式下直接读取是最简方案。

### 陷阱 4: 员工导入 manager 绑定阶段 / Employee Import Manager Binding Phase
**问题:** 现有代码先处理所有员工行，再在第二遍处理 manager 绑定。如果改为每行 SAVEPOINT，需要确保 manager 绑定阶段也包裹在 SAVEPOINT 中。
**原因:** manager_employee_no 引用的员工可能在同一批次中导入，所以两遍处理是必要的。
**避免方式:** 保留两遍处理模式。第一遍（创建/更新员工）使用 SAVEPOINT；第二遍（绑定 manager）也使用 SAVEPOINT，manager 绑定失败作为警告而非致命错误。

### 陷阱 5: 审计日志与 upsert / Audit Log and Upsert
**问题:** D-03 要求"审计日志记录更新操作"，但现有 `_import_employees` 没有区分 create 和 update。
**原因:** 需要在 upsert 逻辑中判断是新建还是更新，更新时写入 AuditLog。
**避免方式:** 在查询 employee_no 后，如果 employee 不为 None，记录为 update 操作并写入 AuditLog。

### 陷阱 6: 前端 207 状态码处理 / Frontend 207 Status Code Handling
**问题:** Axios 默认认为 2xx 都是成功，但 207 需要特殊处理以展示部分失败信息。
**原因:** Axios `validateStatus` 默认只接受 200-299，207 在此范围内所以不会触发 error——但前端需要检查 response 中的 failed_rows 决定展示模式。
**避免方式:** 在 `createImportJob` 返回后，检查 `result.failed_rows > 0` 来决定是否展示错误表格。207 状态码本身不需要特殊 Axios 配置。

## 代码示例 / Code Examples

### 现有代码关键改造点 / Key Modification Points in Existing Code

#### 1. `_load_table` 添加 xlsx 支持
```python
# 当前代码拒绝 xlsx：
#   if suffix in {'xlsx', 'xls'}:
#       raise ValueError(...)
# 改造为：
if suffix in {'xlsx', 'xls'}:
    return pd.read_excel(io.BytesIO(raw_bytes), engine='openpyxl').fillna('')
```

#### 2. `run_import` 添加 5000 行限制
```python
dataframe = self._load_table(file_name, raw_bytes)
if len(dataframe) > self.MAX_ROWS:
    raise ValueError(f'单次导入不能超过 {self.MAX_ROWS} 行，请分批导入。')
```

#### 3. `_import_employees` 改造为 SAVEPOINT 模式
```python
def _import_employees(self, dataframe: pd.DataFrame) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    staged_rows: list[tuple[Employee, str | None]] = []
    identity_service = IdentityBindingService(self.db)

    for index, row in dataframe.iterrows():
        try:
            with self.db.begin_nested():  # SAVEPOINT
                # ... 解析字段、校验、upsert ...
                self.db.add(employee)
                self.db.flush()
                # 自动绑定
                identity_service.auto_bind_user_and_employee(employee=employee)
            staged_rows.append((employee, manager_no or None))
            results.append({'row_index': int(index) + 1, 'status': 'success', ...})
        except Exception as exc:
            results.append({'row_index': int(index) + 1, 'status': 'failed', 'message': str(exc)})

    # 第二遍：manager 绑定
    for employee, manager_no in staged_rows:
        try:
            with self.db.begin_nested():
                # ... manager 绑定逻辑 ...
                pass
        except Exception as exc:
            results.append({'row_index': None, 'status': 'failed', 'message': str(exc)})

    self.db.commit()
    return results
```

#### 4. API 层 207 响应
```python
@router.post('/jobs')
def create_import_job(...):
    service = ImportService(db)
    job = service.run_import(import_type=import_type, upload=file)
    data = ImportJobRead.model_validate(job).model_dump(mode='json')
    if job.failed_rows > 0:
        return JSONResponse(content=data, status_code=207)
    return JSONResponse(content=data, status_code=201)
```

#### 5. Excel 模板生成
```python
def build_template_xlsx(self, import_type: str) -> tuple[str, bytes, str]:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    headers = self.COLUMN_ALIASES[import_type]  # 中文 -> 英文映射的 keys
    # 表头行
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[cell.column_letter].width = 20
    # 示例行...
    output = io.BytesIO()
    wb.save(output)
    return f'{import_type}_template.xlsx', output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
```

#### 6. Excel 错误报告生成
```python
def build_export_report_xlsx(self, job: ImportJob) -> tuple[str, bytes, str]:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = '导入结果报告'
    # 表头
    for col_idx, header in enumerate(['行号', '结果', '错误列', '错误原因'], 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = Font(bold=True)
    # 仅输出失败行（或全部行）
    rows = job.result_summary.get('rows', [])
    for row_idx, item in enumerate(rows, 2):
        ws.cell(row=row_idx, column=1, value=item.get('row_index', ''))
        ws.cell(row=row_idx, column=2, value=item.get('status', ''))
        ws.cell(row=row_idx, column=3, value=item.get('error_column', ''))
        ws.cell(row=row_idx, column=4, value=item.get('message', ''))
    output = io.BytesIO()
    wb.save(output)
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return f'{job.import_type}_{job.id}_report.xlsx', output.getvalue(), media_type
```

## 现有代码差距分析 / Current Code Gap Analysis

| 能力 / Capability | 现状 / Current State | 需要改造 / Needed Change | 复杂度 / Complexity |
|-----|------|------|------|
| 逐行错误收集 | 已实现（results 列表） | 需确保所有异常都被捕获，不冒泡 | 低 |
| SAVEPOINT 部分提交 | 未实现（单一 commit） | 每行 `begin_nested()` | 中 |
| HTTP 207 响应 | 未实现（固定 201） | API 层条件判断 | 低 |
| xlsx 读取 | 明确拒绝 | 改用 `pd.read_excel(engine='openpyxl')` | 低 |
| xlsx 模板生成 | 仅 CSV | 新增 openpyxl 模板生成方法 | 低 |
| xlsx 错误报告 | 仅 CSV | 新增 openpyxl 报告生成方法 | 低 |
| 5000 行限制 | 未实现 | 解析后、导入前检查 | 低 |
| 审计日志记录 upsert | 未实现 | 区分 create/update 并写 AuditLog | 中 |
| 前端错误表格 | 未实现 | 新增错误行展示组件 | 中 |
| 前端 xlsx 模板下载 | 仅 CSV | 添加 xlsx 下载按钮 | 低 |

## 技术现状 / State of the Art

| 旧方式 / Old Approach | 当前方式 / Current Approach | 变更时间 / When Changed | 影响 / Impact |
|--------------|------------------|--------------|--------|
| CSV-only 导入 | Excel + CSV 双格式 | 本阶段 | openpyxl 已安装，只需解除代码限制 |
| 全部成功或全部失败 | HTTP 207 部分成功 | 本阶段 | 更好的用户体验 |
| 无行数限制 | 5000 行限制 | 本阶段 | 防止超大文件导致超时 |

## 开放问题 / Open Questions

1. **认证导入的幂等键设计**
   - 已知信息: 现有代码使用 `(employee_id, certification_type)` 作为 upsert 键
   - 不确定之处: 是否应该加入 `certification_stage` 作为复合键？同一员工同一认证类型可能有不同阶段。
   - 建议: 保持现有 `(employee_id, certification_type)` 不变——同一类型认证只保留最新阶段，符合实际业务场景（一个人的 AI 技能认证只有一个当前阶段）。**置信度: MEDIUM**

2. **错误报告 Excel 列设计**
   - 已知信息: D-02 要求页面表格 + 可下载 Excel 报告
   - 建议: 错误报告 Excel 包含列：行号、结果（成功/失败）、错误字段、错误原因、原始数据摘要。仅输出失败行以减小文件大小。

## 环境可用性 / Environment Availability

| 依赖 / Dependency | 需要方 / Required By | 可用 / Available | 版本 / Version | 备选 / Fallback |
|------------|------------|-----------|---------|----------|
| openpyxl | Excel 读写 | 是 | 3.1.5 | -- |
| pandas | DataFrame 处理 | 是 | 2.2.3 | -- |
| SQLAlchemy | SAVEPOINT | 是 | 2.0.36 | -- |
| SQLite | 开发数据库 | 是 | 内置 | -- |
| pytest | 测试 | 是 | 8.3.5 | -- |

**缺失依赖:** 无。openpyxl 已安装但未在 `requirements.txt` 中列出，需要添加。

## 验证架构 / Validation Architecture

### 测试框架 / Test Framework
| 属性 / Property | 值 / Value |
|----------|-------|
| 框架 / Framework | pytest 8.3.5 |
| 配置文件 / Config file | 无独立 pytest.ini（使用默认） |
| 快速运行 / Quick run | `pytest backend/tests/test_services/test_import_service.py -x` |
| 完整套件 / Full suite | `pytest backend/tests/ -x` |

### 阶段需求 -> 测试映射 / Phase Requirements -> Test Map
| 需求 ID | 行为 / Behavior | 测试类型 | 自动化命令 | 文件存在？ |
|--------|----------|-----------|-------------------|-------------|
| IMP-01 | 惰性验证：收集所有行级错误不中断 | unit | `pytest backend/tests/test_services/test_import_service.py -x -k lazy_validation` | 需新建 |
| IMP-02 | SAVEPOINT 部分提交 + HTTP 207 | unit + integration | `pytest backend/tests/test_services/test_import_service.py -x -k savepoint` | 需新建 |
| IMP-03 | 响应包含 total/success/failure + 逐行错误 | unit | `pytest backend/tests/test_api/test_import_api.py -x -k response_summary` | 需新建 |
| IMP-04 | GBK Excel 无乱码 | unit | `pytest backend/tests/test_services/test_import_service.py -x -k encoding` | 部分存在 |
| IMP-05 | employee_no upsert 幂等 | unit | `pytest backend/tests/test_services/test_import_service.py -x -k upsert` | 需新建 |
| IMP-06 | xlsx 模板下载 | integration | `pytest backend/tests/test_api/test_import_api.py -x -k template_xlsx` | 需新建 |

### 采样频率 / Sampling Rate
- **每次任务提交:** `pytest backend/tests/test_services/test_import_service.py backend/tests/test_api/test_import_api.py -x`
- **每波合并:** `pytest backend/tests/ -x`
- **阶段门:** 完整套件通过

### Wave 0 缺口 / Wave 0 Gaps
- [ ] `backend/tests/test_services/test_import_partial_success.py` — 覆盖 IMP-01, IMP-02
- [ ] `backend/tests/test_api/test_import_207.py` — 覆盖 IMP-02, IMP-03
- [ ] `backend/tests/test_services/test_import_xlsx.py` — 覆盖 IMP-04, IMP-06
- [ ] `backend/tests/test_services/test_import_upsert_audit.py` — 覆盖 IMP-05

## 来源 / Sources

### 主要（HIGH 置信度）/ Primary (HIGH confidence)
- `backend/app/services/import_service.py` — 现有导入服务完整源码审查
- `backend/app/api/v1/imports.py` — 现有 API 路由审查
- `backend/app/models/employee.py` — Employee 模型，确认 employee_no unique 约束
- `backend/tests/test_services/test_import_service.py` — 现有测试覆盖
- `backend/tests/test_services/test_import_idempotency.py` — 认证幂等性测试
- SQLAlchemy 2.0 文档 — `Session.begin_nested()` SAVEPOINT 支持
- openpyxl 3.1.5 — 已安装并验证可用

### 次要（MEDIUM 置信度）/ Secondary (MEDIUM confidence)
- HTTP 207 Multi-Status (RFC 4918 WebDAV) — 标准 HTTP 规范，FastAPI 通过 JSONResponse 支持

## 项目约束（来自 CLAUDE.md）/ Project Constraints (from CLAUDE.md)

- 所有评分、系数、阈值、认证规则必须配置化，不允许硬编码在多个位置
- 批量导入必须考虑幂等性、校验错误回传和部分成功场景
- 优先编写针对导入逻辑的单元测试
- 涉及关键页面布局调整时，必须做浏览器级验证
- 所有关键业务结果都应可审计、可解释、可追踪
- `from __future__ import annotations` 在所有后端模块中必须存在
- 后端服务可启动是前提条件

## 元数据 / Metadata

**置信度分解:**
- 标准技术栈: HIGH — 所有库已安装并验证
- 架构模式: HIGH — 基于现有代码的直接改造，SAVEPOINT 是 SQLAlchemy 标准功能
- 陷阱: HIGH — 基于源码审查识别的具体问题

**研究日期:** 2026-03-28
**有效期:** 30 天（稳定技术栈，无快速变化的外部依赖）
