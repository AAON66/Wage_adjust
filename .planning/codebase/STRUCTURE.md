# Codebase Structure

**Analysis Date:** 2026-03-25

## Summary

The project is a monorepo with a Python/FastAPI backend and a React/TypeScript/Vite frontend in separate top-level directories. Both sides are self-contained with their own dependency manifests. Configuration files live at the project root. The database file (`wage_adjust.db`) is stored at the root during development.

---

## Directory Layout

```
D:/wage_adjust/
├── backend/                    # FastAPI Python application
│   ├── app/
│   │   ├── main.py             # App factory and entry point
│   │   ├── dependencies.py     # FastAPI dependency functions (auth, DB, roles)
│   │   ├── api/
│   │   │   └── v1/             # All versioned REST endpoints
│   │   │       ├── router.py   # Aggregate APIRouter
│   │   │       ├── auth.py
│   │   │       ├── approvals.py
│   │   │       ├── cycles.py
│   │   │       ├── dashboard.py
│   │   │       ├── departments.py
│   │   │       ├── employees.py
│   │   │       ├── evaluations.py
│   │   │       ├── files.py
│   │   │       ├── handbooks.py
│   │   │       ├── imports.py
│   │   │       ├── public.py   # External API (X-API-Key auth)
│   │   │       ├── salary.py
│   │   │       ├── submissions.py
│   │   │       ├── system.py
│   │   │       └── users.py
│   │   ├── core/               # Infrastructure / cross-cutting
│   │   │   ├── config.py       # pydantic-settings Settings class
│   │   │   ├── database.py     # SQLAlchemy engine, Base, session factory
│   │   │   ├── init_db.py      # Seed / init helpers
│   │   │   ├── logging.py      # Structured JSON logging configuration
│   │   │   ├── security.py     # JWT creation/verification, password hashing
│   │   │   └── storage.py      # File storage abstraction
│   │   ├── engines/            # Pure computation (no I/O)
│   │   │   ├── evaluation_engine.py   # Five-dimension scoring + AI level mapping
│   │   │   └── salary_engine.py       # Salary multiplier calculation
│   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── mixins.py       # UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin
│   │   │   ├── approval.py
│   │   │   ├── audit_log.py
│   │   │   ├── certification.py
│   │   │   ├── cycle_department_budget.py
│   │   │   ├── department.py
│   │   │   ├── dimension_score.py
│   │   │   ├── employee.py
│   │   │   ├── employee_handbook.py
│   │   │   ├── evaluation.py
│   │   │   ├── evaluation_cycle.py
│   │   │   ├── evidence.py
│   │   │   ├── import_job.py
│   │   │   ├── salary_recommendation.py
│   │   │   ├── submission.py
│   │   │   ├── uploaded_file.py
│   │   │   └── user.py
│   │   ├── parsers/            # File content extraction
│   │   │   ├── base_parser.py  # BaseParser abstract + ParsedDocument dataclass
│   │   │   ├── code_parser.py
│   │   │   ├── document_parser.py
│   │   │   ├── image_parser.py
│   │   │   └── ppt_parser.py
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   │   ├── approval.py
│   │   │   ├── cycle.py
│   │   │   ├── dashboard.py
│   │   │   ├── department.py
│   │   │   ├── employee.py
│   │   │   ├── evaluation.py
│   │   │   ├── file.py
│   │   │   ├── handbook.py
│   │   │   ├── import_job.py
│   │   │   ├── public.py
│   │   │   ├── salary.py
│   │   │   ├── submission.py
│   │   │   └── user.py
│   │   ├── services/           # Business logic
│   │   │   ├── access_scope_service.py
│   │   │   ├── approval_service.py
│   │   │   ├── cycle_service.py
│   │   │   ├── dashboard_service.py
│   │   │   ├── department_service.py
│   │   │   ├── employee_handbook_service.py
│   │   │   ├── employee_service.py
│   │   │   ├── evaluation_service.py
│   │   │   ├── evidence_service.py
│   │   │   ├── file_service.py
│   │   │   ├── identity_binding_service.py
│   │   │   ├── import_service.py
│   │   │   ├── integration_service.py  # Powers /public/ API endpoints
│   │   │   ├── llm_service.py          # DeepSeek API client + rate limiter
│   │   │   ├── parse_service.py
│   │   │   ├── salary_service.py
│   │   │   ├── submission_service.py
│   │   │   └── user_admin_service.py
│   │   └── utils/
│   │       ├── helpers.py          # UUID generation, utc_now
│   │       └── prompt_safety.py    # Prompt injection detection
│   └── tests/
│       ├── test_api/           # Integration-style API tests
│       ├── test_core/          # Config and DB tests
│       ├── test_engines/       # Engine unit tests
│       ├── test_models/        # Schema/model tests
│       ├── test_parsers/       # Parser unit tests
│       └── test_services/      # Service unit tests
├── frontend/
│   └── src/
│       ├── main.tsx            # Vite entry point
│       ├── App.tsx             # Route tree + AuthProvider
│       ├── index.css           # Global CSS (CSS variables, utility classes)
│       ├── vite-env.d.ts
│       ├── components/         # Reusable UI components, organized by domain
│       │   ├── layout/
│       │   │   └── AppShell.tsx        # Authenticated shell with sidebar nav
│       │   ├── ErrorBoundary.tsx
│       │   ├── ProtectedRoute.tsx      # Role-gated route wrapper
│       │   ├── approval/
│       │   ├── auth/
│       │   ├── cycle/
│       │   ├── dashboard/
│       │   ├── employee/
│       │   ├── evaluation/
│       │   ├── import/
│       │   ├── review/
│       │   └── salary/
│       ├── hooks/
│       │   └── useAuth.tsx     # AuthContext + AuthProvider
│       ├── pages/              # Route-level page components
│       │   ├── ApiDocs.tsx
│       │   ├── Approvals.tsx
│       │   ├── CreateCycle.tsx
│       │   ├── Dashboard.tsx
│       │   ├── EmployeeAdmin.tsx
│       │   ├── Employees.tsx
│       │   ├── EvaluationDetail.tsx
│       │   ├── ImportCenter.tsx
│       │   ├── Login.tsx
│       │   ├── MyReview.tsx
│       │   ├── Register.tsx
│       │   ├── SalarySimulator.tsx
│       │   ├── Settings.tsx
│       │   └── UserAdmin.tsx
│       ├── services/           # HTTP API clients (one file per domain)
│       │   ├── api.ts          # Axios instance + token refresh interceptor
│       │   ├── auth.ts
│       │   ├── approvalService.ts
│       │   ├── cycleService.ts
│       │   ├── dashboardService.ts
│       │   ├── employeeService.ts
│       │   ├── evaluationService.ts
│       │   ├── fileService.ts
│       │   ├── handbookService.ts
│       │   ├── importService.ts
│       │   ├── salaryService.ts
│       │   ├── submissionService.ts
│       │   └── userAdminService.ts
│       ├── types/
│       │   └── api.ts          # TypeScript interfaces mirroring backend schemas
│       └── utils/
│           ├── departmentScope.ts
│           ├── employeeIdentity.ts   # Maps User → Employee record
│           ├── password.ts
│           ├── roleAccess.ts         # Role → home path, nav modules, permission check
│           └── statusText.ts
├── alembic/                    # Alembic migration scaffolding (not actively used)
├── alembic.ini
├── scripts/                    # Developer utility scripts
├── uploads/                    # Local file storage (development)
├── wage_adjust.db              # SQLite database (development)
├── requirements.txt            # Python dependencies
├── architecture.md             # Existing architecture notes
├── CLAUDE.md                   # Project instructions for AI agents
├── task.json                   # Task tracker
├── progress.txt                # Session progress log
├── start_backend_local.cmd     # Windows convenience launcher
├── start_project_local.cmd
└── start_project_local.ps1
```

