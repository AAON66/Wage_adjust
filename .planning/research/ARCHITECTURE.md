# Architecture Patterns: v1.2 Feature Integration

**Domain:** Enterprise Salary Adjustment Platform -- v1.2 production readiness and data management
**Researched:** 2026-04-07
**Overall confidence:** HIGH (based on direct codebase analysis of 30k+ Python LOC and 20k+ TypeScript LOC)

## Recommended Architecture

All 5 v1.2 features integrate into the existing `api/ -> services/ -> engines/ -> models/` layered architecture. One new package (`tasks/`) is added for Celery task definitions. No structural changes to existing layers.

### Component Map: New vs Modified

```
NEW FILES:
  backend/app/core/celery_app.py              -- Celery application factory + config
  backend/app/tasks/__init__.py               -- Celery task package
  backend/app/tasks/feishu_tasks.py           -- Feishu sync as Celery tasks
  alembic/versions/xxxx_add_company_to_employee.py  -- Migration

MODIFIED FILES:
  backend/app/core/config.py                  -- Celery config settings (broker, backend)
  backend/app/core/database.py                -- Add SQLite PRAGMA foreign_keys=ON event listener
  backend/app/main.py                         -- Remove threading.Thread for sync
  backend/app/models/*.py                     -- Replace Mapped[X | None] with Mapped[Optional[X]] for Python 3.9
  backend/app/schemas/*.py                    -- Replace X | None with Optional[X] for Python 3.9
  backend/app/models/employee.py              -- Add company column
  backend/app/schemas/employee.py             -- Add company to read/write schemas
  backend/app/services/sharing_service.py     -- reject_request() cascades file deletion
  backend/app/services/file_service.py        -- Minor: ensure delete_file() is callable from SharingService
  backend/app/api/v1/feishu.py                -- Replace threading.Thread with celery task.delay()
  backend/app/api/v1/imports.py               -- Add import_type filter query param
  frontend/src/pages/EligibilityManagementPage.tsx  -- Add "数据导入" tab
  frontend/src/pages/ImportCenter.tsx          -- Add eligibility import types to IMPORT_TYPES

PYTHON 3.9 COMPAT (broad changes across codebase):
  All model files: Mapped[X | None] -> Mapped[Optional[X]] (SQLAlchemy eval() bypass)
  All schema files: X | None -> Optional[X] (Pydantic eval() bypass)
  Service/API files: str | None in function sigs OK (deferred by __future__)
  requirements.txt: numpy==2.0.2, Pillow==10.4.0 (downgrade for 3.9)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `core/celery_app.py` (NEW) | Celery app instance, broker/backend config | `core/config.py`, Redis |
| `tasks/feishu_tasks.py` (NEW) | Celery task wrappers for async operations | `FeishuService`, `SessionLocal` |
| `SharingService` (MODIFIED) | Rejection now cascades to requester file deletion | `FileService` (new dependency) |
| `Employee` model (MODIFIED) | Adds nullable `company` field | Alembic migration |
| `ImportService` (REUSED, unmodified) | Already supports `performance_grades` + `salary_adjustments` types | No changes needed |
| `FeishuService` (REUSED, unmodified) | `sync_performance_records()` already exists | No changes needed |
| `EligibilityManagementPage` (MODIFIED) | Adds unified import tab | Reuses `ImportJobTable`, `ImportResultPanel` |

---

## Feature 1: Celery+Redis Async Task Activation

### Current State

- `celery==5.4.0` in `requirements.txt` but **zero Celery code exists** -- no `celery_app.py`, no task definitions, no worker config
- `redis==5.2.1` installed; `core/redis.py` provides working `get_redis()` singleton with `redis_url` from config
- Feishu sync currently uses `threading.Thread` in `api/v1/feishu.py:_run_sync_in_background()` (line 152-159)
- APScheduler (`feishu_scheduler.py`) handles periodic Feishu attendance sync
- `FeishuService.sync_with_retry()` already has retry logic with `[5, 15, 45]` second delays

### Where Celery Fits in the Layer Structure

```
backend/app/
  core/
    celery_app.py     <-- NEW: same level as redis.py, config.py (cross-cutting)
  tasks/
    __init__.py       <-- NEW: task package (parallel to services/, not inside it)
    feishu_tasks.py   <-- NEW: wraps FeishuService calls as Celery tasks
