# Phase 36: 历史绩效展示 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 36-historical-performance-display
**Areas discussed:** 数据模型补齐策略 / Manager 访问入口设计 / 挂载位置与复用边界 / 员工 MyReview 是否同款展示

---

## 灰区多选

| 选项 | 描述 | Selected |
|------|------|----------|
| 数据模型补齐策略 | 评语/cycle_start_date 字段缺失如何落地（加字段 + migration 还是降级 SC 三列） | ✓ |
| Manager 访问入口设计 | 新增 by-employee 端点 + AccessScopeService 还是扩展现有 /records | ✓ |
| 挂载位置与复用边界 | SalaryDetail 同页 panel 共用还是独立页面 | ✓ |
| 员工 MyReview 是否同款展示 | 严守 SC 还是扩展到员工自助端 | ✓ |

**User's choice:** 全部 4 个灰区都讨论

---

## 数据模型补齐策略

### 「周期」列粒度

| 选项 | 描述 | Selected |
|------|------|----------|
| 保持 year 粒度、不加新字段 (Recommended) | 直接用 year: int 展示「2026 年度」；cycle_start_date 解读为「按 year 倒序」；零 migration 成本 | ✓ |
| 新加 cycle_start_date: date、支持多粒度 | Alembic 新增 nullable 字段；未来可存半年度/季度；影响 import pipeline + 飞书 mapping | |
| 新加 cycle_name: str (文本显示) + 保持 year 排序 | 加 cycle_name（如「2026H1」）供 UI 显示；排序仍 year DESC | |

**User's choice:** 保持 year 粒度
**Notes:** 避免 schema 膨胀，SC 的 cycle_start_date 解读为 year 倒序

### 「评语」列处理

| 选项 | 描述 | Selected |
|------|------|----------|
| 新增 comment: str \| None 字段（加 migration）(Recommended) | 严格按 SC#1 四列；TEXT 可空；存量行 NULL→UI「—」 | ✓ |
| 降级 SC、不显示评语列（3 列：年度/等级/部门快照） | 不改动模型；SC 文字调整；Deferred 里写「评语列推到 v1.5+」 | |
| 加 comment 字段但仅 manual/excel 来源支持填写 | 飞书同步不带评语（无对应字段）；manual/excel 支持手动填写 | |

**User's choice:** 新增 comment 字段 + migration
**Notes:** 最后决策拼接了第三项语义 — 飞书源 comment 恒为 None，manual/excel 支持（见 D-03）

### 存量行新字段处理

| 选项 | 描述 | Selected |
|------|------|----------|
| 不回填、保留 NULL (Recommended) | 跟 Phase 34 D-07 同款逻辑：快照字段任何回填都是假数据；UI NULL→「—」 | ✓ |
| 为存量行回填 cycle_start_date=YEAR-01-01 | 给老数据后备日期；仅 date 字段方案时相关 | |

**User's choice:** 不回填、保留 NULL

---

## Manager 访问入口设计

### API 路由

| 选项 | 描述 | Selected |
|------|------|----------|
| 新增 GET /performance/records/by-employee/{employee_id} (Recommended) | 专用端点 + require_roles 三元组 + AccessScopeService；与 evaluation/salary 历史 pattern 一致 | ✓ |
| 扩展现有 /performance/records 加 employee_id filter | 复用现有端点；缺点：体积箱 endpoint + 分支逻辑易出 bug | |
| 维持 admin/hrbp、manager 不开通（降 SC） | 快，但跟 ROADMAP 文字不一致 | |

**User's choice:** 新增 by-employee 专用端点

### 返回 shape 分页

| 选项 | 描述 | Selected |
|------|------|----------|
| 不分页、全部返回 (Recommended) | 单员工历史最多 10-20 行，分页浪费；直接 items: PerformanceRecordItem[] | ✓ |
| 复用现有分页 shape | 一致性好，但数据量小不必 | |

**User's choice:** 不分页

### 跨权限拦截

| 选项 | 描述 | Selected |
|------|------|----------|
| 复用 AccessScopeService.ensure_employee_access (Recommended) | 跟 evaluation/salary 一致；Service 抛 PermissionError，API 转 403 | ✓ |
| 在 PerformanceService 另写一套作用域判断 | 重复逻辑无收益 | |

**User's choice:** 复用 AccessScopeService

---

## 挂载位置与复用边界

### 挂载策略

| 选项 | 描述 | Selected |
|------|------|----------|
| 在 EvaluationDetail.tsx 底部挂一次（同页共用）(Recommended) | SalaryDetailPanel 本来就在同页；挂一次，评估/调薪两语境共享；零重复 | ✓ |
| EvaluationDetail + Approvals 各挂一次 | Approvals 现为列表页，要开 drawer；超 SC | |
| 推 SalaryDetail 独立成新页面再挂 | 2304 行 EvaluationDetail 重构风险大 | |

**User's choice:** 挂一次、同页共用

### 组件文件位置

| 选项 | 描述 | Selected |
|------|------|----------|
| frontend/src/components/performance/PerformanceHistoryPanel.tsx (Recommended) | 跟 Phase 34 新增的 TierChip/TierDistributionPanel 同目录，领域聚焦 | ✓ |
| 放在 components/salary/ 跟 SalaryHistoryPanel 为邻 | 与「绩效数据」语义不匹配 | |

**User's choice:** components/performance/

### 数据拉取时机

| 选项 | 描述 | Selected |
|------|------|----------|
| 在 EvaluationDetail 初始化时并行拉取 (Recommended) | 跟 SalaryHistoryPanel 一致的 Promise.all pattern；统一 loading 状态 | ✓ |
| 懒加载：滚动到 panel 时才拉 | 节省带宽但复杂；数据量小不值 | |
| 点击展开时拉 | 默认折叠、用户点击才拉；增加操作步骤 | |

**User's choice:** 初始化并行拉取

---

## 员工 MyReview 是否同款展示

| 选项 | 描述 | Selected |
|------|------|----------|
| 严守 SC、不对员工暴露历史绩效表 (Recommended) | Phase 35 员工自助只显示「本人本期档次」徽章；不展示跨年度历史；v1.5+ 再议 | ✓ |
| 员工也在 MyReview 追加本人历史绩效面板 | 复用 panel，加无参路由 /performance/me/history；UX 更好但 scope creep | |

**User's choice:** 严守 SC、员工端不暴露
**Notes:** 保护绩效数据敏感性 + v1.5+ 再议

---

## Claude's Discretion

- PerformanceHistoryPanel 与 SalaryHistoryPanel 视觉垂直顺序
- 4 列表头的具体 utility class 选择
- 空态卡样式的微调
- 是否加「本期」badge 标注当前评估年度
- comment 列长文本截断策略
- Service 方法实现细节
- Pydantic schema 命名

## Deferred Ideas

- 员工端历史绩效展示（v1.5+）
- /performance/me/history 无参路由（v1.5+）
- 多年趋势 line chart（v1.5+ dashboard）
- 半年度/季度粒度 cycle_start_date（新 phase）
- 飞书同步 comment 字段映射（飞书加字段后）
- Approvals 内联 drawer
- 独立 SalaryDetail 页面
- 存量 comment 回填脚本
- 行点击跳子页
