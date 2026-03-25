# Feature Landscape: HR Evaluation & Salary Adjustment Platform

**Domain:** Enterprise HR salary adjustment with AI capability evaluation
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH (state machine patterns HIGH, explainability MEDIUM, PIPL compliance MEDIUM)

---

## 1. Explainable AI Evaluation — Making LLM Scores Traceable and Auditable

### The Core Problem

LLM-generated scores for employee evaluation are a black box by default. If an employee's AI capability assessment yields a score of 72/100 across five dimensions, the system must answer "why?" at every level — per dimension, per evidence item, per rule applied.

### Recommended Pattern: Chain-of-Thought Structured JSON Output

**Verdict: Use structured JSON prompts with CoT reasoning; store the full prompt + response snapshot.**

Prompt the LLM to reason step-by-step before scoring. Evidence from the LLM-as-a-Judge literature confirms this improves consistency by 10-15% and produces a debuggable reasoning trail. The key constraint is to separate each dimension into its own evaluation pass rather than bundling all five dimensions into one prompt — multi-criteria bundles reduce scoring accuracy.

```
For each of the 5 dimensions, produce a separate LLM call with a prompt that:
1. Provides the specific rubric for that dimension (e.g., "AI工具掌握度: 0-5 scale, criteria A/B/C")
2. Provides the employee's evidence for that dimension only
3. Requests: { "score": 0-5, "reasoning": "...", "evidence_cited": [...] }
4. Uses temperature=0 or 0.1 for reproducibility
```

The per-dimension output schema must be stored verbatim:

```python
class DimensionScore(BaseModel):
    dimension: str              # e.g., "AI工具掌握度"
    weight: float               # 0.15
    raw_score: float            # 0-5 from LLM
    weighted_score: float       # raw_score * weight
    reasoning: str              # LLM chain-of-thought
    evidence_cited: list[str]   # which uploaded files/items influenced this
    model_version: str          # DeepSeek version used
    prompt_hash: str            # SHA-256 of the prompt sent
    evaluated_at: datetime

class EvaluationRecord(BaseModel):
    employee_id: str
    dimension_scores: list[DimensionScore]
    total_score: float          # weighted sum
    ai_level: str               # Level 1-5
    system_salary_suggestion: float
    final_approved_salary: float | None  # filled after approval
    audit_overrides: list[AuditOverride]  # human reviewer changes
```

### Auditability Requirements

Every evaluation record must carry:

- `prompt_hash`: SHA-256 of the exact prompt sent to DeepSeek — allows replay
- `model_version`: The DeepSeek model identifier and version string
- `evaluated_at`: UTC timestamp
- `evidence_cited`: List of uploaded file IDs/names referenced in the reasoning
- Separation of `system_suggestion` vs `reviewer_override` vs `final_approved` — never overwrite original scores

**Rule:** Human reviewers may override dimension scores. Each override must create an `AuditOverride` record: `{dimension, original_score, override_score, reviewer_id, justification, timestamp}`. The original LLM score is never mutated.

### Anti-Pattern: Do Not

- Do not aggregate all 5 dimension evaluations into a single LLM call — this reduces per-dimension reliability
- Do not store only the final score — if you cannot replay the reasoning, the score is not auditable
- Do not use high temperature (>0.2) — evaluations must be reproducible on retry

### Libraries

- `gmssl` (pip install gmssl) — for hashing prompts with SM3 if PIPL-compliant hashing is required
- Standard `hashlib.sha256` is acceptable for prompt fingerprinting (this is not PII)
- Pydantic v2 `BaseModel` with `model_json_schema()` for schema documentation

---

## 2. Multi-Step Approval Workflow — State Machine in FastAPI/SQLAlchemy

### Recommended Pattern: `python-statemachine` v3.x bound to SQLAlchemy model

**Verdict: Use `python-statemachine` 3.0+ with an observer/listener for audit logging. Bind to SQLAlchemy model via a `MachineMixin` pattern. Do NOT use raw string status fields with manual if/else transitions.**

### State Graph

```
draft → submitted → manager_review → hr_review → approved
                                   ↘              ↗
                                    → rejected   (from either review stage)
                                   ↘
                                    → revision_requested → submitted (re-entry)
```

### Implementation Pattern

