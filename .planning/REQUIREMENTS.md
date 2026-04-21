# Requirements: 公司综合调薪工具 — v1.4 员工端体验完善与导入链路稳定性

**Defined:** 2026-04-21
**Core Value:** HR 能运行一次完整、可审计的调薪周期——从员工提交证据、AI 评估到调薪审批，每个决策都可解释可追溯

---

## v1.4 Requirements

### 员工端自助（ESELF — Employee Self-Service）

- [ ] **ESELF-01**: 员工可在 `MyReview` 页面随时查看本人当前的调薪资格状态（合格 / 不合格 / 需审核三态），不依赖活动调薪周期
- [ ] **ESELF-02**: 资格不合格时，员工页面明确列出未通过的规则类别（入职时长 / 上次调薪间隔 / 绩效 / 假勤），每条附带脱敏后的原因说明
- [ ] **ESELF-03**: 员工可在 `MyReview` 页面看到本人所属的绩效档次（1/2/3 档），但不显示具体排名、具体百分位、同档其他人
- [ ] **ESELF-04**: 员工端所有自助端点必须使用无参数路由（如 `/eligibility/me`、`/performance/me/tier`），不接受 `{employee_id}` 变体；跨员工访问返回 403
- [ ] **ESELF-05**: 员工端页面显示「数据更新于 YYYY-MM-DD HH:MM」时间戳，表明资格与档次的数据新鲜度

### 绩效管理（PERF — Performance Management）

- [ ] **PERF-01**: 新增独立「绩效管理」页面（HR + admin 可见），包含绩效列表、导入入口、档次分布视图三部分
- [ ] **PERF-02**: HR 可通过「绩效管理」页面独立导入绩效记录（Excel 上传），导入前展示 Preview + diff
- [ ] **PERF-03**: 系统提供 `PerformanceTierEngine` 纯引擎：输入排序后的 `(employee_id, grade)` 列表，输出 `{employee_id: 1|2|3|None}`；按 `PERCENT_RANK()` 口径，ties（同绩效等级）归入同档
- [ ] **PERF-04**: 当参与档次评估的样本量 < `Settings.performance_tier_min_sample_size`（默认 50）时，引擎对全员返回 `tier=null`；员工端 UI 显示「样本不足」提示
- [ ] **PERF-05**: 档次刷新采用混合策略：绩效数据成功导入后自动触发 `invalidate_tier_cache(year)` 并重算快照；HR 可在「绩效管理」页面手动点击「重算档次」覆盖推荐
- [ ] **PERF-06**: 当实际绩效分布偏离 20/70/10 超过 ±5% 时，HR 端分布视图顶部显示黄色 warning 横幅（分布仍按 `PERCENT_RANK` 硬切，不做"挪人"；员工端不可见该告警）
- [ ] **PERF-07**: 员工评估详情页（`EvaluationDetail`）与调薪建议详情页（`SalaryDetail`）展示历史绩效表：周期 / 绩效等级 / 评语 / 部门快照 四列，按 `cycle_start_date` 倒序
- [ ] **PERF-08**: `PerformanceRecord` 新增 `department_snapshot` 字段（记录该条绩效录入时员工所属部门），UI 每条历史绩效显示该字段

### 工号前导零（EMPNO — Employee Number Leading Zero）

- [ ] **EMPNO-01**: Excel 导入模板使用 openpyxl `cell.number_format = '@'` 文本格式，下发模板的工号列被 Excel 识别为文本
- [ ] **EMPNO-02**: Excel 读取端（`pd.read_excel(dtype=str)`）+ 手动录入端（Pydantic `field_validator` 拒绝 `int/float` 类型 employee_no）+ 飞书同步端（`_map_fields` 对 `employee_no` 永远按 text 处理，禁用 `str(int(value))` 路径）三链路统一按字符串读入
- [ ] **EMPNO-03**: 飞书多维表格绑定配置页校验 `employee_no` 字段类型必须为 text；非 text 类型时阻止保存并提示配置错误
- [ ] **EMPNO-04**: 存量数据保持现状不迁移（仅修复未来写入路径）；`_build_employee_map` 在匹配时保留 leading-zero 容忍匹配并加 metrics 告警，便于后续观测是否仍有旧数据影响

### 调薪资格导入修复（IMPORT — Import Pipeline Fixes）

- [ ] **IMPORT-01**: `ImportService.SUPPORTED_TYPES` 补齐 `hire_info` / `non_statutory_leave` 两类；对应 `REQUIRED_COLUMNS` / `COLUMN_ALIASES` / `_import_*` / `build_template_xlsx` 分支同步补齐
- [ ] **IMPORT-02**: 所有调薪资格导入类型的「下载模板」API 返回非空 `.xlsx` 文件（openpyxl 可成功读回），前端 axios 使用 `responseType: 'blob'`
- [ ] **IMPORT-03**: 飞书同步方法 `sync_performance_records` / `sync_salary_adjustments` / `sync_hire_info` / `sync_non_statutory_leave` 通过 `_with_sync_log` helper 统一写入 `FeishuSyncLog`，含 `{success, updated, unmatched, mapping_failed, failed}` 五类计数器
- [ ] **IMPORT-04**: 飞书同步完成后运行 sanity check：若 `unmatched + mapping_failed + failed > 0`，顶层状态降级为 `partial`；UI 在「同步日志」页面按四类分别展示，并提供「下载未匹配工号 CSV」按钮（前 20 个工号）
- [ ] **IMPORT-05**: 导入支持 `overwrite_mode: Literal['merge', 'replace']`（默认 `merge`）；`merge` 语义为空值保留旧值，`replace` 语义为空值清空字段；HR 必须在 UI 显式勾选 replace 才生效；`AuditLog` 记录 `overwrite_mode`
- [ ] **IMPORT-06**: 同一 `import_type` 的 `ImportJob` 同时只能有一个 `processing` 状态；并发提交返回 409 冲突；参照 `FeishuService.is_sync_running()` 模式实现互斥锁
- [ ] **IMPORT-07**: 导入前强制展示 Preview + diff（按业务键分 Insert / Update / No-change / 冲突四类计数，字段级 diff 展示新旧值），HR 需显式点击「确认导入」才落库