```

The `tasks/` package is a **peer of `services/`**, not a child. Tasks invoke service-layer methods with their own database sessions. This follows the exact same pattern as `scheduler/feishu_scheduler.py:run_incremental_sync()` which creates its own `SessionLocal()`.

**Dependency direction:** `tasks/ -> services/ -> engines/ -> models/` (extends existing chain)

### Celery App Configuration

```python
# backend/app/core/celery_app.py
from __future__ import annotations
from celery import Celery
from backend.app.core.config import get_settings

def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        'wage_adjust',
        broker=settings.celery_broker_url or settings.redis_url,
        backend=settings.celery_result_backend or settings.redis_url,
    )
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_time_limit=1800,           # 30 min hard limit
        task_soft_time_limit=1500,      # 25 min soft limit
        result_expires=3600,            # Results expire after 1 hour
    )
    app.autodiscover_tasks(['backend.app.tasks'])
    return app

celery_app = create_celery_app()
```

### Critical: Celery Worker DB Session Isolation

Celery workers fork from the parent process. The global `Engine` and `SessionLocal` in `database.py` are inherited but their connections become invalid after fork. Use `worker_process_init` signal:

```python
from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker_db(**kwargs):
    """Re-create DB engine in each worker process after fork."""
    from backend.app.core.database import engine
    engine.dispose()  # Dispose inherited connections
```

Each task must create and close its own session:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def feishu_sync_task(self, mode, triggered_by=None):
    db = SessionLocal()
    try:
        from backend.app.services.feishu_service import FeishuService
        service = FeishuService(db)
        service.sync_with_retry(mode=mode, triggered_by=triggered_by)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()
```

### Migration Path from threading.Thread

**Before** (current `api/v1/feishu.py` line 188-195):
```python
thread = threading.Thread(
    target=_run_sync_in_background,
    args=(data.mode, current_user.id),
    daemon=True,
)
thread.start()
```

**After:**
```python
from backend.app.tasks.feishu_tasks import feishu_sync_task
task = feishu_sync_task.delay(data.mode, current_user.id)
return SyncTriggerResponse(
    sync_log_id=task.id,
    status='running',
    message='同步已启动',
)
```

### APScheduler Coexistence

APScheduler in `scheduler/feishu_scheduler.py` can coexist with Celery. It handles periodic cron scheduling, separate from on-demand async tasks. Migrating to Celery Beat is optional and deferred.

### Redis DB Separation

Use separate Redis databases to avoid key namespace collisions:
- `redis://localhost:6379/0` -- app cache, rate limiting (existing)
- `redis://localhost:6379/1` -- Celery broker
- `redis://localhost:6379/2` -- Celery result backend

**Confidence:** HIGH -- Celery 5.4 with Redis broker is production-proven. The isolated-session pattern already exists in `feishu_scheduler.py`.

---

## Feature 2: Employee Company Field

### Current State

`Employee` model columns: `employee_no`, `name`, `id_card_no`, `department`, `sub_department`, `job_family`, `job_level`, `manager_id`, `status`, `hire_date`, `last_salary_adjustment_date`. No `company` field.

### Changes Required

1. **Model** (`backend/app/models/employee.py`):
   ```python
   company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
   ```
   Note: Uses `Optional[str]` not `str | None` for Python 3.9 compatibility with SQLAlchemy's `Mapped` eval.

2. **Migration**: `op.add_column('employees', sa.Column('company', sa.String(128), nullable=True))` with `batch_alter_table` for SQLite compat

3. **Schema** (`backend/app/schemas/employee.py`): Add `company: Optional[str] = None` to read schemas

4. **Import** (`backend/app/services/import_service.py`): Add `'所属公司': 'company'` to `COLUMN_ALIASES['employees']`

