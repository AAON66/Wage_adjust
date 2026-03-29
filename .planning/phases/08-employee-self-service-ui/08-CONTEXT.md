# Phase 8: 员工自助 UI - 上下文

**收集日期:** 2026-03-29
**状态:** 准备规划

<domain>
## 阶段边界

员工可以独立查看自己的评估进度、评估结果（含 5 个维度详情）和审批通过后的调薪建议（仅百分比），无需联系 HR。

范围内:
- 评估状态追踪（步骤条展示审批进度）(EMP-01)
- 评估结果查看（雷达图 + 维度卡片）(EMP-02)
- 调薪建议展示（仅审批通过后，仅百分比）(EMP-03)
- 空状态引导文案
- 在现有 MyReview 页面上扩展

范围外:
- 移动端适配（延后到 v2）
- 员工查看部门平均数据
- 员工查看绝对薪资数字

</domain>

<decisions>
## 实施决策

### 评估状态展示
- **D-01:** 使用**步骤条/进度条**展示审批进度。横向步骤：提交 → 主管审核 → HR 审核 → 已完成。当前阶段高亮，已完成阶段打勾。
- **D-02:** 步骤条显示在 MyReview 页面顶部，员工登录后第一眼看到评估当前所处阶段。

### 评估结果展示
- **D-03:** 使用 **ECharts 雷达图 + 维度卡片**展示 5 维度评估结果。雷达图提供整体视觉概览，下方每个维度一张卡片展示得分、权重和 LLM 维度说明。
- **D-04:** 评估结果区域仅在评估状态为 `confirmed` 或更高（已审批）时显示。草稿和提交中状态不显示结果。

### 调薪建议
- **D-05:** 调薪建议**仅在审批通过后**（status = approved）对员工可见。审核中和未审核状态完全不显示调薪相关信息。
- **D-06:** 仅显示调整幅度百分比（如 "+12%"），**不显示**绝对薪资数字、系统建议值，也不区分系统建议和最终审批值。员工只看到最终结果。

### 页面入口与导航
- **D-07:** **扩展现有 MyReview 页面**（`/my-review`），不新建独立页面。在材料上传区域之上或之下新增评估状态、评估结果、调薪建议区域。
- **D-08:** 员工登录后首页仍为 `/my-review`（已在 roleAccess.ts 中配置）。

### 空状态与引导
- **D-09:** 无评估时显示引导提示："您当前没有进行中的评估。请上传材料开始评估流程。"审核中显示："您的评估正在审核中，请耐心等待。"
- **D-10:** 各区域根据状态独立显示/隐藏，避免信息过载。

### 数据安全
- **D-11:** 员工仅能看到自己的数据。沿用已有 AccessScopeService 权限模型。不显示他人数据、部门平均或任何对比信息。

### Claude's Discretion
- 步骤条的具体样式（纯 CSS 还是小型组件）
- 雷达图的 ECharts 配色和样式
- 维度卡片的布局细节
- MyReview 页面中各区域的排列顺序

</decisions>

<canonical_refs>
## 规范引用

**下游代理在规划或实施前必须阅读以下文件。**

### 员工页面
- `frontend/src/pages/MyReview.tsx` — 现有个人评估中心页面（扩展基础）
- `frontend/src/components/evaluation/StatusIndicator.tsx` — 现有状态标签组件
- `frontend/src/components/evaluation/EvidenceCard.tsx` — 现有证据卡片
- `frontend/src/utils/roleAccess.ts` — 角色模块配置（员工首页 `/my-review`）

### 评估与调薪
- `backend/app/services/evaluation_service.py` — 评估服务（获取维度得分）
- `backend/app/services/salary_service.py` — 调薪建议服务
- `backend/app/services/access_scope_service.py` — 权限隔离

### 先前决策
- `.planning/phases/01-security-hardening-and-schema-integrity/01-CONTEXT.md` — SEC-04 角色薪资字段过滤
- `.planning/phases/02-evaluation-pipeline-integrity/02-CONTEXT.md` — EVAL-07 五维度展示
- `.planning/phases/03-approval-workflow-correctness/03-CONTEXT.md` — 审批状态流转

</canonical_refs>

<code_context>
## 现有代码洞察

### 可复用资产
- `MyReview.tsx` 已有完整的材料上传、文件管理、周期选择逻辑
- `StatusIndicator` 组件已有基础状态展示
- `EvidenceCard` 展示 AI 提取的证据
- ECharts 已安装（Phase 7），可直接用于雷达图
- `useAuth` hook 提供当前用户信息
- `findEmployeeForUser` 工具函数匹配员工记录

### 已建立模式
- 前端通过 `useEffect` + `useState` 获取数据
- API 通过 `Depends(get_current_user)` 获取当前用户
- ECharts 组件在 `components/dashboard/` 下已有成熟模式

### 集成点
- MyReview 页面已有 `submission` 状态，可扩展展示评估详情
- 评估详情 API 已存在（`/evaluations/{id}`），需确认员工权限过滤
- 调薪建议 API 已存在，需确认角色字段过滤（SEC-04）

</code_context>

<specifics>
## 具体要求

- 步骤条需要中文标签（"已提交"、"主管审核中"、"HR 审核中"、"已完成"）
- 雷达图使用 ECharts（Phase 7 已安装）
- 调薪百分比格式："+12%"（正数带加号）
- 维度卡片显示中文维度名（"AI工具掌握度"等）

</specifics>

<deferred>
## 延后事项

- **移动端响应式** — 用户明确延后到 v2
- **部门平均对比** — 员工仅看自己数据，不提供对比
- **调薪历史趋势** — 不在当前范围

</deferred>

---

*Phase: 08-employee-self-service-ui*
*Context gathered: 2026-03-29*
