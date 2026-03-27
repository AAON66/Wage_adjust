# Phase 4: Audit Log Wiring - Research

**Researched:** 2026-03-27
**Domain:** Audit logging, SQLAlchemy transactional writes, FastAPI query API, React admin UI
**Confidence:** HIGH

## Summary

The `AuditLog` model already exists and is partially wired. `ApprovalService.decide_approval` writes an `approval_decided` entry in the same transaction as the approval decision (APPR-03). `SalaryService.update_recommendation` writes a `salary_updated` entry in the same transaction (APPR-04). These two call sites are already correct and serve as the reference pattern for the remaining gaps.

What Phase 4 must add: (1) audit writes in `EvaluationService.manual_review` and `EvaluationService.hr_review` — score changes currently produce no log entry; (2) a `GET /api/v1/audit/` query endpoint with filtering by entity, operator, operation type, and date range, restricted to `admin` role; (3) a frontend AuditLog page accessible from the admin nav. The `operator_id=None` gap in `SalaryService.update_recommendation` also needs fixing — the API layer must pass `current_user` down to the service so the log entry carries a real operator.

The existing `AuditLog` model schema is missing two fields required by AUDIT-01: `operator_role` (currently buried in `detail` JSON) and `request_id`. Both need to be promoted to first-class columns via an Alembic migration so they are indexable and queryable without JSON extraction.

**Primary recommendation:** Add `operator_role` and `request_id` as indexed columns to `AuditLog` via Alembic migration, wire the two missing service call sites, fix the `operator_id=None` gap, add the query API, and build a minimal admin UI table.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUDIT-01 | Every evaluation score change, approval decision, and salary override writes an AuditLog entry containing: entity type, entity ID, operation type, operator user ID + role, old value, new value, timestamp, request ID | Existing model needs `operator_role` + `request_id` columns; `manual_review` and `hr_review` need wiring; `update_recommendation` needs `operator_id` fixed |
| AUDIT-02 | Admin can query `GET /api/v1/audit/` filtered by entity, operator, operation type, date range | No audit router exists yet — needs new router + service + schema |
| AUDIT-03 | Audit log write and business change commit in the same DB transaction — no window where change exists without log | Pattern already established in `decide_approval` and `update_recommendation`; must replicate for evaluation mutations |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.36 | ORM + transactional writes | Already in use; `db.add()` + `db.commit()` is the established pattern |
| Alembic | 1.14.0 | Schema migration for new columns | Sole migration path per DB-02 |
| FastAPI | 0.115.0 | Query endpoint + request ID middleware | Already in use |
| Pydantic | 2.10.3 | Response schema for audit log reads | Already in use |
| React + Axios | 18.3.1 / 1.8.4 | Admin UI table | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `starlette.middleware.base` | (bundled with FastAPI) | Request ID injection middleware | Needed to propagate `X-Request-ID` into service layer |
| `uuid` (stdlib) | — | Generate request ID if header absent | Fallback when caller does not supply one |

**Installation:** No new packages required. All dependencies are already present.

---

## Architecture Patterns

### Recommended Project Structure additions
```
backend/app/
├── middleware/
│   └── request_id.py        # RequestIdMiddleware — injects X-Request-ID into request.state
├── api/v1/
│   └── audit.py             # GET /audit/ router (new)
├── services/
│   └── audit_service.py     # AuditService.query() — filtering + pagination
└── schemas/
    └── audit.py             # AuditLogRead, AuditLogListResponse

frontend/src/
├── pages/
│   └── AuditLog.tsx         # Admin-only audit log table page
└── services/
    └── auditService.ts      # getAuditLogs(params) → axios call
```

### Pattern 1: Transactional Audit Write (established — replicate this)

The correct pattern is already in `ApprovalService.decide_approval` (lines 384–399) and `SalaryService.update_recommendation` (lines 367–380). The audit entry is `db.add()`-ed before `db.commit()`, so both the business mutation and the log entry land in the same transaction.

```python
# Source: backend/app/services/approval_service.py lines 384-399
audit_entry = AuditLog(
    operator_id=current_user.id,
    action='approval_decided',
    target_type='approval_record',
    target_id=approval.id,
    detail={
        'decision': normalized_decision,
        'recommendation_id': str(approval.recommendation_id),
        'operator_role': current_user.role,
        # old/new values go here
    },
)
self.db.add(audit_entry)
self.db.commit()   # business change + audit in one commit
```

### Pattern 2: Request ID Propagation

Request ID must flow from HTTP layer → service layer. The cleanest approach for this codebase (no async, synchronous SQLAlchemy sessions) is a middleware that writes to `request.state`, then the API layer reads it and passes it to the service method.

