# Technology Stack — v1.1 Milestone

**Project:** 公司综合调薪工具 (Enterprise Salary Adjustment Platform)
**Milestone:** v1.1 体验优化与业务规则完善
**Researched:** 2026-03-30
**Overall confidence:** HIGH

---

## Key Finding: No New Libraries Needed

All 5 features in v1.1 are implementable with the existing stack. The work is model additions, new service logic, and frontend component restructuring — not technology adoption. Zero new pip packages. Zero new npm packages.

---

## Feature-by-Feature Stack Analysis

### Feature 1: Account-Employee Binding Hardening / 账号-员工绑定加固

**What exists:** `IdentityBindingService` with auto-bind via `id_card_no`, `User.employee_id` FK, bidirectional `User.employee` / `Employee.bound_user` relationships, manual search by identity.

**What's needed (stack):** Nothing new. This is UI/UX work (add binding entry points in Settings page, display binding status in EmployeeAdmin) plus a possible admin manual-bind API endpoint — all pure FastAPI route + existing service.

| Layer | Change Type | New Library? |
|-------|-------------|--------------|
| Backend model | None | No |
| Backend service | Minor extension to `IdentityBindingService` (admin manual bind/unbind) | No |
| Backend API | New route: `POST /api/v1/users/{id}/bind-employee` | No |
| Frontend | UI changes in Settings + EmployeeAdmin pages | No |

### Feature 2: File Upload Sharing / Approval Mechanism / 文件共享申请机制

**What exists:** `ProjectContributor` model with `status` field (`accepted`, `disputed`, `resolved`), `UploadedFile.content_hash` for duplicate detection, `FileService.list_files(include_shared=True)`.

**What's needed (stack):** A new `FileShareRequest` SQLAlchemy model to track sharing approval requests (requester, file owner, status, timestamps). This is a lightweight request/approve/reject flow separate from the salary approval workflow.

| Layer | Change Type | New Library? |
|-------|-------------|--------------|
| Backend model | New `FileShareRequest` table (requester_id, owner_id, file_id, status, created_at) | No — SQLAlchemy |
| Backend service | New `FileShareService` or extend `FileService` | No |
| Backend API | Routes: `POST /share-request`, `POST /share-request/{id}/approve`, `GET /share-requests` | No — FastAPI |
| Frontend | Share request dialog, pending request indicator, approval list | No |

**Architecture note:** Do NOT reuse the `ApprovalRecord` model. That model is specifically for salary recommendation approvals with `recommendation_id` FK and multi-step `step_order` routing. File sharing is a simple single-step request/approve/reject flow — a separate lightweight table is correct.

**Integration:** On approval, create the `ProjectContributor` record that already feeds into evaluation scoring via `EvaluationService._compute_shared_project_score()`.

### Feature 3: Menu / Navigation Restructuring / 菜单导航重构

**What exists:** `roleAccess.ts` with flat `ROLE_MODULES` dict per role, `AppShell.tsx` sidebar rendering a single flat nav list.

**What's needed (stack):** Pure frontend refactoring. Group nav items into sections (core workflow, data management, settings/admin). No libraries.

| Layer | Change Type | New Library? |
|-------|-------------|--------------|
| Frontend | Restructure `ROLE_MODULES` type to support groups/sections | No |
| Frontend | Update `AppShell` sidebar to render grouped navigation with section headers | No |
| Backend | None | No |

**Anti-recommendation:** Do NOT add a UI component library (Ant Design, Headless UI, Radix) for grouped navigation. The existing Tailwind + custom component pattern is consistent; adding a component library mid-project creates style conflicts and bundle size increases for minimal gain.

### Feature 4: Salary Adjustment Eligibility Engine / 调薪资格校验引擎

**What exists:** `Employee` model (no `hire_date`, no `last_raise_date`, no `performance_rating`), `AttendanceRecord` model (has `leave_days`), `SalaryEngine` and `EvaluationEngine` (pure computation classes, no I/O).

