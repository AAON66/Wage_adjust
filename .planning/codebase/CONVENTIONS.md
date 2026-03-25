# Coding Conventions

**Analysis Date:** 2026-03-25

## Summary

The codebase follows strict, consistent conventions on both backend (Python/FastAPI) and frontend (React/TypeScript). The backend uses modern Python idioms with full type annotations, Pydantic schemas, and SQLAlchemy ORM. The frontend uses TypeScript strict mode with named exports, co-located types, and a service-layer pattern. Neither side uses an auto-formatter (no Prettier, no Black/Ruff config found in project root), but the code is stylistically uniform and evidently hand-maintained to high consistency.

---

## Naming Patterns

**Python files:**
- `snake_case` for all module names: `evaluation_service.py`, `salary_engine.py`, `access_scope_service.py`
- Suffixes signal role: `_service.py`, `_engine.py`, `_parser.py`, `_schema.py` (but schemas dir uses singular: `evaluation.py`)

**TypeScript/TSX files:**
- `PascalCase` for component files: `FileUploadPanel.tsx`, `BudgetSimulationPanel.tsx`
- `camelCase` for non-component modules: `evaluationService.ts`, `api.ts`, `useAuth.tsx`
- Hook files use `use` prefix: `useAuth.tsx`

**Python classes:**
- `PascalCase` for all: `EvaluationService`, `SalaryEngine`, `DepartmentProfile`, `UUIDPrimaryKeyMixin`
- Models inherit from mixins first, then `Base`: `class Employee(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base)`

**Python functions/methods:**
- `snake_case` everywhere
- Private helpers prefixed with `_`: `_build_integrity_summary`, `_query_evaluation`
- Keyword-only arguments enforced with `*` for construction helpers: `build_error_response(*, status_code, error, message, details=None)`

**TypeScript interfaces and types:**
- `PascalCase` for interfaces: `UserProfile`, `AuthContextValue`, `BudgetSimulationPanelProps`
- Props interfaces named `[ComponentName]Props`: `FileUploadPanelProps`, `BudgetSimulationPanelProps`
- Union types with `as const` for enums: `'collecting' | 'submitted' | 'parsing' | ...`

**TypeScript variables/constants:**
- `camelCase` for local variables and functions: `refreshInFlight`, `handleLogin`, `isBootstrapping`
- `SCREAMING_SNAKE_CASE` for module-level constants: `ACCESS_TOKEN_KEY`, `REFRESH_TOKEN_KEY`, `LONG_RUNNING_TIMEOUT`

---

## Code Style

**Formatting:**
- No Prettier config found in project. Code uses consistent 2-space indentation in TSX and consistent 4-space in Python.
- TypeScript: single quotes in type annotations, double quotes for JSX string attributes.
- Python: single quotes for strings throughout backend code.

**Linting:**
- TypeScript: `tsc --noEmit` is the lint command (`"lint": "tsc --noEmit"` in `frontend/package.json`). No ESLint config detected.
- Python: No `pyproject.toml`, `setup.cfg`, or `ruff.toml` found in project root. Two `# noqa: ANN001, ANN201` suppressions present in test stubs where untyped signatures are intentional.

**TypeScript strict mode:**
- `tsconfig.json` has `"strict": true`, `"allowJs": false`, `"noEmit": true`.
- Target: `ES2020`, module resolution: `Bundler`.

---

## Import Organization

**Python:**
- All files begin with `from __future__ import annotations` — mandatory across all backend modules.
- Standard library imports come first, then third-party, then local `backend.app.*` imports. Not enforced by tooling but maintained consistently.
- Example pattern from `backend/app/main.py`:
  ```python
  from __future__ import annotations

  import logging
  from contextlib import asynccontextmanager

  from fastapi import FastAPI, HTTPException, Request
  from fastapi.exceptions import RequestValidationError

  from backend.app.api.v1 import api_router
  from backend.app.core.config import Settings, get_settings
  ```

**TypeScript:**
- Third-party imports first, then relative imports, then type-only imports last.
- Type imports use `import type { ... }` when the symbol is type-only.
- Example from `frontend/src/pages/EvaluationDetail.tsx`:
  ```typescript
  import axios from 'axios';
  import { useEffect, useMemo, useState } from 'react';
  import { Link, useParams, useSearchParams } from 'react-router-dom';

  import { EvidenceCard } from '../components/evaluation/EvidenceCard';
  // ...
  import type { CycleRecord, EmployeeRecord, EvaluationRecord } from '../types/api';
  ```

**Path Aliases:**
- No path aliases configured. All imports use relative paths (`../components/...`, `../services/...`).

---

## TypeScript/Python Type Usage

**TypeScript:**
- Full explicit typing on all function parameters and return types in service layer.
- `interface` preferred over `type` for object shapes.
- Discriminated union types used for status flows: `type BatchParseItemStatus = 'queued' | 'parsing' | 'parsed' | 'failed'`
- `as const` arrays for immutable flow steps: `const FLOW = ['collecting', 'submitted', ...] as const`
- Optional props with `?:` and defaults in destructuring: `{ isGithubImporting = false, isUploading, ... }`
- Nullable types with `| null`: `user: UserProfile | null`, `manager_id: string | null`

**Python:**
- Full PEP 604 union syntax: `str | None`, `Settings | None` (enabled by `from __future__ import annotations`)
- `Mapped[T]` for SQLAlchemy columns: `employee_no: Mapped[str] = mapped_column(...)`
- `Mapped[str | None]` for nullable columns
- Pydantic `BaseModel` for all request/response schemas with `ConfigDict(from_attributes=True)` for ORM serialization
- `pydantic_settings.BaseSettings` for config with `SettingsConfigDict`
- `dataclass(frozen=True)` for engine-internal value objects: `DimensionDefinition`, `DepartmentProfile`
- Return type annotations on all service methods: `def get_evaluation(self, ...) -> AIEvaluation | None:`
- `Callable`, `Generator`, `Mapping` from `collections.abc` / `typing`