```python
# backend/app/middleware/request_id.py
from __future__ import annotations
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response
```

Register in `main.py` `create_app()` alongside existing middleware. API endpoints then read `request.state.request_id` and pass it as a parameter to service methods that write audit entries.

### Pattern 3: AuditLog Model — Required Column Additions

The current model stores `operator_role` and `request_id` only inside the `detail` JSON blob. AUDIT-01 requires them as queryable fields. Two new columns needed:

```python
# Addition to backend/app/models/audit_log.py
operator_role: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
```

Alembic migration uses `batch_alter_table` (SQLite-compatible, consistent with Phase 1 pattern).

### Pattern 4: AuditService Query

```python
# backend/app/services/audit_service.py
from sqlalchemy import select, and_
from backend.app.models.audit_log import AuditLog

class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def query(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        operator_id: str | None = None,
        action: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        filters = []
        if target_type:
            filters.append(AuditLog.target_type == target_type)
        if target_id:
            filters.append(AuditLog.target_id == target_id)
        if operator_id:
            filters.append(AuditLog.operator_id == operator_id)
        if action:
            filters.append(AuditLog.action == action)
        if from_dt:
            filters.append(AuditLog.created_at >= from_dt)
        if to_dt:
            filters.append(AuditLog.created_at <= to_dt)
        stmt = (
            select(AuditLog)
            .where(and_(*filters))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(stmt))
```

### Pattern 5: Evaluation Service Wiring — Missing Call Sites

`EvaluationService.manual_review` and `EvaluationService.hr_review` currently have no audit writes. Both need the same pattern as `decide_approval`. The service methods need a `current_user: User` parameter added (currently absent) so the operator is known.

The API layer already has `current_user` in scope for both endpoints (`manual_review_evaluation` and `hr_review_evaluation` in `evaluations.py`). The change is: pass `current_user` into the service call, capture old values before mutation, add `AuditLog` before `db.commit()`.

### Pattern 6: Fix operator_id=None in SalaryService

`SalaryService.update_recommendation` currently writes `operator_id=None` with the comment "salary service has no auth context". The fix is to add `operator: User | None = None` parameter to `update_recommendation`, and pass `current_user` from the API layer (`salary.py` `update_recommendation` endpoint already has `current_user` in scope).

### Anti-Patterns to Avoid

- **Separate transaction for audit write:** Never `db.commit()` the business change first, then write the audit entry in a second commit. This is the exact window AUDIT-03 prohibits.
- **Audit in a background task or Celery job:** Async audit writes break the atomicity guarantee.
- **JSON-only storage for queryable fields:** `operator_role` and `request_id` must be columns, not buried in `detail`, to support indexed filtering per AUDIT-02.
- **Audit service calling `db.commit()` itself:** The service that owns the business mutation owns the commit. The audit entry is just `db.add()`-ed into the same session before that commit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request ID generation | Custom UUID scheme | `uuid.uuid4()` stdlib | Already used throughout codebase |
| Middleware base class | Custom ASGI wrapper | `starlette.middleware.base.BaseHTTPMiddleware` | Bundled with FastAPI, consistent with existing middleware in `main.py` |
| Pagination | Custom slice logic | SQLAlchemy `.limit()` + `.offset()` | Simple offset pagination is sufficient for admin audit queries; cursor pagination is Phase 10 scope |

---

## Common Pitfalls

### Pitfall 1: operator_id=None breaks audit traceability
**What goes wrong:** `SalaryService.update_recommendation` already writes `operator_id=None`. If left unfixed, salary override audit entries are untraceable to a user.
**Why it happens:** The service was written without auth context injection.
**How to avoid:** Add `operator: User | None = None` to `update_recommendation` signature; pass `current_user` from the API layer.
**Warning signs:** `AuditLog` rows with `operator_id IS NULL` for `action='salary_updated'`.

### Pitfall 2: Schema migration breaks existing audit rows
**What goes wrong:** Adding `operator_role` and `request_id` columns with `nullable=False` and no default will fail on SQLite if existing rows are present.
**Why it happens:** SQLite's `ALTER TABLE ADD COLUMN` requires `nullable=True` or a default for existing rows.
**How to avoid:** Add both columns as `nullable=True` (consistent with `operator_id` which is already nullable). Existing rows will have `NULL` for these fields, which is acceptable.

