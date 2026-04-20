# Pitfalls Research — v1.4 员工端资格可见 + 绩效档次 + 导入链路修复

**Domain:** 企业调薪平台 — 员工自助可见 + 绩效档次分档 + 多源导入一致性
**Researched:** 2026-04-20
**Confidence:** HIGH（基于实际代码审查 + v1.0/v1.1/v1.3 历史踩坑经验）

**Codebase references used:**
- `backend/app/services/eligibility_service.py`
- `backend/app/services/feishu_service.py`
- `backend/app/services/import_service.py`
- `backend/app/services/access_scope_service.py`
- `.planning/PROJECT.md` / `.planning/RETROSPECTIVE.md` / `.planning/MILESTONES.md`

---

## Critical Pitfalls

### Pitfall 1: 员工端资格接口用 `employee_id` 参数导致水平越权

**What goes wrong:**
新增 `/api/v1/eligibility/me` 或类似 `/eligibility/{employee_id}` 时，若照搬 HR 端 `check_employee(employee_id)` 签名并仅用 `require_roles('employee', 'manager', 'hrbp', 'admin')` 守门，employee 角色可以随手改 URL 的 `employee_id` 查他人资格。

**Why it happens:**
- 既有 `EligibilityService.check_employee(employee_id, ...)` 接受任意 employee_id，无所有权校验
- `AccessScopeService.ensure_employee_access` 存在但需要服务层显式调用，不是默认行为
- employee 角色在 v1.1 之前没有资格可见需求，历史接口（如单查）未强制做 self-scope

**How to avoid:**
- 专门给员工端开一个无参数的 `/eligibility/me` 路由，内部用 `current_user.employee_id` 解析，**不接受任何 employee_id 路径参数或 query**
- 若复用通用接口，在 `EligibilityService.check_employee` 加 `requester: User` 必填参数并调用 `AccessScopeService.ensure_employee_access(requester, employee_id)`，employee 角色只有当 `requester.employee_id == employee_id` 才放行
- 在 `tests/test_eligibility_api.py` 加用例：两个 employee 账号互相调用对方 id，必须 403

**Warning signs:**
- 路由签名里出现 `employee_id: str` 且允许 employee 角色调用
- 代码里出现 `if current_user.role == 'employee': ...` 但后面依然从 query 参数取 employee_id
- 前端 `employeeEligibilityService.fetchMine(emp_id)` 会把 id 暴露到 URL

**Phase to address:** HIGH — 员工端资格展示 phase 的首个 plan

---

### Pitfall 2: 百分位边界 ties 导致相邻员工被任意切到不同档

**What goes wrong:**
20/70/10 分档时，位于 20% 边界的员工可能因为浮点或排序稳定性在两次计算中被分到 1 档或 2 档；并列同分的员工可能一个 1 档一个 2 档，引发员工投诉"他凭什么比我高"。

**Why it happens:**
- `numpy.percentile` 与手写 `sorted()+index//n` 对 ties 的处理不同
- 浮点累计 & 等级离散映射（A/B/C/D/E → 5/4/3/2/1 分）会让多人同分非常常见
- 档位计算没有定义"同分共享档位"还是"按工号/入职日期打破 tie"

**How to avoid:**
- 在 `PerformanceTierEngine` 里**显式**声明 tie-break 策略，优先级（从强到弱）：
  1. 同分必须同档（ties 一律向下归入较低档，保护员工不被"踩边界降档"）
  2. 若目标档位容量被同分挤满，档位上限自动扩展，其他档同比压缩
- 写成 pure function 并配 20+ 单测覆盖 ties、全员同分、人数=0/1/2/3 等边界
- 在 UI 顶部显示"同绩效等级员工一律归入同档"文案

**Warning signs:**
- 单测里没有"两员工同分"的用例
- `PerformanceTierEngine.compute()` 返回结果依赖 `Employee.employee_no` 的排序
- 连续两次请求返回不同档位（非幂等）

**Phase to address:** HIGH — 绩效档次引擎 phase

---

### Pitfall 3: 样本量过小时分档毫无意义但仍然展示

**What goes wrong:**
公司总人数 < 10、某年度只有 3 个人有绩效记录时，"20/70/10" 实际变成"1/1/1"或"0/3/0"，员工看到"我是 1 档"以为自己拔尖，其实全公司就 3 个人。

**Why it happens:**
- 开发时用 mock 数据总是几百人，不会触发小样本场景
- 新入职季度或刚导入绩效的一段时间里，`PerformanceRecord` 表只有少量记录
- 前端无脑渲染后端返回的 tier，不判定样本量

**How to avoid:**
- `PerformanceTierEngine` 返回结果里必须带 `sample_size` 字段
- 定义阈值（建议 `min_sample_size = 20`）：低于阈值时 `tier=None`, `reason='sample_too_small'`
- 员工端遇到 `tier=None` 时展示"本年度全公司绩效样本不足，暂不分档"而非 fallback 到空状态
- 后端 config 化阈值到 `Settings.performance_tier_min_sample_size`

**Warning signs:**
- 测试用例从没有 < 20 人场景
- 前端 `tier === 1` 显示"优秀员工"文案，但 `tier=null` 走默认分支
- 小公司部署后员工第一反应"这数据是不是错了"

**Phase to address:** HIGH — 绩效档次引擎 phase

---

### Pitfall 4: 新导入一条绩效记录触发全员档位漂移

**What goes wrong:**
HR 补录一个员工 2025 年绩效 A，由于全员分档基于全量数据实时计算，其他 500 员工的 tier 瞬间漂移（因为分母+1、百分位边界重算），员工看到自己的档位在几分钟内跳动，产生信任危机。

**Why it happens:**
- 实时计算的"纯粹性"和"视觉稳定性"冲突
- v1.4 要求员工端"随时可见最新状态"被直译成"每次请求都全量重算"
- 没有引入 snapshot / 快照概念

