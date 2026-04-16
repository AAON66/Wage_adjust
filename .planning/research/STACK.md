# Technology Stack — v1.2 Milestone

**Project:** v1.2 - Production Readiness & Data Management
**Researched:** 2026-04-07
**Overall confidence:** HIGH

---

## Critical Finding: Python 3.9 Compatibility Matrix

Python 3.9 compatibility is the gating constraint for this milestone. Two current pinned dependencies **break** on Python 3.9.

### Dependency Compatibility Audit (All Current requirements.txt)

| Package | Pinned Version | Python 3.9 | Action Required |
|---------|---------------|------------|-----------------|
| fastapi | 0.115.0 | YES (min 3.9) | None |
| uvicorn[standard] | 0.32.0 | YES (min 3.8) | None |
| sqlalchemy | 2.0.36 | YES (min 3.7) | None |
| alembic | 1.14.0 | YES | None |
| pydantic | 2.10.3 | YES (min 3.9) | None |
| pydantic-settings | 2.6.1 | YES (min 3.9) | None |
| celery | 5.4.0 | YES (min 3.8) | **Upgrade to 5.5+ recommended** (see below) |
| redis | 5.2.1 | YES | None |
| httpx | 0.28.1 | YES (min 3.8) | None |
| aiohttp | 3.11.10 | YES | None |
| pandas | 2.2.3 | YES | None |
| **numpy** | **2.2.1** | **NO** (min 3.10) | **Downgrade to 2.0.2** |
| **pillow** | **11.0.0** | **NO** (min 3.10) | **Downgrade to 10.4.0** |
| pypdf | 5.1.0 | YES | None |
| python-pptx | 1.0.2 | YES | None |
| python-jose[cryptography] | 3.3.0 | YES (min 3.9) | None |
| passlib[bcrypt] | 1.7.4 | YES | None |
| minio | 7.2.11 | YES (min 3.9) | None; future 7.3+ may require 3.10 |
| boto3 | 1.35.90 | YES | Python 3.9 support ends 2026-04-29 |
| openpyxl | 3.1.5 | YES | None |
| slowapi | 0.1.9 | YES (min 3.7) | None; project inactive |
| APScheduler | 3.11.2 | YES (min 3.8) | None |
| cryptography | 44.0.2 | YES | None |
| email-validator | 2.2.0 | YES | None |
| python-multipart | 0.0.12 | YES | None |
| python-dotenv | 1.0.1 | YES | None |
| loguru | 0.7.3 | YES | None |
| psycopg2-binary | 2.9.10 | YES | None |
| asyncpg | 0.30.0 | YES | None |
| hiredis | 3.1.0 | YES | None |
| pytest | 8.3.5 | YES | None |

### Blocking Version Downgrades

```
# MUST change for Python 3.9
numpy==2.2.1     -> numpy==2.0.2        # Last version supporting Python 3.9
pillow==11.0.0   -> Pillow==10.4.0      # Last version supporting Python 3.9
```

**Confidence: HIGH** - Verified via official PyPI metadata and release notes.

### Recommended Upgrade

```
# Celery 5.4 works on Python 3.9, but 5.5+ adds native SQLAlchemy 2.0 and Pydantic 2.x support
celery==5.4.0    -> celery==5.5.1       # SQLAlchemy 2.0 support, Pydantic task serialization
```

**Confidence: HIGH** - Celery 5.5 changelog explicitly lists SQLAlchemy 2.0 support.

### Source Code Compatibility

The codebase already uses `from __future__ import annotations` in every backend module. This means:
- `str | None`, `list[str]`, `dict[str, str]` in type annotations are **safe** on Python 3.9 (evaluated lazily as strings)
- No `match/case` statements found anywhere in the codebase (grep confirmed zero matches)
- No `ExceptionGroup`, `TaskGroup`, `tomllib`, or other 3.11+ stdlib features used

**No source code changes needed for Python 3.9 compatibility.** Only requirements.txt version pins need updating.

---

## New Dependencies for v1.2 Features

### 1. Celery + Redis Activation (No New Packages)

Celery 5.4.0 and redis 5.2.1 are already in requirements.txt. What's needed is **wiring code**, not new dependencies.