---

## Directory Purposes

**`backend/app/api/v1/`:**
- Purpose: HTTP endpoint definitions, one file per domain resource
- Each file exports a single `router = APIRouter(prefix='/<resource>', tags=['<tag>'])` instance
- All routers are registered in `backend/app/api/v1/router.py` and mounted at `settings.api_v1_prefix` (default `/api/v1`)

**`backend/app/core/`:**
- Purpose: Infrastructure that has no business logic and no dependency on models or services
- `config.py` is the single source of truth for all environment-driven settings; all other modules import from it

**`backend/app/engines/`:**
- Purpose: Deterministic, side-effect-free computation; designed to be unit-tested without a database
- Do NOT import from `services/` or `api/`

**`backend/app/models/`:**
- Purpose: SQLAlchemy declarative models; all inherit from `Base` in `backend/app/core/database.py`
- All models use `UUIDPrimaryKeyMixin` for string UUID PKs; most use `CreatedAtMixin`; mutable models add `UpdatedAtMixin`

**`backend/app/parsers/`:**
- Purpose: Isolated file parsing with no external dependencies except file system
- `BaseParser.parse(path: Path) -> ParsedDocument` is the contract all parsers implement

**`backend/app/schemas/`:**
- Purpose: Pydantic v2 models for request validation and response serialization
- `Read` schemas are returned from endpoints; `Create`/`Update` schemas accept inbound bodies

