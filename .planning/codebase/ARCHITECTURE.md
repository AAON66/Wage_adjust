# Architecture

**Analysis Date:** 2026-03-25

## Summary

Wage Adjust Platform is a layered, monorepo-style full-stack application. The backend is a FastAPI service organized into strict horizontal layers (API → Services → Engines → Models). The frontend is a React SPA using React Router v6 for client-side routing. The two tiers communicate exclusively via versioned REST API at `/api/v1/`. A separate public API surface at `/api/v1/public/` provides key-authenticated read access for external HR system integration.

---

## Pattern Overview

**Overall:** Layered architecture (Presentation → Application → Domain → Data)

**Key Characteristics:**
- Backend enforces a strict dependency direction: `api/` → `services/` → `engines/` → `models/`
- Services are injected with a `Session` and optional engine/LLM dependencies for testability
- All models share common UUID primary keys and timestamp mixins
- Frontend mirrors the backend's domain model with a dedicated `services/` layer wrapping all HTTP calls, a `types/api.ts` shared contract, and a `hooks/useAuth.tsx` Context for session state
- Role-based access control is enforced on both sides: `require_roles()` factory in `backend/app/dependencies.py` and `ProtectedRoute` + `roleAccess.ts` in the frontend

---

## Layers

**API Layer:**
- Purpose: Route HTTP requests to services, validate inputs via Pydantic schemas, enforce auth
- Location: `backend/app/api/v1/`
- Contains: One file per domain (`approvals.py`, `evaluations.py`, `salary.py`, etc.)
- Depends on: `services/`, `schemas/`, `dependencies.py`
- Used by: Frontend via Axios, external systems via public API

**Service Layer:**
- Purpose: Implement business logic, orchestrate DB access, call engines and LLM
- Location: `backend/app/services/`
- Contains: `EvaluationService`, `SalaryService`, `ApprovalService`, `ImportService`, `LlmService`, `ParseService`, `AccessScopeService`, `DashboardService`, `IntegrationService`, and others
- Depends on: `engines/`, `models/`, `parsers/`, `core/`
- Used by: `api/v1/` routers

**Engine Layer:**
- Purpose: Pure computation — no I/O, no DB access
- Location: `backend/app/engines/`
- Contains: `EvaluationEngine` (five-dimension weighted scoring, AI level mapping), `SalaryEngine` (multiplier calculation with job level / department / job family adjustments)
- Depends on: `models/evidence.py` value types, `utils/prompt_safety.py`
- Used by: `EvaluationService`, `SalaryService`

**Model Layer:**
- Purpose: ORM entity definitions
- Location: `backend/app/models/`
- Contains: SQLAlchemy declarative models with UUID PKs and timestamp mixins from `backend/app/models/mixins.py`
- Depends on: `backend/app/core/database.py` (`Base`)
- Used by: All services and API layers

**Parser Layer:**
- Purpose: Extract text and metadata from uploaded files (PPT, PDF, images, code, documents)
- Location: `backend/app/parsers/`
- Contains: `BaseParser` (abstract), `PptParser`, `ImageParser`, `DocumentParser`, `CodeParser`
- Depends on: File system only (no DB)
- Used by: `ParseService`

**Core Infrastructure:**
- Purpose: Cross-cutting configuration, database, security, logging, storage
- Location: `backend/app/core/`
- Contains: `config.py` (pydantic-settings `Settings`), `database.py` (SQLAlchemy engine + session factory + `Base`), `security.py` (JWT + bcrypt), `logging.py`, `storage.py`
- Depends on: Nothing within the app
- Used by: All other layers

**Frontend Service Layer:**
- Purpose: Wrap API calls, expose typed async functions to pages and components
- Location: `frontend/src/services/`
- Contains: `api.ts` (Axios instance with JWT interceptor + silent token refresh), plus one file per domain (`evaluationService.ts`, `salaryService.ts`, `approvalService.ts`, etc.)
- Depends on: `types/api.ts`
- Used by: Pages and hooks

---

## Data Flow

**Employee Evaluation Flow:**

1. User uploads files via `POST /api/v1/files/` → `FileService` stores to local `uploads/` directory (or configured S3/MinIO)
2. `POST /api/v1/submissions/{id}/parse` → `ParseService` selects parser by extension, produces `ParsedDocument`
3. `ParseService` calls `DeepSeekService.extract_evidence()` → LLM returns structured JSON → persisted as `EvidenceItem` rows
4. `POST /api/v1/evaluations/generate` → `EvaluationService.generate_evaluation()` calls `DeepSeekService.run_evaluation()` → LLM returns five-dimension raw scores
5. `EvaluationEngine` maps raw scores to weighted `overall_score` and AI level string (`Level 1`–`Level 5`)
6. `AIEvaluation` record persisted with `status="draft"`
7. HR/manager reviews and optionally overrides via `PATCH /api/v1/evaluations/{id}/review`

**Salary Recommendation Flow:**

1. Triggered after evaluation reaches `confirmed` status
2. `SalaryService` fetches `AIEvaluation` + employee attributes (job level, department, job family)
3. `SalaryEngine.calculate()` applies `LEVEL_RULES`, `JOB_LEVEL_ADJUSTMENTS`, `DEPARTMENT_ADJUSTMENTS`, `JOB_FAMILY_ADJUSTMENTS` from `backend/app/engines/salary_engine.py`
4. `SalaryRecommendation` persisted with `status="draft"`
5. Approval records created via `ApprovalService` → multi-step flow (`pending_approval` → `approved`/`rejected`)