**What's needed (stack):** This is the most model-heavy feature. The Employee model needs 3 new nullable columns. A new `EligibilityEngine` (pure computation, no I/O) implements the 4 rules. An Alembic migration adds the columns.

**Rule-to-data mapping:**

| Rule | Data Source | Model Change Required |
|------|-------------|----------------------|
| Tenure >= 6 months | `Employee.hire_date` | **Add `hire_date: Mapped[date \| None]`** |
| Last raise >= 6 months ago | `Employee.last_raise_date` | **Add `last_raise_date: Mapped[date \| None]`** |
| Performance not C-below | `Employee.performance_rating` | **Add `performance_rating: Mapped[str \| None]`** |
| Leave <= 30 days (trailing 12mo) | `AttendanceRecord.leave_days` (aggregate query) | **Already exists** — no model change |

| Layer | Change Type | New Library? |
|-------|-------------|--------------|
| Backend model | 3 new nullable columns on `Employee` | No — SQLAlchemy |
| Backend migration | Alembic `op.add_column()` x3 | No — Alembic already installed |
| Backend engine | New `EligibilityEngine` class (pure computation) | No |
| Backend service | New `EligibilityService` (DB lookups + engine invocation) | No |
| Backend API | `GET /api/v1/employees/{id}/eligibility` | No — FastAPI |
| Frontend | Eligibility badge/panel on employee detail (HR/manager only) | No |
| Data import | Extend `ImportService` column mapping for new fields | No — pandas already handles dates |

**Exception mechanism:** Add a lightweight `EligibilityOverride` table (or `override_reason` + `overridden_by` fields on a new model) so HR can grant exceptions per employee. A dedicated table is cleaner than flags on `SalaryRecommendation`.

**Architecture:** `EligibilityEngine` MUST follow the same pattern as `EvaluationEngine` and `SalaryEngine` — a pure computation class with no database access, receiving all data as method parameters, returning a structured result. This keeps it unit-testable without mocking.

**Nullable column rationale:** All 3 new Employee columns are nullable because existing records lack this data. The engine should treat missing data as "ineligible" with a clear reason string (e.g., `"hire_date not recorded — cannot verify tenure"`).

### Feature 5: Salary Recommendation Display Simplification / 调薪建议展示精简

**What exists:** `EvaluationDetail.tsx` renders salary recommendation data inline with all fields visible.

**What's needed (stack):** Pure frontend. Collapsible sections using native HTML `<details>/<summary>` or a simple `useState` toggle.

| Layer | Change Type | New Library? |
|-------|-------------|--------------|
| Frontend | Refactor salary display: summary (key metrics) + collapsible detail sections | No |
| Backend | None | No |

**Anti-recommendation:** Do NOT add an accordion library. `<details>/<summary>` is native HTML with zero JS cost. If custom animation is needed, a 10-line component with `useState` + CSS `max-height` transition is sufficient.

---

## Current Stack (Unchanged for v1.1)

### Backend

| Technology | Version | Status |
|------------|---------|--------|
| FastAPI | 0.115.0 | Unchanged |
| SQLAlchemy | 2.0.36 | Unchanged |
| Alembic | 1.14.0 | Unchanged (will add new migration) |
| Pydantic | 2.10.3 | Unchanged |
| pydantic-settings | 2.6.1 | Unchanged |
| Python | 3.11+ | Unchanged |
| pandas | 2.2.3 | Unchanged (import extensions) |
| slowapi | 0.1.9 | Unchanged |

### Frontend

| Technology | Version | Status |
|------------|---------|--------|
| React | 18.3.1 | Unchanged |
| React Router DOM | 7.6.0 | Unchanged |
| TypeScript | 5.8.3 | Unchanged |
| Tailwind CSS | 3.4.17 | Unchanged |
| Vite | 6.2.6 | Unchanged |
| Axios | 1.8.4 | Unchanged |
| ECharts | 6.0.0 | Unchanged |

---

## What NOT to Add (and Why)

