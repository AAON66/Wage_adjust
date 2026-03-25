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

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Project: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)**
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Summary
## Languages
- Python 3.x (implied by `from __future__ import annotations` and `match` style patterns) - Backend API, engines, parsers, services
- TypeScript 5.8.3 - Frontend React application (`frontend/tsconfig.json` targets ES2020)
- HTML/CSS - Frontend markup and Tailwind utility classes
## Runtime
- Python virtual environment (`.venv/`)
- ASGI server: `uvicorn[standard]` 0.32.0
- Start command: `uvicorn backend.app.main:app --reload`
- Node.js (version not pinned; no `.nvmrc` found)
- Dev server: Vite 6.2.6 on `127.0.0.1:5174`
- Preview server on port `4174`
- Backend: `pip` with `requirements.txt`
- Frontend: `npm` with `package-lock.json` (lockfile present)
## Frameworks
- FastAPI 0.115.0 - REST API framework; versioned under `/api/v1`
- Pydantic 2.10.3 - Data validation and serialization for all schemas
- pydantic-settings 2.6.1 - Settings loaded from `.env` via `backend/app/core/config.py`
- SQLAlchemy 2.0.36 - ORM with `DeclarativeBase`; synchronous sessions
- Alembic 1.14.0 - Database migrations; config at `alembic.ini`
- React 18.3.1 - UI framework
- React Router DOM 7.6.0 - Client-side routing
- Axios 1.8.4 - HTTP client with JWT interceptors (`frontend/src/services/api.ts`)
- Vite 6.2.6 with `@vitejs/plugin-react` 4.4.1 - Dev server and bundler (`frontend/vite.config.ts`)
- TypeScript compiler - `tsc -b && vite build` for production builds
- Tailwind CSS 3.4.17 - Utility-first CSS (`frontend/tailwind.config.js`)
- PostCSS 8.5.3 with Autoprefixer 10.4.21 (`frontend/postcss.config.js`)
- pytest 8.3.5 - Backend test runner; tests organized under `backend/tests/`
## Key Dependencies
- httpx 0.28.1 - Synchronous HTTP client used exclusively for DeepSeek API calls (`backend/app/services/llm_service.py`)
- aiohttp 3.11.10 - Async HTTP client (present in requirements; available for future async LLM paths)
- python-jose[cryptography] 3.3.0 - JWT encoding/decoding (`backend/app/core/security.py`)
- passlib[bcrypt] 1.7.4 - Password hashing; configured with `pbkdf2_sha256` scheme
- pypdf 5.1.0 - PDF text extraction (`backend/app/parsers/document_parser.py`)
- python-pptx 1.0.2 - PowerPoint slide text extraction (`backend/app/parsers/ppt_parser.py`)
- Pillow 11.0.0 - Image metadata (PNG/JPG); OCR noted as reserved for later task (`backend/app/parsers/image_parser.py`)
- pandas 2.2.3 - DataFrame operations for bulk import
- numpy 2.2.1 - Numerical support for pandas
- email-validator 2.2.0 - Email field validation in Pydantic schemas
- python-multipart 0.0.12 - Multipart file upload support in FastAPI
- minio 7.2.11 - MinIO/S3 object storage SDK (declared but current `LocalStorageService` uses local filesystem)
- boto3 1.35.90 - AWS S3 SDK (declared; not actively wired in current storage layer)
- celery 5.4.0 - Async task queue
- redis 5.2.1 + hiredis 3.1.0 - Redis broker/backend for Celery
- python-dotenv 1.0.1 - `.env` file loading
- loguru 0.7.3 - Declared logging library; active logging uses stdlib `logging` via `dictConfig` (`backend/app/core/logging.py`)
## Configuration
- All settings in `backend/app/core/config.py` via `pydantic_settings.BaseSettings`
- Reads from `.env` file in project root; falls back to defaults
- `.env.example` documents all required variables
- Settings accessed via `get_settings()` (LRU-cached) and injected with FastAPI `Depends`
- SQLite: `sqlite+pysqlite:///./wage_adjust.db`
- File `wage_adjust.db` exists in project root
- PostgreSQL; drivers `psycopg2-binary` 2.9.10 and `asyncpg` 0.30.0 are installed
- `.env.example` shows `DATABASE_URL=postgresql://user:password@localhost:5432/wage_adjust`
- API base URL configured via `VITE_API_BASE_URL` env var; defaults to `http://127.0.0.1:8011/api/v1`
- No `.env` file detected in `frontend/`
## Build Scripts
- `start_backend_local.cmd` - Windows batch file
- `start_project_local.cmd` - Windows batch file
- `start_project_local.ps1` - PowerShell script
- `scripts/start_backend.ps1` - PowerShell for backend only
- `scripts/start_frontend.ps1` - PowerShell for frontend only
## Platform Requirements
- Windows (primary; all startup scripts are `.cmd`/`.ps1`)
- Python virtual environment in `.venv/`
- SQLite available by default (no external DB needed in dev)
- Local `uploads/` directory for file storage
- PostgreSQL database
- Redis for Celery task queue
- MinIO or S3-compatible object storage
- All configuration via environment variables
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Summary
## Naming Patterns
- `snake_case` for all module names: `evaluation_service.py`, `salary_engine.py`, `access_scope_service.py`
- Suffixes signal role: `_service.py`, `_engine.py`, `_parser.py`, `_schema.py` (but schemas dir uses singular: `evaluation.py`)
- `PascalCase` for component files: `FileUploadPanel.tsx`, `BudgetSimulationPanel.tsx`
- `camelCase` for non-component modules: `evaluationService.ts`, `api.ts`, `useAuth.tsx`
- Hook files use `use` prefix: `useAuth.tsx`
- `PascalCase` for all: `EvaluationService`, `SalaryEngine`, `DepartmentProfile`, `UUIDPrimaryKeyMixin`
- Models inherit from mixins first, then `Base`: `class Employee(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base)`
- `snake_case` everywhere
- Private helpers prefixed with `_`: `_build_integrity_summary`, `_query_evaluation`
- Keyword-only arguments enforced with `*` for construction helpers: `build_error_response(*, status_code, error, message, details=None)`
- `PascalCase` for interfaces: `UserProfile`, `AuthContextValue`, `BudgetSimulationPanelProps`
- Props interfaces named `[ComponentName]Props`: `FileUploadPanelProps`, `BudgetSimulationPanelProps`
- Union types with `as const` for enums: `'collecting' | 'submitted' | 'parsing' | ...`
- `camelCase` for local variables and functions: `refreshInFlight`, `handleLogin`, `isBootstrapping`
- `SCREAMING_SNAKE_CASE` for module-level constants: `ACCESS_TOKEN_KEY`, `REFRESH_TOKEN_KEY`, `LONG_RUNNING_TIMEOUT`
## Code Style
- No Prettier config found in project. Code uses consistent 2-space indentation in TSX and consistent 4-space in Python.
- TypeScript: single quotes in type annotations, double quotes for JSX string attributes.
- Python: single quotes for strings throughout backend code.
- TypeScript: `tsc --noEmit` is the lint command (`"lint": "tsc --noEmit"` in `frontend/package.json`). No ESLint config detected.
- Python: No `pyproject.toml`, `setup.cfg`, or `ruff.toml` found in project root. Two `# noqa: ANN001, ANN201` suppressions present in test stubs where untyped signatures are intentional.
- `tsconfig.json` has `"strict": true`, `"allowJs": false`, `"noEmit": true`.
- Target: `ES2020`, module resolution: `Bundler`.
## Import Organization
- All files begin with `from __future__ import annotations` — mandatory across all backend modules.
- Standard library imports come first, then third-party, then local `backend.app.*` imports. Not enforced by tooling but maintained consistently.
- Example pattern from `backend/app/main.py`:
- Third-party imports first, then relative imports, then type-only imports last.
- Type imports use `import type { ... }` when the symbol is type-only.
- Example from `frontend/src/pages/EvaluationDetail.tsx`:
- No path aliases configured. All imports use relative paths (`../components/...`, `../services/...`).
## TypeScript/Python Type Usage
- Full explicit typing on all function parameters and return types in service layer.
- `interface` preferred over `type` for object shapes.
- Discriminated union types used for status flows: `type BatchParseItemStatus = 'queued' | 'parsing' | 'parsed' | 'failed'`
- `as const` arrays for immutable flow steps: `const FLOW = ['collecting', 'submitted', ...] as const`
- Optional props with `?:` and defaults in destructuring: `{ isGithubImporting = false, isUploading, ... }`
- Nullable types with `| null`: `user: UserProfile | null`, `manager_id: string | null`
- Full PEP 604 union syntax: `str | None`, `Settings | None` (enabled by `from __future__ import annotations`)
- `Mapped[T]` for SQLAlchemy columns: `employee_no: Mapped[str] = mapped_column(...)`
- `Mapped[str | None]` for nullable columns
- Pydantic `BaseModel` for all request/response schemas with `ConfigDict(from_attributes=True)` for ORM serialization
- `pydantic_settings.BaseSettings` for config with `SettingsConfigDict`
- `dataclass(frozen=True)` for engine-internal value objects: `DimensionDefinition`, `DepartmentProfile`
- Return type annotations on all service methods: `def get_evaluation(self, ...) -> AIEvaluation | None:`
- `Callable`, `Generator`, `Mapping` from `collections.abc` / `typing`
## Component Patterns (React)
- Context defined in hook file: `const AuthContext = createContext<AuthContextValue | null>(null)`
- Provider exported: `export function AuthProvider({ children }: { children: ReactNode })`
- Consumer hook exported with guard: `export function useAuth()` — throws if used outside provider
## Error Handling
- `HTTPException` → `build_error_response(status_code, error='http_error', message=...)`
- `RequestValidationError` → 422 with structured `details`
- Bare `Exception` → 500 with `logger.exception(...)` + safe generic message
- Services raise `HTTPException` directly when not found or forbidden: `raise HTTPException(status_code=404, detail='...')`
- Access control raises `PermissionError` at service level, caught and re-raised as HTTP 403 in routers
- `from exc` used consistently on re-raises to preserve traceback
- No try/catch in service modules — errors propagate as rejected promises to pages/components
- Axios interceptor handles 401 globally: attempts token refresh, clears session on failure
- Pages handle errors locally with `axios.isAxiosError(err)` checks and local error state
## Logging
## Comments and Documentation Style
- Single-line `"""..."""` docstrings on classes and utility functions only:
- Service methods and API endpoints are typically undocumented (no docstring)
- Inline comments used sparingly to explain non-obvious logic
- No JSDoc found. Comments are rare and only for non-obvious code.
- Type declarations serve as self-documentation.
## Module Design
- All collaborators optional with sensible defaults — enables easy test injection without mocking frameworks.
- One file per domain: `evaluation.py`, `salary.py`, `employee.py`
- Pydantic models for request (`...Request`), response (`...Read`, `...Response`), and update (`...UpdateRequest`) shapes
- One file per domain: `evaluationService.ts`, `salaryService.ts`, `employeeService.ts`
- Each exports plain async functions (not classes) that call `api` (the shared axios instance)
- Long-running AI calls override timeout: `{ timeout: LONG_RUNNING_TIMEOUT }` (120000ms)
- Single file for all API-facing types
- All types are `interface` definitions
## SQLAlchemy Model Design
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Summary
## Pattern Overview
- Backend enforces a strict dependency direction: `api/` → `services/` → `engines/` → `models/`
- Services are injected with a `Session` and optional engine/LLM dependencies for testability
- All models share common UUID primary keys and timestamp mixins
- Frontend mirrors the backend's domain model with a dedicated `services/` layer wrapping all HTTP calls, a `types/api.ts` shared contract, and a `hooks/useAuth.tsx` Context for session state
- Role-based access control is enforced on both sides: `require_roles()` factory in `backend/app/dependencies.py` and `ProtectedRoute` + `roleAccess.ts` in the frontend
## Layers
- Purpose: Route HTTP requests to services, validate inputs via Pydantic schemas, enforce auth
- Location: `backend/app/api/v1/`
- Contains: One file per domain (`approvals.py`, `evaluations.py`, `salary.py`, etc.)
- Depends on: `services/`, `schemas/`, `dependencies.py`
- Used by: Frontend via Axios, external systems via public API
- Purpose: Implement business logic, orchestrate DB access, call engines and LLM
- Location: `backend/app/services/`
- Contains: `EvaluationService`, `SalaryService`, `ApprovalService`, `ImportService`, `LlmService`, `ParseService`, `AccessScopeService`, `DashboardService`, `IntegrationService`, and others
- Depends on: `engines/`, `models/`, `parsers/`, `core/`
- Used by: `api/v1/` routers
- Purpose: Pure computation — no I/O, no DB access
- Location: `backend/app/engines/`
- Contains: `EvaluationEngine` (five-dimension weighted scoring, AI level mapping), `SalaryEngine` (multiplier calculation with job level / department / job family adjustments)
- Depends on: `models/evidence.py` value types, `utils/prompt_safety.py`
- Used by: `EvaluationService`, `SalaryService`
- Purpose: ORM entity definitions
- Location: `backend/app/models/`
- Contains: SQLAlchemy declarative models with UUID PKs and timestamp mixins from `backend/app/models/mixins.py`
- Depends on: `backend/app/core/database.py` (`Base`)
- Used by: All services and API layers
- Purpose: Extract text and metadata from uploaded files (PPT, PDF, images, code, documents)
- Location: `backend/app/parsers/`
- Contains: `BaseParser` (abstract), `PptParser`, `ImageParser`, `DocumentParser`, `CodeParser`
- Depends on: File system only (no DB)
- Used by: `ParseService`
- Purpose: Cross-cutting configuration, database, security, logging, storage
- Location: `backend/app/core/`
- Contains: `config.py` (pydantic-settings `Settings`), `database.py` (SQLAlchemy engine + session factory + `Base`), `security.py` (JWT + bcrypt), `logging.py`, `storage.py`
- Depends on: Nothing within the app
- Used by: All other layers
- Purpose: Wrap API calls, expose typed async functions to pages and components
- Location: `frontend/src/services/`
- Contains: `api.ts` (Axios instance with JWT interceptor + silent token refresh), plus one file per domain (`evaluationService.ts`, `salaryService.ts`, `approvalService.ts`, etc.)
- Depends on: `types/api.ts`
- Used by: Pages and hooks
## Data Flow
- Server state is managed by direct fetch calls in page-level `useEffect` hooks; no global state cache library (no React Query / SWR / Redux)
- Auth state is global via `AuthContext` (`frontend/src/hooks/useAuth.tsx`)
- UI state is local component `useState`
## Key Abstractions
- Purpose: Central evaluation record linking submission → dimension scores → salary recommendation
- Tracks both `ai_overall_score` (raw LLM output) and `overall_score` (final after manager calibration)
- Status progression: `draft` → `confirmed` → (terminated by approval flow)
- Purpose: One record per employee per evaluation cycle; anchor for files, evidence, and evaluations
- Unique constraint on `(employee_id, cycle_id)` enforces one submission per cycle
- Purpose: Stores computed salary figures and deferred adjustment metadata
- Linked 1:1 to `AIEvaluation`; drives approval workflow
- Purpose: One row per approval step per recommendation
- `step_order` field enables ordered multi-step routing; unique constraint on `(recommendation_id, step_name)` prevents duplicates
- Purpose: Centralized permission gate
- Admins see all; HRBP/managers see only their department employees; employees see only themselves
- All protected resource endpoints call `AccessScopeService.ensure_*_access()` before serving data
- Purpose: Encapsulates all LLM calls (evidence extraction, evaluation scoring)
- Includes `InMemoryRateLimiter` with configurable RPM window
- `DeepSeekPromptLibrary` builds all system/user messages; prompts include explicit injection-resistance instructions
- Purpose: Stateless, I/O-free computation of weighted dimension scores and AI level
- Department-specific `DepartmentProfile` definitions allow per-profile keyword and weight customization
- `DEPARTMENT_DIMENSION_EXAMPLES` provides behavioral anchors used in LLM prompts
- Purpose: Deterministic salary calculation from AI level + employee attributes
- All lookup tables (`LEVEL_RULES`, `JOB_LEVEL_ADJUSTMENTS`, etc.) are constants in the file; intended for future externalization to config
## Entry Points
- Location: `backend/app/main.py`
- Start: `uvicorn backend.app.main:app --reload`
- `create_app()` factory registers middlewares, exception handlers, and routes
- `lifespan()` context manager runs `init_database()` on startup (creates tables + runs `ensure_schema_compatibility` migration shim)
- Location: `frontend/src/main.tsx`
- Start: `npm run dev` (Vite dev server, default port 5173)
- Mounts `<BrowserRouter><App /></BrowserRouter>` into `#root`
- `App.tsx` owns all route definitions and the `AuthProvider` wrapper
## Error Handling
- `HTTPException` → normalized `{error, message}` JSON response
- `RequestValidationError` → 422 with `{error: "validation_error", message, details: [...]}` from Pydantic
- Unhandled `Exception` → 500 with opaque message + server-side `logger.exception()` for full traceback
- Services raise `HTTPException` directly when business logic fails (e.g., record not found)
- `AccessScopeService` raises `PermissionError` which API layer catches and converts to 403
## Cross-Cutting Concerns
- Backend: JWT (HS256) via `python-jose`; access token (30 min) + refresh token (7 days); `oauth2_scheme` + `get_current_user` dependency chain
- Public API: static API key via `X-API-Key` header; separate `require_public_api_key` dependency at `backend/app/api/v1/public.py`
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
