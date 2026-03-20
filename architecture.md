# 公司综合调薪工具 - 架构设计文档

## 项目概述

员工提交成果材料 + 系统批量导入基础信息 + LLM 提取证据与生成五维评分 + 规则引擎计算 AI 等级与调薪建议 + 人工复核与校准审批 + 看板跟踪人才发展与预算执行 + 对外 API 输出结果

---

## 技术栈

| 层级 | 技术选型 |
|-----|---------|
| 前端 | React + TypeScript + Tailwind CSS |
| 后端 | FastAPI (Python 3.11+) |
| 数据库 | PostgreSQL |
| 认证 | JWT + OAuth2 / API Key |
| 文件存储 | MinIO / AWS S3 |
| LLM | DeepSeek R1 |
| 文件解析 | pypdf / python-pptx / Pillow / 自定义解析器 |
| 统计分析 | pandas / numpy |
| 缓存与异步 | Redis / Background Tasks / Celery(可选) |

---

## 1. 系统架构图
```mermaid
graph TB
    subgraph Frontend["前端 (React)"]
        UI[用户界面]
        Pages[页面路由]
        Components[业务组件]
    end

    subgraph Backend["后端 (FastAPI)"]
        API[REST API]
        Services[业务服务层]
        Engines[评分与调薪引擎]
        Auth[认证与权限]
    end

    subgraph Database["数据层"]
        DB[(PostgreSQL)]
        Storage[对象存储<br/>MinIO/S3]
        Cache[(Redis)]
    end

    subgraph External["外部AI与集成服务"]
        DeepSeek[DeepSeek R1<br/>证据抽取/能力评级/解释生成]
        HRIS[HR/绩效/薪酬系统]
    end

    subgraph Analytics["分析与治理"]
        Dashboard[组织看板]
        Audit[审计日志]
        ImportCenter[批量导入中心]
    end

    UI --> Pages
    Pages --> Components
    UI --> API
    API --> Auth
    API --> Services
    Services --> Engines
    Services --> DB
    Services --> Storage
    Services --> Cache
    Services --> DeepSeek
    Services --> HRIS
    Services --> Dashboard
    Services --> Audit
    Services --> ImportCenter
```

---

## 2. 核心业务流程图
> **关键特性**: 每一个关键环节都必须支持人工复核、审计追踪和规则配置化。
```mermaid
flowchart TD
    Start([用户开始]) --> Auth{已登录?}
    Auth -->|否| Login[登录/注册]
    Auth -->|是| SelectCycle[选择或创建评估周期]
    Login --> SelectCycle

    SelectCycle --> ImportEmployees[导入员工基础数据]
    ImportEmployees --> CreateSubmission[创建员工评估记录]

    %% 阶段1: 材料采集
    CreateSubmission --> UploadFiles[上传成果材料]
    UploadFiles --> ParseFiles[解析 PPT/图片/代码/文档]
    ParseFiles --> ExtractEvidence[抽取结构化证据]
    ExtractEvidence --> ReviewEvidence{材料和证据是否完整?}
    ReviewEvidence -->|否| RequestMore[补充材料或重新解析]
    RequestMore --> UploadFiles
    ReviewEvidence -->|是| ConfirmEvidence[确认进入评级]

    %% 阶段2: 自动评级
    ConfirmEvidence --> GenerateEvaluation[触发 AI 自动评级]
    GenerateEvaluation --> LLMScoring[DeepSeek 生成五维评分与解释]
    LLMScoring --> RuleMapping[规则引擎映射 AI Level]
    RuleMapping --> ShowEvaluation[展示等级、维度分和证据依据]
    ShowEvaluation --> NeedReview{是否需人工复核?}
    NeedReview -->|是| ManualReview[人工复核与校准]
    ManualReview --> ConfirmEvaluation[确认最终评级]
    NeedReview -->|否| ConfirmEvaluation[确认最终评级]

    %% 阶段3: 调薪建议
    ConfirmEvaluation --> SalaryCalc[计算调薪建议]
    SalaryCalc --> ApplyRules[应用等级系数/认证加成/岗位差异化规则]
    ApplyRules --> BudgetCheck[校验预算与公平性]
    BudgetCheck --> ShowSalary[展示调薪建议与解释]
    ShowSalary --> Calibration{是否需要横向校准?}
    Calibration -->|是| TeamCalibration[进入校准会模式]
    TeamCalibration --> ApprovalStart[提交审批]
    Calibration -->|否| ApprovalStart[提交审批]

    %% 阶段4: 审批与发布
    ApprovalStart --> ManagerApprove[直属主管审批]
    ManagerApprove --> HRApprove[HRBP/薪酬管理员审批]
    HRApprove --> CommitteeApprove[薪酬委员会审批]
    CommitteeApprove --> PublishResult[发布结果]

    %% 阶段5: 运营与输出
    PublishResult --> DashboardUpdate[更新组织看板]
    DashboardUpdate --> ExportAPI[对外 API / 导出结果]
    ExportAPI --> End([结束])
```