---

## Component Patterns (React)

**Function components only.** No class components found.

**Props interface declared inline above component:**
```typescript
interface FileUploadPanelProps {
  isGithubImporting?: boolean;
  isUploading: boolean;
  onFilesSelected: (files: FileList | null) => void;
  onGitHubImport?: (url: string) => void;
}

export function FileUploadPanel({ ... }: FileUploadPanelProps) { ... }
```

**Named exports.** All components and hooks use named exports (not default). Services also use named exports for individual functions.

**Context + Hook pattern for shared state:**
- Context defined in hook file: `const AuthContext = createContext<AuthContextValue | null>(null)`
- Provider exported: `export function AuthProvider({ children }: { children: ReactNode })`
- Consumer hook exported with guard: `export function useAuth()` — throws if used outside provider

**useMemo for context value to prevent re-renders:**
```typescript
const value = useMemo<AuthContextValue>(
  () => ({ user, accessToken, isAuthenticated: Boolean(user && accessToken), ... }),
  [accessToken, isBootstrapping, user],
);
```

**Async effects use cancellation flag pattern:**
```typescript
useEffect(() => {
  let cancelled = false;
  async function bootstrap() {
    // ...
    if (!cancelled) { setUser(profile); }
  }
  void bootstrap();
  return () => { cancelled = true; };
}, []);
```

**`void` prefix for floating promises:** `void bootstrap()` — avoids lint warnings on unhandled promises.

**`useId()` for accessible form elements** — seen in `FileUploadPanel.tsx`.

---

## Error Handling

**Backend — centralized exception handlers in `backend/app/main.py`:**
- `HTTPException` → `build_error_response(status_code, error='http_error', message=...)`
- `RequestValidationError` → 422 with structured `details`
- Bare `Exception` → 500 with `logger.exception(...)` + safe generic message

All error responses share a single shape: `{ error: string, message: string, details?: any }`.

**Backend — service layer:**
- Services raise `HTTPException` directly when not found or forbidden: `raise HTTPException(status_code=404, detail='...')`
- Access control raises `PermissionError` at service level, caught and re-raised as HTTP 403 in routers
- `from exc` used consistently on re-raises to preserve traceback

**Frontend — service layer:**
- No try/catch in service modules — errors propagate as rejected promises to pages/components
- Axios interceptor handles 401 globally: attempts token refresh, clears session on failure
- Pages handle errors locally with `axios.isAxiosError(err)` checks and local error state

---

## Logging

**Framework:** Python `logging` module with `dictConfig` setup in `backend/app/core/logging.py`.

**Pattern:**
```python
logger = logging.getLogger(__name__)
# Module-level logger, named after module path
logger.info('Starting %s v%s', settings.app_name, settings.app_version)
logger.exception('Unhandled application error', exc_info=exc)
```

**Format:** `%(asctime)s %(levelname)s [%(name)s] %(message)s` (text format; config supports `json` format via settings but current implementation uses text format string).

**Level:** Configured via `settings.log_level` (default `INFO`).

**Frontend:** No logging framework. Browser console only.

---

## Comments and Documentation Style

**Python docstrings:**
- Single-line `"""..."""` docstrings on classes and utility functions only:
  ```python
  class UUIDPrimaryKeyMixin:
      """Mixin that provides a UUID primary key stored as text for portability."""

  def utc_now() -> datetime:
      """Return a timezone-aware UTC timestamp."""
  ```
- Service methods and API endpoints are typically undocumented (no docstring)
- Inline comments used sparingly to explain non-obvious logic

**TypeScript:**
- No JSDoc found. Comments are rare and only for non-obvious code.
- Type declarations serve as self-documentation.

---

## Module Design

**Backend services use constructor injection:**
```python
class EvaluationService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        *,
        engine: EvaluationEngine | None = None,
        llm_service: DeepSeekService | None = None,
    ) -> None:
```
- All collaborators optional with sensible defaults — enables easy test injection without mocking frameworks.

**Backend schemas (`backend/app/schemas/`):**
- One file per domain: `evaluation.py`, `salary.py`, `employee.py`
- Pydantic models for request (`...Request`), response (`...Read`, `...Response`), and update (`...UpdateRequest`) shapes

**Frontend services (`frontend/src/services/`):**
- One file per domain: `evaluationService.ts`, `salaryService.ts`, `employeeService.ts`
- Each exports plain async functions (not classes) that call `api` (the shared axios instance)
- Long-running AI calls override timeout: `{ timeout: LONG_RUNNING_TIMEOUT }` (120000ms)

**Frontend types (`frontend/src/types/api.ts`):**
- Single file for all API-facing types
- All types are `interface` definitions

---

## SQLAlchemy Model Design

**Mixin-first inheritance** for shared concerns:
```python
class Employee(UUIDPrimaryKeyMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "employees"
```
Mixins: `UUIDPrimaryKeyMixin` (UUID as text PK), `CreatedAtMixin`, `UpdatedAtMixin`.

**Table names:** `snake_case` plural: `employees`, `ai_evaluations`, `salary_recommendations`.

**Relationships:** Explicitly defined with `back_populates` and `foreign_keys` where ambiguous.

**Computed properties** exposed as `@property` on models: `bound_user_id`, `bound_user_email`.

---

*Convention analysis: 2026-03-25*
