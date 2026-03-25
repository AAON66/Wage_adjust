# Architecture Patterns: Enterprise Salary Adjustment Platform

**Domain:** HR Analytics & Salary Adjustment — FastAPI layered backend
**Researched:** 2026-03-25
**Overall confidence:** HIGH (all major claims verified against official docs or multiple current sources)

---

## 1. Public REST API Design for HR System Integration

### Versioning Strategy

**Use URL-prefix versioning.** Header-based versioning is harder to route, test, and proxy. Path versioning (`/api/v1/public/`) is explicit, cacheable, and the dominant pattern in HR integration scenarios.

```python
# backend/app/api/v1/public.py
from fastapi import APIRouter, Security
from app.core.security import verify_api_key

router = APIRouter(
    prefix="/api/v1/public",
    tags=["public-api"],
    dependencies=[Security(verify_api_key)],
)
```

Include the version at the `APIRouter` prefix level, not at the individual route level. This makes it trivial to mount a `v2` router later without touching existing routes.

**Deprecation pattern** — when v2 ships, add to all v1 responses:

```python
from fastapi import Response

@router.get("/employees/{employee_no}/latest-evaluation")
async def get_evaluation(employee_no: str, response: Response):
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 01 Jan 2027 00:00:00 GMT"
    response.headers["Link"] = '</api/v2/public/employees/{employee_no}/latest-evaluation>; rel="successor-version"'
    ...
```

Mark routes as `deprecated=True` in FastAPI to surface them in OpenAPI docs.

### Pagination

Use **cursor-based pagination** for incremental sync (the primary HR integration use case), and **offset pagination** for UI list views.

```python
# schemas/pagination.py
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")

class CursorPage(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[str] = None   # opaque, base64-encoded last-row id + timestamp
    has_more: bool
    total_count: Optional[int] = None   # omit for large datasets

class OffsetPage(BaseModel, Generic[T]):
    data: List[T]
    page: int
    page_size: int
    total: int
    total_pages: int
```

Cursor must be opaque to the caller. Encode `(id, created_at)` as base64 JSON so you can paginate reliably even when rows insert between page fetches.

```python
import base64, json
from datetime import datetime

def encode_cursor(id: str, created_at: datetime) -> str:
    payload = {"id": id, "ts": created_at.isoformat()}
    return base64.b64encode(json.dumps(payload).encode()).decode()

def decode_cursor(cursor: str) -> dict:
    return json.loads(base64.b64decode(cursor).decode())
```

External endpoints use `?after_cursor=<token>&limit=100` with default limit 100, max 500.

### Webhook Notifications

FastAPI 0.99+ supports documenting outbound webhook payloads natively via `app.webhooks`. This appears in OpenAPI docs automatically — useful when HR system integrators need to autogenerate their receiver code.

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class SalaryResultPublished(BaseModel):
    event: str                     # "salary_result.published"
    cycle_id: str
    employee_no: str
    adjustment_ratio: float        # the only field exposed externally
    effective_date: str
    timestamp: str

@app.webhooks.post("salary-result-published")
def salary_result_published(body: SalaryResultPublished):
    """
    Fired when a salary adjustment result is locked and published.
    Register your receiver URL via POST /api/v1/public/webhooks/subscriptions.
    """
```

**Webhook subscription table** — store in DB, not config:

```python
class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    target_url: Mapped[str]                        # caller's HTTPS endpoint
    event_types: Mapped[list] = mapped_column(ARRAY(String))  # ["salary_result.published"]
    secret: Mapped[str]                            # HMAC signing secret, store hashed
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime]
```

Deliver via background task with HMAC-SHA256 signing. Retry up to 3 times with exponential backoff. Log each delivery attempt.

```python
import hmac, hashlib, httpx
from fastapi import BackgroundTasks