### 用户交互流程

```mermaid
stateDiagram-v2
    [*] --> 周期创建
    周期创建 --> 材料收集中: 导入员工并创建评估记录
    材料收集中 --> 材料收集中: 上传材料/补充材料
    材料收集中 --> 解析处理中: 触发文件解析
    解析处理中 --> 待评级: 证据抽取完成
    待评级 --> 待复核: 自动评级完成且低置信度
    待评级 --> 待调薪: 自动评级完成且可直接确认
    待复核 --> 待调薪: 人工复核通过
    待调薪 --> 待校准: 生成调薪建议
    待调薪 --> 待审批: 无需校准直接提交审批
    待校准 --> 待审批: 校准完成
    待审批 --> 已发布: 审批通过
    待审批 --> 材料收集中: 驳回并要求补充材料
    已发布 --> [*]
```

---

## 3. 数据模型图
```mermaid
erDiagram
    users ||--o{ approval_records : approves
    users ||--o{ audit_logs : operates
    employees ||--o{ employee_submissions : has
    evaluation_cycles ||--o{ employee_submissions : contains
    employee_submissions ||--o{ uploaded_files : uploads
    employee_submissions ||--o{ evidence_items : produces
    employee_submissions ||--o| ai_evaluations : has
    ai_evaluations ||--o{ dimension_scores : contains
    employees ||--o{ certifications : owns
    ai_evaluations ||--o| salary_recommendations : generates
    salary_recommendations ||--o{ approval_records : goes_through
    import_jobs ||--o{ audit_logs : triggers

    users {
        uuid id PK
        string email
        string hashed_password
        string role "admin/hrbp/manager/employee/committee"
        datetime created_at
    }

    employees {
        uuid id PK
        string employee_no "员工编号"
        string name "员工姓名"
        string department "部门"
        string job_family "岗位族"
        string job_level "职级"
        uuid manager_id FK "直属主管"
        string status "active/inactive"
        datetime created_at
        datetime updated_at
    }

    evaluation_cycles {
        uuid id PK
        string name "评估周期名称"
        string review_period "评估周期"
        decimal budget_amount "预算金额"
        string status "draft/collecting/reviewing/approved/published/archived"
        datetime created_at
        datetime updated_at
    }

    employee_submissions {
        uuid id PK
        uuid employee_id FK
        uuid cycle_id FK
        text self_summary "员工自评"
        text manager_summary "主管评价"
        string status "collecting/submitted/parsing/evaluated/reviewing/calibrated/approved/published"
        datetime submitted_at
        datetime created_at
    }

    uploaded_files {
        uuid id PK
        uuid submission_id FK
        string file_name "文件名"
        string file_type "ppt/png/pdf/code/doc/excel"
        string storage_key "对象存储路径"
        string parse_status "pending/processing/success/failed"
        datetime created_at
    }

    evidence_items {
        uuid id PK
        uuid submission_id FK
        string source_type "self_report/manager_review/file_parse/business_metric/system_detected"
        string title "证据标题"
        text content "证据内容"
        float confidence_score "可信度"
        json metadata "来源元数据"
        datetime created_at
    }

    ai_evaluations {
        uuid id PK
        uuid submission_id FK
        float overall_score "综合得分"
        string ai_level "level1/level2/level3/level4/level5"
        float confidence_score "模型置信度"
        text explanation "解释说明"
        string status "draft/generated/reviewed/confirmed"
        datetime created_at
        datetime updated_at
    }

    dimension_scores {
        uuid id PK
        uuid evaluation_id FK
        string dimension_code "tool_mastery/application_depth/learning_agility/sharing_contribution/value_conversion"
        float weight "权重"
        float raw_score "原始分"
        float weighted_score "加权分"
        text rationale "评分依据"
        datetime created_at
    }

    certifications {
        uuid id PK
        uuid employee_id FK
        string certification_type "basic/application/innovation/expert"
        string certification_stage "awareness/application/innovation/leadership"
        float bonus_rate "调薪加成"
        datetime issued_at
        datetime expires_at
    }

    salary_recommendations {
        uuid id PK
        uuid evaluation_id FK
        decimal current_salary "当前薪资"
        float recommended_ratio "建议调薪比例"
        decimal recommended_salary "建议后薪资"
        float ai_multiplier "AI等级系数"
        float certification_bonus "认证加成"
        float final_adjustment_ratio "最终审批调薪比例"
        string status "draft/simulated/reviewing/approved/locked"
        datetime created_at
    }

    approval_records {
        uuid id PK
        uuid recommendation_id FK
        uuid approver_id FK
        string step_name "manager/hrbp/committee"
        string decision "pending/approved/rejected"
        text comment "审批意见"
        datetime decided_at
        datetime created_at
    }

    import_jobs {
        uuid id PK
        string file_name "导入文件名"
        string import_type "employee/metric/certification/history"
        string status "pending/processing/completed/partial_failed/failed"
        int total_rows "总行数"
        int success_rows "成功行数"
        int failed_rows "失败行数"
        json result_summary "导入摘要"
        datetime created_at
    }

    audit_logs {
        uuid id PK
        uuid operator_id FK
        string action "操作动作"
        string target_type "目标类型"
        uuid target_id "目标ID"
        json detail "操作详情"
        datetime created_at
    }
```