**How to avoid:**
- 引入 `PerformanceTierSnapshot` 表：字段 `(year, computed_at, employee_id, tier, sample_size, algorithm_version)`
- 只在以下触发点重新计算快照：
  - HR 手动点击"重新生成本年档次"按钮
  - 绩效导入任务完成后主动触发一次
  - 定时任务每天 02:00 刷一次
- 员工端永远读最近一次快照 + 顶部显示"基于 YYYY-MM-DD HH:MM 数据生成"
- 提供 audit log 记录每次快照生成时间、触发人、影响员工数

**Warning signs:**
- 员工端 API 里有 `PerformanceTierEngine.compute(...)` 调用（应该只读快照表）
- 页面刷新两次档位不一致
- 看板 / 评估详情 / 员工端三处读的数据口径有时间差

**Phase to address:** HIGH — 绩效档次展示 phase

---

### Pitfall 5: 工号前导零在 Excel 读入时已经丢失

**What goes wrong:**
HR 在 Excel 填写 `02651`，保存为 .xlsx 后 Excel 把该列识别为数字列存成 `2651`，我们用 `pd.read_excel(..., dtype=str)` 读出来已经是 `"2651"`，前导零救不回来。`FeishuService._map_fields` 同样：飞书字段类型是「数字」时 SDK 返回 `2651.0`，`str(int(value))` 得到 `"2651"`。

**Why it happens:**
- Excel 默认把 "02651" 识别为数字，保存时实际存的是 `2651`，单元格级 `numberFormat` 只是显示层面的补零
- `pd.read_excel(dtype=str)` 只能阻止 pandas 做类型推断，救不了 Excel 存盘时已丢的信息
- 飞书多维表格字段类型决定 SDK 返回类型；用户误选"数字"类型后不可逆

**How to avoid:**
- **数据源端**（核心防线）：
  - 下发的 .xlsx 模板把"员工工号"列 cell 格式显式设为 `text`（`openpyxl` 里 `cell.number_format = '@'`），并在该列加 `DataValidation` 提示必须文本
  - 飞书多维表格"员工工号"字段必须用「单行文本」，不能是「数字」—— 在 `/api/v1/feishu/config` 校验字段类型，非 text 直接拒绝配置
- **读入端**（兜底防线）：
  - `ImportService._load_table` 针对 `employee_no` 列额外加显式字符串转换 + 告警日志（如果 pandas 识别为 int64 说明源文件已丢失前导零）
  - `FeishuService._map_fields` 对 `employee_no` 不做 `str(int(value))` —— 改为 `str(value) if isinstance(value, str) else None` + 同步日志里记录 `config_warning: '工号字段不是文本类型'`
- **匹配端**（数据兼容）：
  - 保留 `_build_employee_map` 的 leading-zero 宽容匹配（已有），但新增 metrics：统计每次同步命中"宽容匹配"的记录数，>0 时告警 HR

**Warning signs:**
- `pd.read_excel(dtype=str)` 返回的 employee_no 列值是 `"2651"` 而不是 `"02651"`
- 飞书字段定义接口 `list_bitable_fields` 返回"员工工号" `type=2`（数字）而不是 `type=1`（文本）
- `FeishuSyncLog.unmatched_employee_nos` 里同时出现 `"02651"` 和 `"2651"` 两种形式
- 员工手动登录后看到自己工号变成 `2651`（数据库里被截断了）

**Phase to address:** HIGH — 工号前导零修复 phase（第一个 plan）

---

### Pitfall 6: 存量工号无法区分"本应是 02651"vs"合法是 2651"

**What goes wrong:**
数据库里工号 `2651` 可能有两种含义：(a) 原本就是 4 位工号，无需补零；(b) 原本 5 位 `02651` 被 Excel 截断。没有外部对账源的情况下，程序无法自动判断要不要补零。盲目补零会破坏 (a) 类员工的账号。

**Why it happens:**
- 历史数据遗失了"原始输入"信息
- `employee_no` 字段是 unique key，被多处外键引用（`AttendanceRecord.employee_id`, `PerformanceRecord.employee_id`, `User.employee_id`），迁移复杂
- 业务上没有"工号长度必须统一"的硬规则

**How to avoid:**
- **不做自动批量补零**。迁移策略分两步：
  1. 输出"可疑清单"：找出工号是纯数字、长度 < 公司标准长度（如 5 位）、**且**飞书源数据中存在同数字但补零版本的员工。生成 CSV 给 HR 人工确认。
  2. HR 手工确认名单 → 用管理员接口 `POST /api/v1/admin/employees/{id}/rename-employee-no`（需审计日志 + 同步刷新 User、PerformanceRecord、SalaryAdjustmentRecord、AttendanceRecord 里的 `employee_no` 冗余字段）
- 新增约束：今后所有 employee_no 必须从源头保证正确（见 Pitfall 5），不再需要补零迁移

**Warning signs:**
- 迁移脚本里出现 `employee_no.zfill(5)` 且无人工确认步骤
- 有两条员工记录工号分别为 `02651` 和 `2651`（必须合并）
- `User.employee_id` 被补零操作后，该员工 JWT 下次登录失效且未通知

**Phase to address:** HIGH — 工号前导零修复 phase（第二个 plan）

---

### Pitfall 7: 飞书同步日志显示 `status=success` 但实际没落库

**What goes wrong:**
HR 看到 `FeishuSyncLog.status='success', synced_count=120`，但去员工记录里查发现只新增了 3 条，其他都无变化。HR 以为同步正常，下游调薪决策用的是旧数据。

**Why it happens（从代码里能看到多个根因）:**
1. `FeishuService.sync_attendance` 里 `unmatched` 和 `skipped` 不算 `failed`，但 `status='success'` 和 `synced_count=120` 的组合让人误以为 120 条都落库了（实际落库的是 `synced + updated`）
2. `sync_performance_records` 里 `employee_id is None` 只是 `skipped += 1`，日志里只剩一行 warning，HR 看不到
3. `_map_fields` 返回 `None` 的记录直接被丢弃，`FeishuSyncLog` 没有 `mapping_failed_count` 字段体现
4. `sync_salary_adjustments` 里 `raw_date` 解析失败直接 `skipped += 1`，真正的错误原因（"日期格式 xxx 无效"）没写回日志

