# Phase 8: 员工自助 UI - 研究报告

**研究日期:** 2026-03-28
**领域:** React 前端 UI 扩展 + 后端数据聚合
**置信度:** HIGH

## 概要

本阶段的核心目标是在现有 MyReview 页面上扩展三个功能区域：评估进度步骤条、五维度评估结果（ECharts 雷达图 + 维度卡片）、调薪百分比展示。所有必要的后端 API 已存在且支持员工角色访问，前端 ECharts 库已安装（Phase 7），UI 设计合约（08-UI-SPEC.md）已详细定义了组件结构、配色、布局和文案。

主要技术挑战在于：(1) 步骤条的状态映射需要从多个 API 聚合数据（submission、evaluation、approval records）；(2) 调薪建议的条件渲染需严格遵循 SEC-04 角色字段过滤和审批状态判断；(3) MyReview 页面当前已较长，需要在不影响现有功能的前提下插入新区域。

**核心建议:** 在 MyReview 页面中按 UI-SPEC 定义的顺序插入新组件，数据通过已有 API（`fetchEvaluationBySubmission`、`fetchSalaryRecommendationByEvaluation`、`fetchApprovalHistory`）获取，无需新建后端端点。

---

<user_constraints>
## 用户约束（来自 CONTEXT.md）

### 锁定决策
- **D-01:** 使用步骤条/进度条展示审批进度。横向步骤：提交 -> 主管审核 -> HR 审核 -> 已完成。当前阶段高亮，已完成阶段打勾。
- **D-02:** 步骤条显示在 MyReview 页面顶部，员工登录后第一眼看到评估当前所处阶段。
- **D-03:** 使用 ECharts 雷达图 + 维度卡片展示 5 维度评估结果。雷达图提供整体视觉概览，下方每个维度一张卡片展示得分、权重和 LLM 维度说明。
- **D-04:** 评估结果区域仅在评估状态为 `confirmed` 或更高（已审批）时显示。草稿和提交中状态不显示结果。
- **D-05:** 调薪建议仅在审批通过后（status = approved）对员工可见。审核中和未审核状态完全不显示调薪相关信息。
- **D-06:** 仅显示调整幅度百分比（如 "+12%"），不显示绝对薪资数字、系统建议值，也不区分系统建议和最终审批值。
- **D-07:** 扩展现有 MyReview 页面（`/my-review`），不新建独立页面。
- **D-08:** 员工登录后首页仍为 `/my-review`。
- **D-09:** 无评估时显示引导提示；审核中显示等待提示。
- **D-10:** 各区域根据状态独立显示/隐藏。
- **D-11:** 员工仅能看到自己的数据。沿用已有 AccessScopeService 权限模型。

### Claude 自由裁量
- 步骤条的具体样式（纯 CSS 还是小型组件）
- 雷达图的 ECharts 配色和样式
- 维度卡片的布局细节
- MyReview 页面中各区域的排列顺序

### 延后事项（不在范围内）
- 移动端响应式 — 用户明确延后到 v2
- 部门平均对比 — 员工仅看自己数据，不提供对比
- 调薪历史趋势 — 不在当前范围
</user_constraints>

---

<phase_requirements>
## 阶段需求

| ID | 描述 | 研究支持 |
|----|------|---------|
| EMP-01 | 员工可查看自己的评估状态及当前所处审批流程阶段 | 步骤条组件 EvaluationStepBar，数据来源于 submission.status + approval records 的 step_order/decision；后端 API `/approvals/recommendations/{id}/history` 已存在 |
| EMP-02 | 评估完成后，员工可查看自己的评估结果（含 5 个维度分项） | DimensionRadarChart + DimensionCard 组件，数据来源于 `fetchEvaluationBySubmission` 返回的 dimension_scores 数组 |
| EMP-03 | 审批通过后，员工可查看自己的调薪建议（仅显示调整幅度百分比） | SalaryResultCard 组件，数据来源于 `fetchSalaryRecommendationByEvaluation` 返回的 SalaryRecommendationEmployeeRead（仅含 final_adjustment_ratio） |
</phase_requirements>

