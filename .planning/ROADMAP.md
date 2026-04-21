# Roadmap: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-10 (shipped 2026-03-30)
- ✅ **v1.1 体验优化与业务规则完善** — Phases 11-17 (shipped 2026-04-07)
- ✅ **v1.2 生产就绪与数据管理完善** — Phases 18-24 (shipped 2026-04-16)
- ✅ **v1.3 飞书登录与登录页重设计** — Phases 25-28 (shipped 2026-04-20; Phase 29 cancelled)
- 🚧 **v1.4 员工端体验完善与导入链路稳定性** — Phases 30-37 (in progress, started 2026-04-21)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-10) — SHIPPED 2026-03-30</summary>

- [x] Phase 1: Security Hardening and Schema Integrity — completed 2026-03-26
- [x] Phase 2: Evaluation Pipeline Integrity — completed 2026-03-31
- [x] Phase 3: Approval Workflow Correctness — completed 2026-03-31
- [x] Phase 4: Audit Log Wiring — completed 2026-03-31
- [x] Phase 5: Document Deduplication and Multi-Author — completed 2026-03-31
- [x] Phase 6: Batch Import Reliability — completed 2026-03-31
- [x] Phase 7: Dashboard and Cache Layer — completed 2026-03-31
- [x] Phase 8: Employee Self-Service UI — completed 2026-03-31
- [x] Phase 9: Feishu Attendance Integration — completed 2026-03-31
- [x] Phase 10: External API Hardening — completed 2026-03-31

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 体验优化与业务规则完善 (Phases 11-17) — SHIPPED 2026-04-07</summary>

- [x] Phase 11: Menu & Navigation Restructuring (1/1 plan) — completed 2026-03-31
- [x] Phase 12: Account-Employee Binding (2/2 plans) — completed 2026-04-01
- [x] Phase 13: Eligibility Engine & Data Layer (2/2 plans) — completed 2026-04-02
- [x] Phase 14: Eligibility Visibility & Overrides (2/2 plans) — completed 2026-04-04
- [x] Phase 15: Multimodal Vision Evaluation (2/2 plans) — completed 2026-04-04
- [x] Phase 16: File Sharing Workflow (2/2 plans) — completed 2026-04-06
- [x] Phase 17: Salary Display Simplification (2/2 plans) — completed 2026-04-07

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 生产就绪与数据管理完善 (Phases 18-24) — SHIPPED 2026-04-16</summary>

- [x] Phase 18: Python 3.9 兼容与依赖修复 (3/3 plans) — completed 2026-04-08
- [x] Phase 19: Celery+Redis 异步基础设施 (3/3 plans) — completed 2026-04-09
- [x] Phase 20: 员工所属公司字段 (2/2 plans) — completed 2026-04-09
- [x] Phase 21: 文件共享拒绝清理与状态标签 (2/2 plans) — completed 2026-04-09
- [x] Phase 22: AI 评估与批量导入异步迁移 (3/3 plans) — completed 2026-04-12
- [x] Phase 23: 调薪资格统一导入管理 (3/3 plans) — completed 2026-04-15
- [x] Phase 24: 生产部署配置 (2/2 plans) — completed 2026-04-16

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 飞书登录与登录页重设计 (Phases 25-28) — SHIPPED 2026-04-20</summary>