**How to avoid:**
- `FeishuSyncLog` 增加字段 `落库明细 JSON`：`{success, updated, skipped_no_employee, skipped_bad_data, mapping_failed, ...}` 每个数字必须来自独立计数器
- 定义 "success" 的新语义：`success = (unmatched + skipped + failed == 0)`，否则至少 `status='partial'`
- 同步完成后返回给 HR 的 UI 必须拆四类：
  - ✓ 成功落库 N 条
  - ⚠ 未匹配工号 M 条（附前 20 个工号）
  - ⚠ 字段映射失败 K 条（附样本行 record_id）
  - ✗ 写入异常 J 条（附 exception 摘要）
- 每次同步结束后跑一个 sanity check：`SELECT COUNT(*) FROM performance_record WHERE source='feishu' AND updated_at > sync.started_at`，若远小于 `synced_count` 直接把 `status` 降级为 `needs_review`

**Warning signs:**
- `synced_count > 0` 但同一时间窗内 `PerformanceRecord.updated_at` 没有对应数量的变化
- `_map_fields` 返回 `None` 的次数 > 0 却没有记录
- HR 反馈"我看日志是成功的但数据没更新"

**Phase to address:** HIGH — 飞书同步根因修复 phase（第一个 plan）

---

### Pitfall 8: 重复导入按员工+周期"覆盖"的语义歧义

**What goes wrong:**
HR 第一次导入了员工 A 的 2025 绩效=B + 调薪日期=2025-06-01 + 金额=2000。第二次只导入员工 A 2025 绩效=A（调薪列留空），到底是：
(a) 只更新绩效为 A，调薪保持不变？
(b) 把调薪字段清空（因为 CSV 里没填）？
(c) 整行拒绝（列不全）？

**Why it happens:**
- "覆盖更新"是模糊口语，代码里可以落地成 3 种行为
- 现在 `_import_performance_grades` 按 `(employee_id, year)` upsert 只更新 grade（不涉及其他字段），但新的"绩效管理"页可能引入更多列
- `_import_salary_adjustments` 则是 **append**（不是 upsert），重复导入会产生多条同日同类型记录

**How to avoid:**
- 设计层面：在模板下载页 + 导入页面显著位置写明每种导入的语义（"更新-保留空值"模式为默认；"覆盖-清空空值"需要 HR 在 UI 勾选"按原始值覆盖"开关）
- 代码层面：`ImportService` 方法签名增加 `overwrite_mode: Literal['merge', 'replace']`：
  - `merge`（默认）：行内空值保留旧值
  - `replace`：行内空值清空旧值
- 写单测覆盖 4 种矩阵：模式 × (空/非空) × (记录存在/不存在)
- 审计日志记录 `import_job_id + overwrite_mode`，方便事后追溯

**Warning signs:**
- `_import_performance_grades` / `_import_salary_adjustments` 出现 `if value: record.field = value` 混合 `record.field = value or None` 两种写法
- HR 投诉"我把金额列空着导入了一次，原来的金额没了"
- 调薪资格导入页没有"覆盖空值"开关

**Phase to address:** MEDIUM — 调薪资格导入修复 phase

---

### Pitfall 9: 并发导入导致脏写与计数错乱

**What goes wrong:**
HR1 和 HR2 同时导入同一年度绩效的重叠子集，两个 `ImportJob` 的 `_import_performance_grades` 交错执行，出现：
- 同一员工被两个事务同时 upsert，后赢覆盖先赢，但前者已经在前端显示"导入成功"
- `commit()` 顺序导致 audit log 行顺序和实际数据顺序不一致
- 有外键依赖时出现 `IntegrityError: UNIQUE constraint failed: performance_record.employee_id, performance_record.year`（SAVEPOINT 能接住，但 HR 看到大量失败很困惑）

**Why it happens:**
- `ImportJob` 没有"同类型同时只能跑一个"的并发锁
- Celery worker 若并发度 > 1，多个导入 task 在同一张表上竞争
- 飞书同步已有 `is_sync_running()` 互斥但本地导入没有

**How to avoid:**
- 参考 `FeishuService.is_sync_running()` 模式，在 `ImportService.run_import` 开头加：
  ```python
  if self.db.scalar(select(ImportJob).where(
      ImportJob.import_type == normalized_type,
      ImportJob.status == 'processing',
  )):
      raise ValueError('已有相同类型的导入任务在进行中，请等待完成后再试。')
  ```
- 跑 Celery 时，对 `performance_import` 这类任务打 `queue='single'` + concurrency=1
- 所有导入相关 `ImportJob.status='processing'` 行加一个 `started_at`，用 `expire_stale_running_jobs` 模式兜底僵死任务

**Warning signs:**
- 同一年度 PerformanceRecord 出现 `source='excel'` 和 `source='feishu'` 在 1 秒内交替的场景
- Celery worker 并发 > 1 且没有 import-type 级队列
- `ImportJob` 表里多条 `status='processing'` 长期存在

**Phase to address:** MEDIUM — 调薪资格导入修复 phase

---

### Pitfall 10: Excel 模板下载 404 / 空文件 / Content-Type 错

**What goes wrong:**
前端点"下载 xlsx 模板"收到 404、或下载下来是 0 字节、或文件能下载但 Excel 报"文件格式无效"。

**Why it happens（常见四类根因）:**
1. FastAPI `StreamingResponse(buf)` 传递未 `seek(0)` 的 `BytesIO`，或者 `buf.getvalue()` 传给 `Response` 但 `media_type` 写错
2. 前端 `axios.get(url)` 没设 `responseType: 'blob'`，导致 Excel 二进制被按字符串处理，下载下来的 blob 编码错乱
3. 路由挂在错误的 router prefix 下（本项目 `/api/v1/imports/template` vs `/api/v1/eligibility-import/template`）
4. StaticFiles 方案下文件被 gitignore 排除，dev 能访问生产缺失

