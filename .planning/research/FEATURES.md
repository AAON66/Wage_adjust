# Feature Research — v1.4 员工端体验完善与导入链路稳定性

**Domain:** 企业内部调薪平台（员工自助 + 绩效导入 + 数据导入链路稳定性）
**Researched:** 2026-04-20
**Confidence:** MEDIUM-HIGH（业界主流做法可验证；具体 UI 取舍为团队决策）
**Scope:** 仅覆盖 v1.4 4 大新增模块（员工端资格可见 / 绩效分档 / 绩效历史 / 导入链路修复），不重复 v1.1–v1.3 已覆盖能力。

---

## Feature Landscape

### 类别 1：员工端「我是否有资格参与本次调薪」自助页面

业界共识（Workday / SAP SuccessFactors / 国内 HRIS）是「资格可见性」要区分三个分层：
- **planner 视角**（HR/Manager）：看得到谁合格、谁不合格、不合格字段灰显，已全量建成（v1.1）
- **employee 视角**（员工本人）：传统 HCM 默认「不显示不合格原因」，但 2026 主流 compensation transparency 趋势已转为「员工可见自身资格 + 明确缺口」—— 尤其是 EU Pay Transparency Directive 2026-06 生效后
- **visibility date** 机制（Workday）：可在周期内先对 HR 可见、周期外才对员工可见 —— 但本项目现状为「随时可见最新状态」，更偏向新世代 transparency-first 产品

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **资格状态三态可视化**（合格/不合格/待定） | 员工打开页面第一眼就要看到结论，与 HR 端 `STATUS_BADGE` 保持一致避免口径漂移 | **S** | 复用 v1.1 `EligibilityBatchItem.status` + `EligibilityStatusBadge`；纯前端渲染 |
| **未通过规则清单**（哪条不合格） | 不给「为什么」的资格结论会引发员工工单轰炸；Workday UW 公开指南也要求 manager 提供 ineligible 理由 | **S** | 复用 `EligibilityRuleResult[]`（已返回规则级 status + reason） |
| **资格规则说明**（tenure/interval/performance/leave 各是什么） | 员工不熟悉内部术语，需要「tooltip 级」说明 | **S** | 静态文案即可；放在每条规则 label 旁 |
| **周期归属**（本次是哪一轮调薪周期） | 员工首要担心「这是老数据吗」；明示周期开始/结束日期 | **S** | `cycle_id` + 周期名/结束日 |
| **刷新时间戳**（数据何时计算） | 数据口径信任度的基本保障 | **S** | 后端返回 `calculated_at` / `as_of` |
| **随时可见（不按 visibility date 闸门）** | 项目已明确「随时可见最新状态」；这是 transparency-first 的主流新范式 | **S** | 无需建 visibility_date 字段；文档化即可 |
| **绝对不可见他人数据** | 合规硬红线；PIPL + 国内公司文化敏感 | **S** | 复用 `AccessScopeService.ensure_*_access`；仅允许 `self` 查询 |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **达成进度条**（例：司龄 11/12 个月 = 92%） | 把「不合格」转为「可达成」，降低焦虑、给出明确预期 | **M** | 需要引擎暴露 `progress = actual / threshold`；仅对数值型规则（tenure/interval）适用 |
| **预计达标日期**（"你将在 2026-07-01 满足司龄要求"） | 2026 HR trends 强调「from annual event to continuous path」—— 显式 ETA 是最强抓手 | **M** | 基于 `entry_date + threshold` 反推；周期维度需注意「下个周期才能生效」 |
| **缺口精确值**（还差 X 天 / X 分） | 比百分比更直观；Workday 范式中属于 planner 专属信息，下放员工端是差异化 | **S** | 引擎同页输出即可 |
| **申诉/问询入口**（跳转给 HR 提 override 申请） | 闭环；当前 override 流程仅 HR 发起，员工端加一个「申请复核」按钮即可触发 | **M** | 复用 v1.1 override 流程；新增员工侧申请表单 |
| **资格历史**（过去 N 个周期的资格变化） | 员工能看到「我过去被判定为 X、原因是 Y」，建立长期信任 | **M** | 依赖 AuditLog + EligibilityResult 快照；建议 defer 到后续迭代 |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 显示具体排名（"你是部门第 3 名"） | 产品经理直觉「让员工知道自己在哪」 | 触发 stack-ranking 反感 + 数据泄露同级同事；2010s GE/Microsoft/Amazon 已公开放弃 | 只显示档位（1/2/3 档），不显示具体名次 |
| 显示他人资格或评级 | 「让员工互相激励」 | 严重违反数据最小化原则 + PIPL；信任崩塌 | 仅 self-scope；manager/HR 走已有 batch 入口 |
| 显示调薪系数区间（例 1.3–1.5×） | "让员工知道能涨多少" | 系统建议值 ≠ 最终审批值，提前展示会形成「被降薪了」错觉 | 资格页只讲「资格」，调薪建议走已有 SalaryDisplay 审批后开放 |
| 推送式通知「你不合格了」 | 实时告知体贴 | 负面结论主动推送 → 抵触大；员工自己打开页面查看心理负担更轻 | 状态变化时静默更新；入口放显眼，由员工主动查看 |
| 弹窗强制阅读不合格原因 | "避免员工说没看到" | 破坏 transparency 的善意；变成合规走过场 | 默认展开不合格规则卡片即可，无需强制 |