---

## 技术栈

### 核心
| 库 | 版本 | 用途 | 为何标准 |
|-----|------|------|---------|
| React | 18.3.1 | UI 框架 | 项目已有 |
| echarts | 6.0.0 | 图表渲染引擎 | Phase 7 已安装 |
| echarts-for-react | 3.0.6 | React ECharts 封装 | Phase 7 已安装，dashboard 组件已成熟使用模式 |
| TypeScript | 5.8.3 | 类型安全 | 项目已有，strict 模式 |
| Tailwind CSS | 3.4.17 | 样式 | 项目已有 |

### 辅助
| 库 | 版本 | 用途 | 使用场景 |
|-----|------|------|---------|
| Axios | 1.8.4 | HTTP 客户端 | 前端 API 调用，已有 JWT 拦截器 |

**无需安装新依赖。** 所有必要库已在项目中。

---

## 架构模式

### 数据获取架构

MyReview 页面需要从 3 个 API 端点获取新增数据：

```
1. GET /api/v1/evaluations/by-submission/{submission_id}
   → EvaluationRecord（含 dimension_scores[]、ai_level、overall_score、status）
   → 已有权限检查：AccessScopeService.ensure_evaluation_access_by_submission

2. GET /api/v1/salary/by-evaluation/{evaluation_id}
   → SalaryRecommendationEmployeeRead（员工角色仅返回 final_adjustment_ratio + status）
   → 已有角色字段过滤：shape_recommendation_for_role

3. GET /api/v1/approvals/recommendations/{recommendation_id}/history
   → ApprovalListResponse（含各审批步骤的 step_name、step_order、decision、is_current_step）
   → 已有权限检查：ensure_recommendation_access
```

**关键发现：** 所有后端端点已存在且支持员工角色访问。不需要新建后端 API。

### 数据依赖链

```
submission (已有)
  └── evaluation = fetchEvaluationBySubmission(submission.id)
        ├── dimension_scores → 雷达图 + 维度卡片
        ├── status → 控制评估结果区域显隐
        └── salaryRecommendation = fetchSalaryRecommendationByEvaluation(evaluation.id)
              ├── final_adjustment_ratio → 调薪百分比
              ├── status → 控制调薪区域显隐 (仅 approved)
              └── approvalHistory = fetchApprovalHistory(recommendation.id)  [可选]
                    └── steps → 步骤条映射
```

**注意:** 获取链是顺序的（evaluation 依赖 submission_id，salary 依赖 evaluation_id），但可以在 evaluation 返回后并行获取 salary 和 approval history。

### 步骤条状态映射逻辑

```typescript
// 状态到步骤的映射（来自 UI-SPEC）
function resolveCurrentStep(
  submissionStatus: string,
  evaluationStatus: string | null,
  approvalRecords: ApprovalRecord[]
): number {
  // 步骤 3: 已完成（approved/published）
  if (evaluationStatus === 'confirmed' && salaryStatus === 'approved') return 3;

  // 根据 approval records 的 is_current_step 和 step_name 判断
  const currentApproval = approvalRecords.find(r => r.is_current_step && r.decision === 'pending');
  if (currentApproval) {
    // step_name 包含 'manager' → 步骤 1
    // step_name 包含 'hr' → 步骤 2
    if (currentApproval.step_name.includes('manager')) return 1;
    if (currentApproval.step_name.includes('hr')) return 2;
  }

  // 默认：已提交
  return 0;
}
```

**替代方案（更简单）：** 如果 approval records 不可用（员工不是审批人，API 可能返回空），可以通过 evaluation.status 和 salary recommendation.status 推断步骤：
- `submitted` / `evaluated` → step 0
- evaluation.status = `reviewing` 或 `pending_manager` → step 1
- evaluation.status = `pending_hr` → step 2
- salary.status = `approved` → step 3

