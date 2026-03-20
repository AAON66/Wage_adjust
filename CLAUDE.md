# 公司综合调薪工具 - Project Instructions

## Project Context

本项目是一个面向企业内部人才盘点与调薪决策的综合平台，核心目标是基于员工提交的成果材料与业务表现，自动完成 AI 能力评级、调薪建议生成、人才发展跟踪与对外数据服务。

系统需要支持以下核心能力：

1. 智能评价员工技术评级
   - 员工可上传多种成果材料，包括但不限于 `PPT`、`PNG`、代码文件、文档等
   - 系统基于材料内容、业务成果与 AI 应用表现进行综合评估
2. AI 能力评估与调薪计算
   - 基于 AI 能力五级矩阵进行分级
   - 基于 AI 能力五维评估模型进行加权评分
   - 结合成长阶段认证加成生成调薪建议
3. 差异化调薪功能
   - 支持按部门、岗位族、职级、绩效、AI 等级进行差异化调薪
4. 对外输出 API
   - 提供标准 REST API，供 HR 系统、绩效系统、人才系统对接
5. 批量导入人才评估
   - 支持 Excel/CSV/批量文件导入
6. 看板系统
   - 跟踪人才发展情况、能力分布、认证进度、调薪分布与 ROI
7. 自动评级系统
   - 结合大模型分析、规则引擎与人工复核流程完成自动评级

技术栈要求：

- 前端：`React`
- 后端：`FastAPI`
- 主语言：`Python`
- 大模型：`DeepSeek`
- 开发环境：可在 `PyCharm` 中稳定运行和调试

> Note: 详细任务拆分应维护在 `task.json` 中，架构设计说明维护在 `architecture.md` 中。

---

## AI Evaluation Standards

### AI 能力五级矩阵

- `Level 5 / AI大师级`
  - 能力标准：能自主开发 AI 工具并解决复杂业务问题，引领团队 AI 转型，形成方法论输出
  - 调薪系数：`1.5 - 2.0`
- `Level 4 / AI专家级`
  - 能力标准：精通多种 AI 工具并创新应用场景，能培训指导他人使用 AI 工具
  - 调薪系数：`1.3 - 1.5`
- `Level 3 / AI应用级`
  - 能力标准：熟练运用主流 AI 工具提升工作效率，能解决中等复杂度业务问题
  - 调薪系数：`1.1 - 1.3`
- `Level 2 / AI入门级`
  - 能力标准：掌握基础 AI 工具使用，能完成简单 AI 辅助任务
  - 调薪系数：`1.0 - 1.1`
- `Level 1 / AI未入门`
  - 能力标准：缺乏 AI 工具使用能力，完全依赖传统工作方式
  - 调薪系数：`0.9 - 1.0`

### AI 能力五维评估模型

- `AI工具掌握度`，权重 `15%`
  - 评估要点：熟练使用 AI 辅助工具的数量和质量
  - 数据来源：实操测试、项目成果记录
- `AI应用深度`，权重 `15%`
  - 评估要点：AI 解决问题的复杂度和创新性
  - 数据来源：案例分析、成果评估报告
- `AI学习能力`，权重 `20%`
  - 评估要点：自主学习新 AI 工具的速度和效果
  - 数据来源：培训记录、技能认证证书
- `AI分享贡献`，权重 `20%`
  - 评估要点：对团队 AI 能力提升的贡献度
  - 数据来源：内部培训次数、知识库文档贡献
- `AI成果转化`，权重 `30%`
  - 评估要点：AI 应用带来的实际业务价值
  - 数据来源：业绩数据、ROI 分析报告

### AI 成长阶段认证加成

- `AI意识唤醒（0-3个月）`
  - 目标：建立 AI 认知，掌握基础工具
  - 认证收益：通过 AI 基础认证可获得调薪 `+2%`