5. **Frontend**: Display company in employee detail page only (per spec: "仅档案详情可见")

**Impact scope:** Minimal. No engine logic, no eligibility rules, no API contracts affected.

**Confidence:** HIGH

---

## Feature 3: Python 3.9 Compatibility

### CRITICAL FINDING: `Mapped[str | None]` Breaks on Python 3.9

**This is the highest-impact change in v1.2.** Initial analysis suggested `from __future__ import annotations` would protect all PEP 604 union syntax. This is WRONG for SQLAlchemy `Mapped` and Pydantic `BaseModel` fields.

**Why `__future__` is insufficient:**
- `from __future__ import annotations` defers annotation evaluation by the Python interpreter
- BUT SQLAlchemy 2.0's `DeclarativeBase` explicitly calls `eval()` on `Mapped[T]` type parameters during class initialization to determine column types and nullable attributes
- Similarly, Pydantic v2's `ModelMetaclass` calls `typing.get_type_hints()` which evaluates annotations at runtime
- On Python 3.9, `eval("str | None")` raises `TypeError: unsupported operand type(s) for |`

**Scope of changes:**
- 20+ model files, 80+ occurrences of `Mapped[X | None]`
- 81 schema files, 361+ occurrences of `X | None` in Pydantic fields
- Total: ~440 replacements across ~100 files

**What MUST change:**
```python
# BEFORE (breaks on 3.9):
company: Mapped[str | None] = mapped_column(...)

# AFTER (works on 3.9):
from typing import Optional
company: Mapped[Optional[str]] = mapped_column(...)
```

```python
# BEFORE (breaks on 3.9 in Pydantic schemas):
class EmployeeRead(BaseModel):
    company: str | None = None

# AFTER:
from typing import Optional
class EmployeeRead(BaseModel):
    company: Optional[str] = None
```

**What does NOT need changing:**
- Regular function signatures: `def foo(x: str | None) -> str | None:` -- these are deferred by `__future__` and never eval'd at runtime
- Local variable annotations: `result: str | None = None` -- same reason

**Dependency downgrades required:**
- `numpy==2.2.1` -> `numpy==2.0.2` (2.2+ requires Python 3.10)
- `Pillow==11.0.0` -> `Pillow==10.4.0` (11+ requires Python 3.10)

**Confidence:** HIGH for the problem identification (verified via SQLAlchemy and Pydantic issue trackers). The fix is mechanical but broad.

---

## Feature 4: File Sharing Rejection Auto-Delete

### Current State

`SharingService.reject_request()` (lines 165-185) sets `sr.status = 'rejected'` but does NOT delete the requester's file.

`SharingRequest` model has `ondelete='CASCADE'` on `requester_file_id` FK. **However, SQLite does not enforce `ON DELETE CASCADE` by default** -- `database.py` has no `PRAGMA foreign_keys = ON`.

### Critical Prerequisite: Enable SQLite Foreign Keys

Before implementing auto-delete, fix `database.py` to enable FK enforcement:

```python
from sqlalchemy import event, Engine

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    if 'sqlite' in str(dbapi_conn.__class__.__module__):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
```

### Architecture Decision: Service Composition

**Recommended: Inject FileService into SharingService**

```python
class SharingService:
    def __init__(self, db: Session, *, file_service: FileService | None = None, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self._file_service = file_service

    @property
    def file_service(self) -> FileService:
        if self._file_service is None:
            self._file_service = FileService(self.db, self.settings)
        return self._file_service
```

### Modified reject_request Flow

**Order of operations matters** (CASCADE FK consideration):

```python
def reject_request(self, request_id, *, rejector_employee_id):
    # ... existing validation ...
    sr.status = 'rejected'
    sr.resolved_at = utc_now()
    self.db.flush()  # Persist rejection status FIRST

    # THEN delete requester's file (may trigger CASCADE)
    requester_file = self.db.get(UploadedFile, sr.requester_file_id)
    if requester_file is not None:
        # Use FileService for full cleanup (storage + evidence + DB)
        self.file_service.delete_file(requester_file.id)

    return sr
```