### Pitfall 3: Forgetting to register the middleware
**What goes wrong:** `request.state.request_id` raises `AttributeError` in endpoints if the middleware is not registered in `create_app()`.
**Why it happens:** Middleware must be added to the app before routes are registered, or at minimum before requests are processed.
**How to avoid:** Add `app.add_middleware(RequestIdMiddleware)` in `create_app()` in `main.py`, alongside existing CORS middleware.

### Pitfall 4: Frontend audit page accessible to non-admins
**What goes wrong:** Audit log data leaks role/salary information to managers or employees.
**Why it happens:** Missing role guard on the route.
**How to avoid:** Wrap `AuditLog.tsx` route in `ProtectedRoute` with `allowedRoles={['admin']}`, consistent with the existing `roleAccess.ts` pattern.

### Pitfall 5: detail JSON old/new values inconsistent across call sites
**What goes wrong:** Some audit entries store `old_value`/`new_value` as floats, others as strings, making programmatic comparison impossible.
**How to avoid:** Standardize: numeric scores as `float`, status strings as `str`, always use keys `old_value` and `new_value` in `detail` dict. Document the convention in a comment in `audit_log.py`.

---

## Code Examples

### Wiring manual_review (new pattern)
```python
# backend/app/services/evaluation_service.py — manual_review addition
def manual_review(
    self,
    evaluation_id: str,
    *,
    ai_level: str | None,
    overall_score: float | None,
    explanation: str | None,
    dimension_updates: list[dict[str, object]],
    operator: User | None = None,       # NEW parameter
    request_id: str | None = None,      # NEW parameter
) -> AIEvaluation | None:
    evaluation = self.get_evaluation(evaluation_id)
    if evaluation is None:
        return None

    old_score = float(evaluation.overall_score)
    old_level = evaluation.ai_level
    # ... existing mutation logic unchanged ...

    audit_entry = AuditLog(
        operator_id=operator.id if operator else None,
        operator_role=operator.role if operator else None,
        action='evaluation_score_changed',
        target_type='ai_evaluation',
        target_id=evaluation_id,
        request_id=request_id,
        detail={
            'old_overall_score': old_score,
            'new_overall_score': float(evaluation.overall_score),
            'old_ai_level': old_level,
            'new_ai_level': evaluation.ai_level,
            'source': 'manual_review',
        },
    )
    self.db.add(audit_entry)
    self.db.commit()   # single commit covers mutation + audit
    return self.get_evaluation(evaluation.id)
```

### AuditLog schema (new)
```python
# backend/app/schemas/audit.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operator_id: str | None
    operator_role: str | None
    action: str
    target_type: str
    target_id: str
    detail: dict
    request_id: str | None
    created_at: datetime

class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
```

### Audit query endpoint (new)
```python
# backend/app/api/v1/audit.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.dependencies import get_db, require_roles
from backend.app.models.user import User
from backend.app.schemas.audit import AuditLogListResponse, AuditLogRead
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix='/audit', tags=['audit'])

@router.get('/', response_model=AuditLogListResponse)
def list_audit_logs(
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    operator_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles('admin')),
) -> AuditLogListResponse:
    service = AuditService(db)
    items = service.query(
        target_type=target_type, target_id=target_id,
        operator_id=operator_id, action=action,
        from_dt=from_dt, to_dt=to_dt,
        limit=limit, offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=len(items), limit=limit, offset=offset,
    )
```

---

## Audit Coverage Map

All service mutations that must produce an audit entry:

| Service | Method | Action string | Currently wired? | Gap |
|---------|--------|---------------|-----------------|-----|
| `ApprovalService` | `decide_approval` | `approval_decided` | YES (Phase 3) | operator_role in detail only — promote to column |
| `SalaryService` | `update_recommendation` | `salary_updated` | YES (Phase 3) | `operator_id=None` — fix by passing current_user |
| `EvaluationService` | `manual_review` | `evaluation_score_changed` | NO | Wire in Phase 4 |
| `EvaluationService` | `hr_review` | `evaluation_score_changed` | NO | Wire in Phase 4 |
| `EvaluationService` | `confirm_evaluation` | `evaluation_confirmed` | NO | Wire in Phase 4 |