### 导航菜单补齐（NAV — Navigation Phase 11 Verification）

- [ ] **NAV-04**: 补齐 Phase 11 导航菜单重构的 `SUMMARY.md`（或 v1.4 对应 phase 下的 `VERIFICATION.md`），内容覆盖四角色（admin / hrbp / manager / employee）UAT 清单执行截图
- [ ] **NAV-05**: v1.4 新增菜单项（「绩效管理」、员工端「调薪资格」标签页）必须纳入 UAT 清单，与既有菜单一起验证角色过滤逻辑

---

## v2 / v1.5+ Requirements

**Deferred 到 v1.5+，不在 v1.4 roadmap 中。**

### 员工端进阶体验

- **ESELF-06**: 达成进度条（如"司龄 11/12 月 = 92%"）
- **ESELF-07**: 预计达标日期（ETA）
- **ESELF-08**: 档位趋势展示（过去 N 周期档位变化）
- **ESELF-09**: 员工申诉 / 复核入口

### 导入与飞书体验

- **IMPORT-08**: 导入来源 badge（Excel / 飞书 / 手动）+ 历史时间戳
- **IMPORT-09**: 导入回滚按钮（需 pre-image snapshot）
- **IMPORT-10**: 预览阶段可编辑（减少下载-改-上传循环）
- **IMPORT-11**: 同岗位族分档对照

### 基础设施

- **INFRA-01**: boto3 Python 3.10+ 迁移（2026-04-29 EOL，单独跟踪）
- **INFRA-02**: 资格批量查询游标分页（filter-before-paginate 性能瓶颈）
- **INFRA-03**: PostgreSQL 生产环境迁移收尾
- **INFRA-04**: Redis 集群 / MinIO/S3 生产加固
- **INFRA-05**: E2E 集成测试套件
- **INFRA-06**: WebSocket 实时通知（替代轮询）
- **INFRA-07**: 飞书工作台免登（`tt.requestAccess`）
- **INFRA-08**: 嵌入式飞书 QR 扫码面板（原 FUI-01 / FUI-03 deferred）

### 工号与存量数据

- **EMPNO-05**: 存量工号数据修补（HR 签字清单 + AuditLog + 回滚脚本；v1.4 决定不做，留 v1.5+）

---

## Out of Scope

v1.4 明确不做的功能。

| Feature | Reason |
|---------|--------|
| 员工端显示具体排名 / 同档其他人 / 精确百分位 / 具体分数 | 合规红线（PIPL + 员工感受） |
| 强切 20/70/10 且拆散同绩效等级的员工 | 数学精准但员工投诉高发；已决议 ties 同档 |
| 静默覆盖导入（无 preview） | HR 数据不可误覆盖，preview 是行业基线 |
| 空单元格默认清空字段 | 歧义大，行业默认 `merge` + `replace` 显式切换 |
| 自动 zfill 存量工号 | 会误伤合法短工号员工，破坏账号 |
| `/eligibility/{employee_id}` 给 employee 角色调用 | 横向越权风险 |
| 员工端看到带具体日期 / 薪资 / 绩效分数的 detail | 必须走 `EligibilityMaskingService` 脱敏 |
| 频繁跳档（实时重算）| 档位应稳定，依赖显式 invalidate + snapshot |
| 切换飞书集成到 `lark-oapi` SDK | 40+ 间接依赖，零业务收益 |
| 档位刷新定时任务（每日 02:00） | v1.4 采用"导入自动+HR 手动"混合策略，不加定时 |

---

## Traceability

由 Roadmapper 在创建 ROADMAP.md 时填充。

| Requirement | Phase | Status |
|-------------|-------|--------|
| ESELF-01 | — | Pending |
| ESELF-02 | — | Pending |
| ESELF-03 | — | Pending |
| ESELF-04 | — | Pending |
| ESELF-05 | — | Pending |
| PERF-01 | — | Pending |
| PERF-02 | — | Pending |
| PERF-03 | — | Pending |
| PERF-04 | — | Pending |
| PERF-05 | — | Pending |
| PERF-06 | — | Pending |
| PERF-07 | — | Pending |
| PERF-08 | — | Pending |
| EMPNO-01 | — | Pending |
| EMPNO-02 | — | Pending |
| EMPNO-03 | — | Pending |
| EMPNO-04 | — | Pending |
| IMPORT-01 | — | Pending |
| IMPORT-02 | — | Pending |
| IMPORT-03 | — | Pending |
| IMPORT-04 | — | Pending |
| IMPORT-05 | — | Pending |
| IMPORT-06 | — | Pending |
| IMPORT-07 | — | Pending |
| NAV-04 | — | Pending |
| NAV-05 | — | Pending |

**Coverage:**
- v1.4 requirements: 26 total
- Mapped to phases: 0（pending roadmap）
- Unmapped: 26 ⚠️

---

*Requirements defined: 2026-04-21*
*Last updated: 2026-04-21 after v1.4 kickoff*