**How to avoid:**
- 统一采用"编程生成"方案（已在 `build_template_xlsx` 实现），不依赖 StaticFiles
- 路由必须用 `Response(content=bytes, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': 'attachment; filename="xxx.xlsx"'})`
- 前端服务层统一封装：
  ```ts
  const resp = await api.get(url, { responseType: 'blob' });
  const blob = new Blob([resp.data], { type: resp.headers['content-type'] });
  saveAs(blob, filenameFromHeader(resp));
  ```
- 补一个端到端自动化测试：`test_template_download.py` 断言 (a) status=200 (b) Content-Type 正确 (c) `openpyxl.load_workbook(BytesIO(body))` 能成功读回

**Warning signs:**
- 前端 service 里出现 `api.get(templateUrl)` 但没有 `responseType: 'blob'`
- 后端返回 `StreamingResponse(buf)` 但没 `buf.seek(0)`
- Network 面板里响应体长度 = 0 或 Content-Type 是 `application/json`

**Phase to address:** MEDIUM — 调薪资格导入修复 phase

---

### Pitfall 11: 员工跨部门 / 离职再入职的历史绩效口径混乱

**What goes wrong:**
员工 A 2023 年在产品部拿 A、2024 年转到技术部拿 B、2025 年离职 3 个月后重新入职拿 C。评估详情页展示"历史绩效"时，如果只按 `employee_id` 拉，会把 3 条都放一起，但档次比对口径（2024 在产品部全员里算还是技术部全员里算？）就错了。

**Why it happens:**
- `PerformanceRecord` 表没有 `department_at_record_time` 快照字段
- 员工离职再入职可能产生新的 `Employee` 记录（新 UUID），历史 `PerformanceRecord` 关联在旧 UUID 上
- 展示层默认 `employee_id == current_employee.id` 丢失了历史链路

**How to avoid:**
- `PerformanceRecord` 增加 `department_snapshot: str | None` 字段，写入时从 `Employee.department` 复制
- 员工档案引入 `previous_employee_ids: list[str]` 或 `legacy_employee_no: str`（admin 手动标注）；评估详情拉历史绩效时 `WHERE employee_id IN (current_id, *previous_ids)`
- UI 每条绩效记录下角显示"记录时所在部门：XXX"，避免员工以为档次错了
- 员工端 `/eligibility/me` 只展示与当前员工 id 相关的记录（离职重入场景由 HR 主动维护 legacy 映射）

**Warning signs:**
- 评估详情里历史绩效表只有 `(year, grade)` 没有 `department`
- 同一员工两年绩效分别在不同部门但 tier 展示是同一部门的百分位

**Phase to address:** MEDIUM — 历史绩效展示 phase

---

### Pitfall 12: 绩效周期口径混用（季度/半年/年度）

**What goes wrong:**
公司 2024 年还是年度绩效，2025 Q1 切到季度绩效。`PerformanceRecord.year` 字段只承载年度粒度，`grade` 是季度 A 和全年 A 混在一起，档次百分位计算分母/分子错位。

**Why it happens:**
- v1.1 设计 `PerformanceRecord` 只考虑年度一种 cadence
- 导入模板 `年度` 列无法表达 `2025-Q1`
- 飞书源表可能混合提供季度 + 年度数据

**How to avoid:**
- `PerformanceRecord` 增加 `period_type` 字段 (`'annual' | 'semi_annual' | 'quarterly'`) + `period_label` 字段 (`'2025'` / `'2025-H1'` / `'2025-Q1'`)
- 唯一约束从 `(employee_id, year)` 改为 `(employee_id, period_type, period_label)`
- 分档计算必须按 `(period_type, period_label)` 分组，不同 cadence 不互相污染
- 导入模板新增"绩效周期"列，列举可选值 + 示例
- v1.4 不强制启用多 cadence，但表结构留位，迁移时默认全部存量为 `annual + str(year)`

**Warning signs:**
- 唯一约束仍是 `(employee_id, year)`
- 前端"历史绩效"只显示年份不显示 Q1/H1
- HR 导入 Excel 时问"为什么填了季度就覆盖了年度"

**Phase to address:** LOW — v1.4 可以暂缓到 v1.5，但 schema 留位必须在 v1.4 绩效模型 phase 里做

---

### Pitfall 13: RBAC 在新增 endpoint 时漏接 AccessScopeService

**What goes wrong:**
新加了 `/api/v1/performance/me` 和 `/api/v1/performance-tiers`，开发时顺手抄了其他路由的 `require_roles('admin', 'hrbp', 'manager', 'employee')` 守门，但 manager 通过该接口能看到**非本部门**员工的档次（因为没调 `AccessScopeService.ensure_*_access`）。

**Why it happens:**
- `require_roles` 只管"角色白名单"，不管"数据所有权"
- `AccessScopeService` 不是默认生效的，需要服务层主动调用（见 `EligibilityService.check_employees_batch` 内部 `_department_names`）
- 新接口容易漏掉服务层注入点

**How to avoid:**
- 新增任何暴露员工数据的路由时，在 PR checklist 里明列："是否调用了 AccessScopeService？"
- 对 manager / hrbp 角色的路由强制过测试：构造"管理员账号 + 非管辖部门员工 id"场景，断言 403 或空数据
- 在 `backend/tests/test_access_scope_coverage.py` 里加一个 meta-测试：扫描所有 `/api/v1/*` 路由，对带员工 id / 列表返回的路由必须能找到 `AccessScopeService` 调用

**Warning signs:**
- 新 endpoint 里只有 `require_roles(...)` 没有其他守门
- manager 角色登录后能看到所有部门数据
- 代码 diff 里新路由的服务层没有 `scope_svc = AccessScopeService(self.db)` 或等效调用

**Phase to address:** HIGH — 每个涉及员工数据的 phase 都需要验证（作为 DoD 固定项）

---

### Pitfall 14: Celery 任务里用 FastAPI 请求级 Session 导致跨线程脏数据

