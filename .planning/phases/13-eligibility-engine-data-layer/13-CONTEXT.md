# Phase 13: Eligibility Engine & Data Layer - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

系统基于 4 条规则自动判定员工调薪资格（入职时长、上次调薪间隔、绩效等级、非法定假期天数），缺失数据显示"数据缺失"状态，所需数据支持三种导入通道（Excel、飞书、手动录入）。

</domain>

<decisions>
## Implementation Decisions

### 数据模型设计
- **D-01:** `hire_date` 和 `last_salary_adjustment_date` 直接加到 Employee 模型作为新字段，通过 Alembic 迁移添加
- **D-02:** 新建 `PerformanceRecord` 模型，每条记录 = 一个员工某年度的绩效等级（A/B/C/D/E），支持多年历史
- **D-03:** 新建 `SalaryAdjustmentRecord` 模型，每次调薪一条记录（日期、类型[转正/年度/专项]、金额），查询最近一次调薪时间方便

### 资格规则引擎
- **D-04:** 规则阈值配置化——6个月入职、6个月调薪间隔、C级绩效、30天假期等阈值放在配置文件或数据库，HR 可调整而不需改代码
- **D-05:** 资格判定结果实时计算不存储——每次查询时根据最新数据实时计算 4 条规则，避免快照与实际数据不一致
- **D-06:** 引擎遵循现有 EvaluationEngine/SalaryEngine 模式——纯计算类，无 DB 依赖，接收输入数据返回结构化结果

### 数据导入通道
- **D-07:** 三种导入通道全部实现：Excel 批量导入、飞书同步、手动录入
- **D-08:** 绩效和调薪历史的 Excel 模板分开——绩效模板（工号+年度+等级）和调薪历史模板（工号+日期+类型+金额）分别导入
- **D-09:** 飞书同步复用现有 feishu_service.py 的多维表格同步模式

### 缺失数据处理
- **D-10:** 任何规则数据缺失时整体状态为"待定"——已有数据的规则正常判定（合格/不合格），缺失的显示"数据缺失"
- **D-11:** 不需要催办机制——仅在资格列表中显示"数据缺失"状态，HR 自行导入

### Claude's Discretion
- 具体的 Alembic 迁移脚本结构
- EligibilityEngine 的内部方法拆分
- API 端点路径和返回结构设计
- 飞书同步的具体表格字段映射

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 数据模型
- `backend/app/models/employee.py` — 现有 Employee 模型，需添加 hire_date、last_salary_adjustment_date
- `backend/app/models/attendance_record.py` — 现有考勤模型，含 leave_days 字段
- `backend/app/models/salary_recommendation.py` — 现有调薪建议模型，参考字段设计
- `backend/app/models/mixins.py` — UUID、CreatedAt、UpdatedAt 混入

### 引擎模式
- `backend/app/engines/evaluation_engine.py` — 纯计算引擎参考模式（dataclass 输入输出，无 DB）
- `backend/app/engines/salary_engine.py` — 另一个纯计算引擎参考

### 导入服务
- `backend/app/services/import_service.py` — 现有 CSV/XLSX 导入流程（pandas + SAVEPOINT）
- `backend/app/services/feishu_service.py` — 飞书多维表格同步模式

### 需求文档
- `.planning/REQUIREMENTS.md` — ELIG-01, ELIG-02, ELIG-03, ELIG-04, ELIG-08, ELIG-09

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ImportService`: 已有 employee/certification 导入支持，可扩展 performance_grades 和 salary_adjustments 导入类型
- `FeishuService`: 已有考勤数据同步，可复用多维表格同步模式
- `EvaluationEngine/SalaryEngine`: 纯计算引擎模式，EligibilityEngine 应遵循相同模式

### Established Patterns
- Models 使用 UUIDPrimaryKeyMixin + CreatedAtMixin + UpdatedAtMixin
- Schemas 使用 Pydantic BaseModel + ConfigDict(from_attributes=True)
- ImportService 使用 pandas DataFrame + 逐行 SAVEPOINT 处理
- 所有 API 在 `/api/v1/` 下

### Integration Points
- Employee 模型扩展需要 Alembic 迁移
- ImportService 需要新增 performance_grades 和 salary_adjustments 导入类型
- API 路由注册在 `backend/app/api/v1/router.py`
- 前端侧边栏已有菜单插槽（Phase 11 分组结构）

</code_context>

<specifics>
## Specific Ideas

- AttendanceRecord 现有 leave_days 字段未区分法定/非法定假期，需要在 ELIG-04 中明确区分方式
- PerformanceRecord 需要支持 A/B/C/D/E 等级体系
- SalaryAdjustmentRecord 的 type 字段需区分：转正调薪、年度调薪、专项调薪
- 配置化的规则阈值应支持按评估周期独立配置（不同年度可能有不同阈值）

</specifics>

<deferred>
## Deferred Ideas

None — 讨论保持在阶段范围内

</deferred>

---

*Phase: 13-eligibility-engine-data-layer*
*Context gathered: 2026-04-02*