---

### 类别 2：绩效档次分档展示（20/70/10 全公司）

#### 业界对比（关键结论）

| 公司/产品 | 分档模式 | 员工可见度 | 参考 |
|-----------|---------|-----------|------|
| GE（Jack Welch 时代） | 强制 20/70/10 | 可见档位 + 可见排名倾向 | 已 2010s 后退出 |
| Microsoft（2013 后） | 停用 stack ranking | 员工不可见相对排名 | 已改为 connect-model |
| Amazon | 强制分档 | **员工不可见结果** | 作为反面典型 |
| AIG Benmosche | 10/20/50/10/10 | 档位可见 + 奖金差异化 | 2010 至今 |
| Yahoo QPR | 10/25/50/10/5 | 档位可见 | Mayer 时期 |
| SAP SuccessFactors | 按 Template 配置 | 可配置（默认不对员工暴露分档） | 参考主流 |
| 国内互联网（阿里/字节/美团） | 3.5/3.25/3.75 分档 | 档位可见，排名不显式 | 惯例 |

**结论**：业界共识是「可见档位，不可见排名」；分档本身是行业惯例且被员工接受，但「你是第几名」是禁忌。

#### 严格百分位 vs 等级映射 vs 混合模型

| 模型 | 说明 | 优点 | 缺点 | 本项目建议 |
|------|------|------|------|-----------|
| **严格百分位**（20/70/10 按分数切） | 按连续分数 rank 到 20%/70%/10% | 数学简单、可复现 | 样本量少时跳动剧烈；边界 10 人分数相同时不稳 | 适合 ≥500 人的大公司 |
| **等级映射**（A→1档，B→2档，C→3档） | 绩效结果本身已分档，做 1:1 映射 | 口径稳定；已有 `performance_grade` 字段 | 依赖上游分档分布与 20/70/10 一致 | **推荐**：与现有 PerformanceRecord 字段语义无缝 |
| **混合**（档 + 分数微调） | 按档位大类 + 分数二次切分 | 兼顾稳定与细分 | 解释成本高 | 当前阶段不必要 |

**推荐做法**：以**等级映射**为主（对齐现有绩效导入的 grade 值），20/70/10 作为健康度参考（用于看板自检分布，非硬性强切）。若某周期分布严重失衡（例如 40% 判为 1 档）触发告警，由 HR 复核。

#### 分档计算口径

