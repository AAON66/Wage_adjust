# Testing Patterns

**Analysis Date:** 2026-03-25

## Summary

The project has substantial backend test coverage using pytest with a clear domain-based organization. All tests are integration-style: they spin up real SQLite databases with unique paths and test through real service/API boundaries. No mocking framework is used — instead, injectable collaborators (LLM services, HTTP clients) are replaced by explicit stub classes or `httpx.MockTransport`. The frontend has no test files or test framework configured.

---

## Test Framework

**Runner:**
- pytest (via `.venv/Scripts/pytest.exe`)
- No `pytest.ini`, `setup.cfg`, or `pyproject.toml` found in project root — pytest is run with default discovery
- Config: no custom markers, no `conftest.py` found at any level

**Assertion Library:**
- pytest's built-in `assert` statements — no `unittest.TestCase`, no `assertpy` or similar

**Run Commands:**
```bash
# Activate venv first
.venv\Scripts\activate

# Run all tests
pytest

# Run specific domain
pytest backend/tests/test_api/
pytest backend/tests/test_services/
pytest backend/tests/test_engines/

# Run a single file
pytest backend/tests/test_api/test_auth.py

# Run with output
pytest -v
pytest -s   # show print output
```

---

## Test File Organization

**Location:** All tests in `backend/tests/` — NOT co-located with source.

**Structure:**
```
backend/tests/
├── test_api/           # FastAPI endpoint integration tests (TestClient)
│   ├── test_auth.py
│   ├── test_approval_api.py
│   ├── test_dashboard_api.py
│   ├── test_employee_cycle_api.py
│   ├── test_evaluation_api.py
│   ├── test_file_api.py
│   ├── test_handbook_api.py
│   ├── test_import_api.py
│   ├── test_main.py
│   ├── test_public_api.py
│   ├── test_salary_api.py
│   └── test_user_admin_api.py
├── test_core/          # Config and database setup tests
│   ├── test_config.py
│   └── test_database.py
├── test_engines/       # Scoring and salary engine unit tests
│   └── test_rule_engines.py
├── test_models/        # Schema/ORM model tests
│   └── test_schema_models.py
├── test_parsers/       # File parser tests
│   └── test_code_parser.py
└── test_services/      # Service layer integration tests
    ├── test_approval_service.py
    ├── test_cycle_service.py
    ├── test_dashboard_service.py
    ├── test_employee_service.py
    ├── test_evaluation_service.py
    ├── test_evidence_service.py
    ├── test_import_service.py
    ├── test_integration_service.py
    ├── test_llm_service.py
    ├── test_parse_service.py
    └── test_salary_service.py
```

**Naming:**
- Test files: `test_[domain]_[layer].py` or `test_[domain].py`
- Test functions: `test_[what_is_being_tested]_[expected_behavior]`
- Example: `test_evaluation_engine_penalizes_prompt_manipulation_content`, `test_salary_service_returns_employee_history_in_cycle_order`

---

## Test Types

**No strict separation by type.** All tests are integration tests:

**API layer tests (`test_api/`):**
- Use `fastapi.testclient.TestClient` wrapping a real `create_app()` instance
- Override `get_db` dependency with an isolated SQLite session
- Test full HTTP request/response cycle including auth headers, status codes, body shape
- Each test file defines its own `build_client()` / `build_test_client()` helper
- Example pattern:
  ```python
  def build_client() -> tuple[TestClient, ApiDatabaseContext]:
      context = ApiDatabaseContext()
      app = create_app(context.settings)
      app.dependency_overrides[get_db] = context.override_get_db
      return TestClient(app), context
  ```

**Service layer tests (`test_services/`):**
- Instantiate real service classes with isolated SQLite databases
- Seed data directly by creating ORM model instances and committing them
- Test full service method flows including DB reads/writes
- LLM service swapped for a stub class when testing salary/evaluation services

**Engine tests (`test_engines/`):**
- Instantiate engine classes directly (`EvaluationEngine()`, `SalaryEngine()`)
- Pass in `EvidenceItem` model instances as pure Python objects
- Assert on result fields (scores, levels, explanation text, Chinese string content)

**Core/model tests:**
- `test_config.py`: instantiate `Settings` directly with overrides, assert field parsing
- `test_schema_models.py`: create a real SQLite DB, run `init_database()`, inspect table names with SQLAlchemy `inspect()`

**Parser tests (`test_parsers/`):**
- Build real zip archives in `.tmp/` directory using `zipfile.ZipFile`
- Instantiate parser classes and call `.parse()` on the file path
- Assert on `parsed.metadata` and text content

---

## Database Isolation Strategy

Each test (or test module) creates its own uniquely-named SQLite database file in `.tmp/`:

```python
def build_context():
    temp_root = Path('.tmp').resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f'salary-{uuid4().hex}.db').as_posix()
    settings = Settings(database_url=f'sqlite+pysqlite:///{database_path}')
    load_model_modules()
    engine = create_db_engine(settings)
    init_database(engine)
    return create_session_factory(settings)
```

**Key characteristics:**
- Unique hex-suffixed filenames prevent cross-test pollution
- SQLite ensures no external database dependency
- `load_model_modules()` must be called before `init_database()` to register all ORM classes
- `.tmp/` directory is created at test root level; these files accumulate (no cleanup seen)

---

## Mocking

**No mocking framework used** (no `unittest.mock`, no `pytest-mock`).