- `AI技能应用（3-12个月）`
  - 目标：熟练运用 AI 解决实际业务问题
  - 认证收益：完成 2 个 `ROI > 20%` 的应用项目并通过 AI 应用认证，可获得调薪 `+5%`
- `AI方法创新（1-2年）`
  - 目标：创新 AI 应用场景并推广至团队
  - 认证收益：通过 AI 创新认证可获得调薪 `+8%`
- `AI领导影响（2年以上）`
  - 目标：引领 AI 转型并培养 AI 人才
  - 认证收益：通过 AI 专家认证可获得长期调薪 `+12%`

### Core Evaluation Rules

- 评级结果必须可追溯，必须能解释每个维度得分来源
- 调薪建议必须区分“系统建议值”和“最终审批值”
- 自动评级结果必须支持人工复核与覆写，并保留审计日志
- 评分规则、系数区间、认证加成必须配置化，不允许硬编码在多个位置

---

## MANDATORY: Agent Workflow

Every new agent session MUST follow this workflow:

### Step 1: Initialize Environment

优先确认前后端开发环境可启动：

```bash
# backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

这一步的目标是确认：

- 后端 API 可以启动
- 前端开发服务器可以启动
- 本地环境可在 `PyCharm` 中直接调试

**DO NOT skip this step.** 在开始功能开发前，先确认最小可运行环境成立。

### Step 2: Select Next Task

阅读 `task.json` 并选择一个任务处理。

选择标准按以下顺序：

1. 优先选择 `passes: false` 的任务
2. 优先完成基础能力和依赖性更强的任务
3. 优先完成影响主流程闭环的功能
4. 若有多项候选，优先选择能形成端到端价值链的任务

对于本项目，基础优先级通常如下：

1. 项目初始化与环境配置
2. 数据模型与文件上传能力
3. DeepSeek 封装与评估引擎
4. 自动评级与调薪计算
5. 批量导入与外部 API
6. 看板与人才发展追踪

### Step 3: Implement the Task

- 仔细阅读任务描述和步骤
- 明确该任务影响的数据流、评分规则与 API 契约
- 优先复用已有模块、Schema、服务层和组件模式
- 文件解析、评分计算、调薪规则、审批状态流转要保持职责清晰
- 任何涉及 AI 评估的改动，都要同时考虑“输入材料”“模型调用”“结构化评分”“人工复核”四个环节

### Step 4: Test Thoroughly

实现后必须验证该任务涉及的全部功能。

**Testing Requirements - MANDATORY**

1. `前端页面或交互改动`
   - 必须验证页面可正常加载与交互
   - 必须验证上传、列表、筛选、评分展示、看板图表等核心流程
   - 涉及关键页面布局调整时，必须做浏览器级验证

2. `后端 API 改动`
   - 必须验证接口状态码、返回结构、鉴权逻辑与异常分支
   - 必须覆盖上传、评估、批量导入、调薪建议、看板统计、外部 API 等关键路径

3. `评估/计算逻辑改动`
   - 必须验证五维权重计算正确
   - 必须验证等级映射正确
   - 必须验证成长认证加成正确
   - 必须验证差异化调薪规则在边界值下行为正确

4. `文件处理能力改动`
   - 必须验证不同文件类型上传与解析流程
   - 必须验证异常文件、空文件、不支持格式、超大文件的错误处理

5. `所有改动都必须通过`
   - Python 代码无语法错误
   - 关键单元测试通过
   - 前端 lint/build 通过
   - 后端服务可启动

**Minimum test checklist**

- [ ] API/页面可正常运行
- [ ] 上传与评估主流程可执行
- [ ] 评分结果可解释
- [ ] 调薪结果符合配置规则
- [ ] lint / build / tests 通过

### Step 5: Update Progress

将本次工作记录到 `progress.txt`：

```text
## [Date] - Task: [task description]

### What was done:
- [specific changes made]

### Testing:
- [how it was tested]