**What goes wrong:**
导入 / 飞书同步 / 档次计算被异步化到 Celery 后，若沿用 `Depends(get_db)` 注入的 Session，任务会跨 worker 线程共享 session，出现 `DetachedInstanceError`、`This session is bound to another connection` 或更隐蔽的数据交叉。

**Why it happens:**
- v1.2 Phase 19 已经建立 Celery foundation 并解决过一次（见 PROJECT.md `Celery+Redis async foundation: shared worker DB lifecycle`）
- 但开发在新写任务时容易直接把同步函数 `task.delay(db_session)` 传进去（不可 pickle 会直接报错）或闭包捕获外层 session

**How to avoid:**
- Celery 任务**必须**用独立 `SessionLocal()`，标准模板：
  ```python
  @celery_app.task
  def run_import_task(job_id: str):
      db = SessionLocal()
      try:
          ImportService(db).continue_job(job_id)
          db.commit()
      except Exception:
          db.rollback()
          raise
      finally:
          db.close()
  ```
- 绝对不要让 Celery 任务签名里出现 `db: Session` 参数
- Code review checklist 加"任务是否 `SessionLocal() + try/finally close`"

**Warning signs:**
- Celery worker 日志出现 `DetachedInstanceError` 或 `Object is not bound to a Session`
- 任务失败后 `ImportJob.status` 永远卡在 `processing`
- 多任务并发时报 `This session is bound to another connection`

**Phase to address:** HIGH — 每个新增 Celery 任务的 phase（绩效档次快照计算、大批量导入）

---

### Pitfall 15: Pydantic v2 field_validator / model_validator 误用

**What goes wrong:**
新增 `PerformanceTierSchema` 或 `EligibilityMeResponse` 时，用了 Pydantic v1 风格 `@validator` 或 `pre=True` 的 v2 误法，导致校验没跑、运行时 500。

**Why it happens:**
- 项目混合存在 v1 和 v2 的 Pydantic 代码风格（`model_config = ConfigDict(...)` 是 v2）
- AI 写代码经常混入 v1 语法

**How to avoid:**
- v2 规则：
  - 字段级：`@field_validator('field')` + `@classmethod`
  - 多字段：`@model_validator(mode='after')` 返回 `self`，或 `mode='before'` 接 `dict`
  - 不再有 `pre=True` / `always=True`；`mode='before'` 取代
- 新 Schema 模板复用 `backend/app/schemas/eligibility.py`（已是 v2 正确示例）
- 运行 `pytest backend/tests/test_schemas.py` 加一组反例断言（空字符串、类型不匹配）

**Warning signs:**
- 代码里同时出现 `@validator` 和 `@field_validator`
- 校验错误没触发 422 而是返回 200 + 错误值
- `mypy` / `tsc --noEmit` 报 `Pydantic v1 API is deprecated`

**Phase to address:** LOW — 所有 schema 改动 phase 的 DoD 检查

---

### Pitfall 16: Alembic batch_alter_table 在 SQLite 的已知边界

**What goes wrong:**
为 `PerformanceRecord` 新增 `period_type` / `department_snapshot` 字段时写了 `op.add_column(...)`，SQLite 执行报错或约束被重置。已有 `PerformanceTierSnapshot` 表需要唯一复合约束，SQLite 也会踩坑。

**Why it happens:**
- SQLite 不支持 ALTER TABLE DROP COLUMN / ALTER COLUMN / ADD CONSTRAINT；项目已经统一采用 `batch_alter_table`（见 PROJECT.md Key Decisions）
- 开发者新手容易直接 `op.add_column` 不走 batch

**How to avoid:**
- 所有修改表结构的 migration **必须**用：
  ```python
  with op.batch_alter_table('performance_records', recreate='auto') as batch_op:
      batch_op.add_column(sa.Column(...))
      batch_op.create_unique_constraint(...)
  ```
- 删除唯一约束时显式声明 `recreate='always'` —— SQLite 需要重建表
- 跑完迁移必须验证：本地 SQLite + 真实 PostgreSQL 都能成功
- 参考既有示例 `alembic/versions/e55f2f84b5d1_add_company_to_employee.py`

**Warning signs:**
- Migration 里直接 `op.add_column` 不在 `batch_alter_table` 里
- `sqlite3.OperationalError: duplicate column name` / `near "ADD": syntax error`
- PostgreSQL 跑过、SQLite 没跑过（或反之）

**Phase to address:** HIGH — 每个涉及表结构变更的 phase

---

### Pitfall 17: 前端 useEffect 依赖数组导致档位数据抖动

**What goes wrong:**
员工端"我的资格 + 我的绩效档次"页面用 `useEffect(() => { fetch(...) }, [user, cycle, filter])` 拉取数据，其中 `user` 是 AuthContext 返回的对象，每次 render 是新引用，导致 fetch 无限重跑、档位闪烁。

**Why it happens:**
- `useAuth` 返回的 `user` 对象在没有用 `useMemo` 的情况下每次都是新引用
- 开发者误以为"相同内容就相同引用"
- 项目 tsconfig `strict: true` 但 React 的 exhaustive-deps lint 没启用

**How to avoid:**
- `useAuth` 内部用 `useMemo` 稳定 user 引用
- 页面里依赖 `user.id` / `user.role` 而不是 `user` 整体
- fetch 逻辑封装成 `useEmployeeEligibility(employeeId: string)` hook，依赖原始标量
- 开发时用 React DevTools Profiler 查看组件渲染频次，> 2 次/秒就是信号

**Warning signs:**
- 网络面板同一 endpoint 短时间内被打 10 次以上
- 档位数字在界面上肉眼可见地抖动
- DevTools Profiler 显示组件 render count 很高

**Phase to address:** MEDIUM — 员工端展示 phase

---

### Pitfall 18: 员工端展示"为什么不合格"的合规红线

**What goes wrong:**
员工看到"不合格原因：入职不足 12 个月（2024-12-01 入职）"—— 暴露了具体入职日期；或"不合格：上次调薪 2024-05-15 距今 < 12 个月"暴露上次调薪时间。在某些公司合规场景下，员工端不应展示精确日期（只应展示"入职时长未达标"）。