**重要发现：** `list_approvals` 按 `approver_id` 过滤非 admin/hrbp 用户，但 `/approvals/recommendations/{id}/history` 使用 `ensure_recommendation_access` 进行权限检查，这依赖 `AccessScopeService`。员工应该能通过此端点查看自己评估的审批历史。需要在实施时验证此路径对 employee 角色是否畅通。

### 新增组件结构

```
frontend/src/components/evaluation/
├── EvaluationStepBar.tsx      (新增) 横向步骤条
├── DimensionRadarChart.tsx    (新增) ECharts 雷达图
├── DimensionCard.tsx          (新增) 单个维度得分卡片
├── SalaryResultCard.tsx       (新增) 调薪百分比卡片
├── StatusIndicator.tsx        (现有) 状态标签
├── EvidenceCard.tsx           (现有) 证据卡片
├── FileUploadPanel.tsx        (现有) 文件上传
└── FileList.tsx               (现有) 文件列表
```

### 组件 Props 接口

```typescript
// EvaluationStepBar
interface EvaluationStepBarProps {
  currentStep: number; // 0-3
}

// DimensionRadarChart
interface DimensionRadarChartProps {
  scores: Array<{
    dimension_code: string;
    raw_score: number;
    weight: number;
  }>;
}

// DimensionCard
interface DimensionCardProps {
  dimensionCode: string;
  rawScore: number;
  weight: number;
  rationale: string;
}

// SalaryResultCard
interface SalaryResultCardProps {
  adjustmentRatio: number; // 0.12 表示 +12%
}
```

### ECharts 雷达图配置模式

基于项目已有 ECharts 使用模式（`AILevelChart.tsx`）：

```typescript
import ReactECharts from 'echarts-for-react';

// 雷达图 option 结构
const option = {
  textStyle: {
    fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif',
    color: '#646A73',
  },
  tooltip: {
    trigger: 'item',
    backgroundColor: '#FFFFFF',
    borderColor: '#E0E4EA',
    borderWidth: 1,
    textStyle: { color: '#1F2329', fontSize: 13 },
  },
  radar: {
    indicator: [
      { name: 'AI工具掌握度', max: 100 },
      { name: 'AI应用深度', max: 100 },
      { name: 'AI学习能力', max: 100 },
      { name: 'AI分享贡献', max: 100 },
      { name: 'AI成果转化', max: 100 },
    ],
    splitLine: { lineStyle: { color: '#E0E4EA' } },
    axisName: { color: '#646A73', fontSize: 13 },
  },
  series: [{
    type: 'radar',
    data: [{
      value: [score1, score2, score3, score4, score5],
      areaStyle: { color: 'rgba(20, 86, 240, 0.18)' },
      lineStyle: { color: '#1456F0', width: 2 },
      itemStyle: { color: '#1456F0' },
      symbolSize: 4,
    }],
  }],
};

<ReactECharts option={option} style={{ height: 320, width: '100%' }} />
```

### MyReview 页面扩展后布局

```
AppShell 头部（不变）
├── [新增] EvaluationStepBar（全宽，仅 submission 非 collecting 时显示）
├── [现有] metric-strip（调整第3格为审批阶段名称）
├── [新增] 评估结果区域（仅 confirmed/approved 状态）
│   ├── 上部: grid [雷达图 1.2fr | 综合得分+AI等级 0.8fr]
│   └── 下部: grid 5张维度卡片 [md:2col, xl:3col]
├── [新增] 调薪建议区域（仅 approved 状态）
│   └── SalaryResultCard
├── [现有] 材料提交区域（两列布局不变）
└── [现有] 证据摘要区域（不变）
```

### 反模式