### Notes:
- [any relevant notes for future agents]
```

### Step 6: Commit Changes

如果任务已完整通过验证，应将相关改动一次性提交，包括：

- 代码
- `task.json`
- `progress.txt`
- 如有必要的文档更新

```bash
git add .
git commit -m "[task description] - completed"
```

规则：

- 只有在任务完成且验证通过后，才能将 `passes` 从 `false` 改为 `true`
- 不要删除任务，不要重写任务原始意图
- 一个任务相关的代码、文档、任务状态更新应保持在同一个提交中

---

## Blocking Issues

如果任务无法完成，必须停止并明确记录阻塞原因。

### 必须请求人工介入的典型情况

1. `缺少关键配置`
   - DeepSeek API Key 未提供
   - 数据库连接未配置
   - 对象存储或文件服务未配置
   - 审批流依赖的企业内部系统未开放

2. `外部依赖不可用`
   - OCR、文件解析、向量服务不可访问
   - 第三方 HR/绩效系统接口未开通
   - 企业单点登录未配置

3. `测试无法执行`
   - 需要真实企业数据样本但当前缺失
   - 需要真实审批人或组织架构数据
   - 需要受限网络环境中的服务授权

### 阻塞时的处理规则

**DO NOT**

- 不要提交伪完成代码
- 不要将 `task.json` 标记为完成
- 不要省略风险说明

**DO**

- 在 `progress.txt` 中记录当前进度与阻塞原因
- 明确指出还缺什么配置、数据或授权
- 输出可执行的下一步人工处理建议

### 阻塞信息模板

```text
任务阻塞 - 需要人工介入

当前任务: [task name]

已完成工作:
- [completed work]

阻塞原因:
- [why work cannot continue]

需要人工协助:
1. [required action]
2. [required action]

解除阻塞后继续方式:
- 运行 [command] 或继续执行 [next step]
```

---

## Project Structure

建议项目结构如下：

```text
/
├── CLAUDE.md                # 本文件：项目协作与开发说明
├── task.json                # 任务定义与完成状态
├── progress.txt             # 每次会话进度记录
├── architecture.md          # 架构设计文档
├── requirements.txt         # Python 依赖
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── engines/         # 评分引擎、调薪引擎、规则引擎
│   │   ├── parsers/         # PPT/图片/代码/文档解析
│   │   └── utils/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
└── uploads/                 # 本地开发文件缓存或临时存储
```

---

## Commands

```bash
# backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
pytest

# frontend
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

如果后续引入格式化或静态检查工具，也应纳入标准命令，例如：

```bash
ruff check .
black .
```

---

## Coding Conventions

- 以后端 `Python + FastAPI` 为核心，保持模块边界清晰
- 前端使用 `React`，组件按页面域和业务域组织
- 所有评分、系数、阈值、认证规则必须配置化
- 所有 AI 结果尽量输出结构化 JSON，避免不可控自由文本直出
- 上传解析、评分引擎、API 输出之间必须通过明确的 Schema 对接
- 所有关键业务结果都应可审计、可解释、可追踪
- 对外 API 要保持版本化，例如 `/api/v1/...`
- 批量导入必须考虑幂等性、校验错误回传和部分成功场景
- 看板统计必须区分实时数据与离线聚合数据的边界
- 优先编写针对评分逻辑、调薪逻辑、导入逻辑的单元测试

---

## Key Rules

1. 一次聚焦一个任务，避免同时改动过多主流程
2. 涉及评分与调薪的逻辑，必须先保证正确性，再考虑表现层
3. 自动评级必须可解释，不能只输出最终等级
4. 文件上传与解析链路必须考虑失败场景
5. 对外 API 必须保证返回结构稳定
6. 差异化调薪规则必须可配置、可扩展
7. 看板数据必须和底层评估数据口径一致
8. 完成任务前必须测试，未测试不得标记完成
9. 遇到外部依赖阻塞时，记录清楚后停止，不要伪造结果
10. 所有重要变更都要让后续代理能看懂并接手