### Expired Request File Cleanup

Do NOT add file deletion to `_expire_stale_requests()` (it runs on every list/count query). Instead, create a separate Celery task for expired file cleanup:

```python
@celery_app.task
def cleanup_expired_sharing_files():
    """Periodic task to delete files from expired sharing requests."""
    # Run nightly via Celery Beat or cron
```

**Confidence:** HIGH -- `FileService.delete_file()` is well-tested. FK prerequisite is the main risk.

---

## Feature 5: Unified Eligibility Data Import Management

### Current State

**Backend -- all endpoints exist:**
- `POST /api/v1/imports/jobs` with `import_type=performance_grades` -- works
- `POST /api/v1/imports/jobs` with `import_type=salary_adjustments` -- works
- `FeishuService.sync_performance_records()` exists but has no API endpoint

**Frontend -- incomplete:**
- `ImportCenter.tsx` `IMPORT_TYPES` only includes `employees` and `certifications`
- `EligibilityManagementPage.tsx` has 2 tabs, no import tab

### Architecture: Unified Import Tab

Add a third tab "数据导入" to `EligibilityManagementPage`:

1. **Excel import** for `performance_grades` and `salary_adjustments` (reuses `ImportService`)
2. **Feishu bitable sync** for performance records (reuses `FeishuService`)
3. **Import history** filtered to eligibility-related types

### Backend Changes

1. Add `import_type` filter query param to `GET /imports/jobs`
2. Add `POST /api/v1/feishu/sync-performance` endpoint
3. Update `ImportCenter.tsx` `IMPORT_TYPES` to include all 4 types

### Frontend Component Reuse

Reuses existing: `ImportJobTable`, `ImportResultPanel`, `importService.ts` functions.

New in tab: import type selector, Feishu sync trigger, filtered history.

**Confidence:** MEDIUM -- backend ready, frontend needs UX design.

---

## Data Flow Diagrams

### Celery Task Flow

```
API Handler                  Redis (db 1)             Celery Worker
     |                          |                         |
     |-- task.delay(args) ----->|                         |
     |<-- task_id (immediate)---|                         |
     |                          |-- pick up task -------->|
     |                          |                         |-- engine.dispose()
     |                          |                         |-- SessionLocal()
     |                          |                         |-- service.method()
     |                          |                         |-- db.close()
     |                          |<-- store result (db 2)--|
```

### Rejection Auto-Delete Flow

```
POST /api/v1/sharing/{id}/reject
  |
  v
SharingService.reject_request()
  |-- Validate rejector == original uploader
  |-- sr.status = 'rejected', sr.resolved_at = utc_now()
  |-- db.flush()  (persist status BEFORE file deletion)
  |-- FileService.delete_file(sr.requester_file_id)
  |     |-- LocalStorageService.delete(storage_key)
  |     |-- Delete EvidenceItem records
  |     |-- db.delete(uploaded_file) -> CASCADE ProjectContributor
  |     |-- Recalculate submission status
  |-- Return rejected SharingRequest
```

---

## Patterns to Follow

### Pattern 1: Celery Task with Isolated Session + Engine Disposal
**What:** Dispose inherited engine, create fresh `SessionLocal()`, close in `finally`.
**When:** All Celery tasks touching the database.
**Why:** Fork-inherited connections are invalid; workers need fresh connections.
**Precedent:** `scheduler/feishu_scheduler.py:run_incremental_sync()`.

### Pattern 2: Service Composition via Optional Constructor Injection
**What:** Services accept optional collaborator services with lazy defaults.
**When:** One service needs another (SharingService needs FileService).
**Precedent:** All services accept `settings: Settings | None = None`.

### Pattern 3: Alembic Migration with batch_alter_table
**What:** Use `batch_alter_table` for all SQLite-touching migrations.
**When:** Any schema change to existing tables.
**Precedent:** Existing Alembic migrations in the project.