- **不要在前端硬编码维度名称映射** — 维度代码到中文名称的映射应集中管理在一个常量文件中，避免在多个组件中重复
- **不要在 MyReview 中一次性调用所有 API** — 应该按依赖链顺序获取，evaluation 不存在时不请求 salary 和 approval
- **不要在前端判断角色来过滤字段** — 后端 `shape_recommendation_for_role` 已处理角色字段过滤，前端只需渲染返回的数据
- **不要创建新的后端端点** — 现有端点已满足所有数据需求

---

## 不要手工实现

| 问题 | 不要自建 | 使用已有方案 | 原因 |
|------|---------|------------|------|
| 雷达图渲染 | Canvas 手绘雷达图 | `echarts-for-react` + radar 图表类型 | ECharts 已安装且有成熟模式 |
| 角色字段过滤 | 前端判断角色隐藏字段 | 后端 `shape_recommendation_for_role` | SEC-04 已实现，后端是唯一权威源 |
| 权限控制 | 前端路由守卫 | 后端 `AccessScopeService` | 已有权限模型，前端只需处理 403 |
| 状态标签样式 | 自定义状态标签 | 现有 `StatusIndicator` 组件 | 已有完整的状态样式映射 |

---

## 常见陷阱

### 陷阱 1: 审批步骤映射不准确
**问题:** 步骤条需要显示"当前在哪一步"，但 approval records 的 step_name 可能不一致。
**根因:** 审批流程支持自定义步骤名，不一定严格匹配 "manager_review" / "hr_review"。
**避免方式:** 使用 `step_order` 数字而非 step_name 字符串来判断当前步骤位置；同时结合 `is_current_step` 标记。
**警告信号:** 步骤条停在错误的位置。

### 陷阱 2: 评估不存在时的 404 处理
**问题:** `fetchEvaluationBySubmission` 在评估尚未生成时返回 404。
**根因:** 员工刚上传材料但尚未触发评估时，evaluation 不存在是正常状态。
**避免方式:** 用 try-catch 捕获 404，将其视为"暂无评估"空状态，而非错误状态。
**警告信号:** 页面在新员工首次访问时显示红色错误信息。

### 陷阱 3: 调薪建议的条件渲染时机
**问题:** D-05 要求仅 approved 状态显示调薪信息，但 salary recommendation 的 status 和 approval records 的最终 decision 是两个不同概念。
**根因:** salary_recommendation.status 由审批流程更新，需要确认是 recommendation.status = 'approved' 还是最后一步 approval.decision = 'approved'。
**避免方式:** 使用 `salary_recommendation.status === 'approved'` 作为唯一判断条件，这是审批流程完成后更新的最终状态。
**警告信号:** 调薪信息在审批通过前提前显示，或通过后仍不显示。

### 陷阱 4: 数据获取的竞态条件
**问题:** MyReview 页面切换周期时，旧的异步请求可能覆盖新数据。
**根因:** 现有代码已使用 `cancelled` 标记处理竞态，但新增的链式 API 调用会增加竞态窗口。
**避免方式:** 在每个 async effect 中统一使用 `cancelled` 标记，所有状态设置前检查是否已取消。
**警告信号:** 快速切换周期后显示上一个周期的评估数据。

### 陷阱 5: 维度代码到中文名称的映射缺失
**问题:** `dimension_scores[].dimension_code` 是英文代码（如 `TOOL_MASTERY`），需要转为中文。
**根因:** 后端返回的是代码而非显示名称。
**避免方式:** 在前端创建集中的常量映射（`DIMENSION_LABELS`），所有组件共用。
**警告信号:** 雷达图和卡片显示英文代码而非中文名称。

---

## 代码示例

### 已有 ECharts 组件模式（来自 AILevelChart.tsx）

```typescript
// 项目已有的 ECharts 基础样式常量
const BASE_TEXT_STYLE = {
  fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif',
  color: '#646A73',
};

const BASE_TOOLTIP = {
  backgroundColor: '#FFFFFF',
  borderColor: '#E0E4EA',
  borderWidth: 1,
  textStyle: { color: '#1F2329', fontSize: 13 },
  padding: [8, 12] as [number, number],
  extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.10);',
};

// 使用方式
<ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
```