| 维度 | 推荐 | 理由 |
|------|------|------|
| **比较样本** | 全公司 | 按项目要求；避免小部门「必有垫底」的结构性不公 |
| **周期锚点** | 当前调薪周期关联的绩效周期 | 与 v1.1 performance rule 对齐；用 `PerformanceRecord.cycle_id` |
| **样本量阈值** | ≥50 人才分档，否则显示「样本不足」 | 小公司/早期阶段无意义分档；避免"3 人的 10%"闹剧 |
| **空值处理** | 无绩效记录 → 显示「待录入」，不分档 | 避免「无数据 = 三档」的污名化 |

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **员工端显示 1/2/3 档**（标签而非排名） | 项目要求；行业主流 | **S** | 单字段返回：`performance_tier: 1 \| 2 \| 3 \| null` |
| **档位说明 tooltip**（"1 档 = 全公司前 20%"） | 不解释口径的档位 = 不透明黑盒 | **S** | 静态文案 |
| **样本量 + 分档来源注释** | "基于全公司 1,234 名员工、2026-Q1 绩效分档" —— 解释口径 | **S** | 返回 `sample_size` + `reference_cycle` |
| **HR 端显示绝对分档 + 分布图** | HR 需要可解释地和员工沟通 | **M** | 看板一个直方图即可；复用 Recharts |
| **不显示具体排名 / 同档其他人** | 合规 + 文化底线 | **S** | 后端只返回自身 tier |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **档位趋势**（过去 3 个周期的档位变化） | 员工判断「我在进步还是退步」的最直接信号 | **M** | 依赖历史 PerformanceRecord；和类别 3 合并实现 |
| **分档分布健康度告警**（HR 端） | 若某周期 1 档占 50%、3 档占 30%，自动高亮 | **M** | SQL 聚合 + 阈值；看板新 tile |
| **同岗位族对照**（可选） | "你在研发职系处于 1 档" | **L** | 切分维度复杂；defer |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 显示同档其他人数 / 名单 | "让员工知道自己不孤单" | 信息泄露；触发内部比较 | 不显示 |
| 显示精确百分位（「前 23%」） | 感觉比档更精细 | 实质就是排名；Amazon/Microsoft 放弃的原因之一 | 坚持三档即可 |
| 强切 20/70/10（即使实际分布是 30/60/10 也强制挪人） | 数学「完美」 | 会把分数相同的人硬分到不同档；引发投诉 | 按等级映射 + 分布告警 |
| 频繁跳档（单次迟到就从 1 档掉 3 档） | 敏感反应 | 档位应稳定；跳动频繁会失去指导意义 | 档位依赖绩效等级；绩效等级本身已平滑 |
| 在员工端暴露「你离 1 档还差 X 分」 | 努力可达性 | 绩效分与调薪不同，绩效分透明化是独立议题；本期不做 | 仅显示档位 + 趋势，不显示分数 |

---

### 类别 3：绩效历史展示（评估详情 / 调薪建议内）

行业主流 HCM（GoCo、ChartHop、Lattice、PerformYard）都提供 **Employee Timeline**：按时间顺序汇聚 review、职级、薪资、档位变化。本项目只需该 pattern 的最小子集。

#### UI 形态选择

| 形态 | 适用场景 | 本期建议 |
|------|---------|---------|
| **表格**（周期 × 列） | 信息密度高、可排序 | **推荐**：评估详情 / 调薪建议侧边栏的紧凑场景 |
| **时间线竖排**（节点 + 标签） | 叙事性、直观「路径」 | 员工端「我的绩效」独立页（可选，defer） |
| **折线图**（分数趋势） | 分数连续时效果好 | 本项目是离散等级，折线意义不大；**不推荐** |
| **对比图**（vs 部门均值） | 需要同行参照 | 违反「不显示他人」原则；**不用** |

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **评估详情 / 调薪建议页内展示历史绩效表** | 项目明确要求；AI 评估 + 绩效需要合并叙事 | **M** | 新组件 `PerformanceHistoryPanel`；按 `employee_id` 拉 `PerformanceRecord` 列表 |
| **最小显示单元**：周期 / 等级 / 绩效分 / 评语 | 四个字段缺一不可 | **S** | 已有 `PerformanceRecord` 模型；确认字段齐备 |
| **按时间倒序**（最新在上） | 惯例；最新信息最相关 | **S** | `order by cycle_start_date desc` |
| **空状态处理**（无历史时显示「暂无绩效记录」） | 避免空白区域 | **S** | 纯前端 |
| **与调薪周期关联显示** | 哪个周期的绩效驱动了哪次调薪，一眼可见 | **S** | 在行里 `cycle` 列加 badge；调薪周期可高亮 |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **与 AI 评估结果并排展示** | "绩效等级 3 档 × AI 等级 L4" 是调薪建议的两条腿；合并视图让审批更高效 | **M** | 调薪建议页已有 AI 评估面板；左右并列即可 |
| **评语展开/折叠** | 评语可能很长；默认折叠避免页面撑爆 | **S** | `<details>` 或自定义展开 |
| **导入来源标识**（Excel/飞书/手动） | 审计价值；出问题能快速定位源头 | **S** | 每条记录带 `source` 字段；UI 一个小 badge |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 显示具体分数给员工 | 对齐 HR 视角 | 绩效分口径与调薪不同；分数暴露会引发「为什么我 82 分却 2 档」的质疑 | 员工端仅显示等级 + 档位，分数留 HR |
| 时间线动画 / 幻灯片切换 | 炫技 | 低价值、增加复杂度 | 静态表格 |
| 同部门历史对比图 | "看到团队如何变化" | 违反最小数据 + 同类别 2 的 anti-feature | 不做 |