### 状态流转说明
| 字段 | 可能值 | 说明 |
|-----|-------|------|
| evaluation_cycles.status | draft | 刚创建，尚未开始 |
| | collecting | 材料与基础数据收集中 |
| | reviewing | 已进入评级/调薪复核流程 |
| | approved | 调薪结果审批通过 |
| | published | 结果已发布 |
| | archived | 周期已归档 |
| employee_submissions.status | collecting | 等待上传材料 |
| | submitted | 已提交材料 |
| | parsing | 文件解析中 |
| | evaluated | AI 评级完成 |
| | reviewing | 人工复核中 |
| | calibrated | 已完成校准 |
| | approved | 已审批完成 |
| | published | 已对外发布 |
| ai_evaluations.status | draft | 尚未生成评级 |
| | generated | 自动评级已生成 |
| | reviewed | 人工复核完成 |
| | confirmed | 最终评级确认 |
| salary_recommendations.status | draft | 尚未生成调薪建议 |
| | simulated | 已完成试算 |
| | reviewing | 校准/审批中 |
| | approved | 审批通过 |
| | locked | 结果锁定 |

---

## 4. 页面结构图
```mermaid
graph TB
    subgraph Auth["认证页面"]
        LoginPage[登录页 /login]
        RegisterPage[注册页 /register]
    end

    subgraph Main["主要页面"]
        HomePage[首页 /]
        EmployeesPage[员工评估列表 /employees]
        CreateCyclePage[创建评估周期 /cycles/create]
        DetailPage[员工评估详情 /evaluations/:id]
        SimulatorPage[调薪模拟 /salary-simulator]
        ApprovalsPage[审批中心 /approvals]
        DashboardPage[组织看板 /dashboard]
        ImportPage[批量导入中心 /imports]
    end

    subgraph DetailFeatures["评估详情页功能"]
        EmployeeSection[员工信息区]
        FileSection[材料上传与预览区]
        EvidenceSection[证据与解释区]
        ScoreSection[五维评分区]
        SalarySection[调薪建议区]
        ReviewSection[复核与校准区]
        Actions[操作按钮<br/>解析/生成评级/试算/提交审批]
    end

    subgraph DashboardFeatures["组织看板功能"]
        OverviewCards[概览指标卡]
        Heatmap[部门热力图]
        LevelDistribution[AI等级分布图]
        BudgetPanel[预算执行面板]
        PotentialPanel[高潜人才面板]
    end

    HomePage --> EmployeesPage
    HomePage --> DashboardPage
    HomePage --> SimulatorPage
    HomePage --> ApprovalsPage
    LoginPage --> HomePage
    RegisterPage --> LoginPage
    EmployeesPage --> DetailPage
    CreateCyclePage --> EmployeesPage
    DetailPage --> SimulatorPage
    DetailPage --> ApprovalsPage

    DetailPage --> EmployeeSection
    DetailPage --> FileSection
    DetailPage --> EvidenceSection
    DetailPage --> ScoreSection
    DetailPage --> SalarySection
    DetailPage --> ReviewSection
    DetailPage --> Actions

    DashboardPage --> OverviewCards
    DashboardPage --> Heatmap
    DashboardPage --> LevelDistribution
    DashboardPage --> BudgetPanel
    DashboardPage --> PotentialPanel
```

