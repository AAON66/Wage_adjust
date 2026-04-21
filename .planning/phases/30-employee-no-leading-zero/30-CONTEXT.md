# Phase 30: 工号前导零修复 - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Excel / 飞书 / 手动录入三条写入链路统一按字符串处理 `employee_no`，修复下游数据键源头。模板下发端约束为文本格式；读入端统一按 `str` 处理；飞书映射端去除 `str(int(value))` 误用；飞书配置保存时校验字段类型必须为 text。存量数据**不做迁移**，只修复未来写入路径；`_build_employee_map` 的 leading-zero 容忍匹配保留并加计数器观测，便于后续评估是否需要单独的存量修补 phase。

**Not in scope:**
- 存量工号数据批量 `zfill` 补零（EMPNO-05，推迟到 v1.5+）
- 工号改名 API / AuditLog 改名行为（和存量迁移一并延后）
- 全局 metrics / Prometheus 基础设施（Phase 30 只引入一个字段级计数器）

</domain>

<decisions>
## Implementation Decisions

### 飞书字段类型校验（EMPNO-03）
- **D-01:** 飞书多维表格绑定配置页「保存」时即时校验。服务端在 `POST /api/v1/feishu/config` 保存前调用飞书 `list_bitable_fields` 接口，拉取 bitable 字段元信息，若 `employee_no` 映射到的字段 type 不是 text（文本 / 多行文本），拒绝保存并返回结构化错误 `{error: "invalid_field_type", field: "employee_no", expected: "text", actual: "{type}"}`，前端展示「工号字段类型必须为文本」
- **D-02:** 同步运行时不做二次校验，以减少每次同步的 API 调用；保存时校验失败即阻断配置生效，保证后续同步从源头正确。若 HR 事后在飞书改了字段类型，需要他们重新保存配置触发校验

### 观测落地形式（EMPNO-04）
- **D-03:** `FeishuSyncLog` 模型新增字段 `leading_zero_fallback_count: int`（默认 0，向后兼容）。每次 `_build_employee_map` 查表时，如果一次查询是通过 `lstrip('0')` 的容忍匹配命中（即原工号不在 `emp_map` 但 stripped 版本命中），计数器 +1。同步结束后随 FeishuSyncLog 一起落库；HR 在「同步日志」页可直接看到这次同步有多少条记录是靠容忍匹配救回来的
- **D-04:** 该计数器是**诊断信号**，不是告警。数值 > 0 不降级同步状态；但在 UI 日志页显示时用黄色文字提示「N 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式」
- **D-05:** Alembic 迁移增加 `leading_zero_fallback_count INTEGER DEFAULT 0 NOT NULL`；走 `op.batch_alter_table` 保持 SQLite 兼容（项目既定模式）

### 批量导入规范化（EMPNO-02）
- **D-06:** 混合策略：模板端强制列格式为文本 + 读入端检测格式异常时报错并带补救提示
- **D-07:** `ImportService._load_table` 在 `pd.read_excel(dtype=str)` 读回后，对「关键业务键列」（`employee_no` / `manager_employee_no`）额外做 format sanity check：如果发现该行值是 `'1234.0'` 这种「float 被 stringified」的模式（正则 `^\d+\.0$`），或者 `isinstance(row['employee_no'], (int, float))` 未被 dtype 捕获的情况，该行进入 `failed_rows`，错误消息为「第 N 行员工工号列格式异常（疑似丢失前导零）。请在 Excel 中将该列改为「文本」格式后重新上传，或从系统重新下载最新模板」
- **D-08:** `FeishuService._map_fields` 对 `employee_no` 字段永远按 text 处理：删除 `if isinstance(value, float) and value == int(value): value = str(int(value))` 分支；统一 `value = str(value).strip()`；补一条 `logger.warning` 当进入的 raw value 类型非 str 时记录「飞书 employee_no 非文本类型，已强制转字符串（可能已丢失前导零）」

### Excel 模板（EMPNO-01）
- **D-09:** `build_template_xlsx` 对「员工工号」列统一设 `cell.number_format = '@'`（文本格式），包括表头行、示例行与其下若干预设空行（至少 100 行预设，避免 HR 新增数据时 Excel 重新识别列类型）。同策略套用到 `certifications` / `performance_grades` / `salary_adjustments` 全部模板的员工工号列，以及 `certifications` 的认证类型/阶段等其他短字符串列
- **D-10:** 示例行工号改为 `'02651'` 风格（体现前导零），其他示例字段（姓名、部门等）保持可识别的中文风格。目的是 HR 下载模板时能直观看到「工号是文本且带前导零」。保留 `EMP-` 前缀式工号的项目如果存在，在 placeholder 上注释「支持数字式工号（如 02651）或字母数字混合式（如 EMP-1001）」