| Component | Already Have | What to Add |
|-----------|-------------|-------------|
| Celery app factory | No | `backend/app/core/celery_app.py` |
| Task modules | No | `backend/app/tasks/` directory |
| Celery config | Partial (redis_url in Settings) | Add broker/backend URL settings |
| Flower monitoring | No | `flower==2.0.1` (optional, dev only) |

**Recommended Celery configuration additions to Settings:**

```python
# Add to config.py
celery_broker_url: str = "redis://localhost:6379/0"
celery_result_backend: str = "redis://localhost:6379/1"
celery_task_always_eager: bool = False  # True for testing without Redis
```

**Architecture pattern:** Create a standalone Celery app in `backend/app/core/celery_app.py` that imports settings. Celery workers run as a separate process (`celery -A backend.app.core.celery_app worker`). Tasks use **synchronous SQLAlchemy sessions** (psycopg2), not async. FastAPI endpoints dispatch tasks via `.delay()` and return task IDs immediately.

**Confidence: HIGH** - Standard pattern, well-documented.

### 2. Production Deployment (New Packages)

| Package | Version | Purpose | Why |
|---------|---------|---------|-----|
| gunicorn | 23.0.0 | Process manager for uvicorn workers | Standard production setup; manages worker lifecycle, graceful restart, memory leak prevention via `max_requests` |

**Do NOT add to requirements.txt** - gunicorn goes in a separate `requirements-prod.txt` or Dockerfile only. Development uses `uvicorn --reload` directly.

```bash
# Production start command
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --preload \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 120
```

Worker count: equal to CPU cores (async Uvicorn workers handle concurrency internally; the `2N+1` formula is for sync workers, not async).

**Docker base image:** `python:3.9-slim` (smallest image that satisfies the Python 3.9 requirement).

**Nginx:** Use as reverse proxy in front of gunicorn. Standard config, no Python package needed.

**Confidence: HIGH** - Official FastAPI deployment documentation recommends this exact pattern.

### 3. Feishu Bitable API for Eligibility Import

The project already has a complete `FeishuService` using raw `httpx` calls to Feishu Open APIs. This works and is already battle-tested for attendance and performance sync.

| Option | Recommendation | Rationale |
|--------|---------------|-----------|
| `lark-oapi` SDK (v1.5.3) | **Do NOT add** | Adds `requests` as transitive dependency (project uses `httpx`). Existing raw httpx integration works. SDK wraps same REST endpoints. |
| Continue with `httpx` | **YES** | Already proven pattern in `FeishuService`. Bitable search API is the same endpoint. Just add new field mappings and config entries. |

The existing `_fetch_all_records()` method already handles:
- Token management with auto-refresh
- Paginated bitable search with `page_token`
- Filter with fallback to app-layer filtering
- Field mapping and type coercion
- Retry with exponential backoff

For eligibility data import, extend `FeishuService` with a new `sync_eligibility_data()` method following the same pattern as `sync_attendance()` and `sync_performance_records()`.

**Confidence: HIGH** - The existing code is the evidence. No SDK needed.

### 4. File Sharing Rejection Auto-Delete + Pending Labels

**No new packages needed.** Pure application logic using existing SQLAlchemy models and file storage service.

### 5. Unified Eligibility Data Import Management

**No new packages needed.** Combines existing:
- `FeishuService` (for bitable pull)
- `ImportService` + `openpyxl`/`pandas` (for Excel upload)
- New unified management UI + API endpoints

---

## Recommended Stack Changes Summary

### requirements.txt Changes

```
# Version downgrades for Python 3.9 compatibility
numpy==2.0.2          # was 2.2.1 (2.2+ requires Python 3.10)
Pillow==10.4.0        # was 11.0.0 (11+ requires Python 3.10)

# Version upgrade for Celery + SQLAlchemy 2.0 support
celery==5.5.1         # was 5.4.0 (5.5 adds native SQLAlchemy 2.0 + Pydantic 2.x task support)
```

### New File: requirements-prod.txt

```
-r requirements.txt
gunicorn==23.0.0
```

### Optional: requirements-dev.txt

```
-r requirements.txt
flower==2.0.1         # Celery monitoring dashboard
```

### Config Additions (backend/app/core/config.py)

```python
# Celery settings
celery_broker_url: str = "redis://localhost:6379/0"
celery_result_backend: str = "redis://localhost:6379/1"
celery_task_always_eager: bool = False
celery_task_time_limit: int = 1800          # 30 minutes max per task
celery_task_soft_time_limit: int = 1500     # 25 minutes soft limit
```