```python
# python-statemachine 3.x
from statemachine import StateMachine, State

class SalaryReviewMachine(StateMachine):
    draft            = State(initial=True)
    submitted        = State()
    manager_review   = State()
    hr_review        = State()
    approved         = State(final=True)
    rejected         = State(final=True)
    revision_needed  = State()

    submit           = draft.to(submitted) | revision_needed.to(submitted)
    start_mgr_review = submitted.to(manager_review)
    approve_by_mgr   = manager_review.to(hr_review)
    reject           = manager_review.to(rejected) | hr_review.to(rejected)
    request_revision = manager_review.to(revision_needed) | hr_review.to(revision_needed)
    approve_by_hr    = hr_review.to(approved, cond="salary_within_policy")
    force_approve    = hr_review.to(approved)   # override path

    def salary_within_policy(self):
        # guard: check salary delta against configurable policy thresholds
        return self.model.proposed_delta_pct <= self.model.policy_max_delta_pct
```

```python
# SQLAlchemy model integration
class SalaryAdjustment(Base):
    __tablename__ = "salary_adjustments"
    id          = Column(UUID, primary_key=True)
    employee_id = Column(UUID, ForeignKey("employees.id"))
    status      = Column(String(50), default="draft")
    ...

    def get_machine(self):
        m = SalaryReviewMachine(model=self)
        m.add_listener(WorkflowAuditListener(record_id=self.id))
        return m
```

```python
# Audit listener — registered as observer
class WorkflowAuditListener:
    def __init__(self, record_id, db_session=None):
        self.record_id = record_id
        self.db = db_session

    def after_transition(self, source, target, event):
        # write to audit_log table — never modify original record
        entry = WorkflowAuditLog(
            record_id=self.record_id,
            from_state=source.id,
            to_state=target.id,
            event=event,
            actor_id=current_actor_id(),   # from request context
            timestamp=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
```

### FastAPI Endpoint Pattern

```python
@router.post("/salary-adjustments/{record_id}/transitions/{event}")
async def trigger_transition(
    record_id: UUID,
    event: Literal["submit", "approve_by_mgr", "reject", "request_revision", "approve_by_hr"],
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(SalaryAdjustment, record_id)
    machine = record.get_machine()
    try:
        machine.send(event)
        record.status = machine.current_state.id
        await db.commit()
    except TransitionNotAllowed:
        raise HTTPException(422, f"Transition '{event}' not allowed from state '{record.status}'")
    return {"status": record.status}
```

### Database Schema for Audit Table

```sql
CREATE TABLE workflow_audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_id   UUID NOT NULL REFERENCES salary_adjustments(id),
    from_state  VARCHAR(50) NOT NULL,
    to_state    VARCHAR(50) NOT NULL,
    event       VARCHAR(50) NOT NULL,
    actor_id    UUID NOT NULL REFERENCES users(id),
    comment     TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_workflow_audit_record ON workflow_audit_log(record_id, created_at);
```

### Libraries

- `python-statemachine==3.0.0` — `pip install python-statemachine`
- `sqlalchemy-state-machine` (optional alternative for simpler workflows)
- Do NOT use `transitions` library — it is older, less maintained

### Key Rules

- Never let application code directly set `record.status = "approved"` — all state changes must flow through the machine
- Guards (`cond=`) enforce policy constraints before persistence — salary delta thresholds, approver role checks
- The `revision_needed → submitted` cycle is explicitly modelled so re-submissions are traceable
- Store both the current state and the full audit log — the log is the source of truth for "who approved what"

---

## 3. Bulk Import Patterns for HR Data

### Recommended Pattern: Pandera validation + per-row result tracking + idempotency key

**Verdict: Use `pandas.read_excel` for parsing, `pandera` for schema validation with `lazy=True`, per-row transaction isolation in SQLAlchemy, idempotency via employee_id + import_batch_id, and HTTP 207 Multi-Status for partial success responses.**

### Import Pipeline (5 stages)

```
Stage 1: File parsing   — pandas.read_excel / csv.reader
Stage 2: Schema check   — pandera lazy validation (collect ALL errors before failing)
Stage 3: Deduplication  — match rows against existing records by employee_id + period
Stage 4: Row processing — per-row try/except, independent DB transactions
Stage 5: Response       — 207 Multi-Status with per-row success/failure
```

### Pandera Schema for HR Import