**Why it happens:**
- 既有 `RuleResult.detail` 字段直接带具体日期（见 `EligibilityEngine`）
- HR 端要详细信息，员工端直接复用同结构

**How to avoid:**
- `EligibilityResult` 暴露给员工端时，走一层 masking service：
  - `TENURE`: "已入职 X 个月，距达标还需 Y 个月" —— 不暴露入职日期
  - `ADJUSTMENT_INTERVAL`: "距上次调薪未满 X 个月" —— 不暴露上次日期
  - `PERFORMANCE`: "近一次绩效未达标" —— 不暴露具体等级
  - `LEAVE`: "本年度非法定假期累计 X 天" —— 天数可以暴露，无 PII 风险
- 和合规 / HR 业务方对齐 masking 规则后写进 `EligibilityMaskingService`
- 管理员可在 Settings 里配置是否全量展示（默认 mask）

**Warning signs:**
- 员工端返回的 `detail` 字段里含 `YYYY-MM-DD`、薪资数字
- HR 未参与 UAT 就放量
- 合规团队未审阅员工可见文案

**Phase to address:** HIGH — 员工端资格展示 phase（Requirements 阶段必须和 HR 对齐 masking 规则）

---

### Pitfall 19: Phase 11 导航验证变成隐式重写

**What goes wrong:**
v1.1 遗留的 Phase 11 菜单改造"功能已落代码但 SUMMARY 没写"，现在要"验证补齐"。开发一上手发现实际代码和记忆不符，顺手做了大 refactor，最后提交一个包含 30+ 文件的"验证+优化"混合 PR，审查困难且引入回归。

**Why it happens:**
- "验证"和"修复"边界不清
- 原始 Phase 11 设计意图没有文档
- 新 Phase 添加的菜单项和既有菜单代码不兼容时开发会想"顺便重构"

**How to avoid:**
- 明确区分两个子任务：
  1. **Verification-only**（只读 + 文档）：跑一遍 UAT 清单、截图、记录不符合预期的条目 → 输出到 `.planning/v1.4/phase_xx/VERIFICATION.md`
  2. **Fix**（如果需要）：针对 Verification 发现的问题单独开 plan，一次只改一个菜单项
- PR diff 超过 10 个文件就拆分
- 在 SUMMARY.md 里明确记录"当前菜单行为 vs 期望行为"对照表，哪怕维持现状也写

**Warning signs:**
- 单个 PR 同时触及多个菜单配置 + 多个页面 + 权限守门
- 提交信息写 "phase 11 verification and improvements"
- 回归测试缺失