**`backend/app/services/`:**
- Purpose: All business logic and orchestration; the only layer that accesses the database and calls external services
- Each service class receives `db: Session` in `__init__`; optional dependencies (engines, LLM) can be injected for testing

**`backend/tests/`:**
- Purpose: Test suite mirroring the source layout
- `test_api/` tests use the FastAPI `TestClient`; `test_services/` and `test_engines/` use pure Python with mocks

**`frontend/src/components/`:**
- Purpose: Reusable UI pieces; organized by domain subdirectory (e.g., `evaluation/`, `salary/`)
- `layout/AppShell.tsx` is the authenticated shell used by all protected pages
- `ProtectedRoute.tsx` wraps route groups to enforce login + role checks

**`frontend/src/pages/`:**
- Purpose: One file per route; owns the page-level data fetching (`useEffect` + service calls) and layout
- Pages import domain components, call service functions, and pass data down as props

**`frontend/src/services/`:**
- Purpose: All HTTP communication; thin wrappers around the shared Axios instance in `api.ts`
- Functions are typed with interfaces from `frontend/src/types/api.ts`

**`frontend/src/types/api.ts`:**
- Purpose: Single file containing all TypeScript interfaces for API request/response payloads
- Kept in sync with backend Pydantic schemas manually

**`frontend/src/utils/`:**
- Purpose: Pure helper functions; no React imports
- `roleAccess.ts` is the authoritative frontend source for role → modules and role → home path mapping

---

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: Backend application factory; start with `uvicorn backend.app.main:app --reload`
- `frontend/src/main.tsx`: Frontend Vite entry; start with `npm run dev` from `frontend/`

**Configuration:**
- `backend/app/core/config.py`: All environment settings via `Settings` (pydantic-settings); reads from `.env`
- `frontend/vite.config.*` (not present as named file): env var `VITE_API_BASE_URL` read in `frontend/src/services/api.ts`
- `alembic.ini`: Alembic config (currently not used for active migrations)
- `requirements.txt`: Python dependency manifest

**Core Logic:**
- `backend/app/engines/evaluation_engine.py`: Five-dimension AI scoring with department profiles
- `backend/app/engines/salary_engine.py`: Salary multiplier calculation tables and logic
- `backend/app/services/llm_service.py`: DeepSeek API client, rate limiter, prompt library
- `backend/app/services/access_scope_service.py`: Central permission gate for all resource access
- `backend/app/core/database.py`: `Base`, engine, session factory, `ensure_schema_compatibility` migration shim

**Routing:**
- `backend/app/api/v1/router.py`: Registers all domain routers into `api_router`
- `frontend/src/App.tsx`: All client-side routes with `ProtectedRoute` role guards

**Auth:**
- `backend/app/core/security.py`: JWT creation/verification, password hashing
- `backend/app/dependencies.py`: `get_current_user`, `require_roles`, `get_public_api_key` FastAPI dependencies
- `frontend/src/hooks/useAuth.tsx`: `AuthProvider` + `useAuth` hook (Context-based global auth state)
- `frontend/src/services/api.ts`: Axios interceptors for token attachment and silent refresh

**Testing:**
- `backend/tests/`: All backend tests organized by layer

---

## Naming Conventions