```python
import pandera as pa
from pandera import Column, DataFrameSchema, Check

employee_import_schema = DataFrameSchema({
    "employee_id":  Column(str,   Check.str_matches(r"^EMP\d{6}$"), nullable=False),
    "name":         Column(str,   nullable=False),
    "department":   Column(str,   nullable=False),
    "job_level":    Column(str,   Check.isin(["P1","P2","P3","P4","P5","M1","M2"]), nullable=False),
    "current_salary": Column(float, Check.greater_than(0), nullable=False),
    "performance_grade": Column(str, Check.isin(["S","A","B","C","D"]), nullable=True),
    "national_id":  Column(str,   Check.str_length(18, 18), nullable=True),  # 18-digit Chinese ID
})

try:
    validated_df = employee_import_schema.validate(df, lazy=True)
except pa.errors.SchemaErrors as e:
    # e.failure_cases is a DataFrame of row-level failures
    # Convert to API-ready structure
    errors = e.failure_cases[["index","column","check","failure_case"]].to_dict("records")
```

### Idempotency: Deduplicate by Natural Key

```python
# Each row has a natural key: (employee_id, import_period)
# On conflict: UPDATE existing record (upsert), do not create duplicate

from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(EmployeeImportRecord).values(**row_data)
stmt = stmt.on_conflict_do_update(
    index_elements=["employee_id", "import_period"],
    set_={"salary": stmt.excluded.salary, "updated_at": func.now()}
)
await db.execute(stmt)
```

Alternatively, use an `Idempotency-Key` header (SHA-256 of file content) cached in Redis for 24h to prevent duplicate file submissions.

### Per-Row Transaction Isolation

```python
async def process_bulk_import(rows: list[dict], db: AsyncSession):
    results = []
    for idx, row in enumerate(rows):
        try:
            async with db.begin_nested():   # savepoint per row
                await upsert_employee(db, row)
            results.append({"index": idx, "status": 201, "employee_id": row["employee_id"]})
        except Exception as e:
            results.append({
                "index": idx,
                "status": 422,
                "employee_id": row.get("employee_id"),
                "error": {"type": type(e).__name__, "message": str(e)}
            })
    return results
```

### HTTP 207 Response Structure

```python
@router.post("/employees/bulk-import")
async def bulk_import(file: UploadFile, ...):
    ...
    succeeded = [r for r in results if r["status"] < 300]
    failed    = [r for r in results if r["status"] >= 300]

    overall_status = 201 if not failed else (207 if succeeded else 400)

    return JSONResponse(
        status_code=overall_status,
        content={
            "status": "partial_success" if failed and succeeded else ("success" if not failed else "failure"),
            "summary": {
                "total": len(results),
                "succeeded": len(succeeded),
                "failed": len(failed),
            },
            "results": results,   # full per-row detail
        }
    )
```

### Validation Error Categories for Client Retry Logic

| Error Type | HTTP Code | Retryable |
|-----------|-----------|-----------|
| Schema / format error | 422 | No — fix data |
| Duplicate key (already exists, identical data) | 200 | No — already done |
| Conflict (duplicate key, different data) | 409 | Investigate |
| Server error during processing | 500 | Yes |
| Rate limit / resource contention | 429 | Yes, with backoff |

### Libraries

- `pandas==2.x` — `pip install pandas openpyxl` (openpyxl required for .xlsx)
- `pandera==0.20+` — `pip install pandera` — row-level validation with lazy mode
- `python-multipart` — for FastAPI file uploads
- Optional: `pandantic` for Pydantic-based DataFrame validation

### Anti-Patterns

- Do not wrap the entire import in a single transaction — one bad row should not roll back 999 good rows
- Do not return only a count of errors — return row index + column + error message per failure
- Do not trust Excel column ordering — always read by column name, not position

---

## 4. Dashboard Analytics Patterns

### Recommended Pattern: Server-side aggregated endpoints + Recharts + Redis cache

**Verdict: Pre-compute all dashboard aggregations server-side. Do NOT send raw employee records to the frontend for client-side aggregation. Use Redis with 5-15 minute TTL for non-real-time metrics. Use WebSocket or polling (30s interval) only for "live" metrics like pending approval counts.**

### Chart Type to Data Mapping