### Claude's Discretion
- Pydantic `EmployeeBase.employee_no: str = Field(min_length=1, max_length=64)` 当前已拒绝 int/float 类型 JSON 输入，足够约束手动录入 API 层，不再新增 `field_validator`
- 正则 `^\d+\.0$` 的补救提示文案细节（保持「请改成文本格式后重新上传」大意即可）
- 新增单元测试的具体 mock 数据（覆盖 ties、类型转换、容忍匹配计数）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 内部参考
- `.planning/ROADMAP.md` § "Phase 30: 工号前导零修复" — 4 条 Success Criteria
- `.planning/REQUIREMENTS.md` § "工号前导零（EMPNO）" — EMPNO-01/02/03/04 原始定义

### 研究依据
- `.planning/research/STACK.md` — pandas `dtype=str` / openpyxl `number_format='@'` 技术方案
- `.planning/research/ARCHITECTURE.md` — `FeishuService._map_fields:240-245` 与 `ImportService.SUPPORTED_TYPES` 根因定位
- `.planning/research/PITFALLS.md` — Pitfall 5/6（存量迁移风险）、Pitfall 16（Alembic batch_alter_table）
- `.planning/research/SUMMARY.md` § "Theme 3: 上游数据源是问题的真正源头"

### 代码集成点
- `backend/app/services/feishu_service.py:215-253` — `_map_fields` 方法（D-08 改动点）
- `backend/app/services/feishu_service.py:259-282` — `_build_employee_map` / `_lookup_employee`（D-03 计数器插桩点）
- `backend/app/services/import_service.py:254-309` — `build_template_xlsx`（D-09/D-10 改动点）
- `backend/app/services/import_service.py:381-430` — `_load_table` + required/alias 校验（D-07 改动点）
- `backend/app/models/feishu_sync_log.py` — 增加 `leading_zero_fallback_count` 字段（D-03）
- `backend/app/api/v1/feishu.py` + `backend/app/schemas/feishu.py` — 配置保存校验入口（D-01）
- `backend/app/schemas/employee.py:8-30` — `EmployeeBase.employee_no` 类型约束（现状足够，Claude's Discretion 中不改）

### 既定模式参考
- `.planning/codebase/CONVENTIONS.md` — Pydantic v2、`from __future__ import annotations`、keyword-only 参数等既定约定
- `.planning/codebase/ARCHITECTURE.md` — `api/ → services/ → engines/ → models/` 分层方向

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FeishuService._build_employee_map` / `_lookup_employee`（feishu_service.py:259-282）— 容忍匹配已就绪，Phase 30 只在此插入计数器
- `FeishuSyncLog` 模型（models/feishu_sync_log.py）— 已有 sync 日志结构，直接扩展字段即可
- `op.batch_alter_table` 模式 — v1.0 Phase 01 起已建立的 SQLite 兼容迁移路径
- `build_template_xlsx` 的 openpyxl + BytesIO pattern（import_service.py:254-309）— 现有模板生成框架完整

### Established Patterns
- 所有 Pydantic v2 Schema 使用 `field_validator`、`model_validator`，禁用 v1 的 `@validator`（project convention）
- 飞书 API 调用统一通过 `httpx` 直调（拒绝迁移 `lark-oapi`）— 见研究 STACK.md 结论
- `stdlib logging` via `dictConfig`（core/logging.py）— Phase 30 的 warning 继续走 `logger.warning`
- 批量导入错误收集走 `failed_rows` list + `ImportService` 的统一 schema — 不变

### Integration Points
- **FeishuSyncLog schema 迁移** — Alembic batch_alter_table 增加字段，零 downtime
- **飞书配置保存校验** — 需要增加一个新方法 `FeishuService.validate_field_mapping(app_token, table_id, field_mapping)`，在 `create_config` / `update_config` 保存前调用
- **模板下载端** — `build_template_xlsx` 内部改造，调用方无感知
- **批量导入端** — `_load_table` 增加 format sanity check 分支，不改变对外 API

</code_context>

<specifics>
## Specific Ideas

- 用 `'02651'` 作为模板示例工号（用户原话中的具体工号），HR 一看就理解"前导零不应丢失"
- 补救提示文案方向：「该列已丢失前导零格式」+「请改文本列」+「或重新下载模板」三段式
- FeishuSyncLog 页面显示「N 条记录通过前导零容忍匹配成功」的黄色提示与 Phase 31 的五类计数器同一页面展示

</specifics>

<deferred>
## Deferred Ideas

- 存量工号数据修补（HR 签字清单 + AuditLog 改名 + 回滚脚本）— v1.5+ EMPNO-05
- 新建独立的 `MetricEvent` 表作为通用观测基础设施 — 超出 v1.4 scope
- 飞书同步运行时的字段类型二次校验（D-02 已决定不做）
- 为 `EmployeeBase.employee_no` 增加 Pydantic `field_validator` 拒绝特定模式（现有 `str` + `min_length=1` 已够）
- 模板下载时的自定义 HTTP Header 提示「请用 Excel 打开并保持文本列格式」— UX 增强，留待观察 HR 反馈

</deferred>

---

*Phase: 30-employee-no-leading-zero*
*Context gathered: 2026-04-21*