**Pattern 1 — Stub classes for LLM services:**
```python
class StubSalaryExplanationLLM:
    def generate_salary_explanation(self, evaluation_context, salary_context, fallback_payload):
        return DeepSeekCallResult(
            payload={
                'explanation': f"{evaluation_context['employee_name']}...",
                'budget_commentary': '...',
                'fairness_commentary': '...',
                'risk_flags': ['...'],
            },
            used_fallback=False,
            provider='deepseek',
        )

service = SalaryService(db, settings=Settings(...), llm_service=StubSalaryExplanationLLM())
```

**Pattern 2 — httpx.MockTransport for HTTP-level mocking:**
```python
def handler(request: httpx.Request) -> httpx.Response:
    calls['count'] += 1
    if calls['count'] == 1:
        return httpx.Response(503, json={'error': 'temporary'})
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({...})}}]})

client = httpx.Client(transport=httpx.MockTransport(handler))
settings = Settings(deepseek_api_key='test-key', deepseek_max_retries=1)
service = DeepSeekService(settings, client=client, sleeper=lambda _: None)
```

**Pattern 3 — Stub upload objects for file import:**
```python
class UploadStub:
    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.file = __import__('io').BytesIO(content)
```

**What to mock:**
- LLM/DeepSeek calls — always replaced with stubs (real API key not available in tests)
- HTTP transports when testing retry/fallback logic in LLM service
- File uploads — use `UploadStub` with `BytesIO` content

**What NOT to mock:**
- Database operations — always use real SQLite
- Service logic — always test through real service instances
- FastAPI routing — always test through real `TestClient`

---

## Fixtures and Factories

**No pytest fixtures (`@pytest.fixture`) used.** Test setup uses inline helper functions per file.

**Seed helpers:**
```python
def seed_departments(db, *names: str) -> None:
    for name in names:
        db.add(Department(name=name, description=f'{name} scope', status='active'))
    db.commit()

def seed_submission(session_factory, *, department='Engineering', job_family='Platform'):
    db = session_factory()
    employee = Employee(employee_no=f'EMP-{uuid4().hex[:6]}', ...)
    # ... create cycle, submission, evidence items
    return db, employee, submission
```

**Context builder pattern** (used across multiple test files):
```python
def build_context() -> tuple[Settings, object]:
    # Creates isolated SQLite DB and returns (settings, session_factory)
    ...
```

**Test data location:** Generated inline in test files. No shared fixture files or factory libraries.

---

## Coverage

**Requirements:** No coverage targets enforced. No `pytest-cov` configuration found.

**View coverage (if installed):**
```bash
pytest --cov=backend/app --cov-report=term-missing
```

**Observed coverage areas:**

| Area | Coverage Status |
|------|----------------|
| Auth flow (register/login/refresh/change-password) | Well covered — multi-step flows |
| Evaluation engine (scoring, level mapping, department profiles) | Well covered — 6+ test cases |
| Salary service (recommend/simulate/lock/history) | Well covered — 3+ test cases |
| Import service (employees, certifications CSV) | Covered |
| LLM service (fallback, retry, JSON parsing) | Covered |
| API endpoints (evaluation, salary, auth, import, dashboard) | Covered via TestClient |
| Schema/model table creation | Covered |
| Code parser (archive sampling) | Covered |
| Config (CORS parsing variants) | Covered |
| Frontend (all pages, components, hooks) | NOT COVERED — no test framework |

---

## Test Coverage Gaps

**Frontend — not tested at all:**
- No test runner, no test config, no test files in `frontend/src/`
- All React components, hooks, and services are untested
- `useAuth.tsx` bootstrap/refresh logic untested
- Axios interceptor token refresh deduplication logic untested
- `frontend/src/utils/` untested

**Backend — partial gaps:**
- `backend/app/parsers/` — only `code_parser` tested; PPT, PDF, DOCX parsers not tested
- `backend/app/core/security.py` — JWT encoding/decoding not directly unit tested (covered indirectly via auth API tests)
- `backend/app/core/storage.py` — file storage untested
- `backend/app/api/v1/departments.py`, `cycles.py`, `users.py` — minimal or no API-level tests visible
- Error boundary paths in services (e.g., corrupt files, malformed CSVs) — partially covered

**No E2E tests.** No Playwright, Cypress, or similar framework detected.

---

## Common Patterns

**Multi-step flow tests (API layer):**
```python
def test_register_login_refresh_and_me_flow() -> None:
    with build_test_client() as client:
        register_response = client.post('/api/v1/auth/register', json={...})
        assert register_response.status_code == 201
        access_token = register_response.json()['tokens']['access_token']

        me_response = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {access_token}'})
        assert me_response.status_code == 200
```

**Assertion on Chinese content in explanations:**
```python
assert '真实材料' in result.explanation
assert '主要依据来自' in result.dimensions[0].rationale
assert '疑似引导评分内容' in result.explanation
```
Engine tests verify business-meaningful Chinese text is present, not just numeric correctness.

**Comparative assertions for dimension weighting:**
```python
assert score_map['IMPACT'] > score_map['LEARN']
assert engineering_depth.raw_score > sales_depth.raw_score
assert sales_impact.weight > engineering_impact.weight
```

**Boundary and clamping tests:**
```python
assert result.final_adjustment_ratio <= 0.22
assert engine.is_over_budget(total_increase=Decimal('5000.00'), budget_amount=Decimal('4000.00')) is True
```

**Settings override for test isolation:**
```python
settings = Settings(
    allow_self_registration=False,
    database_url=f'sqlite+pysqlite:///{database_path}',
    deepseek_api_key='your_deepseek_api_key',
)
```

---

*Testing analysis: 2026-03-25*