| Dashboard Widget | Chart Type | Recharts Component | Data Strategy |
|---|---|---|---|
| Salary band distribution | Histogram / Bar | `BarChart` + `Bar` | Pre-aggregated by band |
| AI level distribution | Pie / Donut | `PieChart` + `Cell` | Pre-aggregated count per level |
| Salary adjustment trend | Line/Area | `AreaChart` + `Area` | Monthly aggregates |
| Department salary heatmap | Bar grouped | `BarChart` multiple `Bar` | Dept x level matrix |
| Certification completion | Progress bars | `RadialBarChart` | Count/total per stage |
| ROI per department | Bar chart | `BarChart` | Pre-computed ROI values |
| Pending approvals (live) | KPI card | Stat card + polling | 30s interval refresh |
| Score distribution | Histogram | `BarChart` with bins | Server-binned data |

### Recharts Implementation Patterns

**Always wrap in ResponsiveContainer:**

```tsx
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, Cell } from "recharts";

// AI Level distribution chart
const AILevelDistribution = ({ data }: { data: LevelCount[] }) => (
  <ResponsiveContainer width="100%" height={300}>
    <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
      <XAxis dataKey="level" />
      <YAxis />
      <Tooltip formatter={(value) => [`${value} 人`, "人数"]} />
      <Legend />
      <Bar dataKey="count" name="员工人数">
        {data.map((entry, index) => (
          <Cell key={index} fill={LEVEL_COLORS[entry.level]} />
        ))}
      </Bar>
    </BarChart>
  </ResponsiveContainer>
);
```

**Memoize chart data to prevent unnecessary re-renders:**

```tsx
const chartData = useMemo(() =>
  rawData.map(d => ({
    level: d.ai_level,
    count: d.employee_count,
    avg_salary_delta: (d.avg_salary_delta * 100).toFixed(1) + "%"
  })),
  [rawData]
);
```

**Real-time polling for KPI cards (pending approvals):**

```tsx
const usePendingApprovals = () => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const fetch = () => api.get("/dashboard/pending-approvals").then(r => setCount(r.data.count));
    fetch();
    const interval = setInterval(fetch, 30_000);  // 30-second poll
    return () => clearInterval(interval);
  }, []);
  return count;
};
```

### Backend Aggregation Endpoints

Pre-compute on the server, never expose raw employee data to dashboard queries:

```python
@router.get("/dashboard/salary-distribution")
async def salary_distribution(
    department: str | None = None,
    period: str = "2024-Q1",
    cache: Redis = Depends(get_redis),
):
    cache_key = f"dashboard:salary_dist:{department}:{period}"
    cached = await cache.get(cache_key)
    if cached:
        return json.loads(cached)

    # Query pre-aggregated view or compute here
    result = await db.execute(
        text("""
        SELECT salary_band, COUNT(*) as employee_count, AVG(adjustment_pct) as avg_adjustment
        FROM salary_adjustments
        WHERE period = :period
          AND (:dept IS NULL OR department = :dept)
        GROUP BY salary_band
        ORDER BY salary_band
        """),
        {"period": period, "dept": department}
    )
    data = [dict(row) for row in result]
    await cache.setex(cache_key, 900, json.dumps(data))  # 15-minute TTL
    return data
```

### Real-Time vs. Aggregated Boundary

| Metric | Strategy | Refresh |
|--------|----------|---------|
| Pending approvals count | Poll `/dashboard/pending` | 30 seconds |
| New evaluations today | Poll with Redis counter | 30 seconds |
| Salary distribution by band | Redis cache | 15 minutes |
| AI level distribution | Redis cache | 15 minutes |
| Department ROI | Redis cache | 1 hour |
| Historical trend (quarterly) | Pre-computed DB view | Daily batch job |
| Certification completion rate | Redis cache | 15 minutes |

### Libraries

- `recharts==2.x` — primary charting, already in most React projects
- `react-query` or `swr` — for data fetching with cache + revalidation instead of raw useEffect
- `fastapi-cache2` — `pip install fastapi-cache2[redis]` — decorator-based Redis caching for FastAPI

### Anti-Patterns

- Do not return paginated employee lists and aggregate in the frontend — this is O(n) browser computation for no benefit
- Do not poll faster than 30 seconds for non-critical metrics — unnecessary server load
- Do not use WebSocket for metrics that do not need sub-second freshness (HR dashboards never do)

---

## 5. China PIPL Compliance for Sensitive PII

### Regulatory Context

The Personal Information Protection Law (PIPL, effective 2021) and the new national standard GB/T 45574-2025 (effective November 2025) classify employee data including national ID numbers (身份证号), biometric data, and financial account information as **Sensitive Personal Information (敏感个人信息)**. Violations carry fines up to 5% of annual revenue.