---

## 5. API 设计

### 员工与周期 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| POST | /api/v1/employees | 创建员工档案 |
| GET | /api/v1/employees | 获取员工列表 |
| GET | /api/v1/employees/{id} | 获取员工详情 |
| POST | /api/v1/cycles | 创建评估周期 |
| GET | /api/v1/cycles | 获取评估周期列表 |
| PATCH | /api/v1/cycles/{id} | 更新评估周期 |
| POST | /api/v1/cycles/{id}/publish | 发布评估周期 |

### 材料上传与解析 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| POST | /api/v1/submissions/{id}/files | 上传员工成果材料 |
| GET | /api/v1/submissions/{id}/files | 获取材料列表 |
| POST | /api/v1/files/{id}/parse | 触发单文件解析 |
| POST | /api/v1/submissions/{id}/parse-all | 批量解析当前提交材料 |
| GET | /api/v1/files/{id}/preview | 获取文件预览地址 |
| GET | /api/v1/submissions/{id}/evidence | 获取证据列表 |

### 自动评级 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| POST | /api/v1/evaluations/generate | 生成员工 AI 评级 |
| POST | /api/v1/evaluations/regenerate | 重新生成评级 |
| GET | /api/v1/evaluations/{id} | 获取评级详情 |
| PATCH | /api/v1/evaluations/{id}/manual-review | 人工复核并修改等级或分数 |
| POST | /api/v1/evaluations/{id}/confirm | 确认最终评级 |

### 调薪建议 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| POST | /api/v1/salary/recommend | 生成调薪建议 |
| GET | /api/v1/salary/{id} | 获取调薪建议详情 |
| POST | /api/v1/salary/simulate | 预算模拟与差异化试算 |
| PATCH | /api/v1/salary/{id} | 修改最终审批值 |
| POST | /api/v1/salary/{id}/lock | 锁定调薪方案 |