### Pattern 4: Optional[X] for Mapped/Pydantic, X | None for Function Sigs
**What:** Use `Optional[X]` in SQLAlchemy `Mapped` and Pydantic model fields; `X | None` is safe in function signatures.
**When:** Python 3.9 target environment.
**Why:** SQLAlchemy and Pydantic eval annotations at runtime; function sigs are deferred by `__future__`.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Celery Tasks Importing FastAPI Dependencies
**Instead:** Create `SessionLocal()` directly, instantiate services manually.

### Anti-Pattern 2: Async Celery Tasks
**Instead:** All tasks as regular `def` functions with synchronous SQLAlchemy.

### Anti-Pattern 3: Deleting Files Without FileService
**Instead:** Always use `FileService.delete_file()` for full cascade cleanup.

### Anti-Pattern 4: Adding Celery Beat Prematurely
**Instead:** Keep APScheduler for periodic tasks; Celery for on-demand async only.

### Anti-Pattern 5: Sharing Same Redis DB for Celery and Rate Limiter
**Instead:** Separate Redis databases (0, 1, 2) for different concerns.

---

## Build Order (Dependency-Aware)

```
Phase 1: Python 3.9 Compatibility (MUST BE FIRST -- blocker)
  - Downgrade numpy==2.0.2, Pillow==10.4.0
  - Replace Mapped[X | None] -> Mapped[Optional[X]] in all models (~20 files)
  - Replace X | None -> Optional[X] in all Pydantic schemas (~81 files)
  - Enable SQLite PRAGMA foreign_keys=ON in database.py
  - Test on Python 3.9 interpreter
  - WHY FIRST: Application cannot start on 3.9 without these changes

Phase 2: Celery+Redis Infrastructure
  - core/celery_app.py with separate Redis DBs
  - tasks/ package with feishu_tasks.py
  - worker_process_init signal for DB engine disposal
  - Migrate feishu.py from threading.Thread to task.delay()
  - Worker startup documentation
  - WHY SECOND: infrastructure for Phase 5

Phase 3: Employee Company Field (trivial)
  - Alembic migration with batch_alter_table
  - Model + schema changes (using Optional[str] syntax)
  - Import alias addition
  - Frontend detail page display
  - WHY HERE: quick win

Phase 4: Sharing Rejection Auto-Delete
  - Inject FileService into SharingService
  - Modify reject_request() with correct flush-then-delete ordering
  - Add pending/rejected status labels to outgoing sharing requests
  - Separate expired file cleanup (Celery task, not lazy expiry)
  - WHY HERE: self-contained

Phase 5: Unified Eligibility Import Management
  - Backend: import_type filter on list_jobs
  - Backend: Feishu performance sync endpoint
  - Frontend: "数据导入" tab in EligibilityManagementPage
  - Frontend: extend ImportCenter IMPORT_TYPES
  - WHY LAST: most complex, benefits from Celery
```

### Phase Ordering Rationale

- **Python 3.9 first:** Application literally cannot start on 3.9 without model/schema fixes and dependency downgrades. This is a hard blocker, not a nice-to-have.
- **Celery second:** Once the app starts on 3.9, build async infrastructure.
- **Company field third:** Small, uses patterns established in Phase 1.
- **Rejection auto-delete fourth:** Benefits from PRAGMA fix in Phase 1.
- **Eligibility import last:** Most complex frontend work; can use Celery from Phase 2.

---

## Sources

- Direct codebase analysis: all service, model, schema, API, and frontend files referenced above
- [SQLAlchemy Issue #9110](https://github.com/sqlalchemy/sqlalchemy/issues/9110): `Mapped[str | None]` fails on Python 3.9
- [Pydantic Issue #7923](https://github.com/pydantic/pydantic/issues/7923): PEP 604 unions fail on Python 3.9
- [SQLAlchemy Cascading Deletes](https://docs.sqlalchemy.org/en/20/orm/cascades.html): CASCADE behavior documentation
- Celery 5.4 documentation: task patterns, worker signals, Redis broker config
- `requirements.txt`: numpy==2.2.1 (requires 3.10+), Pillow==11.0.0 (requires 3.10+)