**Phase to address:** MEDIUM — Phase 11 导航验证 phase（独立、不要并入其他 phase）

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| 档次每次请求实时计算（不建快照） | 快 1 天 | 员工看到抖动、HR 投诉"为啥我的档位一直变" | **Never** — v1.4 就必须做快照 |
| 飞书同步失败只记 `error_message` 不拆分类 | 节省一轮 schema 设计 | HR 反复投诉无法自助定位，永远占用工程答疑 | **Never** — 从一开始就拆四类计数器 |
| 员工端资格接口直接复用 HR 接口 + `employee_id` 参数 | 少写一个路由 | 水平越权、安全事故 | **Never** |
| `_build_employee_map` 宽容 leading-zero 匹配 | 兼容存量数据 | 掩盖数据质量问题，长期有幽灵匹配 | Acceptable 但必须 metric 报警 |
| xlsx 导入时依赖用户"正确保存为文本" | 少做一步前端校验 | 工号前导零反复丢失 | **Never** — 必须在模板里强制 text 格式 |
| 绩效档次 sample_size < 20 依然展示 | 所有小公司也能看到 | 员工误解分档含义 | **Never** — 必须 fallback 到 `tier=null` + 说明文案 |
| 存量工号盲目 zfill 补零迁移 | 一次脚本搞定 | 破坏合法 4 位工号员工的账号 | **Never** — 必须人工确认清单 |
| 在 Celery 任务里传 request-scoped db session | 开发期快 | 生产环境随机 DetachedInstanceError | **Never** |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| 飞书多维表格 字段类型 | 默认把"员工工号"建成「数字」 | 配置时校验字段类型必须是 text；非 text 拒绝保存 |
| 飞书 bitable filter | 把 `since` 直接用在 filter，字段不存在时 filter 整体失败 | 已有 fallback（`filter_failed`）模式，但要加监控日志 |
| 飞书 tenant_access_token | 每次请求都重新获取 | 已有 `TOKEN_REFRESH_BUFFER` 机制，保留 |
| Excel xlsx (用户侧) | 用户在 Excel 里直接打开模板会再次丢失前导零 | 模板 cell format 设为 `@`（text），并在模板说明页写"请勿重命名列" |
| pandas `pd.to_datetime` | 没带 `utc=True` 在本地时区环境跑出偏移 | 导入日期字段统一 `pd.to_datetime(value, utc=True)` |
| pandas `read_csv/read_excel` | 没传 `dtype=str` 时 employee_no 被识别为 int | 现有代码已传 `dtype=str` — 保留 |
| Celery + SQLAlchemy | 跨线程共享 session | 每个任务 `SessionLocal()` + try/finally close |
| Redis（rate limiter） | Redis down 时限流直接崩 | 已有 in-memory fallback（见 `InMemoryRateLimiter`）— 保留 |
| FastAPI StreamingResponse | 返回未 seek 的 BytesIO | 返回 `Response(content=bytes, media_type=..., headers=...)` 代替 |
| Axios blob 下载 | 没设 `responseType: 'blob'` | 服务层强制包一层 `{ responseType: 'blob' }` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 员工端资格接口每次实时跑 EligibilityEngine | 响应时间 300-500ms + DB 4 次查询 | 加 Redis 缓存（TTL 5 分钟）+ 绩效/调薪写入时显式失效 | 1000+ 员工并发登录早高峰 |
| 档次每次请求全量 `SELECT ... ORDER BY` 全员 | DB 慢查询 + 会话锁竞争 | PerformanceTierSnapshot 表 + 仅读快照 | 全公司 > 500 人时 |
| batch eligibility query filter-before-paginate | 内存中对 N 员工跑循环 | 已有已知限制（PROJECT.md 提到 ~10k 员工阈值） | > 10k 员工 |
| 飞书同步 rate limiter 仅 60 req/min | 单次同步如果 > 6000 条会退避到 100 分钟 | 按员工分片同步 + 分页 page_size 500 已用尽 | > 30k 员工 |
| Excel 导入 `MAX_ROWS=5000` 但没分批反馈 | 4999 行也要等到最后才能看进度 | `progress_callback` 已支持，确保 Celery 任务里每 100 行上报一次 | 4000+ 行时 |
| useEffect 依赖 user 对象不稳定 | 员工端档位 / 资格 fetch 被重复触发 10 次 | useMemo + 依赖数组只放标量 | 打开员工端首页即触发 |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `/eligibility/{employee_id}` 被 employee 角色访问 | 横向越权枚举全公司资格 | 员工端专用 `/eligibility/me` 无参数路由 + `AccessScopeService` 双保险 |
| 员工端展示含 PII（身份证 / 薪资 / 精确日期） | 合规事故、PIPL 违规 | `EligibilityMaskingService` 统一脱敏 + 合规审阅 |
| 飞书 app_secret 明文存 DB 或 log | 泄露后可控整个飞书应用 | 已有 `encrypted_app_secret` + `decrypt_value` 模式，保留并确保 log 不落明文 |
| 工号迁移脚本没审计日志 | 无法回溯谁改了员工工号 | 所有 `rename-employee-no` 操作写 `AuditLog(action='employee_no_rename', detail={before, after})` |
| Excel 模板下载不校验权限 | 无登录用户能拿到内部字段清单 | Template 下载路由也必须 `require_roles('hrbp', 'admin')` |
| 员工手动输入工号自绑定时未校验前导零 | 02651 员工输入 2651 反而绑到 4 位合法员工上 | 绑定逻辑先做严格匹配，失败后告知"工号不存在"而不是 fallback 到宽容匹配 |
| 并发导入同一员工记录 | 竞争条件导致历史覆盖、审计缺失 | 导入互斥锁（Pitfall 9）+ SAVEPOINT 内 audit 落库 |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 员工看到"不合格"但不知道怎么改善 | 焦虑 / 投诉 HR | 每条 failing rule 附"改善建议"（如"距离达标还需 X 个月"） |
| 档位跳动（见 Pitfall 4） | 员工对系统失去信任 | 快照 + 显式"基于 YYYY-MM-DD 生成"标签 |
| 飞书同步 UI 只显示 success/failed | HR 无法定位哪些员工没匹配 | 拆四类 + 点击"未匹配"下载 CSV |
| 下载模板后 Excel 打开看到工号是数字 | HR 保存时又丢前导零 | 模板 cell format `@` + 首行写"请勿修改格式"说明 |
| 重复导入"覆盖"语义不明 | HR 导入一次发现数据被清掉 | UI 上显式提供 merge/replace 两个按钮 |
| 导入中途退出 / 刷新 | ImportJob 永远 processing | 显示"正在后台处理，可安全离开；完成后可在任务列表查看" |
| Phase 11 导航改动后管理员看不到某个菜单 | 管理员找不到"绩效管理"入口 | 菜单配置 × role 映射表必须有 E2E 测试 |
| 员工端资格展示没有"数据更新时间" | 员工误以为数据是 live 的实际是缓存 | 每个卡片右上角显示"更新于 YYYY-MM-DD HH:MM" |
| HR 在员工详情里看到历史绩效但不知道换过部门 | 判断错分档合理性 | 每条历史绩效显示 `department_snapshot` |

---

## "Looks Done But Isn't" Checklist

