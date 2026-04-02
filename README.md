# Wage Adjust Platform

企业内部评估与调薪运营平台。系统围绕“材料采集 -> 证据抽取 -> AI 评估 -> 调薪建议 -> 审批发布 -> 看板分析 -> 对外输出”构建完整闭环，当前仓库已包含前后端、数据库迁移、测试、导入导出、公共 API、飞书考勤同步和审计能力。

## 当前实现

- 员工、部门、评估周期、账号与权限管理
- 员工材料上传、解析、证据抽取与结构化展示
- 五维 AI 能力评分、等级映射、人工复核与校准
- 调薪建议生成、预算模拟、多级审批与结果追踪
- 组织看板、审批状态、部门洞察与分布分析
- 批量导入员工与认证信息，支持模板下载与结果导出
- 公共只读 API、API Key 管理、Webhook、审计日志
- 飞书考勤配置、手动同步、定时同步与同步日志

## 技术栈

### 后端

- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- Redis + SlowAPI
- APScheduler
- pandas / numpy
- pypdf / python-pptx / Pillow / openpyxl

### 前端

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios
- ECharts

### 数据与集成

- 本地开发默认 SQLite
- 生产配置面向 PostgreSQL
- 本地文件存储默认使用 `uploads/`
- 支持 DeepSeek 模型调用
- 支持飞书考勤同步

## 核心业务流程

1. 管理员创建评估周期并配置预算。
2. 导入员工基础信息、认证信息和组织结构。
3. 员工提交自评与成果材料，系统解析文件并抽取证据。
4. 评估引擎结合规则与 LLM 结果生成五维评分和 AI 等级。
5. 主管或 HRBP 可人工复核、调整分数并确认评估结果。
6. 调薪引擎根据等级、认证、预算等因素生成调薪建议。
7. 建议进入审批流，最终进入发布与看板分析。
8. 外部系统可通过只读公共 API 拉取结果。

## 角色与权限

- `admin`：系统配置、周期管理、预算、导入、账号、API Key、Webhook、审计
- `hrbp`：评估复核、审批推进、导入中心、看板、飞书同步查看与触发
- `manager`：团队评估查看、复核、审批、个人工作区
- `employee`：个人评估记录、材料、个人设置

默认配置下 `ALLOW_SELF_REGISTRATION=false`，实际使用更偏向管理员统一创建账号。

## 目录结构

```text
.
├── backend/                  # FastAPI 应用、模型、服务、测试
│   ├── app/
│   │   ├── api/v1/           # REST API
│   │   ├── core/             # 配置、数据库、安全、存储、日志
│   │   ├── engines/          # 评估与调薪规则引擎
│   │   ├── middleware/
│   │   ├── models/
│   │   ├── scheduler/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
├── frontend/                 # React + Vite 前端
├── alembic/                  # 数据库迁移
├── scripts/                  # 本地启动与演示数据脚本
├── uploads/                  # 本地文件存储目录
├── architecture.md           # 架构设计文档
├── DEPLOYMENT.md             # 部署说明
└── task.json                 # 任务完成记录
```

## 主要页面

- `/`
- `/login`
- `/workspace`
- `/employees`
- `/employees/:employeeId`
- `/cycles/create`
- `/salary-simulator`
- `/approvals`
- `/dashboard`
- `/import-center`
- `/attendance`
- `/api-key-management`
- `/webhook-management`
- `/audit-log`
- `/settings`

## 主要后端接口

- `/health`
- `/api/v1/system/meta`
- `/api/v1/auth/*`
- `/api/v1/users/*`
- `/api/v1/departments/*`
- `/api/v1/employees/*`
- `/api/v1/cycles/*`
- `/api/v1/submissions/*`
- `/api/v1/files/*`
- `/api/v1/evaluations/*`
- `/api/v1/salary/*`
- `/api/v1/approvals/*`
- `/api/v1/dashboard/*`
- `/api/v1/imports/*`
- `/api/v1/public/*`
- `/api/v1/feishu/*`
- `/api/v1/attendance/*`
- `/api/v1/api-keys/*`
- `/api/v1/webhooks/*`

## 本地开发环境

推荐版本：

- Python 3.11+
- Node.js 18+
- npm 9+
- Redis 7+（推荐）

## 快速开始

### 1. 安装后端依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
npm install --prefix frontend
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，至少关注以下字段：

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `PUBLIC_API_KEY`
- `BACKEND_CORS_ORIGINS`
- `REDIS_URL`
- `DEEPSEEK_API_KEY`
- `NATIONAL_ID_ENCRYPTION_KEY`

说明：

- 本地默认推荐直接使用 SQLite，例如 `sqlite+pysqlite:///./wage_adjust.db`
- 生产环境应改为 PostgreSQL
- 若 `DEEPSEEK_API_KEY` 未配置，系统会退回本地兜底逻辑
- 生产环境启动前必须替换默认的 `JWT_SECRET_KEY` 和 `PUBLIC_API_KEY`

### 4. 初始化数据库

```bash
source .venv/bin/activate
python -m alembic upgrade head
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### 5. 启动后端

macOS / Linux:

```bash
source .venv/bin/activate
PYTHONPATH=$(pwd) python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8011
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1
```

### 6. 启动前端

```bash
npm run dev --prefix frontend -- --host 127.0.0.1 --port 5174
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_frontend.ps1
```

### 7. 访问地址

- 前端：`http://127.0.0.1:5174`
- 后端健康检查：`http://127.0.0.1:8011/health`
- 后端 API 前缀：`http://127.0.0.1:8011/api/v1`

前端默认请求地址来自 `VITE_API_BASE_URL`，未配置时使用 `http://127.0.0.1:8011/api/v1`。

## 演示数据

仓库内提供中文演示数据重置脚本：

```bash
source .venv/bin/activate
PYTHONPATH=$(pwd) python scripts/reset_cn_demo_data.py
```

它会重建一套本地演示数据，包括员工、周期、评估、调薪、审批和示例材料文件。

## 测试与构建

### 后端测试

```bash
source .venv/bin/activate
pytest backend/tests -q -p no:cacheprovider
```

### 前端类型检查 / 构建

```bash
npm run lint --prefix frontend
npm run build --prefix frontend
```

## 当前实现说明

- 当前仓库已经包含较完整的业务链路，不再是原型或纯界面工程。
- `xlsx` 模板生成与导入依赖 `openpyxl`，当前依赖中已包含该库。
- 本地开发默认使用 `LocalStorageService`，上传文件保存在 `uploads/`。
- Redis 在开发环境不可用时，部分限流能力会降级；生产环境下会进行更严格的启动校验。
- 公共 API 为只读接口，使用 `X-API-Key` 鉴权，并写入审计日志。
- 飞书同步支持配置保存、手动触发、定时任务重载和同步日志查看。

## 常用文档

- [架构设计](./architecture.md)
- [部署说明](./DEPLOYMENT.md)
- [外部 API 对接文档](./docs/外部API对接文档.md)
- [任务完成记录](./task.json)

## 生产部署提示

部署前至少应完成以下事项：

- 将 `DATABASE_URL` 切换为 PostgreSQL
- 配置强随机的 `JWT_SECRET_KEY`
- 配置强随机的 `PUBLIC_API_KEY`
- 配置真实的 `BACKEND_CORS_ORIGINS`
- 配置可用的 Redis
- 配置 `NATIONAL_ID_ENCRYPTION_KEY`
- 根据需要接入真实对象存储或继续使用本地存储
- 为后端和静态前端配置反向代理、HTTPS 和监控

更详细的部署信息见 [DEPLOYMENT.md](./DEPLOYMENT.md)。