---

### 类别 4：统一导入管理（HR 视角）

#### 覆盖策略主流对比

| 策略 | 说明 | 适用 | 本期建议 |
|------|------|------|---------|
| **Upsert（按业务键更新）** | 存在则按字段更新，不存在则插入 | HR 数据最主流；数据 90% 重叠 | **推荐**：默认策略，按 `(employee_no, cycle_id)` 业务键 |
| **Replace / Overwrite** | 整表清空重写 | 数据全量快照、结构变化大 | 不合适；HR 数据分权部分更新，全量清空风险过高 |
| **Append-only / 增量** | 只追加不覆盖 | 审计记录、事件流 | 不合适；同周期重复导入会产生脏数据 |
| **手动选择** | 用户勾选每行 insert/update/skip | 极高敏感度场景 | 当前不必要；preview 足够 |

**项目结论**：采用 **staged upsert with preview**：
1. 上传 → 落入 staging（内存或临时表）
2. 对 `(employee_no, cycle_id)` 匹配，分类为 `新增 / 更新 / 无变化 / 字段冲突`
3. 展示 diff 预览（Insert 几行、Update 几行且具体 diff）
4. 用户确认后在事务中执行
5. 写审计日志；保留 import_batch_id 以支持回滚

#### 空值语义（关键踩坑）

| 场景 | 常见歧义 | 行业推荐 |
|------|---------|---------|
| Excel 单元格空着 | "不修改" vs "清空" | **默认「不修改」**；若要「清空」需显式输入特殊值（如 `__CLEAR__`）或在预览页勾选 |
| 整列缺失 | "整列都不动" vs "整列都清空" | **「整列不动」**；严禁默认清空 |
| 字符串 `"null"` / `"-"` / `""` | 用户表达意图不一 | 明示文档；只认空字符串为 noop |

#### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Preview 预览界面**（Insert / Update / No-change 分类） | 标准 HR 导入工作流；Salesforce/MDM 工业标准 | **M-L** | 新建 preview endpoint；前端列表带 diff 渲染 |
| **Update 行字段级 diff**（旧值 → 新值） | HR 必须能审计"改了什么" | **M** | 后端返回 `field: {old, new}` 字典 |
| **失败行内行展示错误**（第几行哪列为什么失败） | 已在 v1.0 建立；v1.4 对绩效/资格统一该模式 | **S** | 复用现有 per-row error reporting |
| **按业务键 upsert**（`(employee_no, cycle_id)` 覆盖更新） | 项目明确要求；防止重复导入产生重复行 | **M** | 增 unique constraint + ON CONFLICT UPDATE |
| **确认步骤**（预览后显式点「执行导入」） | 不可逆操作必须二次确认 | **S** | 前端 modal |
| **空值 = 不修改**（明示文档 + UI 提示） | 行业默认；避免静默清空 | **S** | 后端 skip None；前端 template 说明 |
| **Excel 模板下载返回真实 .xlsx 文件**（v1.4 明确 bug） | 基本可用性 | **S** | 修复返回 `FileResponse` / 正确 `Content-Type` |
| **导入批次唯一 ID + 审计** | 任何改动可追溯到批次 + 操作者 + 时间 | **S** | 复用 AuditLog；batch_id 作为关联键 |
| **工号保留前导零（import 全链路）** | 项目明确要求；Excel/飞书/手动三链路一致 | **M** | pandas `dtype={'employee_no': str}`；飞书响应字段 cast；前端 input trim 但不 parseInt；存量数据迁移 |

#### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **回滚按钮**（按 import_batch_id 撤销） | 误操作兜底；Databricks/staging-swap 工业范式 | **L** | 需要保留 pre-image snapshot；本期可选 defer |
| **预览阶段可编辑**（行级修正后再提交） | 减少「下载-改 Excel-重上传」循环 | **L** | 复杂度高；defer |
| **飞书同步状态透明化**（每一步节点显示 OK / 失败原因） | v1.4 明确要求修复静默失败根因 | **M** | 现有 FeishuSyncPanel 已有 useTaskPolling；增强错误分级展示 |
| **飞书同步按表路由**（多维表格每张表状态独立） | 项目已引入飞书多表；每表独立状态更易定位 | **M** | 已存在于 v1.2 Phase 23；v1.4 只需修复同步成功但未落库 |
| **Excel 导入与飞书同步状态并轨**（同一导入历史时间线） | HR 心智统一：无论来源，都是一次导入 | **M** | 统一 ImportBatch 模型 |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| 静默覆盖（无 preview 直接执行） | "快捷" | HR 数据不可误覆盖；标准做法必须 preview | 预览→确认两步 |
| 空单元格 = 清空字段（默认行为） | "让 Excel 成为唯一数据源" | 歧义重、不可逆；Workday/SAP 均默认 preserve | 空 = noop；显式 `__CLEAR__` 才清空 |
| 失败就整批回滚 | "原子性" | 99 行对、1 行错就全败 → 导入不可用 | 部分成功 + 详细失败报告（项目已实现，v1.4 保持） |
| 自动去除前导零（认为是"格式问题"） | "数据清洁" | 工号是字符串 key，改数值会破坏联表；已是项目明确 bug | 全链路强制 string |
| 飞书同步无进度显示 | "后台自动就行" | 失败时用户不知何时失败 / 是否已落库 | 现已有 `useTaskPolling`；v1.4 补足失败原因分级 |
| 模板"动态生成"（随配置变化） | "灵活" | 下载模板 ≠ 真实 xlsx 文件（v1.4 明确 bug） | 静态模板文件或确定性生成；返回真实二进制 |

---

## Feature Dependencies

```
[员工端资格可见页]
    ├──requires──> [EligibilityEngine 输出 progress/gap]（已有 v1.1 基础，需扩展）
    ├──requires──> [AccessScopeService.ensure_self_scope]（v1.1 已有）
    └──enhances──> [申诉/override 员工侧入口]（复用 v1.1 override 流程）

[员工端绩效档位 1/2/3]
    ├──requires──> [PerformanceRecord 全量准确导入]（依赖 类别 4 修复）
    ├──requires──> [全公司档位计算服务 TierService]（v1.4 新增）
    └──requires──> [performance_grade → tier 映射规则]（配置化）

[评估详情 / 调薪建议内绩效历史]
    ├──requires──> [PerformanceRecord 历史全量]（依赖 类别 4 修复）
    └──enhances──> [AI 评估结果联合展示]（复用现有详情页）

[调薪资格/绩效导入修复]
    ├──requires──> [工号前导零保留]（全链路字符串）
    ├──requires──> [业务键 upsert]（unique constraint + 迁移）
    ├──requires──> [Excel 模板下载修复]（返回真实文件）
    ├──requires──> [飞书同步静默失败根因修复]
    └──enhances──> [Preview + diff UI]（差异化能力，可 P2）

[Phase 11 导航菜单验证补齐]
    ├──requires──> [SUMMARY.md 补齐]
    └──requires──> [UAT 清单执行]
```

### Dependency Notes

- **绩效档位展示 requires 绩效导入修复**：档位计算依赖准确、全量的 `PerformanceRecord`；必须先解决「飞书同步成功但未落库」
- **员工端资格页 requires Engine 扩展**：现有 `EligibilityRuleResult` 只有 pass/fail，需扩展 `progress` / `gap` / `eta_date`
- **工号前导零修复 是所有类别的前置**：员工端自助页靠工号定位，不修复则 all 员工查不到资格 / 绩效
- **Preview+diff UI enhances 业务键 upsert**：没有 preview，upsert 的风险面扩大（误覆盖无法发现）；但 preview 非必需前置
- **申诉入口 enhances 资格页**：资格页先上，申诉入口作为 P2 增量

---

## MVP Definition

### Launch With (v1.4 MVP — 必须)

员工端价值闭环 + 导入稳定性修复：

