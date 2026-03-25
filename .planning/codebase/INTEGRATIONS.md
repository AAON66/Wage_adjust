# External Integrations

**Analysis Date:** 2026-03-25

## Summary

The primary external dependency is the DeepSeek LLM API for all AI evaluation tasks. Authentication is handled entirely in-house using JWT. File storage currently uses the local filesystem with MinIO/S3 SDK libraries declared but not wired. Redis and Celery are declared but not actively used. A versioned public REST API is exposed for downstream HR/talent system integration.

---

## AI / LLM

**DeepSeek API:**
- Purpose: Evidence extraction from uploaded files, AI capability evaluation scoring, salary explanation generation, handbook document parsing
- Base URL: `https://api.deepseek.com/v1` (configurable via `DEEPSEEK_API_BASE_URL`)
- Default model: `deepseek-reasoner` (overrides to `deepseek-chat` for parsing and evaluation tasks when default is `deepseek-reasoner`)
- SDK/Client: `httpx.Client` with manual `Authorization: Bearer` header (`backend/app/services/llm_service.py`)
- Rate limiting: In-memory sliding window limiter (`InMemoryRateLimiter`); configurable via `DEEPSEEK_REQUESTS_PER_MINUTE`
- Retry logic: Up to `DEEPSEEK_MAX_RETRIES` (default 2) with 0.2s incremental backoff
- Timeout: Separate configurable timeouts for general, parsing, and evaluation tasks (`DEEPSEEK_TIMEOUT_SECONDS`, `DEEPSEEK_PARSING_TIMEOUT_SECONDS`, `DEEPSEEK_EVALUATION_TIMEOUT_SECONDS`)
- Fallback: All LLM calls return a structured fallback payload when API key is unconfigured or rate limited; callers check `DeepSeekCallResult.used_fallback`
- Response format: `json_object` mode enforced; JSON block regex extraction as last-resort parse fallback
- Task types: `evidence_extraction`, `evaluation_generation`, `salary_explanation`, `handbook_parsing`

**Required env vars:**
- `DEEPSEEK_API_KEY` - Bearer token for DeepSeek API
- `DEEPSEEK_API_BASE_URL` - API endpoint (defaults to `https://api.deepseek.com/v1`)
- `DEEPSEEK_MODEL` - Primary model name (default `deepseek-reasoner`)
- `DEEPSEEK_PARSING_MODEL` - Optional override for parsing tasks
- `DEEPSEEK_EVALUATION_MODEL` - Optional override for evaluation tasks

---

## External File Sources

**GitHub (unauthenticated):**
- Purpose: Employees can submit GitHub repository or file URLs as evidence materials
- Implementation: `backend/app/services/file_service.py` - `FileService.import_github_file()`
- Supported URL forms: `github.com/{owner}/{repo}`, `github.com/{owner}/{repo}/blob/{ref}/{path}`, `github.com/{owner}/{repo}/tree/{ref}`, `raw.githubusercontent.com/...`
- Downloads via: `urllib.request.urlopen` (no auth token; public repos only)
- GitHub Contents API: `https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}` for file downloads
- GitHub Archive API: `https://api.github.com/repos/{owner}/{repo}/zipball` for repo/branch archives
- Timeouts: 30 seconds (`GITHUB_DOWNLOAD_TIMEOUT_SECONDS`)
- Auth: None (unauthenticated GitHub API; rate limited by GitHub IP policy)
- Error handling: Raises `ValueError` on 401/403/404; surfaces user-readable Chinese message

---

## Data Storage

**Database:**
- Development: SQLite (`sqlite+pysqlite:///./wage_adjust.db`) - file in project root
- Production target: PostgreSQL (drivers `psycopg2-binary`, `asyncpg` installed)
- ORM: SQLAlchemy 2.0 synchronous sessions; `backend/app/core/database.py`
- Migrations: Alembic 1.14.0; config at `alembic.ini`; scripts in `alembic/`
- Schema compatibility: Runtime column-addition patches in `ensure_schema_compatibility()` for in-place upgrades without full migration (`backend/app/core/database.py`)
- Connection env vars:
  - `DATABASE_URL` - Full SQLAlchemy connection string
  - `DATABASE_POOL_SIZE` (default 10)
  - `DATABASE_MAX_OVERFLOW` (default 20)
  - `DATABASE_ECHO` - SQL query logging toggle

**File Storage:**
- Active implementation: `LocalStorageService` - writes to `uploads/{submission_id}/{uuid}_{filename}` on local disk (`backend/app/core/storage.py`)
- Storage base dir: Configurable via `STORAGE_BASE_DIR` (default `uploads`)
- Preview URLs: `file://` URIs from `pathlib.Path.as_uri()`
- Declared but not wired: `minio` 7.2.11 and `boto3` 1.35.90 present in `requirements.txt` for MinIO/S3; `STORAGE_ENDPOINT`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_BUCKET_NAME` env vars defined in `Settings` and `.env.example` but the active `FileService` uses `LocalStorageService` exclusively
- Upload limits: `MAX_UPLOAD_SIZE_MB` (default 200 MB per file)
- Allowed extensions: `.ppt`, `.pptx`, `.pdf`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.zip`, `.md`, `.xlsx`, `.xls`, `.py`, `.ts`, `.tsx`, `.js`, `.json`, `.txt`, `.yml`, `.yaml` (plus extensionless text files like `README`, `Dockerfile`)