| Temptation | Why Not |
|------------|---------|
| React Query / TanStack Query | The app uses direct `useEffect` + `useState` fetch pattern consistently across 18+ pages. Adding a caching/state layer for 5 incremental features creates inconsistency. Defer to a dedicated DX improvement milestone. |
| Ant Design / Headless UI / Radix | Menu restructuring and collapsible sections are standard HTML/CSS/React. Adding a component library mid-project creates dual styling systems. |
| Notification library (react-toastify) | File share requests use the existing inline feedback pattern. An in-app notification center is not in v1.1 scope. |
| State management (Redux, Zustand) | The app uses Context + local state. None of the 5 features add cross-cutting state. |
| WebSocket / SSE | File share notifications can be pull-based (check on page load). Real-time push is out of scope. |
| Form library (React Hook Form) | No complex multi-step forms are being added. Controlled components with `useState` are sufficient. |
| Date library (date-fns, dayjs) | Eligibility date math is backend-only (Python `datetime.date`). Frontend only displays dates — ISO string formatting works natively. |

---

## Database Migration Required

Single Alembic migration covering all v1.1 model changes:

```python
# Employee table extensions
op.add_column('employees', sa.Column('hire_date', sa.Date(), nullable=True))
op.add_column('employees', sa.Column('last_raise_date', sa.Date(), nullable=True))
op.add_column('employees', sa.Column('performance_rating', sa.String(16), nullable=True))

# File share requests (new table)
op.create_table(
    'file_share_requests',
    sa.Column('id', sa.String(36), primary_key=True),
    sa.Column('file_id', sa.String(36), sa.ForeignKey('uploaded_files.id'), nullable=False),
    sa.Column('requester_submission_id', sa.String(36), sa.ForeignKey('employee_submissions.id'), nullable=False),
    sa.Column('owner_submission_id', sa.String(36), sa.ForeignKey('employee_submissions.id'), nullable=False),
    sa.Column('status', sa.String(32), nullable=False, default='pending'),
    sa.Column('contribution_pct', sa.Float(), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
)

# Eligibility overrides (new table)
op.create_table(
    'eligibility_overrides',
    sa.Column('id', sa.String(36), primary_key=True),
    sa.Column('employee_id', sa.String(36), sa.ForeignKey('employees.id'), nullable=False),
    sa.Column('cycle_id', sa.String(36), sa.ForeignKey('evaluation_cycles.id'), nullable=False),
    sa.Column('rule_code', sa.String(64), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('approved_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
)
```

---

## Integration Points Summary

| New Feature | Integrates With | How |
|-------------|----------------|-----|
| Binding hardening | `IdentityBindingService`, `User` model, Settings page | Extends existing service + adds UI entry points |
| File sharing | `ProjectContributor`, `FileService`, `EvaluationService` | Approval creates `ProjectContributor` record that feeds scoring |
| Menu restructuring | `roleAccess.ts`, `AppShell.tsx` | Refactors existing flat nav into grouped sections |
| Eligibility engine | `Employee`, `AttendanceRecord`, `SalaryEngine` | New engine runs before salary calculation; blocks ineligible employees |
| Display simplification | `EvaluationDetail.tsx` | Pure UI refactor, no API changes |

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| No new backend libraries | HIGH | All 5 features use existing patterns verified in codebase (SQLAlchemy, FastAPI routes, pure engine classes) |
| No new frontend libraries | HIGH | Navigation grouping and collapsible sections are standard HTML/CSS/React — verified by examining current component patterns |
| Employee model changes | HIGH | SQLAlchemy `Mapped` + Alembic migration is established in codebase (4 existing migrations, `compare_type=True` in env.py) |
| Eligibility engine pattern | HIGH | Direct analog to existing `EvaluationEngine` and `SalaryEngine` pure-computation classes |
| File share request model | HIGH | Simple status-machine table; mirrors existing `ProjectContributor` lifecycle but with explicit request/approve flow |

## Sources

- Direct codebase inspection: all models, services, engines, frontend components referenced above
- Existing `.planning/PROJECT.md` for milestone scope confirmation
- `requirements.txt` and `frontend/package.json` for current dependency inventory