Key constraint for internal enterprise tools: **China's Commercial Cryptography Regulations mandate SM-series algorithms (SM2/SM3/SM4) for encryption of personal information and "important data."** Standard international algorithms (AES, RSA) are technically prohibited for PIPL-regulated data in China, though enforcement is more focused on internet companies and data processors handling external user data.

Practical recommendation for this internal HR tool: Use SM4 for encrypting PII at rest, SM3 for integrity hashing. This aligns with the law and uses lightweight pure-Python implementations.

### Sensitive Fields in This System

| Field | Classification | Required Protection |
|-------|----------------|---------------------|
| 身份证号 (National ID) | Sensitive PII | Encrypt at rest, mask in API |
| 姓名 (Full name) | Personal Info | Mask partially in API |
| 手机号 (Phone number) | Personal Info | Mask in API |
| 薪资 (Salary data) | Financial/Confidential | Access-controlled, audit-logged |
| 绩效评级 (Performance grade) | Internal HR data | Role-based access |
| AI评分细节 (AI score details) | HR analytics | Role-based access |

### Encryption at Rest Pattern

```python
# pip install gmssl
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
import base64, os

SM4_KEY = os.environ["SM4_SECRET_KEY"].encode()  # 16 bytes, from env/secrets manager
IV = bytes(16)  # use a random IV per record in production

def encrypt_pii(plaintext: str) -> str:
    cipher = CryptSM4()
    cipher.set_key(SM4_KEY, SM4_ENCRYPT)
    encrypted = cipher.crypt_cbc(IV, plaintext.encode("utf-8"))
    return base64.b64encode(IV + encrypted).decode()

def decrypt_pii(ciphertext: str) -> str:
    raw = base64.b64decode(ciphertext)
    iv, data = raw[:16], raw[16:]
    cipher = CryptSM4()
    cipher.set_key(SM4_KEY, SM4_DECRYPT)
    return cipher.crypt_cbc(iv, data).decode("utf-8").rstrip('\x00')
```

Store encrypted values in the database. Never store plaintext national IDs.

### SQLAlchemy Column-Level Encryption

```python
from sqlalchemy import TypeDecorator, String
from app.utils.crypto import encrypt_pii, decrypt_pii

class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_pii(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_pii(value)

class Employee(Base):
    __tablename__ = "employees"
    id         = Column(UUID, primary_key=True)
    name       = Column(String(100))
    national_id = Column(EncryptedString(500))  # longer to hold base64+IV
    phone      = Column(EncryptedString(200))
```

This approach is transparent to the rest of the application — queries still use plaintext, but the ORM transparently encrypts/decrypts.

### API Response Masking with Pydantic v2

Apply masking at the Pydantic serialization layer — the decrypted value is obtained internally but the masked version is what leaves the API:

```python
from pydantic import BaseModel, field_serializer

class EmployeeResponse(BaseModel):
    id: str
    name: str
    national_id: str          # decrypted internally, masked in output
    phone: str

    @field_serializer("national_id")
    def mask_national_id(self, value: str) -> str:
        # Show first 6 and last 4 digits: 330104********1234
        if not value or len(value) != 18:
            return "******************"
        return value[:6] + "********" + value[-4:]

    @field_serializer("name")
    def mask_name(self, value: str) -> str:
        # Show first character only: 张**
        if not value:
            return value
        return value[0] + "*" * (len(value) - 1)

    @field_serializer("phone")
    def mask_phone(self, value: str) -> str:
        # Show first 3 and last 4: 138****5678
        if not value or len(value) < 7:
            return "***********"
        return value[:3] + "****" + value[-4:]
```

For privileged endpoints (HR admins, audit workflows), provide a separate unmasked response schema gated by role:

```python
class EmployeePrivilegedResponse(EmployeeResponse):
    # Override serializers to return full value for authorized users
    @field_serializer("national_id")
    def mask_national_id(self, value: str) -> str:
        return value  # no masking

    @field_serializer("name")
    def mask_name(self, value: str) -> str:
        return value
```

Route-level enforcement:

```python
@router.get("/employees/{id}", response_model=EmployeeResponse)
async def get_employee(id: UUID, current_user: User = Depends(get_current_user)):
    employee = await fetch_employee(id)
    if current_user.role in ("hr_admin", "auditor"):
        return EmployeePrivilegedResponse.model_validate(employee)
    return EmployeeResponse.model_validate(employee)
```