**Caching:**
- Redis declared: `redis` 5.2.1 + `hiredis` 3.1.0 in `requirements.txt`
- `REDIS_URL` env var defined (default `redis://localhost:6379/0`)
- Not actively used in any service layer; available for future Celery or cache integration

---

## Authentication and Identity

**Mechanism:** Custom JWT-based authentication (no third-party auth provider)
- Implementation: `backend/app/core/security.py`
- Library: `python-jose[cryptography]` 3.3.0 for JWT sign/verify
- Password hashing: `passlib` with `pbkdf2_sha256` scheme
- Token types: `access` (30 min default) and `refresh` (7 days default)
- Algorithm: HS256 (symmetric)
- Frontend token storage: `localStorage` keys `wage_adjust.access_token`, `wage_adjust.refresh_token`, `wage_adjust.user`
- Frontend auto-refresh: Axios response interceptor in `frontend/src/services/api.ts` retries 401s with refresh token; single in-flight dedup via `refreshInFlight` promise

**Required env vars:**
- `JWT_SECRET_KEY` - Must be changed from default `change_me`; min 8 chars
- `JWT_ALGORITHM` (default `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 30)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (default 7)

**Self-registration:**
- Controlled by `ALLOW_SELF_REGISTRATION` (default `false`); admin creates users when disabled

---

## Public REST API (Outbound Integration)

**Purpose:** Downstream HR, performance, and talent systems consume evaluation and salary data

**Authentication:** Static API key via `X-API-Key` header; validated against `PUBLIC_API_KEY` setting

**Endpoints (all under `/api/v1/public`):**
- `GET /public/employees/{employee_no}/latest-evaluation` - Latest AI evaluation and salary recommendation for an employee
- `GET /public/cycles/{cycle_id}/salary-results` - All salary results for an evaluation cycle
- `GET /public/cycles/{cycle_id}/approval-status` - Approval workflow status for a cycle
- `GET /public/dashboard/summary` - Aggregated platform dashboard data

**Audit logging:** All public API accesses written to `audit_log` table via `IntegrationService.log_public_access()` (`backend/app/services/integration_service.py`)

**Required env vars:**
- `PUBLIC_API_KEY` - Static key for downstream system access
- `PUBLIC_API_RATE_LIMIT` (default `1000/hour`; declared but rate limiting enforcement not observed in current implementation)

---

## Task Queue (Declared, Not Active)

**Celery:**
- `celery` 5.4.0 in `requirements.txt`
- Intended broker: Redis (`REDIS_URL`)
- Not currently wired to any task definitions or worker processes

---

## Monitoring and Observability

**Error Tracking:** None (no Sentry, Datadog, or similar SDK detected)

**Logging:**
- Backend: Python stdlib `logging` configured via `dictConfig` at startup (`backend/app/core/logging.py`)
- Log level: Configurable via `LOG_LEVEL` (default `INFO`)
- Log format: Timestamped text to stdout/stderr; `LOG_FORMAT=json` env var declared but JSON formatter not implemented (stdlib text format used)
- `loguru` 0.7.3 is declared in `requirements.txt` but stdlib `logging` is used in all active code

**Metrics:** None detected

---

## CORS

**Allowed origins (defaults):**
- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:5174`
- `http://127.0.0.1:5174`

**Configuration:** `BACKEND_CORS_ORIGINS` env var accepts JSON array or comma-separated string (`backend/app/core/config.py`)

---

## CI/CD and Deployment

**CI Pipeline:** None detected (no `.github/workflows/`, no `Jenkinsfile`, no `gitlab-ci.yml`)

**Deployment:** No containerization files detected (no `Dockerfile`, no `docker-compose.yml`)

**Platform:** Local Windows development only; scripts are `.cmd` and `.ps1`

---

## Environment Configuration Summary

| Variable | Default | Required for Production |
|---|---|---|
| `DATABASE_URL` | `sqlite+pysqlite:///./wage_adjust.db` | Yes (PostgreSQL URL) |
| `JWT_SECRET_KEY` | `change_me` | Yes (strong secret) |
| `DEEPSEEK_API_KEY` | `your_deepseek_api_key` | Yes |
| `DEEPSEEK_API_BASE_URL` | `https://api.deepseek.com/v1` | No |
| `DEEPSEEK_MODEL` | `deepseek-reasoner` | No |
| `STORAGE_ENDPOINT` | `http://localhost:9000` | Yes (if using MinIO/S3) |
| `STORAGE_ACCESS_KEY` | `your_access_key` | Yes (if using MinIO/S3) |
| `STORAGE_SECRET_KEY` | `your_secret_key` | Yes (if using MinIO/S3) |
| `STORAGE_BUCKET_NAME` | `wage-adjust-files` | Yes (if using MinIO/S3) |
| `REDIS_URL` | `redis://localhost:6379/0` | Yes (if enabling Celery) |
| `PUBLIC_API_KEY` | `your_public_api_key` | Yes (if exposing public API) |
| `BACKEND_CORS_ORIGINS` | localhost origins | Yes (production domain) |
| `ALLOW_SELF_REGISTRATION` | `false` | No |
| `LOG_LEVEL` | `INFO` | No |

**Secrets location:** `.env` file in project root (not committed); `.env.example` documents all variables

---

*Integration audit: 2026-03-25*