### 复核与审批 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| GET | /api/v1/reviews/pending | 获取待复核任务列表 |
| POST | /api/v1/reviews/{id}/calibrate | 提交校准结果 |
| GET | /api/v1/approvals/pending | 获取待审批列表 |
| POST | /api/v1/approvals/{id}/approve | 审批通过 |
| POST | /api/v1/approvals/{id}/reject | 审批驳回 |
| GET | /api/v1/approvals/{id}/history | 获取审批历史 |

### 看板与导入 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| GET | /api/v1/dashboard/overview | 获取总览指标 |
| GET | /api/v1/dashboard/ai-level-distribution | 获取 AI 等级分布 |
| GET | /api/v1/dashboard/department-heatmap | 获取部门热力图 |
| GET | /api/v1/dashboard/salary-budget | 获取预算使用情况 |
| POST | /api/v1/imports/employees | 上传员工导入文件 |
| POST | /api/v1/imports/metrics | 上传业务指标或认证记录 |
| GET | /api/v1/imports/{id} | 获取导入任务详情 |

### 对外开放 API

| 方法 | 路径 | 描述 |
|-----|------|-----|
| GET | /api/v1/public/employees/{employee_no}/latest-evaluation | 获取员工最新评级 |
| GET | /api/v1/public/cycles/{id}/salary-results | 获取周期调薪结果 |
| GET | /api/v1/public/cycles/{id}/approval-status | 获取审批状态 |
| GET | /api/v1/public/dashboard/summary | 获取看板摘要数据 |

---

## 6. 外部 API 集成

### 6.1 DeepSeek R1 (证据抽取 + 自动评级 + 解释生成)

```python
# 使用 httpx 或 requests 库调用
# 端点: https://api.deepseek.com/v1/chat/completions
认证: Bearer Token
模型: deepseek-reasoner
```

#### 自动评级请求示例 (Python):
```python
import httpx

async def generate_ai_evaluation(employee_profile: dict, evidence_list: list, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-reasoner",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是企业AI能力评估专家，请根据员工证据材料输出五维评分、AI等级、评分解释、关键证据和置信度，结果必须结构化。"
                    },
                    {
                        "role": "user",
                        "content": f"员工信息: {employee_profile}\n证据列表: {evidence_list}\n请按照AI工具掌握度、AI应用深度、AI学习能力、AI分享贡献、AI成果转化五个维度评分，并映射Level1到Level5。"
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 4000
            }
        )
        return response.json()
```

#### 调薪解释生成请求示例 (Python):
```python
async def generate_salary_explanation(level_result: dict, salary_context: dict, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-reasoner",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是企业薪酬策略顾问，请根据AI评级结果、认证加成、预算规则输出调薪建议解释和风险提示。"
                    },
                    {
                        "role": "user",
                        "content": f"评级结果: {level_result}\n调薪上下文: {salary_context}\n请输出建议调薪比例、关键原因、预算风险和人工复核建议。"
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 3000
            }
        )
        return response.json()
```

---

## 7. 成果材料类型

| 类型ID | 类型名称 | 描述 |
|-------|---------|-----|
| ppt | PPT 汇报材料 | 项目复盘、成果展示、方案汇报 |
| image | 图片材料 | 截图、海报、流程图、数据可视化 |
| code | 代码材料 | 代码仓库、脚本、PR、自动化工具 |
| pdf | PDF 文档 | 项目说明、结项报告、方案文档 |
| markdown | Markdown/文本 | 技术文档、知识库、复盘总结 |
| excel | 表格数据 | ROI 分析、业绩数据、导入模板 |
| archive | 压缩包 | 项目打包材料、代码包、资源包 |
| link | 外部链接 | Git 仓库、飞书文档、知识库链接 |

---

## 8. 评估维度与调薪规则类型