### 已有 API 调用模式（来自 evaluationService.ts）

```typescript
// 通过 submission_id 获取评估结果
export async function fetchEvaluationBySubmission(submissionId: string): Promise<EvaluationRecord> {
  const response = await api.get<EvaluationRecord>(`/evaluations/by-submission/${submissionId}`);
  return response.data;
}

// 通过 evaluation_id 获取调薪建议（后端自动按角色过滤字段）
export async function fetchSalaryRecommendationByEvaluation(evaluationId: string): Promise<SalaryRecommendationRecord> {
  const response = await api.get<SalaryRecommendationRecord>(`/salary/by-evaluation/${evaluationId}`);
  return response.data;
}
```

### 已有角色字段过滤模式（来自 salary.py）

```python
# 后端已有的角色字段过滤 — 员工只能看到 final_adjustment_ratio
class SalaryRecommendationEmployeeRead(BaseModel):
    id: str
    evaluation_id: str
    final_adjustment_ratio: float  # 唯一的数字字段
    status: str
    created_at: datetime
    explanation: str | None = None
```

### 已有审批历史 API（来自 approvalService.ts）

```typescript
// 需要在 approvalService.ts 中新增此函数（当前未导出但后端端点已存在）
export async function fetchApprovalHistory(recommendationId: string): Promise<ApprovalListResponse> {
  const response = await api.get<ApprovalListResponse>(`/approvals/recommendations/${recommendationId}/history`);
  return response.data;
}
```

### 维度代码映射常量

```typescript
// 来自 UI-SPEC 文案合约
const DIMENSION_LABELS: Record<string, string> = {
  TOOL_MASTERY: 'AI工具掌握度',
  APPLICATION_DEPTH: 'AI应用深度',
  LEARNING_ABILITY: 'AI学习能力',
  SHARING_CONTRIBUTION: 'AI分享贡献',
  OUTCOME_CONVERSION: 'AI成果转化',
};

const DIMENSION_WEIGHTS: Record<string, number> = {
  TOOL_MASTERY: 0.15,
  APPLICATION_DEPTH: 0.15,
  LEARNING_ABILITY: 0.20,
  SHARING_CONTRIBUTION: 0.20,
  OUTCOME_CONVERSION: 0.30,
};
```

---

## 现有技术状态

| 旧方式 | 当前方式 | 变更时间 | 影响 |
|--------|---------|---------|------|
| ECharts 5.x | ECharts 6.0.0 | Phase 7 安装 | radar 类型配置兼容，无 breaking changes |
| 无角色字段过滤 | SEC-04 角色字段过滤 | Phase 1 | 员工调用 salary API 只返回 final_adjustment_ratio |
| 直接 StatusIndicator | 步骤条 + StatusIndicator | Phase 8 新增 | 步骤条为新增组件，StatusIndicator 保持不变 |

---

## 待确认问题

1. **审批历史端点对 employee 角色的可访问性**
   - 已知: `ensure_recommendation_access` 调用 `AccessScopeService`，理论上员工可以访问自己评估的审批记录
   - 不确定: 是否需要先获取 recommendation_id（evaluation 返回的数据中不直接包含此字段）
   - 建议: 实施时先测试此路径；如果无法获取 recommendation_id，可改为从 evaluation.status 和 salary.status 推断步骤

2. **recommendation_id 的获取路径**
   - 已知: `SalaryRecommendationEmployeeRead` 包含 `id` 字段即 recommendation_id
   - 已知: `fetchSalaryRecommendationByEvaluation` 返回此数据
   - 建议: 先获取 salary recommendation，从其 `id` 获取 recommendation_id，再查询审批历史

---

## 验证架构