- [x] Phase 25: 技术债清理 (1/1 plan) — completed 2026-04-16
- [x] Phase 26: 飞书 OAuth2 后端接入 (2/2 plans) — completed 2026-04-16
- [x] Phase 27: 飞书 OAuth2 前端集成 (3/3 plans) — completed 2026-04-20 (D-17 redirect-flow)
- [x] Phase 27.1: 设置页飞书账号绑定与解绑 (INSERTED, 3/3 plans) — completed 2026-04-20
- [x] Phase 28: 登录页粒子背景 (2/2 plans) — completed 2026-04-20
- ~~Phase 29: 登录页重设计整合~~ — **Cancelled 2026-04-20** (LOGIN-01 Won't Do; 当前 Login 页 + 粒子背景已满足实用需求)

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

### 🚧 v1.4 员工端体验完善与导入链路稳定性 (In Progress)

**Milestone Goal:** 让员工在自己的页面就能看到本次调薪的资格状态与绩效档次，补齐绩效导入与历史展示链路，并修复工号前导零、飞书同步、Excel 模板下载等已知阻塞性 bug。

**Execution Order:**
Phases execute in numeric order with data-integrity-first sequencing: 30 → 31 → 32 → 33 → 34 → 35 → 36 → 37.

**Key sequencing rationale:**
- **Phase 30 (工号前导零) 最先** — 下游所有导入/同步/匹配都以稳定的 `employee_no` 为业务键；修复晚了需要全部重跑
- **Phase 31 (飞书可观测性) 先于 32 (导入功能补齐)** — 先有日志再诊断，HR 才能自助排查导入 bug
- **Phase 33 (TierEngine 纯引擎) 先于 34 (Service + API)** — 延续 `EligibilityEngine` 分层模式，Service 消费 Engine
- **Phase 35 (员工端) 依赖 30 + 34** — 工号稳定 + 档次 API 就绪后才能交付员工可见价值
- **Phase 36 (历史绩效) 依赖 34** — 复用 `/performance/records` API 的读取口径
- **Phase 37 (Phase 11 验证) 独立** — 纯文档 + UAT，不阻塞任何 phase，可插入空档期

- [ ] **Phase 30: 工号前导零修复** - Excel/飞书/手动三链路统一按字符串处理 employee_no，修复下游数据键源头 (EMPNO-01/02/03/04)
- [ ] **Phase 31: 飞书同步可观测性** - 四个同步方法统一写入 `FeishuSyncLog` 五类计数器，HR 可自助诊断「假成功」问题 (IMPORT-03/04)
- [ ] **Phase 32: 调薪资格导入功能补齐** - 补齐 hire_info/non_statutory_leave 两类导入、Excel 模板下载、覆盖语义、并发互斥、Preview+diff (IMPORT-01/02/05/06/07)
- [ ] **Phase 33: 绩效档次纯引擎** - `PerformanceTierEngine` 按 `PERCENT_RANK` 口径分档，ties 同档、样本不足返回 null、分布偏离告警 (PERF-03/04/06)
- [ ] **Phase 34: 绩效管理服务与 API** - 新增「绩效管理」页面 + `/api/v1/performance` 路由 + 档次缓存/快照 + 导入回调触发重算 (PERF-01/02/05/08)
- [ ] **Phase 35: 员工端自助体验** - `MyReview` 展示本人资格状态（三态+未通过规则）+ 绩效档次徽章 + 数据更新时间戳，全部走无参数路由 (ESELF-01/02/03/04/05)
- [ ] **Phase 36: 历史绩效展示** - `EvaluationDetail` 与 `SalaryDetail` 复用 `PerformanceHistoryPanel`，按 `cycle_start_date` 倒序展示含部门快照的历史绩效 (PERF-07)
- [ ] **Phase 37: Phase 11 导航验证补齐** - 补齐 Phase 11 `SUMMARY.md`/`VERIFICATION.md`，四角色 UAT 清单覆盖 v1.4 新增菜单（纯文档，无代码） (NAV-04/05)

## Phase Details

### Phase 30: 工号前导零修复
**Goal**: HR 导入或飞书同步的员工工号能完整保留前导零，下游所有匹配/导入/同步动作在稳定的 `employee_no` 键上运行
**Depends on**: Nothing (数据键源头，最早交付)
**Requirements**: EMPNO-01, EMPNO-02, EMPNO-03, EMPNO-04
**Success Criteria** (what must be TRUE):
  1. HR 从「下载模板」拿到的 xlsx 文件中工号列是文本格式（openpyxl 读回 `cell.number_format == '@'`），在 Excel 里手动录入 `01234` 再保存不会变成 `1234`
  2. 三条写入链路（Excel 导入 / 飞书同步 / 手动表单录入）对同一个工号字符串 `01234` 的读取结果一致，写入数据库后保留前导零不被转为数字
  3. 管理员在飞书多维表格绑定配置页尝试把 `employee_no` 字段选成「数字」类型时被阻止保存，并看到「配置错误：工号字段类型必须为 text」
  4. 存量数据未迁移但未来写入路径已修复；`_build_employee_map` 匹配时对 leading-zero 差异（如 `1234` vs `01234`）仍能容忍匹配并在日志里打出告警 metrics，便于后续观测
**Plans**: TBD

### Phase 31: 飞书同步可观测性
**Goal**: HR 在「同步日志」页面能看到每次飞书同步的五类计数器（success/updated/unmatched/mapping_failed/failed），不再出现「飞书 API 返回 200 但数据未落库」的无法诊断场景
**Depends on**: Phase 30 (工号修复后 `unmatched_count` 才能准确反映真实匹配失败而非前导零丢失)
**Requirements**: IMPORT-03, IMPORT-04
**Success Criteria** (what must be TRUE):
  1. `sync_performance_records` / `sync_salary_adjustments` / `sync_hire_info` / `sync_non_statutory_leave` 四个同步方法每次执行都在 `FeishuSyncLog` 产生一条记录，含 `{success, updated, unmatched, mapping_failed, failed}` 五类计数器
  2. 同步完成时若 `unmatched + mapping_failed + failed > 0`，顶层状态降级为 `partial`，不再显示「全部成功」
  3. HR 在「同步日志」页面看到四类计数分别展示（成功/更新/未匹配/映射失败/写库失败），可以点击「下载未匹配工号 CSV」拿到前 20 个未匹配工号排查
  4. 同一个同步流程被触发两次（网络抖动或重复点击），日志里能看到两条独立记录，不会静默合并或丢失
**Plans**: TBD

### Phase 32: 调薪资格导入功能补齐
**Goal**: HR 能通过调薪资格导入页面完整操作 hire_info / non_statutory_leave 等所有导入类型，模板下载返回真实 xlsx 文件，覆盖语义和并发行为符合行业默认
**Depends on**: Phase 31 (先有同步/导入日志再补导入功能，HR 才能自助诊断)
**Requirements**: IMPORT-01, IMPORT-02, IMPORT-05, IMPORT-06, IMPORT-07
**Success Criteria** (what must be TRUE):
  1. HR 点击「下载模板」按钮，对所有调薪资格导入类型（含 hire_info / non_statutory_leave）都能拿到非空 `.xlsx` 文件，前端用 `responseType: 'blob'` 下载后 openpyxl 可成功读回
  2. HR 上传导入文件前能看到 Preview + diff（按业务键分 Insert / Update / No-change / 冲突四类计数，字段级 diff 展示新旧值），点击「确认导入」才真正落库
  3. HR 可显式勾选「覆盖模式」在 merge（空值保留旧值，默认）和 replace（空值清空字段）之间切换；`AuditLog` 记录本次导入的 `overwrite_mode`
  4. 同一个 `import_type` 的导入任务同时只能有一个 `processing` 状态；并发第二次提交时接口返回 409 冲突并提示「该类型导入正在进行中」
  5. HR 导入同一批数据两次（模拟重复提交），系统按员工+周期维度覆盖更新，不会产生重复行
**Plans**: TBD

### Phase 33: 绩效档次纯引擎
**Goal**: 系统能根据排序后的绩效列表计算每个员工的 1/2/3 档（20/70/10），ties 归入同档，小样本下返回 null，分布偏离硬切比例时产生告警信号
**Depends on**: Nothing (纯引擎无 I/O，可独立开发和单测)
**Requirements**: PERF-03, PERF-04, PERF-06
**Success Criteria** (what must be TRUE):
  1. 调用 `PerformanceTierEngine.assign()` 输入排序后的 `(employee_id, grade)` 列表，返回 `{employee_id: 1|2|3|None}` 映射；相同 grade 的员工被分到同一档（ties 不被机械拆分）
  2. 输入样本量 < `Settings.performance_tier_min_sample_size`（默认 50）时，引擎对全员返回 `tier=null`，并在结果里带 `insufficient_sample=true` 标志
  3. 输入人数为 0 / 1 / 2 / 3 等边界样本时引擎不抛异常，行为与「样本不足」分支一致
  4. 当实际分档分布偏离 20/70/10 超过 ±5% 时，引擎输出结构里带 `distribution_warning=true` 标志，供上层 UI 在 HR 端顶部显示黄色 warning 横幅
  5. 单元测试覆盖 20+ 用例：ties、全员同分、samples=0/1/2/3、分布偏离、`min_sample_size` 可配置化
**Plans**: TBD

### Phase 34: 绩效管理服务与 API
**Goal**: HR 有独立「绩效管理」页面（列表 + 导入 + 档次分布），档次在导入完成后自动刷新，HR 也能手动触发重算覆盖
**Depends on**: Phase 33 (Service 消费 Engine)
**Requirements**: PERF-01, PERF-02, PERF-05, PERF-08
**Success Criteria** (what must be TRUE):
  1. HR + admin 在导航菜单看到「绩效管理」入口，进入后看到三部分：绩效记录列表、导入入口、档次分布视图（employee/manager 角色看不到该菜单）
  2. HR 在「绩效管理」页面上传 Excel 绩效记录后先看到 Preview + diff，确认后落库，落库完成后档次分布视图在刷新时立即反映新数据（无需重启服务）
  3. HR 点击「重算档次」按钮可手动触发档次快照重算，UI 上显示重算完成时间戳
  4. 新录入的每条 `PerformanceRecord` 持久化员工当时的部门名称到 `department_snapshot` 字段；历史记录里能看到员工变动过部门前后的部门归属
  5. `/api/v1/performance/records` 和 `/api/v1/performance/tier-summary` 返回的数据与底层 `PerformanceRecord` 表口径一致，不同查询入口不会出现档次漂移
**Plans**: TBD

### Phase 35: 员工端自助体验
**Goal**: 员工在自己的 `MyReview` 页面能随时看到本次调薪的资格状态（三态+未通过规则）和绩效档次（1/2/3 档），不需要 HR 介入、不暴露其他员工数据
**Depends on**: Phase 30 (工号稳定) + Phase 34 (档次 API 就绪)
**Requirements**: ESELF-01, ESELF-02, ESELF-03, ESELF-04, ESELF-05
**Success Criteria** (what must be TRUE):
  1. 员工登录后在 `MyReview` 页面看到「调薪资格」区域，显示本人当前的资格状态（合格 / 不合格 / 需审核）和当前周期，不需要 HR 配置活动周期也能看到
  2. 资格不合格时页面明确列出未通过的规则类别（入职时长 / 上次调薪间隔 / 绩效 / 假勤），每条附有脱敏后的原因说明（不含具体 YYYY-MM-DD 日期或薪资数字）
  3. 员工页面看到本人的绩效档次徽章（1/2/3 档），样本不足时显示「本年度全公司绩效样本不足，暂不分档」，但任何时候都看不到具体排名、具体百分位、同档其他人名单
  4. 员工 A 尝试访问员工 B 的资格接口（如手动构造 `/eligibility/{B_employee_id}` URL）时收到 403；所有员工自助端点都是无参数路由（`/eligibility/me`、`/performance/me/tier`）
  5. 页面显示「数据更新于 YYYY-MM-DD HH:MM」时间戳，员工能看到资格与档次的数据新鲜度
**Plans**: TBD
**UI hint**: yes

### Phase 36: 历史绩效展示
**Goal**: 评估详情页与调薪建议详情页能展示员工历史绩效的周期/等级/评语/部门快照，帮助 HR 和 manager 在审批时看到员工的绩效连续性
**Depends on**: Phase 34 (复用 `/performance/records` API + `department_snapshot` 字段)
**Requirements**: PERF-07
**Success Criteria** (what must be TRUE):
  1. HR/manager 打开员工评估详情页（`EvaluationDetail`）在底部看到「历史绩效」表，四列：周期 / 绩效等级 / 评语 / 部门快照，按 `cycle_start_date` 倒序排列
  2. 同一个员工的历史绩效面板在调薪建议详情页（`SalaryDetail`）复用展示，两处口径一致
  3. 员工没有任何历史绩效时显示「暂无历史绩效记录」空状态，不报错不崩溃
  4. 员工在不同时期所属部门发生变化时，历史绩效表每条记录显示的 `department_snapshot` 反映该条绩效录入时员工所属的部门（不是当前部门）
**Plans**: TBD
**UI hint**: yes

### Phase 37: Phase 11 导航验证补齐
**Goal**: Phase 11（v1.1 菜单重构）遗留的文档债务与 UAT 债务补齐，四角色菜单过滤逻辑有可追溯的验证记录，v1.4 新增菜单项纳入同一份清单
**Depends on**: Nothing (纯文档 + UAT，无代码改动；独立可插入任意空档期)
**Requirements**: NAV-04, NAV-05
**Success Criteria** (what must be TRUE):
  1. Phase 11 对应的 `SUMMARY.md`（或 v1.4 phase 下的 `VERIFICATION.md`）被补齐，内容覆盖 admin / hrbp / manager / employee 四角色的菜单可见项 UAT 清单执行记录（含截图）
  2. v1.4 新增的菜单项（「绩效管理」、员工端「调薪资格」标签页）被纳入同一份 UAT 清单，一并验证角色过滤逻辑
  3. UAT 清单每一项有明确的期望结果与实际结果对照；角色 A 不可见的菜单项在角色 A 的截图中确认看不到
  4. 本 phase 的 PR diff 严格限定为文档变更（≤ 10 文件，不含代码），不借机做任何代码修复
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 30 → 31 → 32 → 33 → 34 → 35 → 36 → 37.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Security Hardening | v1.0 | 5/5 | Complete | 2026-03-26 |
| 2. Evaluation Pipeline | v1.0 | 6/6 | Complete | 2026-03-31 |
| 3. Approval Workflow | v1.0 | 3/3 | Complete | 2026-03-31 |
| 4. Audit Log Wiring | v1.0 | 3/3 | Complete | 2026-03-31 |
| 5. Document Dedup | v1.0 | 4/4 | Complete | 2026-03-31 |
| 6. Batch Import | v1.0 | 3/3 | Complete | 2026-03-31 |
| 7. Dashboard & Cache | v1.0 | 3/3 | Complete | 2026-03-31 |
| 8. Employee Self-Service | v1.0 | 2/2 | Complete | 2026-03-31 |
| 9. Feishu Attendance | v1.0 | 3/3 | Complete | 2026-03-31 |
| 10. External API | v1.0 | 3/3 | Complete | 2026-03-31 |
| 11. Menu & Navigation | v1.1 | 1/1 | Complete | 2026-03-31 |
| 12. Account Binding | v1.1 | 2/2 | Complete | 2026-04-01 |
| 13. Eligibility Engine | v1.1 | 2/2 | Complete | 2026-04-02 |
| 14. Eligibility Visibility | v1.1 | 2/2 | Complete | 2026-04-04 |
| 15. Vision Evaluation | v1.1 | 2/2 | Complete | 2026-04-04 |
| 16. File Sharing | v1.1 | 2/2 | Complete | 2026-04-06 |
| 17. Display Simplification | v1.1 | 2/2 | Complete | 2026-04-07 |
| 18. Python 3.9 兼容 | v1.2 | 3/3 | Complete | 2026-04-08 |
| 19. Celery+Redis 基础设施 | v1.2 | 3/3 | Complete | 2026-04-09 |
| 20. 员工所属公司 | v1.2 | 2/2 | Complete | 2026-04-09 |
| 21. 共享拒绝清理 | v1.2 | 2/2 | Complete | 2026-04-09 |
| 22. 异步迁移 | v1.2 | 3/3 | Complete | 2026-04-12 |
| 23. 资格导入管理 | v1.2 | 3/3 | Complete | 2026-04-15 |
| 24. 生产部署 | v1.2 | 2/2 | Complete | 2026-04-16 |
| 25. 技术债清理 | v1.3 | 1/1 | Complete | 2026-04-16 |
| 26. 飞书 OAuth2 后端 | v1.3 | 2/2 | Complete | 2026-04-16 |
| 27. 飞书 OAuth2 前端 | v1.3 | 3/3 | Complete | 2026-04-20 |
| 27.1. 设置页飞书绑定 | v1.3 | 3/3 | Complete | 2026-04-20 |
| 28. 粒子背景 | v1.3 | 2/2 | Complete | 2026-04-20 |
| 30. 工号前导零修复 | v1.4 | 0/? | Not started | — |
| 31. 飞书同步可观测性 | v1.4 | 0/? | Not started | — |
| 32. 调薪资格导入功能补齐 | v1.4 | 0/? | Not started | — |
| 33. 绩效档次纯引擎 | v1.4 | 0/? | Not started | — |
| 34. 绩效管理服务与 API | v1.4 | 0/? | Not started | — |
| 35. 员工端自助体验 | v1.4 | 0/? | Not started | — |
| 36. 历史绩效展示 | v1.4 | 0/? | Not started | — |
| 37. Phase 11 导航验证补齐 | v1.4 | 0/? | Not started | — |