| 维度/规则ID | 名称 | 描述 |
|-------|---------|-----|
| tool_mastery | AI工具掌握度 | 熟练使用 AI 工具的数量、质量与深度 |
| application_depth | AI应用深度 | AI 解决问题的复杂度和创新程度 |
| learning_agility | AI学习能力 | 学习新 AI 工具和方法的速度与效果 |
| sharing_contribution | AI分享贡献 | 对团队 AI 能力建设的培训与知识贡献 |
| value_conversion | AI成果转化 | AI 应用带来的效率、收入或降本价值 |
| level_multiplier | AI等级系数 | 根据 Level1-Level5 映射调薪系数区间 |
| certification_bonus | 认证加成 | 根据基础/应用/创新/专家认证叠加调薪加成 |
| role_adjustment | 岗位差异化 | 按部门、岗位族、职级、绩效等修正调薪建议 |
| budget_guard | 预算控制 | 校验推荐方案是否超预算或破坏分布平衡 |

---

## 9. Python 项目结构

```
wage-adjust/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── config.py           # 配置管理
│   │   ├── dependencies.py     # 依赖注入
│   │   ├── api/                # API 路由
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── employees.py
│   │   │       ├── cycles.py
│   │   │       ├── files.py
│   │   │       ├── evaluations.py
│   │   │       ├── salary.py
│   │   │       ├── approvals.py
│   │   │       ├── dashboard.py
│   │   │       ├── imports.py
│   │   │       └── public.py
│   │   ├── models/             # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── employee.py
│   │   │   ├── evaluation_cycle.py
│   │   │   ├── submission.py
│   │   │   ├── uploaded_file.py
│   │   │   ├── evidence.py
│   │   │   ├── evaluation.py
│   │   │   ├── dimension_score.py
│   │   │   ├── certification.py
│   │   │   ├── salary_recommendation.py
│   │   │   ├── approval.py
│   │   │   ├── import_job.py
│   │   │   └── audit_log.py
│   │   ├── schemas/            # Pydantic 模式
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── employee.py
│   │   │   ├── cycle.py
│   │   │   ├── evaluation.py
│   │   │   ├── salary.py
│   │   │   └── dashboard.py
│   │   ├── services/           # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── llm_service.py
│   │   │   ├── file_service.py
│   │   │   ├── parse_service.py
│   │   │   ├── evidence_service.py
│   │   │   ├── employee_service.py
│   │   │   ├── cycle_service.py
│   │   │   ├── review_service.py
│   │   │   ├── approval_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── import_service.py
│   │   │   └── integration_service.py
│   │   ├── engines/            # 核心引擎
│   │   │   ├── evaluation_engine.py
│   │   │   └── salary_engine.py
│   │   ├── parsers/            # 文件解析器
│   │   │   ├── base_parser.py
│   │   │   ├── ppt_parser.py
│   │   │   ├── image_parser.py
│   │   │   ├── code_parser.py
│   │   │   └── document_parser.py
│   │   ├── core/               # 核心功能
│   │   │   ├── __init__.py
│   │   │   ├── security.py
│   │   │   ├── database.py
│   │   │   └── storage.py
│   │   └── utils/              # 工具函数
│   │       ├── __init__.py
│   │       └── helpers.py
│   ├── tests/                  # 测试
│   │   ├── __init__.py
│   │   ├── test_api/
│   │   ├── test_engines/
│   │   └── test_services/
│   ├── alembic/                # 数据库迁移
│   │   ├── versions/
│   │   └── env.py
│   ├── requirements.txt        # 依赖列表
│   ├── pyproject.toml          # 项目配置
│   └── .env.example            # 环境变量示例
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/           # API 调用
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yml          # Docker 编排
```

### Python 依赖 (requirements.txt)

