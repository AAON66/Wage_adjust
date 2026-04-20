# Stack Research — v1.4 员工端资格可见 + 绩效档次 + 导入链路修复

**Domain:** 企业内部调薪平台 — 后续里程碑增量（员工端可见性、绩效档次、Excel/飞书导入 bug 修复）
**Researched:** 2026-04-20
**Confidence:** HIGH

---

## TL;DR — 无新增依赖

**v1.4 的 4 条 feature 全部可以用现有技术栈实现**。不需要新增任何 Python 包、不需要新增任何前端包、不需要引入 SDK。

现有栈已覆盖所有需求：

| 需求 | 现有能力 | 补充动作 |
|------|---------|---------|
| 员工端资格可见 | React 18 + axios + 现有 `EligibilityService` | 新增只读路由 + Props 改造；零依赖 |
| 绩效档次（20/70/10） | SQLite 3.25+ 窗口函数 `NTILE(10)` / `PERCENT_RANK()` | 纯 SQL；SQLAlchemy 2.0 `func.ntile().over()` 已原生支持 |
| 绩效管理页 / 历史展示 | React Router v7 + echarts + 现有 `PerformanceRecord` 模型 | 新增页面组件；零依赖 |
| 工号前导零保留 | pandas 2.2.3 `dtype=str` + openpyxl 3.1.5 | **已在** `import_service.py:395` 使用；bug 在上游 Excel/飞书，非栈问题 |
| Excel 模板下载 | FastAPI `StreamingResponse` + openpyxl | **已在** `build_template_xlsx` 正确实现；bug 在前端下载链路 |
| 飞书同步落库 | 现有 `FeishuService` + httpx 0.28.1 | 纯业务 bug（事务/字段映射），栈不需要换 |

**下面的文档详细说明每条结论的依据、现有代码引用点、以及排查切入点。**

---

## Recommended Stack (for v1.4)

### Core Technologies — 保持不变

| Technology | Version | Purpose | Why Keep |
|------------|---------|---------|----------|
| FastAPI | 0.115.0 | REST API 框架 | v1.0 起验证过的稳定选择，`/api/v1/` 版本化已建立 |
| SQLAlchemy | 2.0.36 | ORM + 查询构造 | `func.ntile().over()` 原生支持窗口函数，无需换库 |
| SQLite | 3.25+（运行时 ≥ 3.50.4 已验证） | 开发数据库 | 绩效分档所需的 `NTILE/PERCENT_RANK` 在 3.25.0（2018-09）引入；本机 `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` 输出 3.50.4 |
| pandas | 2.2.3 | Excel/CSV 解析 | 已配 `dtype=str`；下面 STACK-01 节详解为何 dtype=str 仍可能丢前导零 |
| openpyxl | 3.1.5 | .xlsx 读写 | 模板导出（write）与导入（pandas engine）两用；write_only 模式可扩展到 10 万+ 行 |
| React | 18.3.1 | 前端框架 | 员工端可见页面复用现有 `ProtectedRoute` + `useAuth` |
| axios | 1.8.4 | 前端 HTTP | 已有 `api.ts` JWT 拦截器 + refresh token 链路 |
| echarts + echarts-for-react | 6.0.0 / 3.0.6 | 图表库 | 绩效档次分布、历史绩效趋势用柱状/堆叠图，已在 Dashboard 验证 |
| httpx | 0.28.1 | 后端 HTTP | 飞书 bitable API 现已用 httpx 同步调用；继续用 |

### Supporting Libraries — 保持不变

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.10.3 | Schema | 新增 `EmployeeEligibilityRead`、`PerformanceTierRead` 等只读 Schema |
| alembic | 1.14.0 | 迁移 | 如需新增字段（例如 `performance_tier_snapshot`）走 `batch_alter_table` |
| python-jose | 3.3.0 | JWT | 员工端调取自己资格的权限门控继续用 `get_current_user` |
| loguru / logging | 0.7.3 | 日志 | 飞书同步已配 `logger.exception`；排查飞书落库问题依赖现有 logger |
| numpy | 2.0.2 | 数值 | 绩效档次**不需要**在 Python 端算分（推 SQL 层）；保留现状即可 |

### Development Tools — 保持不变

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | 8.3.5 | 单元测试 | 新增：窗口函数分档的边界用例（全员同档/人数<10 等） |
| Alembic | 迁移 | 使用 `op.batch_alter_table` 保持 SQLite 兼容 |
| TypeScript (tsc --noEmit) | 前端 lint | 现有 `npm run lint` |