### 测试框架
| 属性 | 值 |
|------|------|
| 框架 | pytest 8.3.5 (后端) + TypeScript tsc (前端) |
| 配置文件 | `backend/tests/` 目录结构已有 |
| 快速运行命令 | `cd backend && python -m pytest tests/test_api/test_salary_roles.py -x` |
| 完整套件命令 | `cd backend && python -m pytest` + `cd frontend && npm run lint` |

### 阶段需求 -> 测试映射
| 需求 ID | 行为 | 测试类型 | 自动化命令 | 文件存在? |
|---------|------|---------|-----------|---------|
| EMP-01 | 员工可查看评估状态和审批阶段 | integration | `python -m pytest tests/test_api/test_evaluation_api.py -x -k employee` | 部分（评估 API 测试已有，需新增员工视角用例） |
| EMP-02 | 员工可查看 5 维度评估结果 | integration | `python -m pytest tests/test_api/test_evaluation_api.py -x -k by_submission` | 已有（by-submission 端点测试） |
| EMP-03 | 员工可查看调薪百分比（仅 approved） | integration | `python -m pytest tests/test_api/test_salary_roles.py -x` | 已有（角色字段过滤测试） |

### 采样频率
- **每任务提交:** `cd frontend && npx tsc --noEmit` + 页面加载验证
- **每 wave 合并:** `cd backend && python -m pytest` + `cd frontend && npm run lint`
- **阶段门:** 完整套件绿色 + 手动验证员工角色登录后各状态下的页面显示

### Wave 0 缺口
- [ ] 前端组件无单元测试框架（项目整体如此，不在本阶段解决）
- [ ] 需确认 employee 角色调用 `/approvals/recommendations/{id}/history` 的权限行为

---

## 项目约束（来自 CLAUDE.md）

- 前端使用 React，后端使用 FastAPI + Python
- 所有评分、系数、阈值、认证规则必须配置化，不硬编码在多个位置
- 评级结果必须可追溯，必须能解释每个维度得分来源
- 调薪建议必须区分"系统建议值"和"最终审批值"（但员工只看最终结果，D-06 已锁定）
- 所有关键业务结果都应可审计、可解释、可追踪
- 对外 API 保持版本化 `/api/v1/...`
- 前端 lint 命令: `npm run lint`（即 `tsc --noEmit`）
- 前端无 ESLint，仅 TypeScript 严格模式类型检查

---

## 来源

### 主要（HIGH 置信度）
- `frontend/src/pages/MyReview.tsx` — 现有页面结构和数据获取模式
- `frontend/src/components/dashboard/AILevelChart.tsx` — ECharts 使用模式
- `frontend/src/types/api.ts` — 完整类型定义（EvaluationRecord、DimensionScoreRecord、SalaryRecommendationRecord）
- `backend/app/api/v1/evaluations.py` — 评估端点，已验证 by-submission 支持员工角色
- `backend/app/api/v1/salary.py` — 调薪端点，已验证 shape_recommendation_for_role 角色过滤
- `backend/app/api/v1/approvals.py` — 审批历史端点
- `backend/app/schemas/salary.py` — SalaryRecommendationEmployeeRead 定义
- `.planning/phases/08-employee-self-service-ui/08-UI-SPEC.md` — 完整 UI 设计合约
- `.planning/phases/08-employee-self-service-ui/08-CONTEXT.md` — 用户决策

### 次要（MEDIUM 置信度）
- `backend/app/services/approval_service.py` — list_history 方法，employee 角色访问路径需实施时验证

---

## 元数据

**置信度细分:**
- 技术栈: HIGH — 所有库已安装，版本已确认
- 架构: HIGH — 已有端点和组件模式完全覆盖需求
- 陷阱: HIGH — 基于对现有代码的深入分析
- 步骤条映射: MEDIUM — approval records 的 employee 角色访问路径需验证

**研究日期:** 2026-03-28
**有效期至:** 2026-04-28（稳定，无外部依赖变更风险）