### PIPL Compliance Checklist

- [ ] National IDs and phone numbers stored encrypted with SM4
- [ ] SM4 key stored in environment variable or secrets manager (NOT in code or database)
- [ ] API responses mask PII by default; full data only to authorized roles
- [ ] All access to PII fields is logged (who, when, which record)
- [ ] Data retention: processing logs and assessment reports kept 3 years (per GB/T 45574-2025)
- [ ] Employee consent recorded for AI-based evaluation processing
- [ ] No PII in application logs, error messages, or exception tracebacks
- [ ] Cross-border data transfer avoided (keep all data in China infrastructure)

### Key Management

Do NOT manage encryption keys in the application database or code. Use:
- Environment variables for development
- A secrets manager (e.g., Vault, Alibaba Cloud KMS) for production
- Rotate SM4 keys periodically; maintain a key version column in the database for rolling re-encryption

---

## Feature Dependency Map

```
File Upload + Parsing
    ↓
DeepSeek Evaluation (5-dimension, structured JSON)
    ↓
AI Level Mapping + Salary Calculation
    ↓
Approval Workflow (State Machine)
    ↓
Dashboard Aggregation (Redis-cached)
    ↓
Bulk Import (runs in parallel with manual path)
    ↓
External API (read-only, masked PII, versioned)
```

---

## MVP Feature Priority

**Build first (table stakes):**
1. File upload and extraction (PDFs, images, code files)
2. Per-dimension DeepSeek evaluation with structured JSON output
3. Salary calculation engine (5-level matrix + certification bonuses)
4. Basic approval workflow (draft → submitted → manager → hr → approved)
5. PII field encryption at rest + API masking

**Build second (differentiators):**
6. Dashboard with AI level distribution and salary band charts
7. Bulk Excel import with per-row error reporting
8. Human reviewer override with audit trail

**Defer (complexity without immediate value):**
9. External REST API for third-party HR systems — defer until internal workflows are stable
10. Real-time WebSocket dashboard updates — 30s polling is sufficient for this use case
11. OCR for scanned PDF materials — add after basic upload pipeline works

---

## Sources

- [python-statemachine 3.0 documentation](https://python-statemachine.readthedocs.io/en/latest/index.html) — state machine patterns, observer/listener API
- [python-statemachine transitions](https://python-statemachine.readthedocs.io/en/latest/transitions.html) — guard conditions, callback hooks
- [Pandera error report documentation](https://pandera.readthedocs.io/en/latest/error_report.html) — lazy validation, row-level error collection
- [Bulk API partial success patterns](https://oneuptime.com/blog/post/2026-02-02-rest-bulk-api-partial-success/view) — HTTP 207, per-item status codes, retry categorization
- [LLM-as-a-Judge: complete guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) — structured JSON output, CoT scoring, reproducibility
- [China PIPL technical overview (Skyflow)](https://www.skyflow.com/post/china-data-residency-pipl-compliance) — tokenization, data residency, encryption requirements
- [GB/T 45574-2025 sensitive PII standard (Morgan Lewis)](https://www.morganlewis.com/pubs/2025/06/china-issues-new-national-standard-on-security-requirements-for-sensitive-personal-information) — sensitive data categories, 3-year retention requirement
- [gmssl Python package](https://github.com/knitmesh/gmssl) — SM2/SM3/SM4 implementation
- [SM4/SM3 algorithm overview](https://www.onlinehashcrack.com/guides/cryptography-algorithms/sm4-sm3-algorithms-china-s-standards-explained.php) — China commercial cryptography mandates
- [Pydantic SecretStr and field_serializer](https://www.getorchestra.io/guides/pydantic-secret-types-handling-sensitive-data-securely-with-secretstr-and-secretbytes) — API response masking patterns
- [Recharts dashboard patterns (Ecosire)](https://ecosire.com/blog/recharts-data-visualization-guide) — ResponsiveContainer, useMemo, real-time polling
- [FastAPI Redis caching (Redis.io)](https://redis.io/tutorials/develop/python/fastapi/) — cache-aside pattern, TTL strategy
- [China PIPL compliance guide (China Briefing)](https://www.china-briefing.com/doing-business-guide/china/company-establishment/pipl-personal-information-protection-law) — legal framework and penalties