**Auth Flow:**

1. `POST /api/v1/auth/login` returns `{access_token, refresh_token}`
2. `frontend/src/services/api.ts` attaches `Bearer` token via request interceptor
3. On 401, interceptor deduplicates in-flight refresh requests and retries with new token
4. `useAuth` context bootstraps session on mount by verifying stored token via `GET /api/v1/auth/me`, falling back to refresh

**State Management:**
- Server state is managed by direct fetch calls in page-level `useEffect` hooks; no global state cache library (no React Query / SWR / Redux)
- Auth state is global via `AuthContext` (`frontend/src/hooks/useAuth.tsx`)
- UI state is local component `useState`

---

## Key Abstractions

**`AIEvaluation` (backend/app/models/evaluation.py):**
- Purpose: Central evaluation record linking submission → dimension scores → salary recommendation
- Tracks both `ai_overall_score` (raw LLM output) and `overall_score` (final after manager calibration)
- Status progression: `draft` → `confirmed` → (terminated by approval flow)

**`EmployeeSubmission` (backend/app/models/submission.py):**
- Purpose: One record per employee per evaluation cycle; anchor for files, evidence, and evaluations
- Unique constraint on `(employee_id, cycle_id)` enforces one submission per cycle

**`SalaryRecommendation` (backend/app/models/salary_recommendation.py):**
- Purpose: Stores computed salary figures and deferred adjustment metadata
- Linked 1:1 to `AIEvaluation`; drives approval workflow

**`ApprovalRecord` (backend/app/models/approval.py):**
- Purpose: One row per approval step per recommendation
- `step_order` field enables ordered multi-step routing; unique constraint on `(recommendation_id, step_name)` prevents duplicates

**`AccessScopeService` (backend/app/services/access_scope_service.py):**
- Purpose: Centralized permission gate
- Admins see all; HRBP/managers see only their department employees; employees see only themselves
- All protected resource endpoints call `AccessScopeService.ensure_*_access()` before serving data

**`DeepSeekService` (backend/app/services/llm_service.py):**
- Purpose: Encapsulates all LLM calls (evidence extraction, evaluation scoring)
- Includes `InMemoryRateLimiter` with configurable RPM window
- `DeepSeekPromptLibrary` builds all system/user messages; prompts include explicit injection-resistance instructions

**`EvaluationEngine` (backend/app/engines/evaluation_engine.py):**
- Purpose: Stateless, I/O-free computation of weighted dimension scores and AI level
- Department-specific `DepartmentProfile` definitions allow per-profile keyword and weight customization
- `DEPARTMENT_DIMENSION_EXAMPLES` provides behavioral anchors used in LLM prompts

**`SalaryEngine` (backend/app/engines/salary_engine.py):**
- Purpose: Deterministic salary calculation from AI level + employee attributes
- All lookup tables (`LEVEL_RULES`, `JOB_LEVEL_ADJUSTMENTS`, etc.) are constants in the file; intended for future externalization to config

---

## Entry Points

**Backend:**
- Location: `backend/app/main.py`
- Start: `uvicorn backend.app.main:app --reload`
- `create_app()` factory registers middlewares, exception handlers, and routes
- `lifespan()` context manager runs `init_database()` on startup (creates tables + runs `ensure_schema_compatibility` migration shim)

**Frontend:**
- Location: `frontend/src/main.tsx`
- Start: `npm run dev` (Vite dev server, default port 5173)
- Mounts `<BrowserRouter><App /></BrowserRouter>` into `#root`
- `App.tsx` owns all route definitions and the `AuthProvider` wrapper

---

## Error Handling

**Strategy:** Centralized exception handlers registered in `backend/app/main.py`

**Patterns:**
- `HTTPException` → normalized `{error, message}` JSON response
- `RequestValidationError` → 422 with `{error: "validation_error", message, details: [...]}` from Pydantic
- Unhandled `Exception` → 500 with opaque message + server-side `logger.exception()` for full traceback
- Services raise `HTTPException` directly when business logic fails (e.g., record not found)
- `AccessScopeService` raises `PermissionError` which API layer catches and converts to 403

---

## Cross-Cutting Concerns

**Logging:** Structured JSON logging via `backend/app/core/logging.py`; configured from `Settings.log_level` and `Settings.log_format`

**Validation:** Pydantic v2 schemas in `backend/app/schemas/` for all request/response bodies; field validators in `Settings` for CORS origins parsing

**Authentication:**
- Backend: JWT (HS256) via `python-jose`; access token (30 min) + refresh token (7 days); `oauth2_scheme` + `get_current_user` dependency chain
- Public API: static API key via `X-API-Key` header; separate `require_public_api_key` dependency at `backend/app/api/v1/public.py`

**Prompt Injection Defense:** `backend/app/utils/prompt_safety.py` (`scan_for_prompt_manipulation`) runs on parsed file content before LLM submission; detected manipulations are flagged in `evidence.metadata_json` and surfaced in the evaluation integrity summary

**Database Migrations:** No Alembic migrations in active use; `ensure_schema_compatibility()` in `backend/app/core/database.py` applies `ALTER TABLE ADD COLUMN` statements on startup to keep SQLite schema in sync with model changes

---

*Architecture analysis: 2026-03-25*
