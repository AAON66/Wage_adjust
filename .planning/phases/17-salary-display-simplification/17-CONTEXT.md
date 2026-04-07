# Phase 17: Salary Display Simplification - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

调薪建议页面默认展示关键摘要，详细数据通过展开查看，调薪资格以徽章形式直观展示。重构 EvaluationDetail.tsx 的 salary module 渲染逻辑，将当前全量展示改为摘要+折叠详情结构。

</domain>

<decisions>
## Implementation Decisions

### 摘要层内容
- **D-01:** 摘要层默认展示三个指标卡片：考勤概况（复用现有 AttendanceKpiCard）、调薪资格徽章、AI 综合评分/等级
- **D-02:** 摘要层还展示"最终调薪比例"作为核心数字（大字号突出）
- **D-03:** 其余数据（建议涨幅、AI 系数、认证加成、联动预览、建议说明、维度明细）全部折叠到详情层
- **D-04:** AttendanceKpiCard 直接复用现有组件，不做精简改动

### 展开/折叠交互
- **D-05:** 使用单个"展开详情"按钮，点击后展开全部详细数据（维度明细、评分解释、调薪计算过程、联动预览等）
- **D-06:** 展开后按钮变为"收起"，收起后回到摘要层
- **D-07:** 展开/收起使用 React state 控制，不用原生 `<details>` 标签

### 资格徽章设计
- **D-08:** 调薪资格以彩色状态徽章展示——合格=绿色、不合格=红色、数据缺失=黄色
- **D-09:** 复用现有 `status-pill` CSS 类样式，保持与项目其他徽章一致
- **D-10:** 点击徽章后在徽章下方内联展开 4 条规则逐条判定结果（每条显示通过/未通过状态）
- **D-11:** 规则展开采用内联方式，不弹窗不跳转，与现有 `<details>` 风格一致

### 人工调整与审批按钮
- **D-12:** "人工调整"和"提交审批"按钮始终可见在摘要层底部，不跟随详情展开
- **D-13:** 点击"人工调整"展开调整窗口（复用现有 isSalaryEditorOpen 状态逻辑）
- **D-14:** 核心操作入口不被折叠详情埋没，HR/主管随时可触达

### 历史走势图处理
- **D-15:** SalaryHistoryPanel（含走势 SVG 图和历史明细卡片）移入详情层内部
- **D-16:** 摘要层不显示历史走势图，减少视觉负担

### 空状态处理
- **D-17:** 当评估尚未生成调薪建议时，摘要层显示精简提示文字（"还未生成调薪建议"）+ "生成调薪建议"按钮
- **D-18:** 资格徽章和 AI 评分如果已有数据仍可展示，调薪相关区域显示空状态

### 维度明细展示格式
- **D-19:** 详情层中 5 个维度得分采用简单表格格式——一行一维度，显示维度名、得分、权重、加权分
- **D-20:** 复用 review module 中已有的类似表格风格，保持一致性

### Claude's Discretion
- 展开/收起动画效果（有无、时长）
- 摘要层卡片的具体间距和排列方式
- 详情层内部各区块的具体排列顺序
- 资格徽章尚无数据时的占位展示方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 调薪建议当前实现
- `frontend/src/pages/EvaluationDetail.tsx` — salary module 渲染逻辑（约 line 2060-2268），当前全量展示结构
- `frontend/src/components/evaluation/SalaryResultCard.tsx` — 已有简化调薪卡片组件（仅显示调薪比例），可参考
- `frontend/src/components/salary/SalaryHistoryPanel.tsx` — 历史走势 SVG 图 + 明细卡片，需移入详情层
- `frontend/src/components/salary/BudgetSimulationPanel.tsx` — 预算模拟面板（参考组件模式）

### 资格引擎（Phase 13/14 产出）
- `backend/app/engines/eligibility_engine.py` — EligibilityEngine, RuleResult, EligibilityResult 数据结构
- `backend/app/services/eligibility_service.py` — EligibilityService.check_employee() 方法签名
- `backend/app/api/v1/eligibility.py` — 资格 API 端点
- `backend/app/schemas/eligibility.py` — 资格 Pydantic schemas

### 考勤组件
- `frontend/src/components/attendance/AttendanceKpiCard.tsx` — 考勤概况卡片，摘要层直接复用

### 需求文档
- `.planning/REQUIREMENTS.md` — DISP-01, DISP-02, DISP-03 需求定义

### 前序 Context
- `.planning/phases/14-eligibility-visibility-overrides/14-CONTEXT.md` — 资格数据可见性决策（D-07: 后端+前端双重保障）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AttendanceKpiCard`: 考勤概况组件，直接复用不改动
- `SalaryResultCard`: 已有简化调薪比例展示组件（仅显示调薪比例），可参考其精简思路
- `SalaryHistoryPanel`: 完整历史走势组件，整体移入详情层
- `status-pill` CSS 类: 项目内通用徽章样式，资格徽章可直接复用
- `isSalaryEditorOpen` state: 已有人工调整窗口展开/收起逻辑
- `DIMENSION_LABELS` / `formatDimensionLabel()`: 已有维度标签映射

### Established Patterns
- EvaluationDetail 使用 `MODULE_KEYS` + `activeModule` state 切换模块
- salary module 通过 `renderSalaryModule()` IIFE 渲染
- 条件渲染使用 `? ... : null` 三元表达式
- 卡片使用 `surface` / `surface-subtle` CSS 类 + grid 布局
- 现有 `<details>` 标签用于建议说明展开

### Integration Points
- 需要新增调用 EligibilityService API 获取资格数据到 EvaluationDetail 页面
- 资格 API 需要权限检查（employee 角色不可访问，Phase 14 D-07）
- salary module 渲染函数需要重构为摘要层 + 详情层两部分

</code_context>

<specifics>
## Specific Ideas

- 摘要层布局参考 preview mockup: 三指标卡片横排 + 核心调薪比例大字号 + 底部操作按钮
- 资格徽章展开后的 4 条规则列表，每条用 checkmark/cross 图标标记状态
- "展开详情"按钮应该视觉上明显但不抢占操作按钮的注意力

</specifics>

<deferred>
## Deferred Ideas

None — 讨论保持在阶段范围内

</deferred>

---

*Phase: 17-salary-display-simplification*
*Context gathered: 2026-04-07*