```txt
# Web 框架
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12

# 数据库
sqlalchemy==2.0.36
alembic==1.14.0
psycopg2-binary==2.9.10
asyncpg==0.30.0

# 认证
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# HTTP 客户端
httpx==0.28.1
aiohttp==3.11.10

# 数据验证与统计
pydantic==2.10.3
pydantic-settings==2.6.1
email-validator==2.2.0
pandas==2.2.3
numpy==2.2.1

# 文件解析
pypdf==5.1.0
python-pptx==1.0.2
pillow==11.0.0

# 对象存储
minio==7.2.11
boto3==1.35.90

# 缓存/异步 (可选)
redis==5.2.1
hiredis==3.1.0
celery==5.4.0

# 工具
python-dotenv==1.0.1
loguru==0.7.3
```

---

## 10. 环境变量

```env
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/wage_adjust
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# JWT 认证
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 对象存储 (MinIO/S3)
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=your_access_key
STORAGE_SECRET_KEY=your_secret_key
STORAGE_BUCKET_NAME=wage-adjust-files

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_API_BASE_URL=https://api.deepseek.com/v1

# 应用配置
APP_NAME=公司综合调薪工具
APP_VERSION=1.0.0
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# Redis (可选 - 用于缓存、任务队列和会话)
REDIS_URL=redis://localhost:6379/0

# 对外开放 API
PUBLIC_API_KEY=your_public_api_key
PUBLIC_API_RATE_LIMIT=1000/hour

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 11. 核心功能特性
### 11.1 智能材料解析
- 支持员工上传 PPT、图片、代码、PDF、表格、文本等多种成果材料
- 自动提取材料正文、备注、元信息和关键片段
- 预留 OCR、代码仓库分析、截图理解等扩展能力
- 支持解析失败重试和异常文件提示

### 11.2 可解释的 AI 能力评级
- 基于五维评估模型进行加权评分
- 将综合得分映射为 Level1-Level5
- 输出维度得分、命中证据、理由和置信度
- 对低置信度结果自动进入人工复核流程

### 11.3 差异化调薪引擎
- 根据 AI 等级映射调薪系数区间
- 支持成长认证加成、岗位差异化系数、关键岗位策略
- 支持预算校验、公平性校验和调薪解释生成
- 区分系统建议值和最终审批值

### 11.4 校准与审批机制
- 支持主管复核、HRBP 审批、薪酬委员会审批
- 支持横向校准会模式，对比同岗同级员工结果
- 保留人工覆写记录和审批链路审计日志
- 支持驳回、补充材料和重新评级

### 11.5 批量导入与组织看板
- 支持批量导入员工、业务指标、认证记录和历史评估
- 提供错误回传、幂等处理和结果导出
- 看板展示能力分布、预算执行、认证进度、ROI 和高潜人才
- 支持按周期、部门、岗位族、职级筛选

### 11.6 对外输出与平台治理
- 提供标准 REST API 供 HR/绩效/薪酬系统调用
- 支持 API Key 鉴权、分页和增量同步
- 支持权限隔离、敏感字段保护和审计追踪
- 为后续规则沙盒、模型版本管理和多租户预留扩展空间

---

## 12. 数据统计指标

### 用户维度
- 员工 AI 等级分布
- 认证通过率
- 人工复核率
- 高潜人才数量

### 调薪维度
- 建议调薪总额
- 已审批金额
- 预算使用率
- 超预算风险数量

### 组织维度
- 部门能力热力图
- 岗位族能力对比
- ROI 成果转化总额
- 不同等级人数分布

---

## 13. 未来扩展方向

1. **组织校准会增强**
   - 同岗同级横向比对
   - 评分偏差分析
   - 校准结论沉淀

2. **真实性与合规评估**
   - 材料异常检测
   - 重复证据识别
   - AI 使用合规评分

3. **人才发展闭环**
   - 个性化学习路径推荐
   - 认证任务自动生成
   - 晋升与调薪联动建议

4. **规则沙盒与策略回放**
   - 历史数据回放
   - 权重与阈值试验
   - 薪酬策略对比分析

5. **平台产品化**
   - 多租户支持
   - 多语言界面
   - 更多外部系统适配器