`generate_evaluation` does not need an audit entry — it is a system-generated initial result, not a human decision. `recommend_salary` similarly is a system calculation, not a human override.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | none — inline session factory per test file (see `test_approval_service.py`) |
| Quick run command | `pytest backend/tests/test_services/test_audit_service.py -x` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIT-01 | `manual_review` writes AuditLog with correct fields in same transaction | unit | `pytest backend/tests/test_services/test_audit_service.py::test_manual_review_writes_audit -x` | ❌ Wave 0 |
| AUDIT-01 | `hr_review` writes AuditLog with correct fields | unit | `pytest backend/tests/test_services/test_audit_service.py::test_hr_review_writes_audit -x` | ❌ Wave 0 |
| AUDIT-01 | `update_recommendation` audit entry has non-null operator_id after fix | unit | `pytest backend/tests/test_services/test_audit_service.py::test_salary_update_audit_has_operator -x` | ❌ Wave 0 |
| AUDIT-01 | AuditLog row contains operator_role and request_id columns | unit | `pytest backend/tests/test_services/test_audit_service.py::test_audit_log_schema -x` | ❌ Wave 0 |
| AUDIT-02 | `GET /api/v1/audit/` filters by action, target_type, operator_id, date range | integration | `pytest backend/tests/test_api/test_audit_api.py -x` | ❌ Wave 0 |
| AUDIT-02 | Non-admin role receives 403 on audit endpoint | integration | `pytest backend/tests/test_api/test_audit_api.py::test_audit_requires_admin -x` | ❌ Wave 0 |
| AUDIT-03 | Rollback of business mutation also rolls back audit entry | unit | `pytest backend/tests/test_services/test_audit_service.py::test_audit_atomicity -x` | ❌ Wave 0 |

### Sampling Rate
- Per task commit: `pytest backend/tests/test_services/test_audit_service.py -x`
- Per wave merge: `pytest backend/tests/ -x`
- Phase gate: full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_services/test_audit_service.py` — covers AUDIT-01, AUDIT-03
- [ ] `backend/tests/test_api/test_audit_api.py` — covers AUDIT-02
- [ ] `backend/tests/test_services/test_audit_service.py` uses same inline `create_db_context()` + `seed_workflow_entities()` pattern as `test_approval_service.py`

---

## Environment Availability

Step 2.6: SKIPPED — phase is purely backend service wiring + new API endpoint + React page. No external tools, databases beyond SQLite, or CLI utilities beyond what is already running.

---

## Project Constraints (from CLAUDE.md)

- All schema changes via Alembic migration (DB-02) — new `operator_role` and `request_id` columns must go through a migration file, not `create_all`
- `from __future__ import annotations` mandatory on all backend modules
- Services raise `HTTPException` directly for not-found; `PermissionError` at service level caught as 403 in routers
- All evaluations results must be auditable and explainable — this phase directly fulfills that constraint
- Coding convention: `operator_id`, `operator_role`, `request_id` as nullable columns (not hardcoded in multiple places)
- Frontend: `ProtectedRoute` + `roleAccess.ts` for role-gating the audit page
- No new packages — all required libraries already in `requirements.txt`
- `batch_alter_table` for SQLite-compatible Alembic migrations (established in Phase 1)

---

## Open Questions

1. **Should `confirm_evaluation` produce an audit entry?**
   - What we know: it transitions status to `confirmed` and may update `overall_score`
   - What's unclear: it can be called by any authenticated user with evaluation access, not just admin/hrbp
   - Recommendation: yes, wire it — it is a status-changing decision even if automated; use action `evaluation_confirmed`

2. **Should the audit query API support total count for pagination?**
   - What we know: current pattern in this codebase uses `len(items)` which only counts the current page
   - What's unclear: whether admin needs to know total rows across all pages
   - Recommendation: add a `COUNT(*)` query alongside the data query in `AuditService`; return it as `total` in the response. Adds one extra query but makes the UI paginator functional.

3. **Should existing `approval_decided` and `salary_updated` entries be backfilled with `operator_role`?**
   - What we know: existing rows have `operator_role` in `detail` JSON but not as a column
   - Recommendation: no backfill needed — the column is nullable, old rows will have `NULL`, which is acceptable. The UI can fall back to `detail.operator_role` for display.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `backend/app/models/audit_log.py`, `backend/app/services/approval_service.py` (lines 384–399), `backend/app/services/salary_service.py` (lines 349–381)
- Direct codebase inspection: `backend/app/models/mixins.py`, `backend/app/dependencies.py`, `backend/app/api/v1/evaluations.py`
- Direct codebase inspection: `backend/tests/test_services/test_approval_service.py` — test infrastructure pattern

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 docs: `batch_alter_table` for SQLite-compatible column additions — consistent with Phase 1 migration pattern already in codebase
- Starlette `BaseHTTPMiddleware` — bundled with FastAPI, used for request ID injection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — patterns directly observed in existing working code
- Pitfalls: HIGH — gaps identified by direct code inspection, not inference
- Test patterns: HIGH — existing test files provide exact infrastructure template

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable stack, no fast-moving dependencies)