async def deliver_webhook(subscription_id: str, payload: dict):
    sub = await get_subscription(subscription_id)
    body = json.dumps(payload).encode()
    sig = hmac.new(sub.secret.encode(), body, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient() as client:
        await client.post(
            sub.target_url,
            content=body,
            headers={"X-Signature-SHA256": f"sha256={sig}", "Content-Type": "application/json"},
            timeout=10.0,
        )
```

### API Key Management

Use `X-API-Key` header. Store keys as bcrypt hashes (or SHA-256 prefix for lookup + bcrypt for full verify). Never log raw keys.

```python
# core/security.py
import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyRecord:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    # Use constant-time comparison to prevent timing attacks
    record = await db.scalar(
        select(ApiKeyRecord).where(ApiKeyRecord.key_prefix == api_key[:8])
    )
    if not record or not secrets.compare_digest(
        hashlib.sha256(api_key.encode()).hexdigest(),
        record.key_hash,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return record
```

**API key table:**

```python
class ApiKeyRecord(Base):
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str]                              # "SAP HR Integration - Production"
    key_prefix: Mapped[str] = mapped_column(index=True)  # first 8 chars for lookup
    key_hash: Mapped[str]                          # SHA-256 of full key
    scopes: Mapped[list] = mapped_column(ARRAY(String))  # ["read:evaluations", "read:salary"]
    rate_limit_per_hour: Mapped[int] = mapped_column(default=1000)
    created_by: Mapped[uuid.UUID]                  # FK to users
    last_used_at: Mapped[Optional[datetime]]
    expires_at: Mapped[Optional[datetime]]
    is_active: Mapped[bool] = mapped_column(default=True)
```

Key rotation: generate new key, return it once (never store plaintext), old key stays active for a configurable overlap window (e.g., 7 days), then deactivate.

---

## 2. Role-Aware Response Filtering in FastAPI

### The Core Pattern: Schema Inheritance + Conditional Return

Do not use `response_model_include`/`response_model_exclude` at the route level for role filtering — it is fragile and hard to audit. Instead, define a schema hierarchy and return the correct model instance from the route handler.

```python
# schemas/salary.py
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

class SalaryRecommendationEmployee(BaseModel):
    """Visible to the employee themselves."""
    id: str
    employee_no: str
    ai_level: str
    recommended_ratio: float           # adjustment % only, no absolutes
    certification_bonus: float
    status: str

class SalaryRecommendationManager(SalaryRecommendationEmployee):
    """Adds current/recommended salary for manager and above."""
    current_salary: Decimal
    recommended_salary: Decimal
    ai_multiplier: float

class SalaryRecommendationHRBP(SalaryRecommendationManager):
    """Adds internal notes and final approved value for HRBP."""
    final_adjustment_ratio: Optional[float]
    budget_flag: Optional[str]         # "over_budget", "equity_risk", etc.

class SalaryRecommendationAdmin(SalaryRecommendationHRBP):
    """Full detail for admin — includes raw engine outputs."""
    engine_debug: Optional[dict]
    override_history: Optional[list]
```

**Route handler — select schema by role:**

```python
# api/v1/salary.py
from app.schemas.salary import (
    SalaryRecommendationEmployee,
    SalaryRecommendationManager,
    SalaryRecommendationHRBP,
    SalaryRecommendationAdmin,
)
from app.core.security import CurrentUser, require_role

ROLE_SCHEMA_MAP = {
    "employee": SalaryRecommendationEmployee,
    "manager": SalaryRecommendationManager,
    "hrbp": SalaryRecommendationHRBP,
    "admin": SalaryRecommendationAdmin,
}

@router.get("/salary/{recommendation_id}")
async def get_salary_recommendation(
    recommendation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await salary_service.get_recommendation(db, recommendation_id)

    # Ownership check: employees can only see their own record
    if current_user.role == "employee" and rec.employee_id != current_user.employee_id:
        raise HTTPException(status_code=403)

    schema_class = ROLE_SCHEMA_MAP.get(current_user.role, SalaryRecommendationEmployee)
    return schema_class.model_validate(rec)
```

**Why `model_validate` not `schema_class(**rec.__dict__)`:** `model_validate` works with SQLAlchemy ORM objects directly (Pydantic v2), handles nested relationships, and correctly applies field validators.

### Dependency: CurrentUser with Role

```python
# core/security.py
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_jwt(token)
    user = await db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401)
    return user

# Type alias for annotated dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Visibility Matrix

| Field | employee | manager | hrbp | admin |
|-------|----------|---------|------|-------|
| `ai_level` | Yes | Yes | Yes | Yes |
| `recommended_ratio` | Yes (own only) | Yes (team) | Yes (all) | Yes |
| `current_salary` | No | Yes | Yes | Yes |
| `recommended_salary` | No | Yes | Yes | Yes |
| `final_adjustment_ratio` | No | No | Yes | Yes |
| `engine_debug` | No | No | No | Yes |
| `override_history` | No | No | Yes | Yes |

**Critical rule:** The employee role dependency must enforce ownership (employee can only see their own record). Manager scope enforcement (team-only visibility) belongs in the query, not the schema — add a `WHERE manager_id = :current_user_id` clause when the caller is a manager.

---

## 3. Audit Log Patterns in SQLAlchemy

### Schema

```python
# models/audit_log.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, JSON, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    # WHO
    operator_id: Mapped[Optional[uuid.UUID]]       # null for system/API-key actions
    operator_role: Mapped[Optional[str]] = mapped_column(String(20))
    api_key_id: Mapped[Optional[uuid.UUID]]        # set when action via public API
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    request_id: Mapped[Optional[str]] = mapped_column(String(64))
    # WHAT
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "evaluation.confirm", "salary.approve", "salary.override"
    # WHERE (polymorphic target)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "ai_evaluation", "salary_recommendation", "employee"
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # RESULT
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    # "success" | "failure" | "rejected"
    detail: Mapped[Optional[dict]] = mapped_column(JSON)
    # structured delta: {"before": {...}, "after": {...}} or {"reason": "..."}

    __table_args__ = (
        # Primary query: "show me everything that happened to this evaluation"
        Index("ix_audit_target", "target_type", "target_id"),
        # Secondary query: "what did this user do today?"
        Index("ix_audit_operator", "operator_id", "created_at"),
        # Tertiary query: "all approval actions in cycle X timeframe"
        Index("ix_audit_action_time", "action", "created_at"),
    )
```

**Why not a FK to `users`?** Audit logs are forensic records. If a user is deleted, the log must still show who acted. Store `operator_id` as a plain UUID without a FK constraint.

**Why composite indexes instead of single-column?** The three most common audit queries are: by target (entity history), by operator+time (user activity report), and by action+time (compliance report). Each composite index covers its query pattern without a full-table scan.

### Append Pattern — Never Update or Delete

```python
# services/audit_service.py
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditContext

async def record(
    db: AsyncSession,
    ctx: AuditContext,
    action: str,
    target_type: str,
    target_id: str,
    result: str = "success",
    detail: Optional[dict] = None,
) -> None:
    """Fire-and-forget append. Never updates existing rows."""
    log = AuditLog(
        operator_id=ctx.operator_id,
        operator_role=ctx.operator_role,
        api_key_id=ctx.api_key_id,
        ip_address=ctx.ip_address,
        request_id=ctx.request_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        result=result,
        detail=detail,
    )
    db.add(log)
    # Do NOT await flush here; let it commit with the parent transaction
    # so log and business mutation are atomic
```

**Call site in service layer:**

```python
async def confirm_evaluation(db, evaluation_id, ctx: AuditContext):
    eval_ = await db.get(AIEvaluation, evaluation_id)
    eval_.status = "confirmed"
    await audit_service.record(
        db, ctx,
        action="evaluation.confirm",
        target_type="ai_evaluation",
        target_id=evaluation_id,
        detail={"previous_status": "reviewed", "confirmed_level": eval_.ai_level},
    )
    await db.commit()   # audit log and status change commit together
```

### AuditContext — Middleware Collects, Service Consumes

```python
# schemas/audit.py
from pydantic import BaseModel
from typing import Optional
import uuid

class AuditContext(BaseModel):
    operator_id: Optional[uuid.UUID] = None
    operator_role: Optional[str] = None
    api_key_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None

# dependencies.py
async def get_audit_context(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
) -> AuditContext:
    return AuditContext(
        operator_id=current_user.id if current_user else None,
        operator_role=current_user.role if current_user else None,
        ip_address=request.client.host,
        request_id=request.headers.get("X-Request-ID"),
    )
```

Inject `AuditContext` as a dependency alongside `db` in service calls. Never build it inside the service — keep services testable without HTTP context.

### Querying the Audit Log Efficiently

```python
# Query by entity (entity history page)
stmt = (
    select(AuditLog)
    .where(AuditLog.target_type == "salary_recommendation")
    .where(AuditLog.target_id == recommendation_id)
    .order_by(AuditLog.created_at.desc())
)

# Query by user activity
stmt = (
    select(AuditLog)
    .where(AuditLog.operator_id == user_id)
    .where(AuditLog.created_at >= start_date)
    .order_by(AuditLog.created_at.desc())
    .limit(100)
)
```

For compliance exports (large time-range scans), use `yield_per` to stream rows without loading everything into memory:

```python
result = await db.stream_scalars(
    select(AuditLog).where(AuditLog.created_at >= start).order_by(AuditLog.created_at)
)
async for log in result:
    yield log  # stream to CSV writer
```

---

## 4. Database Migration Strategies with Alembic

### The Expand-Contract Pattern (Mandatory for Production)

Every schema change that could break running application instances must use expand-contract. This is especially important for this project because:
- Dev uses SQLite; production uses PostgreSQL — migration behavior differs
- Salary data is never offline; zero-downtime is a hard requirement

**Three phases, three deploys:**

```
Phase 1 (Expand):    Add new structure. Old code still works.
Phase 2 (Migrate):   Backfill data. Both old and new code work.
Phase 3 (Contract):  Remove old structure. New code only.
```

**Alembic branch labels for expand/contract:**

```python
# alembic/versions/001_expand_add_adjustment_ratio.py
revision = "abc123"
down_revision = "base_revision"
branch_labels = ("expand",)

def upgrade():
    op.add_column(
        "salary_recommendations",
        sa.Column("adjustment_ratio_v2", sa.Numeric(10, 4), nullable=True),
    )

def downgrade():
    op.drop_column("salary_recommendations", "adjustment_ratio_v2")
```

```python
# alembic/versions/002_contract_drop_old_column.py
revision = "def456"
down_revision = "abc123"
branch_labels = ("contract",)

def upgrade():
    op.alter_column("salary_recommendations", "adjustment_ratio_v2", nullable=False)
    op.drop_column("salary_recommendations", "adjustment_ratio")

def downgrade():
    op.add_column(
        "salary_recommendations",
        sa.Column("adjustment_ratio", sa.Float, nullable=True),
    )
```

Apply separately:

```bash
alembic upgrade expand    # deploy 1 — add nullable column
# [run data backfill script or migration job]
alembic upgrade contract  # deploy 2 — enforce NOT NULL, drop old column
```

### Safe Operation Reference

| Operation | Safe? | Pattern |
|-----------|-------|---------|
| Add nullable column | YES — always safe | Single migration |
| Add NOT NULL column | NO — locks table | Add nullable → backfill → NOT NULL separately |
| Rename column | NO — breaks references | Add new → copy → drop old (3 deploys) |
| Drop column | Only after code removed | Contract phase only |
| Add index | DANGER on large tables | Use `CREATE INDEX CONCURRENTLY` |
| Add FK constraint | Risky with existing data | Validate=False first, then validate |
| Add unique constraint | Risky | Create as DEFERRABLE or validate separately |

### CREATE INDEX CONCURRENTLY in Alembic

Standard `op.create_index()` wraps everything in a transaction. `CONCURRENTLY` cannot run in a transaction. Use `autocommit_block`:

```python
def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_audit_logs_target",
            "audit_logs",
            ["target_type", "target_id"],
            postgresql_concurrently=True,
            if_not_exists=True,   # idempotent — safe to re-run
        )
```

Always add `if_not_exists=True` on concurrent indexes so the migration is idempotent if it fails mid-way.

### Lock Timeouts — Prevent Long Lock Waits

Set timeouts at the start of every migration that touches large tables:

```python
def upgrade():
    op.execute("SET lock_timeout = '3s'")       # fail fast if can't acquire lock
    op.execute("SET statement_timeout = '60s'") # kill runaway DDL

    op.add_column(
        "employees",
        sa.Column("ai_certification_stage", sa.String(30), nullable=True),
    )
```

### Brownfield Initialization (Existing App, Adding Alembic)

If the project already has tables and you're adding Alembic:

```bash
# Step 1: Tell Alembic the current schema is baseline
alembic stamp head

# Step 2: Generate future migrations normally
alembic revision --autogenerate -m "add webhook_subscriptions"
```

In `alembic/env.py`, target the models so autogenerate detects new tables:

```python
from app.models import *  # noqa: F401  — import all models so metadata is populated
from app.core.database import Base

target_metadata = Base.metadata
```

### SQLite Dev vs PostgreSQL Prod

SQLite does not support `ALTER TABLE ... ALTER COLUMN`, `CONCURRENTLY`, or most constraint operations. For dev, disable batch mode selectively:

```python
def upgrade():
    dialect = op.get_context().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("employees") as batch_op:
            batch_op.add_column(sa.Column("new_field", sa.String, nullable=True))
    else:
        op.add_column("employees", sa.Column("new_field", sa.String, nullable=True))
```

**Recommendation:** Use PostgreSQL even in development (via Docker) to catch migration incompatibilities before they reach staging. SQLite is only acceptable for unit tests with in-memory databases.

---

## 5. Dashboard Query Optimization

### Rule 1: Aggregate in SQL, Not Python

Never load a full table to compute counts or sums in Python. Use SQL aggregation and let PostgreSQL's query planner optimize it.

```python
# WRONG — loads all submissions into Python
submissions = await db.scalars(select(EmployeeSubmission))
level_counts = Counter(s.ai_level for s in submissions)   # N rows in memory

# CORRECT — database computes the aggregation
from sqlalchemy import func

stmt = (
    select(
        AIEvaluation.ai_level,
        func.count(AIEvaluation.id).label("count"),
    )
    .where(AIEvaluation.cycle_id == cycle_id)
    .where(AIEvaluation.status == "confirmed")
    .group_by(AIEvaluation.ai_level)
)
result = await db.execute(stmt)
level_distribution = {row.ai_level: row.count for row in result}
```

### Rule 2: Eliminate N+1 Loads

N+1 manifests when you load a list and then per-item access a relationship. Use `selectinload` for one-to-many (collections) and `joinedload` for many-to-one (single object).

```python
# WRONG — triggers N queries for dimension_scores
evaluations = await db.scalars(select(AIEvaluation).where(...))
for ev in evaluations:
    scores = ev.dimension_scores   # lazy load per evaluation

# CORRECT — 2 queries total regardless of N
stmt = (
    select(AIEvaluation)
    .options(selectinload(AIEvaluation.dimension_scores))
    .where(AIEvaluation.cycle_id == cycle_id)
)
evaluations = await db.scalars(stmt)
```

Use `joinedload` for many-to-one (employee → manager lookup):

```python
stmt = (
    select(EmployeeSubmission)
    .options(
        joinedload(EmployeeSubmission.employee),
        selectinload(EmployeeSubmission.uploaded_files),
    )
    .where(EmployeeSubmission.cycle_id == cycle_id)
)
```

**Async important:** With `AsyncSession`, lazy loading raises `MissingGreenlet` errors. You must use `selectinload`/`joinedload` explicitly — there is no fallback to implicit lazy loading in async mode.

### Rule 3: Caching Dashboard Results with fastapi-cache2 + Redis

Dashboard queries (level distribution, budget usage, department heatmap) are expensive and change at most every few minutes. Cache them.

```bash
pip install fastapi-cache2[redis]
```

```python
# main.py
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis.asyncio import Redis

@app.on_event("startup")
async def startup():
    redis = Redis.from_url("redis://localhost:6379")
    FastAPICache.init(RedisBackend(redis), prefix="wage-adjust-cache")
```

```python
# api/v1/dashboard.py
from fastapi_cache.decorator import cache

@router.get("/dashboard/ai-level-distribution")
@cache(expire=300)   # 5 minutes — level distribution changes only when evaluations confirm
async def get_level_distribution(cycle_id: str, db: AsyncSession = Depends(get_db)):
    ...

@router.get("/dashboard/overview")
@cache(expire=60)    # 1 minute — overview metrics change more frequently
async def get_overview(cycle_id: str, db: AsyncSession = Depends(get_db)):
    ...
```

**Cache invalidation on mutation:** When an evaluation is confirmed or a salary recommendation is approved, explicitly invalidate the affected cache keys.

```python
from fastapi_cache import FastAPICache

async def invalidate_dashboard_cache(cycle_id: str):
    backend = FastAPICache.get_backend()
    for key_suffix in ["ai-level-distribution", "overview", "department-heatmap", "salary-budget"]:
        await backend.clear(key=f"wage-adjust-cache:dashboard:{cycle_id}:{key_suffix}")
```

**Cache key must include cycle_id and user role** to prevent data leakage between cycles or roles:

```python
from fastapi_cache.decorator import cache

def dashboard_key_builder(func, *args, **kwargs):
    cycle_id = kwargs.get("cycle_id", "all")
    user = kwargs.get("current_user")
    role = user.role if user else "anonymous"
    return f"wage-adjust-cache:dashboard:{cycle_id}:{role}:{func.__name__}"

@router.get("/dashboard/salary-budget")
@cache(expire=120, key_builder=dashboard_key_builder)
async def get_salary_budget(
    cycle_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ...
```

**Do not cache salary detail responses** (individual employee salary data). Only cache aggregate/statistical views.

### TTL Strategy by Endpoint Type

| Endpoint | TTL | Reason |
|----------|-----|--------|
| `dashboard/overview` | 60s | Changes as approvals complete |
| `dashboard/ai-level-distribution` | 300s | Only changes on evaluation confirm |
| `dashboard/department-heatmap` | 300s | Evaluation-driven, low churn |
| `dashboard/salary-budget` | 120s | Approval-driven changes |
| `public/cycles/{id}/salary-results` | 600s | Published data is immutable |
| `public/employees/{no}/latest-evaluation` | 300s | Changes only on cycle publish |

### Rule 4: Efficient Multi-Join Dashboard Queries

For the overview card (total employees, by-level counts, budget used), use a single CTE query rather than 4 separate queries:

```python
from sqlalchemy import select, func, case
from sqlalchemy.orm import aliased

async def get_cycle_overview(db: AsyncSession, cycle_id: str) -> dict:
    stmt = (
        select(
            func.count(EmployeeSubmission.id).label("total_submissions"),
            func.sum(
                case(
                    (AIEvaluation.ai_level == "level5", 1),
                    else_=0,
                )
            ).label("level5_count"),
            func.sum(SalaryRecommendation.recommended_salary).label("total_recommended_budget"),
            func.sum(SalaryRecommendation.current_salary).label("current_budget_base"),
        )
        .select_from(EmployeeSubmission)
        .outerjoin(AIEvaluation, AIEvaluation.submission_id == EmployeeSubmission.id)
        .outerjoin(
            SalaryRecommendation,
            SalaryRecommendation.evaluation_id == AIEvaluation.id,
        )
        .where(EmployeeSubmission.cycle_id == cycle_id)
    )
    row = (await db.execute(stmt)).one()
    return {
        "total_submissions": row.total_submissions,
        "level5_count": row.level5_count or 0,
        "budget_increase_pct": (
            (row.total_recommended_budget - row.current_budget_base) / row.current_budget_base * 100
            if row.current_budget_base else 0
        ),
    }
```

### Rule 5: Index the Right Columns

Dashboard queries filter primarily on `cycle_id` and `status`. Add composite indexes:

```python
# In your Alembic migration (via model __table_args__)
__table_args__ = (
    Index("ix_submission_cycle_status", "cycle_id", "status"),
    Index("ix_evaluation_cycle_level", "cycle_id", "ai_level", "status"),
    Index("ix_salary_evaluation_status", "evaluation_id", "status"),
)
```

For audit log compliance queries spanning large date ranges, add a partial index on high-volume action types:

```sql
CREATE INDEX CONCURRENTLY ix_audit_approval_actions
ON audit_logs (created_at)
WHERE action LIKE 'salary.%' OR action LIKE 'evaluation.%';
```

---

## Component Boundaries Summary

| Component | Responsibility | Must NOT do |
|-----------|---------------|-------------|
| `api/v1/*.py` | Route declaration, auth deps, schema selection by role | Business logic, DB queries |
| `services/*.py` | Orchestrate business operations, write audit logs | Direct HTTP response construction |
| `engines/*.py` | Pure calculation — evaluation scoring, salary math | DB access, HTTP calls |
| `schemas/*.py` | Input validation, role-stratified output models | Computation, DB access |
| `models/*.py` | ORM definitions, table indexes | Business rules |
| `parsers/*.py` | File-to-structured-data extraction | Scoring, DB writes |

**Audit log write rule:** All writes to `audit_logs` happen inside services, never in API routes or engines. This keeps audit coverage consistent regardless of how a service is invoked (HTTP, background task, or admin CLI).

**Salary field visibility rule:** The `current_salary` and `recommended_salary` raw values must never appear in `SalaryRecommendationEmployee` schema or any public API schema. This is enforced by schema inheritance — the fields simply do not exist on the base class.

---

## Sources

- FastAPI OpenAPI Webhooks (official): https://fastapi.tiangolo.com/advanced/openapi-webhooks/
- FastAPI Response Model (official): https://fastapi.tiangolo.com/tutorial/response-model/
- FastAPI Security Tools (official): https://fastapi.tiangolo.com/reference/security/
- SQLAlchemy 2.0 Relationship Loading (official): https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
- Alembic Operation Reference (official): https://alembic.sqlalchemy.org/en/latest/ops.html
- Zero-Downtime Upgrades with Alembic (that.guru): https://that.guru/blog/zero-downtime-upgrades-with-alembic-and-sqlalchemy/
- Alembic Migrations Without Downtime (Exness Tech Blog): https://medium.com/exness-blog/alembic-migrations-without-downtime-a3507d5da24d
- FastAPI Cache Strategies Boilerplate: https://benavlabs.github.io/FastAPI-boilerplate/user-guide/caching/cache-strategies/
- FastAPI Audit Log Design (greeden.me, March 2026): https://blog.greeden.me/en/2026/03/17/a-practical-introduction-to-audit-log-design-in-fastapi-design-and-implementation-patterns-for-safely-recording-who-did-what-and-when/
- FastAPI Response Filtering (compilenrun.com): https://www.compilenrun.com/docs/framework/fastapi/fastapi-response-handling/fastapi-response-filtering/
- SQLAlchemy 2.0 with FastAPI (oneuptime.com, Jan 2026): https://oneuptime.com/blog/post/2026-01-27-sqlalchemy-fastapi/view
- FastAPI Performance Caching 101 (greeden.me, Feb 2026): https://blog.greeden.me/en/2026/02/03/fastapi-performance-tuning-caching-strategy-101-a-practical-recipe-for-growing-a-slow-api-into-a-lightweight-fast-api/
- PostgreSQL CREATE INDEX Documentation (official): https://www.postgresql.org/docs/current/sql-createindex.html
- CREATE INDEX CONCURRENTLY with Alembic (GitHub issue): https://github.com/sqlalchemy/alembic/issues/277
- FastAPI Enterprise RBAC and Auditing (squash.io): https://www.squash.io/implementing-fastapi-enterprise-functionalities-sso-rbac-and-auditing/
- API Key Management Best Practices (oneuptime.com, Feb 2026): https://oneuptime.com/blog/post/2026-02-20-api-key-management-best-practices/view
- fastapi-cache2 PyPI: https://pypi.org/project/fastapi-cache2/