**Backend Files:**
- Models: `snake_case.py` matching table name (e.g., `salary_recommendation.py` → `salary_recommendations` table)
- Services: `<domain>_service.py` (e.g., `evaluation_service.py`)
- API routes: `<domain>.py` (e.g., `evaluations.py`)
- Schemas: `<domain>.py` mirroring the model file name

**Frontend Files:**
- Pages: `PascalCase.tsx` (e.g., `EvaluationDetail.tsx`)
- Components: `PascalCase.tsx` in a subdirectory matching domain (e.g., `components/evaluation/EvidenceCard.tsx`)
- Services: `camelCase.ts` with `Service` suffix (e.g., `evaluationService.ts`), except `api.ts` and `auth.ts`
- Types: all in `frontend/src/types/api.ts`
- Utils: `camelCase.ts` (e.g., `roleAccess.ts`)

**Backend Classes:**
- Models: `PascalCase` matching entity concept (e.g., `AIEvaluation`, `EmployeeSubmission`)
- Services: `PascalCase` + `Service` suffix (e.g., `EvaluationService`)
- Engines: `PascalCase` + `Engine` suffix (e.g., `SalaryEngine`)
- Schemas: `PascalCase` + suffix indicating intent (`Read`, `Create`, `Update`, `Response`, `Request`)

---

## How Features Are Organized

Features follow a vertical slice that maps to a domain noun:

```
evaluation/
  backend/app/api/v1/evaluations.py       ← HTTP endpoint
  backend/app/schemas/evaluation.py       ← request/response contracts
  backend/app/services/evaluation_service.py  ← business logic
  backend/app/models/evaluation.py        ← DB entity
  backend/app/engines/evaluation_engine.py    ← pure computation
  frontend/src/pages/EvaluationDetail.tsx ← page
  frontend/src/services/evaluationService.ts  ← HTTP client
  frontend/src/components/evaluation/     ← UI components
  backend/tests/test_api/test_evaluation_api.py
  backend/tests/test_services/test_evaluation_service.py
```

Every new domain feature should follow this same vertical structure.

---

## Where to Add New Code

**New API Endpoint:**
- Add router file to `backend/app/api/v1/<domain>.py`
- Register router in `backend/app/api/v1/router.py`
- Add Pydantic schemas to `backend/app/schemas/<domain>.py`
- Add business logic to `backend/app/services/<domain>_service.py`

**New DB Model:**
- Create `backend/app/models/<domain>.py` inheriting from `Base` with `UUIDPrimaryKeyMixin`
- Import model in `backend/app/models/__init__.py` so it's registered before `Base.metadata.create_all()`

**New Frontend Page:**
- Create `frontend/src/pages/<PageName>.tsx`
- Add `Route` entry in `frontend/src/App.tsx`, wrapped in `ProtectedRoute` with correct `allowedRoles`
- Add link to relevant `ROLE_MODULES` entry in `frontend/src/utils/roleAccess.ts`

**New Frontend Component:**
- Create `frontend/src/components/<domain>/<ComponentName>.tsx`

**New API Client Function:**
- Add to the matching `frontend/src/services/<domain>Service.ts`
- Add TypeScript interface to `frontend/src/types/api.ts`

**New Utility:**
- Pure backend helpers: `backend/app/utils/helpers.py`
- Pure frontend helpers: `frontend/src/utils/<name>.ts`

**New Parser:**
- Extend `BaseParser` in `backend/app/parsers/<type>_parser.py`
- Register it in `ParseService` so it is selected by file extension

---

## Special Directories

**`uploads/`:**
- Purpose: Local development file storage for uploaded employee materials
- Generated: Yes (at runtime)
- Committed: No (should be in `.gitignore`)

**`.tmp/`:**
- Purpose: Temporary upload staging and pytest temp files
- Generated: Yes (by backend and test runner)
- Committed: No

**`alembic/`:**
- Purpose: Alembic migration scaffolding
- Generated: Partially (versions/ would contain migration scripts)
- Currently active: No; schema changes are handled by `ensure_schema_compatibility()` in `backend/app/core/database.py`

**`.planning/`:**
- Purpose: Agent planning documents, codebase analysis, and task context
- Committed: Yes

**`.claude/`:**
- Purpose: Claude Code agent configurations, commands, and MCP tooling
- Committed: Partially

---

*Structure analysis: 2026-03-25*