### New Files to Create

| File | Purpose |
|------|---------|
| `backend/app/core/celery_app.py` | Celery app factory with config from Settings |
| `backend/app/tasks/__init__.py` | Task package |
| `backend/app/tasks/evaluation_tasks.py` | Async AI evaluation tasks |
| `backend/app/tasks/sync_tasks.py` | Async Feishu sync tasks |
| `requirements-prod.txt` | Production-only dependencies |
| `Dockerfile` | Production container image |
| `docker-compose.yml` | Multi-service orchestration (app + worker + redis + postgres + nginx) |
| `nginx/nginx.conf` | Reverse proxy config |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Feishu SDK | Raw httpx (existing) | lark-oapi 1.5.3 | Adds `requests` as transitive dep; existing httpx integration proven; SDK wraps same REST endpoints |
| Task queue | Celery 5.5 + Redis | FastAPI BackgroundTasks | BackgroundTasks dies with the process; no retry, no monitoring, no distributed execution |
| Task queue | Celery 5.5 + Redis | ARQ (arq) | Less mature ecosystem; Celery already declared and understood |
| Process manager | gunicorn + uvicorn workers | uvicorn --workers | gunicorn offers graceful restart, max_requests memory leak prevention, mature production tooling |
| Process manager | gunicorn + uvicorn workers | Kubernetes pod scaling | Over-engineering for current deployment target; gunicorn is sufficient |
| Python version | 3.9 (target) | 3.10+ | Server constraint requires 3.9; all deps can be pinned to compatible versions |
| Monitoring | flower (optional) | Celery events + custom | flower is zero-config, production-ready |

---

## Installation

```bash
# Core (development)
pip install -r requirements.txt

# Production (includes gunicorn)
pip install -r requirements-prod.txt

# Development with Celery monitoring
pip install -r requirements-dev.txt
```

---

## Python 3.9 Sunset Warning

Python 3.9 reached EOL on 2025-10-31. Key implications:
- **boto3** drops Python 3.9 support on 2026-04-29 (imminent -- 3 weeks away)
- **minio** next major version will likely require 3.10+
- **numpy** and **Pillow** already require 3.10+ in their latest versions
- Staying on 3.9 means pinning to older versions of several packages, missing security patches

**Recommendation:** Treat Python 3.9 as a transitional target. Pin dependencies carefully now, and plan migration to Python 3.10+ within 6 months. The `from __future__ import annotations` pattern throughout the codebase means source code will work on 3.10+ without changes when the server is upgraded.

---

## Sources

- [Celery PyPI](https://pypi.org/project/celery/) - Version compatibility, Python 3.9 support confirmed for 5.4/5.5
- [Celery 5.5 What's New](https://docs.celeryq.dev/en/v5.5.1/history/whatsnew-5.5.html) - SQLAlchemy 2.0 + Pydantic 2.x support
- [FastAPI Deployment - Server Workers](https://fastapi.tiangolo.com/deployment/server-workers/) - gunicorn + uvicorn pattern
- [Pillow Python Support](https://pillow.readthedocs.io/en/stable/installation/python-support.html) - 11.0+ requires Python 3.10
- [NumPy 2.2.0 Release Notes](https://numpy.org/devdocs/release/2.2.0-notes.html) - Python 3.10+ requirement
- [NumPy Python 3.9 drop issue](https://github.com/numpy/numpy/issues/24932) - Dropped in 2.1.0
- [lark-oapi PyPI](https://pypi.org/project/lark-oapi/) - v1.5.3, Python >=3.7
- [pandas GitHub Issue #55528](https://github.com/pandas-dev/pandas/issues/55528) - Python 3.9 still supported in 2.2.x
- [AWS Python Support Policy](https://aws.amazon.com/blogs/developer/python-support-policy-updates-for-aws-sdks-and-tools/) - boto3 Python 3.9 EOL 2026-04-29
- [Celery + Redis + FastAPI Production Guide](https://medium.com/@dewasheesh.rana/celery-redis-fastapi-the-ultimate-2025-production-guide-broker-vs-backend-explained-5b84ef508fa7)
- [Mastering Gunicorn and Uvicorn](https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e) - Worker configuration
- [FastAPI Best Practices 2026](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026)