- [ ] **类别 1 Table Stakes 全部**：资格状态、未通过规则、规则说明、刷新时间戳、self-only 访问、随时可见
- [ ] **类别 2 Table Stakes 全部**：员工显示 1/2/3 档、tooltip 说明、样本量注释、HR 端分布图、不显示排名
- [ ] **类别 3 Table Stakes 全部**：评估详情/调薪建议历史绩效表、倒序、空状态、与周期关联
- [ ] **类别 4 Table Stakes 全部**：Preview + diff、Update 字段级 diff、按业务键 upsert、空值 = 不修改、Excel 模板修复、工号前导零修复、飞书同步静默失败修复、审计
- [ ] **Phase 11 补齐**：SUMMARY.md + UAT 清单

### Add After Validation (v1.x 后续)

员工端生效后的增量改进：

- [ ] **类别 1**：达成进度条、预计达标日期、申诉入口
- [ ] **类别 2**：档位趋势图、分布健康度告警
- [ ] **类别 3**：导入来源 badge、AI+绩效并排展示优化
- [ ] **类别 4**：回滚按钮、预览阶段可编辑

### Future Consideration (v2+)

- [ ] 资格历史快照（需要 EligibilityResult 历史表）
- [ ] 同岗位族分档对照
- [ ] 实时变更推送（依赖 WebSocket 基础设施，已 defer）
- [ ] E2E 集成测试套件（整体 defer）

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 工号前导零全链路修复 | HIGH（阻塞性 bug，所有员工查不到数据） | M | **P1** |
| 调薪资格导入飞书同步根因修复 | HIGH（阻塞性 bug） | M | **P1** |
| Excel 模板下载修复 | HIGH（阻塞性 bug） | S | **P1** |
| 按业务键 upsert（重复导入覆盖） | HIGH（现有数据污染） | M | **P1** |
| 员工端资格状态 + 不合格规则 | HIGH（项目核心价值） | S | **P1** |
| 员工端绩效 1/2/3 档显示 | HIGH（项目明确目标） | M | **P1** |
| 评估详情/调薪建议历史绩效表 | HIGH（审批闭环） | M | **P1** |
| 导入 Preview + diff | HIGH（HR 数据安全） | M-L | **P1** |
| 规则说明 tooltip + 样本量 + 刷新时间 | MEDIUM（透明度） | S | **P1** |
| Phase 11 导航补齐 | MEDIUM（规划债） | S | **P1** |
| 达成进度条 + ETA | MEDIUM（体验加分） | M | P2 |
| 档位趋势（历史档位） | MEDIUM | M | P2 |
| 分布健康度告警 | MEDIUM | M | P2 |
| 申诉/复核入口 | MEDIUM | M | P2 |
| 导入回滚按钮 | LOW（preview 已大幅降低风险） | L | P3 |
| 预览阶段可编辑 | LOW | L | P3 |
| 资格历史快照 | LOW | L | P3 |

**Priority key:**
- P1：v1.4 必须有（Launch With MVP）
- P2：v1.4 建议有（Add After Validation）
- P3：v1.4 之外

---

## Competitor Feature Analysis

| Feature | Workday | SAP SuccessFactors | 国内 HRIS（泛集） | Our v1.4 |
|---------|---------|--------------------|-----------------| --------|
| 员工端资格可见 | 闸门式（visibility date） | 默认不可见 | 多数不做 | 随时可见 + 不合格原因（differentiator） |
| 不合格原因 | manager 手动备注 | 无 | 无 | 规则级自动返回（复用 v1.1） |
| 分档显示 | 可配置 | 可配置 | 1/2/3/A/B/C 常见 | 1/2/3 档，全公司对比，不显示排名 |
| 绩效历史 | Employee Timeline | 组件化嵌入 | 多数有 | 表格形态内嵌评估详情 |
| Preview 导入 | 有 | 有 | 分叉：有/无都存在 | 有（MVP 必须） |
| 字段级 diff | 有 | 有 | 少数有 | 有（MVP 必须） |
| 回滚按钮 | 有 | 部分 | 少数有 | P3（defer） |
| 空值语义 | 默认 noop | 默认 noop | 各家不一 | 默认 noop（文档化） |
| 工号前导零 | 字符串默认 | 字符串默认 | 国内 Excel 高频踩坑 | 修复全链路 + 存量迁移 |

---

## Sensitive Items（需团队共识的项）

以下项涉及 HR 合规 / 员工感受，需在实现前与业务方复核：