- [ ] **员工端资格 API：** 常缺 employee 角色的水平越权测试 — 验证两个 employee 账号互访返回 403
- [ ] **员工端资格 API：** 常缺 PII masking — 验证 `detail` 字段不含具体日期和薪资数字
- [ ] **绩效档次引擎：** 常缺 ties 单测 — 验证 N 员工同分时全部归入同档
- [ ] **绩效档次引擎：** 常缺小样本单测 — 验证 sample_size < 阈值返回 `tier=null`
- [ ] **绩效档次快照：** 常缺失效触发 — 验证导入后快照自动刷新 + audit log 记录
- [ ] **工号前导零修复：** 常缺 xlsx 模板 cell format — 用 openpyxl 打开模板后 cell.number_format 必须是 `'@'`
- [ ] **工号前导零修复：** 常缺飞书字段类型校验 — 配置保存时拒绝非 text 类型的 employee_no 字段
- [ ] **工号前导零迁移：** 常缺人工确认步骤 — 迁移脚本必须生成"可疑清单 CSV"并需 HR 签字确认才执行
- [ ] **飞书同步日志：** 常缺四类拆分计数 — 验证 `{success, updated, unmatched, mapping_failed, failed}` 各自独立可见
- [ ] **飞书同步日志：** 常缺 sanity check — 验证同步后 DB 行数变化 ≈ synced_count，否则降级为 needs_review
- [ ] **Excel 模板下载：** 常缺 responseType: 'blob' — 前端服务必须指定，end-to-end 测试能 openpyxl 读回
- [ ] **Excel 模板下载：** 常缺权限守门 — 路由必须 require_roles
- [ ] **重复导入覆盖：** 常缺 merge/replace 语义开关 — 未提供开关时默认 merge（不清空空值）
- [ ] **并发导入：** 常缺互斥锁 — 同类型 ImportJob 同时只能跑一个
- [ ] **Celery 任务：** 常缺独立 Session — 任务签名里绝不能有 `db: Session` 参数
- [ ] **历史绩效展示：** 常缺 department_snapshot — 每条记录必须带记录时的部门
- [ ] **RBAC 新路由：** 常缺 AccessScopeService 调用 — manager 跨部门访问测试必须 403
- [ ] **Alembic 迁移：** 常缺 batch_alter_table — 任何列/约束改动必须走 batch
- [ ] **前端 useEffect：** 常缺依赖数组稳定化 — 网络面板验证同 endpoint 不会被打 10 次以上
- [ ] **Phase 11 验证：** 常缺 VERIFICATION.md — 不管结论如何必须有文档留痕

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 员工端水平越权（Pitfall 1） | HIGH | 1) 立即下线员工端资格接口 2) 审计 AuditLog 追溯谁访问了谁的数据 3) 通报合规 4) 修复后上线 |
| 档位抖动引发员工投诉（Pitfall 4） | MEDIUM | 1) 立即切到快照模式 2) 对抖动时段员工发送"技术问题已修复"说明 3) 冻结档位展示 24h 直到快照稳定 |
| 工号盲目补零破坏账号（Pitfall 6） | HIGH | 1) 从 `AuditLog(action='employee_no_rename')` 批量回滚 2) 通知受影响员工重新登录 3) 人工核对工号与外部 HR 系统 |
| 飞书同步"假成功"（Pitfall 7） | MEDIUM | 1) 跑 reconciliation 脚本比对 Feishu 源数据 vs DB 2) 将受影响年份的 `PerformanceRecord` 清空并重新同步 3) 追加缺失计数器字段到 FeishuSyncLog |
| 重复导入覆盖语义错误（Pitfall 8） | LOW-MEDIUM | 1) 从 AuditLog 找到 old_value 恢复 2) 前端加 merge/replace 开关 3) 写 runbook |
| 并发导入脏写（Pitfall 9） | LOW | 1) 加互斥锁 2) 回滚到最近 pre-import 快照（如果启用了 ImportJob snapshot） |
| RBAC 漏接（Pitfall 13） | HIGH if shipped | 1) 立即收紧到 admin-only 2) 全量审计谁访问过 3) 补 AccessScopeService |
| Celery session 问题（Pitfall 14） | LOW | 1) 重启 worker 2) 改为 SessionLocal() 模板 3) failed ImportJob 手动标记重跑 |
| 员工端 PII 泄露（Pitfall 18） | HIGH | 1) 立即下线员工端页面 2) 合规评估 3) 回放过去日志看谁看到了 4) masking 后上线并发公告 |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. 员工端资格横向越权 | 员工端资格展示 phase | 两个 employee 互访测试 403 |
| 2. 百分位 ties | 绩效档次引擎 phase | 单测覆盖 ties、全员同分 |
| 3. 小样本分档无意义 | 绩效档次引擎 phase | 单测 sample_size < 20 返回 tier=null |
| 4. 导入一条就全员档位漂移 | 绩效档次快照 phase | 多次请求返回相同 snapshot + "更新于 ts" UI 标签 |
| 5. xlsx / 飞书 employee_no 丢前导零 | 工号前导零修复 phase（上游） | 模板 openpyxl 读回 cell.number_format='@'；飞书字段类型非 text 拒绝 |
| 6. 存量工号补零破坏账号 | 工号前导零迁移 phase | 必须有人工确认清单 + AuditLog + rollback 脚本 |
| 7. 飞书同步假成功 | 飞书同步根因修复 phase | 四类计数器 + sanity check + HR UAT |
| 8. 覆盖语义歧义 | 调薪资格导入修复 phase | merge/replace 单测 4 矩阵 |
| 9. 并发导入脏写 | 调薪资格导入修复 phase | 互斥锁测试 + Celery concurrency=1 配置 |
| 10. 模板下载 404/Content-Type | 调薪资格导入修复 phase | E2E 测试 openpyxl 读回 + 前端 blob 下载 |
| 11. 跨部门/离职历史绩效 | 历史绩效展示 phase | department_snapshot 字段 + UI 标注 |
| 12. 绩效周期口径混乱 | 绩效模型 schema phase | 表结构预留 period_type + 默认 annual 迁移 |
| 13. RBAC 漏接 AccessScopeService | 每个新路由 phase（DoD） | 跨部门访问测试 403 |
| 14. Celery 跨线程 session | 每个新 Celery 任务 phase（DoD） | 代码 review：SessionLocal() + try/finally |
| 15. Pydantic v2 误用 | Schema phase（DoD） | 反例单测触发 422 |
| 16. Alembic SQLite batch | 每个表结构变更 phase | 本地 SQLite + PostgreSQL 双跑迁移 |
| 17. useEffect 抖动 | 员工端展示 phase | Network 面板请求频次 < 2/秒 |
| 18. 员工端 PII 暴露 | 员工端资格展示 phase（Requirements） | 合规审阅 masking 文案 + `detail` 字段扫描 |
| 19. Phase 11 验证变重写 | Phase 11 验证 phase | PR diff ≤ 10 文件 + VERIFICATION.md 留痕 |

---

## Sources

- `.planning/PROJECT.md` — v1.0/v1.1/v1.3 validated decisions + known issues
- `.planning/RETROSPECTIVE.md` — filter-before-paginate debt, Phase 11 SUMMARY 缺失, fix commits 模式
- `.planning/MILESTONES.md` — v1.3 飞书 OAuth 和前置集成经验
- `backend/app/services/eligibility_service.py` — 既有 check_employee / check_employees_batch / override 流程
- `backend/app/services/feishu_service.py` — `_map_fields` 里 employee_no 强转数字、`_build_employee_map` leading-zero fallback、`sync_*` 方法的 skipped 计数模糊问题
- `backend/app/services/import_service.py` — run_import, SAVEPOINT 模式, 模板下载, xlsx 无 text format
- `backend/app/services/access_scope_service.py` — 数据所有权守门模式参照
- 代码中已有 `alembic/versions/*.py` — batch_alter_table 既有模式参照
- FastAPI docs on `StreamingResponse` vs `Response` for binary content (verified via repo usage)
- Pydantic v2 migration guide (HIGH confidence — repo already uses v2 `ConfigDict` pattern)

---

*Pitfalls research for: v1.4 员工端资格可见 + 绩效档次 + 导入链路修复*
*Researched: 2026-04-20*