---

## Installation

**不需要执行任何 `pip install` 或 `npm install`。** 所有 v1.4 功能的依赖均已在 `requirements.txt` 和 `frontend/package.json` 中。

验证命令（可选）：

```bash
# 确认 SQLite 3.25+（实际 3.50.4）
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"

# 确认 pandas + openpyxl 能读写 xlsx
python3 -c "import pandas as pd, openpyxl; print(pd.__version__, openpyxl.__version__)"
```

---

## STACK-01：Excel 导入前导零保留 — 现状与修复路径

### 现状代码（`backend/app/services/import_service.py:381-396`）

```python
def _load_table(self, file_name: str, raw_bytes: bytes) -> pd.DataFrame:
    ...
    if suffix == 'csv':
        return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding, dtype=str).fillna('')
    if suffix in {'xlsx', 'xls'}:
        return pd.read_excel(io.BytesIO(raw_bytes), engine='openpyxl', dtype=str).fillna('')
```

**结论：读端 Python 代码已正确，`dtype=str` 是 pandas 2.2 官方推荐做法。**

### 为什么前导零仍然会丢（根因在 Excel 文件本身）

| 源头 | 丢失点 | 证据 |
|------|--------|------|
| Excel 列格式为「数字」 | Excel **存储层**就已把 `02615` 存成 `2615.0` 数值，openpyxl 读到的 raw cell 是 `2615`，根本看不到前导 0 | pandas issue [#46895](https://github.com/pandas-dev/pandas/issues/46895) 长期未修；[pandas 3.0 docs](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html) 未解决 |
| 飞书多维表格"工号"字段类型 = 数字 | 飞书 API 返回 `fields.工号 = 2615`（float），`_extract_cell_value` 得到 float，然后 `str(int(2615)) = '2615'`（见 `feishu_service.py:240-245`）— 前导零在飞书存储层已丢 | `FeishuService._map_fields` 第 242-244 行显式处理 `if isinstance(value, float) and value == int(value): value = str(int(value))` |
| 前端手动录入表单 | React 表单 `<input type="text">` 或默认 text 应该能保留，但如果后端 Schema 用 `int`，Pydantic 会强转 | 需检查 `EmployeeCreate` Schema |

### 推荐修复（纯业务层，不需换栈）

1. **模板端**：下载的 `.xlsx` 模板，员工工号列预先设成 **Text/文本格式**（openpyxl 的 `cell.number_format = '@'` 或 `NamedStyle`）— 用户复制粘贴数据进来时 Excel 不会自动转数字
2. **读端兜底**：配置文件声明"工号类字段"白名单（如 `employee_no`、`manager_employee_no`），在 `_normalize_columns` 之后统一 `.str.zfill(N)` 或记录原始 cell 是否带前导 0（但源数据已丢则无解）
3. **飞书端**：在 `FeishuService._map_fields` 的 employee_no 分支加显式修复 — 调用方约定使用"文本"类型字段；如飞书端确定是数字字段但工号固定 5 位，则 `value = str(int(value)).zfill(5)`
4. **存量数据**：一次性 Alembic data migration（或脚本）：按规则补齐 `Employee.employee_no`

### 库升级？不需要

- `calamine` 引擎（通过 `python-calamine`）在某些场景对"文本格式"更忠实，但 pandas 官方也承认这对"存储层已是数字"的情况无效
- **推荐不引入 calamine**：多一层依赖 + 不解决根因 + 现状代码已是最佳实践

**Confidence: HIGH** — 验证自 [pandas 2.2.3 read_excel docs](https://pandas.pydata.org/pandas-docs/version/2.2.3/reference/api/pandas.read_excel.html)、[pandas GH#46895](https://github.com/pandas-dev/pandas/issues/46895)、[Python.org discussion thread](https://discuss.python.org/t/when-reading-spreadsheet-how-to-keep-leading-zeros/61389)。

---

## STACK-02：Excel 模板下载 — 当前做法已最佳

### 现状代码（`import_service.py:254-309`）

```python
def build_template_xlsx(self, import_type: str) -> tuple[str, bytes, str]:
    from openpyxl import Workbook
    ...
    wb = Workbook()
    ws = wb.active
    ...
    buf = io.BytesIO()
    wb.save(buf)
    content = buf.getvalue()
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return f'{normalized_type}_template.xlsx', content, media_type
```

**这就是 FastAPI + openpyxl 动态模板下载的标准模式。无需重构。**

### "模板下载失败"的排查切入点（不是栈问题）

| 症状 | 可能根因 | 验证办法 |
|------|---------|---------|
| 前端下载的文件大小为 0 | Router 没把 `content` 透传给 `Response`/`StreamingResponse`；或 `Content-Disposition` header 缺失 | 检查 `backend/app/api/v1/imports.py`（或等价文件）中返回逻辑 |
| 前端下载得到 HTML（JSON 响应） | axios 没设 `responseType: 'blob'`；或 auth 失败返回 401 HTML | 检查 `frontend/src/services/importService.ts` |
| Excel 打不开（"文件损坏"） | 前端用 `JSON.stringify` 污染了 binary；或字节流经过 `text` 解码 | 浏览器开发者工具 Network → Response → 看字节数是否完整 |
| 文件名乱码 | `Content-Disposition` 用了非 ASCII，且没用 `filename*=UTF-8''` 编码 | 用 `RFC 5987` 格式：`attachment; filename="fallback.xlsx"; filename*=UTF-8''{urlencoded_name}` |

### FastAPI 端推荐实现（若需要重写，保持一致）

```python
from fastapi import APIRouter
from fastapi.responses import Response
from urllib.parse import quote

@router.get("/imports/template")
def download_template(import_type: str, service: ImportService = Depends(...)):
    filename, content, media_type = service.build_template_xlsx(import_type)
    encoded = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
```

**`Response` vs `StreamingResponse`：** 模板是小文件（< 50KB），用 `Response` + bytes 最简单。`StreamingResponse` 更适合 100MB+ 大文件或写边生成的数据（如 `write_only=True` 的大报表）。

**Confidence: HIGH** — 验证自 [FastAPI custom response docs](https://fastapi.tiangolo.com/advanced/custom-response/)、[FastAPI issue #3622（空文件陷阱）](https://github.com/fastapi/fastapi/issues/3622)。

---

## STACK-03：绩效档次 20/70/10 计算 — 用 SQL 窗口函数

### 需求拆解

- 全公司员工按绩效排序，分成三档：前 20% = 1 档，中 70% = 2 档，后 10% = 3 档
- 员工看到自己的档位，不看到排名
- **一次计算覆盖所有员工**（非单人实时查询）

### 方案对比

| 方案 | SQL/Python | 优势 | 劣势 |
|------|-----------|------|------|
| **SQL `PERCENT_RANK()`**（推荐） | SQL | 数据库引擎计算，O(N log N)；绩效等级 A/B/C/D/E 先映射为数值再排名；单 query 返回分档 | 需 SQLite ≥ 3.25（已验证 3.50.4） |
| SQL `NTILE(10)` | SQL | 严格按等分切 10 桶，然后 1 桶=1 档、2-8 桶=2 档、9-10 桶=3 档 | 当同绩效等级员工横跨档位分界线时不确定性较强 |
| Python `numpy.percentile` | Python | 与业务逻辑耦合低 | 全表拉到内存；O(N) 但 N 过万时慢；同步路径不适合 |
| Python `pandas.qcut` | Python | 方便 | 同上，且需处理 NaN |

### 推荐：用 `PERCENT_RANK()`（而不是 `NTILE`）

**原因：** 绩效等级 (A/B/C/D/E) 是离散值，很多员工同等级。`NTILE` 会机械切桶，导致同等级员工被拆到不同档位；`PERCENT_RANK()` 配合 `ORDER BY grade` 可让同等级员工获得相同百分位，更公平。

### SQLAlchemy 2.0 实现示例

```python
from sqlalchemy import func, select, case

# 绩效等级 -> 排序权重（A 最好 = 最高 rank）
grade_score = case(
    (PerformanceRecord.grade == 'A', 5),
    (PerformanceRecord.grade == 'B', 4),
    (PerformanceRecord.grade == 'C', 3),
    (PerformanceRecord.grade == 'D', 2),
    (PerformanceRecord.grade == 'E', 1),
    else_=0,
)

percent_rank_expr = func.percent_rank().over(
    partition_by=PerformanceRecord.year,   # 按年度分档
    order_by=grade_score.desc(),
)

tier_expr = case(
    (percent_rank_expr <= 0.20, 1),
    (percent_rank_expr >= 0.90, 3),
    else_=2,
)

stmt = select(
    PerformanceRecord.employee_id,
    PerformanceRecord.year,
    PerformanceRecord.grade,
    tier_expr.label('tier'),
).where(PerformanceRecord.year == 2025)
```

### 边界用例

| 情况 | 建议处理 |
|------|---------|
| 某年度员工 < 10 人 | 档位不稳定；可在 Service 层加守卫 "员工数 < 阈值（如 10）时只返回 grade，不返回 tier" |
| 员工本年度没有绩效记录 | `LEFT JOIN` + `tier = NULL` → 前端展示 "暂无档位" |
| 员工绩效是 D/E | 严格 20/70/10 切分时，若 D/E 人数 > 10% 会"挤进"2 档；业务需确认是否严格按百分位还是 hard cut E=3 档 |

**对 Executor 的提示：** 这个数学决策需要在 Requirements 阶段与 HR 确认 "20/70/10 是严格百分位 vs 固定等级映射"。

**Confidence: HIGH** — 验证自 [SQLite window functions docs](https://sqlite.org/windowfunctions.html)、[SQLite PERCENT_RANK tutorial](https://www.sqlitetutorial.net/sqlite-window-functions/sqlite-percent_rank/)；SQLAlchemy 2.0 `func.X().over()` 构造通过代码审读和训练知识验证。

---

## STACK-04：飞书 Python SDK —— 继续用 httpx，不换

### 现状评估

现有 `FeishuService`（`backend/app/services/feishu_service.py`，~1100 行）**已经把飞书集成做完了**：
- Token 获取 + 提前 5 分钟刷新（`_ensure_token`）
- Bitable 分页拉取（`_fetch_all_records`，含 filter 降级）
- 频控（`InMemoryRateLimiter(60 RPM)`）
- 重试 3 次，递增间隔 [5, 15, 45]s（`sync_with_retry`）
- 字段映射 + 类型强转（`_map_fields`）
- 工号前导零容错（`_build_employee_map` + `_lookup_employee`）
- 事务性 upsert + 失败后新 session 记录 sync_log
- 增量同步 overlap window（5 分钟）

**换用官方 `lark-oapi` SDK 的代价：**
- 重写 ~800 行稳定运行的代码
- 引入新依赖（`lark-oapi==1.5.3`，~40 个间接依赖）
- v1.0 已验证过的飞书链路可能引入退化
- SDK 并不能省下字段映射、rate limit、重试等业务逻辑

**结论：不引入 `lark-oapi`。继续用 httpx。**

### 飞书"同步成功但数据未落库"的排查切入点

根据 `FeishuService.sync_performance_records`（第 461-556 行）的执行路径，**可能的无声失败**有 5 处：

| 切入点 | 症状 | 排查方法 |
|--------|------|---------|
| **1. `_map_fields` 跳过整行** | `has_employee_no = False` 时 `return None`，整条 record 丢弃；日志 `logger.warning('Record skipped — no employee_no after mapping...')` | 搜索日志 `grep "Record skipped"` |
| **2. `_lookup_employee` 未匹配** | `unmatched_count` 计数 + 记录到 `sync_log.unmatched_employee_nos`（前 100 个） | 查 `FeishuSyncLog.unmatched_employee_nos` |
| **3. 分页 `has_more=true` 但 `page_token=null`** | `_fetch_all_records` 第 178-180 行会 break，可能遗漏后续页 | 日志里对比 `total_fetched` 与飞书表实际行数 |
| **4. `_extract_cell_value` 对复杂字段返回 None** | 如飞书"人员"字段返回 `[{"id":"...","name":"..."}]`，`_extract_cell_value` 取 `name`，但若字段为空数组则返回 None → 字段丢失但行保留 | 打开 `logger.setLevel(logging.DEBUG)` 看 `'Raw fields from Feishu'` 日志 |
| **5. upsert 里某 `flush` 静默失败** | `try/except Exception` 只记 `logger.exception`，`failed_count++`；但整体 `sync_log.status = 'success'` 仍然报告成功 | 查 `FeishuSyncLog.failed_count` 是否 > 0；查日志 `'Failed to process ... record'` |

### 推荐排查顺序

```
1. FeishuSyncLog（DB 里最近一次 sync）
   - total_fetched = ?
   - synced / updated / skipped / unmatched / failed 各是多少
   - unmatched_employee_nos 里有哪些工号
2. 日志（stdout + 文件）
   - Record skipped — no employee_no
   - Performance sync: employee_no=XXX not found
   - Failed to process ... record
3. 直接调 `list_bitable_fields` API 确认字段定义
   - 飞书端"员工工号"字段的 type=? ui_type=?
   - field_mapping 里的 feishu_field 名字是否完全匹配（含全半角空格）
```

**不是栈问题，是业务逻辑可观测性问题**。v1.4 应新增 Observable 改进（见 PITFALLS.md）而非换库。

**Confidence: HIGH** — 代码审读自 `backend/app/services/feishu_service.py`；SDK 对比自 [lark-oapi PyPI](https://pypi.org/project/lark-oapi/)。

---

## STACK-05：员工端资格可见 — 纯前端路由 + 现有 API

### 现状

| 组件 | 现有能力 | v1.4 需要做什么 |
|------|---------|---------------|
| `frontend/src/hooks/useAuth.tsx` | JWT session + user.role | 无改动 |
| `ProtectedRoute` 组件 | 角色门控 | 员工端新页面用 `requireRoles=['employee']`（或不限角色，让员工也能访问） |
| `EligibilityListTab.tsx` | HR/管理端批量查询 | 复用其中的 rule breakdown 展示组件，**抽出**一个 `<EligibilityRuleList>` 纯展示组件 |
| 后端 `/api/v1/eligibility/me` | **需要新增** | 新端点：调用方从 JWT 取 employee_id，返回当前周期的资格 + rule 明细 |
| `AccessScopeService.ensure_eligibility_access` | 已有 HR/manager 访问控制 | 新增员工 self-access 分支（`user_id == target_employee.user_id`） |

### 不需要新增依赖

- 不需要 React Query / SWR — 资格数据更新频率低（每月一次调薪周期），页面加载时 fetch 一次即可
- 不需要 Zustand / Redux — 单页面本地 state 即可
- 不需要新图表库 — 4 条 rule 的 pass/fail 用现有 tailwind badge 渲染

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pandas `dtype=str` + 文本格式模板 | `python-calamine` 引擎 | 仅在测试发现 calamine 对某类 Excel 文件处理显著更好时切换；v1.4 不需要 |
| SQL `PERCENT_RANK()` | Python `numpy.percentile` | 仅当员工规模超 10 万，且需要复杂的 tie-breaking 业务规则时考虑落地到 Python |
| `NTILE(10)` 手动分段 | `PERCENT_RANK()` | 当业务要求每档**严格等人数**（而非等百分位）时用 NTILE |
| 继续用 httpx 直调飞书 API | 官方 `lark-oapi` 1.5.3 | 全新项目起步时可考虑；**现有项目不建议重写** |
| FastAPI `Response(content=bytes)` | `StreamingResponse` | 模板文件 < 1MB 用 Response；大报表（> 10MB）或需要 `write_only=True` 用 StreamingResponse |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| 引入 React Query / SWR / Zustand | 员工端资格页是只读 + 单次 fetch；现有项目零全局状态库，引入会让约定漂移 | `useState` + `useEffect` + 现有 `eligibilityService.ts` |
| 升级 pandas 到 3.0 | 3.0 有 breaking changes（API 重构、NaN 处理），v1.4 没带来价值 | 保持 2.2.3 |
| 切换 Excel 读引擎到 `xlrd` | xlrd 自 2.0 起不再支持 .xlsx | 继续用 openpyxl |
| 引入 `fastexcel` / `calamine` 双引擎 | 增加维护面 + 不解决"数字存储层已丢前导零"的根因 | 模板端强制文本格式 + 读端白名单补零 |
| 引入 `lark-oapi` SDK | 40+ 间接依赖、需重写稳定代码、不省业务逻辑 | 继续用 httpx + 现有 `FeishuService` |
| 用 Python/pandas 算百分位分档 | 全表进内存 + 慢；SQL 窗口函数更对 | `func.percent_rank().over(...)` |

---

## Stack Patterns by Variant

**如果后续迁移到 PostgreSQL（v1.4 不做）：**
- `PERCENT_RANK()` / `NTILE()` 完全兼容，无需改 SQLAlchemy 代码
- asyncpg 0.30.0 已在 requirements.txt

**如果员工规模超 10 万（目前 ~1k）：**
- 资格批量查询走 cursor pagination（filter-before-paginate 不可行）
- 绩效分档结果缓存到 Redis（现有 hiredis + celery 可用）
- 飞书分页大小 500 → 100（避免单页 timeout）

**如果前导零丢失问题扩散到其他字段（如手机号、订单号）：**
- 在 `import_service.py` 提取"强制字符串列"配置（per import_type），读取后统一 `str.zfill(N)`
- 对应 schema 声明 `Literal['str_preserve']` 标记字段

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| pandas 2.2.3 | openpyxl 3.1.5 | 已验证；`engine='openpyxl'` 是默认 |
| SQLAlchemy 2.0.36 | SQLite 3.25+ | 窗口函数 `.over()` 从 SQLAlchemy 1.4+ 支持；2.0 API 稳定 |
| SQLite（pysqlite）runtime | Python 3.11+ | 本机 `python3.11` 绑的 SQLite 3.50.4，远超 3.25 门槛 |
| FastAPI 0.115.0 | Starlette ~0.37 | `StreamingResponse` / `Response` API 稳定 |
| openpyxl 3.1.5 | Python 3.11+ | `NamedStyle('text', number_format='@')` 用于模板文本格式化 |
| React 18.3.1 | React Router 7.6.0 | 现有稳定组合 |

---

## 与 Downstream Consumer 的接口

**Roadmapper 应如何用本文档：**
- v1.4 不需要增加"依赖升级/新增"类 plan — 所有功能可用现有栈实现
- v1.4 需要增加的是"业务 bug 修复 + Schema 新增 + Service 层方法新增"类 plan

**Requirements 阶段应引用本文档的：**
- STACK-01 的"读端+模板端+飞书端+存量修补" 4 条修复路径 → 对应"工号前导零保留"feature 的子需求
- STACK-03 的 `PERCENT_RANK()` + 边界用例 → 对应"绩效档次计算"需求
- STACK-04 的 5 个排查切入点 → 对应"飞书同步未落库"bug 修复任务

**Executor 阶段应引用本文档的：**
- `func.percent_rank().over(...)` SQL 构造示例（STACK-03）
- FastAPI `Response` + `Content-Disposition` RFC 5987 示例（STACK-02）
- openpyxl `cell.number_format = '@'` 模板文本格式化（STACK-01 修复项 1）

---

## Sources

- [pandas 2.2.3 read_excel documentation](https://pandas.pydata.org/pandas-docs/version/2.2.3/reference/api/pandas.read_excel.html) — HIGH, 官方文档，确认 dtype/converters 参数语义
- [pandas GH#46895 — Leading zeros in data for read_excel vs read_csv](https://github.com/pandas-dev/pandas/issues/46895) — HIGH, pandas 官方 issue 追踪
- [Python.org discussion — When reading Spreadsheet, how to KEEP leading zeros](https://discuss.python.org/t/when-reading-spreadsheet-how-to-keep-leading-zeros/61389) — MEDIUM, 社区共识："根因在 Excel 存储层"
- [SQLite Window Functions official docs](https://sqlite.org/windowfunctions.html) — HIGH, 确认 3.25 起原生支持 PERCENT_RANK/NTILE
- [SQLite PERCENT_RANK tutorial](https://www.sqlitetutorial.net/sqlite-window-functions/sqlite-percent_rank/) — HIGH, 语义 `(rank-1)/(N-1)` 的边界行为
- [FastAPI Custom Response docs](https://fastapi.tiangolo.com/advanced/custom-response/) — HIGH, 官方 StreamingResponse / Response 指引
- [FastAPI issue #3622 — Empty file when sending an XLSX or BytesIO](https://github.com/fastapi/fastapi/issues/3622) — HIGH, 经典 seek(0) 陷阱
- [lark-oapi on PyPI (v1.5.3)](https://pypi.org/project/lark-oapi/) — HIGH, 确认是官方推荐 SDK 但不建议迁移
- [SQLite 3.25 release notes — window functions introduction](https://blog.xojo.com/2018/12/18/sqlite-3-25-adds-window-functions-and-improves-alter-table/) — MEDIUM, 历史节点
- 本机验证：`python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` → `3.50.4`
- 代码审读：`backend/app/services/import_service.py:381-396`（pd.read_excel dtype=str 已配置）、`backend/app/services/feishu_service.py:240-245`（FeishuService._map_fields employee_no float→str 转换）、`backend/app/services/import_service.py:254-309`（build_template_xlsx openpyxl 模式）

---

*Stack research for: 公司综合调薪工具 v1.4 — 员工端资格可见 + 绩效档次 + 导入链路修复*
*Researched: 2026-04-20*
*Confidence: HIGH — 所有推荐通过代码审读 + 官方文档 + 社区共识三重验证*