1. **「随时可见资格状态」vs「周期内才可见」**：本项目明确选择前者（transparency-first），但需确认 HR 是否要求在某些敏感时点（如大规模降薪前）临时关闭
2. **「不合格原因」的措辞**：项目已采用「未通过规则」中性表达；避免「不达标」「未达及格线」等评判性用语
3. **「样本量不足时」的 fallback**：档位不展示时，员工端文案要避免歧义（"样本不足，暂不展示档位"而非"你没有档位"）
4. **存量工号前导零数据修复的时点**：建议在 v1.4 上线时一次性迁移，避免新老数据混用期

---

## Sources

- [Vitality Curve (Wikipedia)](https://en.wikipedia.org/wiki/Vitality_curve) — HIGH — 20/70/10 模型溯源与 GE/Microsoft/AIG/Yahoo/Amazon 案例
- [Stack Ranking: Pros, Cons & Alternatives (AIHR)](https://www.aihr.com/hr-glossary/stack-ranking/) — MEDIUM — 行业采用率 42% → 14% 的变化
- [Stack Ranking to Evaluate Performance (HR Cloud)](https://www.hrcloud.com/blog/stack-ranking-your-employees-good-practice-or-risky-behavior/) — MEDIUM — 员工可见性问题讨论
- [E-HR Self-Service Portal 2026 Guide (Valuebound)](https://www.valuebound.com/resources/blog/e-hr-self-service-portal-2026-complete-guide) — MEDIUM — 2026 transparency-first 趋势
- [2026 HR Compliance Checklist (BBSI)](https://www.bbsi.com/business-owner-resources/2026-hr-compliance-checklist?hs_amp=true) — MEDIUM — EU Pay Transparency Directive 2026-06 生效
- [HR Executive — HR Priorities 2026](https://hrexecutive.com/9-ways-to-maximize-hr-impact-in-2026/) — MEDIUM — 从年度评审 → 持续反馈
- [Workday Merit Process (Surety Systems)](https://www.suretysystems.com/insights/aligning-rewards-and-performance-with-the-workday-merit-process/) — MEDIUM — Workday merit eligibility 机制
- [Workday Compensation Review Dates (Commit Consulting)](https://commitconsulting.com/blog/workday-advanced-compensation-dates) — MEDIUM — Workday visibility date 闸门
- [FY26 Merit Process Guide (UW)](https://hr.uw.edu/comp/fy26merit/) — MEDIUM — 不合格原因 manager 备注范式
- [SAP SuccessFactors Eligibility Rules](https://userapps.support.sap.com/sap/support/knowledge/en/2084628) — MEDIUM — eligibility engine 三层粒度（plan/component/field）
- [Upsert vs Replace with Staging Table (Medium)](https://medium.com/@tzhaonj/data-engineering-upsert-vs-replace-and-how-a-staging-table-can-help-you-find-the-perfect-middle-ea6db324b9ef) — MEDIUM — staging + preview 工业范式
- [Rollback Strategy Planning (Ispirer)](https://www.ispirer.com/blog/how-to-plan-rollback-strategy) — MEDIUM — 回滚最佳实践
- [Read Excel with Leading Zeros (python.org discuss)](https://discuss.python.org/t/when-reading-spreadsheet-how-to-keep-leading-zeros/61389) — HIGH — pandas `dtype={'col': str}` 标准做法
- [openpyxl Styles Documentation](https://openpyxl.readthedocs.io/en/3.1/styles.html) — HIGH — number_format 写入端保留前导零
- [pandas Issue #46895](https://github.com/pandas-dev/pandas/issues/46895) — HIGH — read_excel vs read_csv 在前导零处理上的差异
- [GoCo Performance Management](https://www.goco.io/hris-platform/performance-management) — MEDIUM — Employee Timeline 参考
- [ChartHop HRIS](https://www.charthop.com/modules/hris) — MEDIUM — 历史时间线参考
- [PerformYard Performance Tools](https://www.performyard.com/articles/performance-management-tools) — MEDIUM — 绩效分析 UI 模式
- [Feishu Sync Data Between Bases](https://www.feishu.cn/hc/en-US/articles/128401098783-sync-data-between-bases) — MEDIUM — 飞书多维表格同步官方能力

---
*Feature research for: v1.4 员工端体验完善与导入链路稳定性*
*Researched: 2026-04-20*
