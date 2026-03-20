# Deployment Notes

## Target Shape

The project is ready for a small single-node deployment split into:

- FastAPI backend
- React static frontend build
- PostgreSQL database
- Optional object storage compatible with S3/MinIO

## Pre-Deployment Checklist

- Set `DATABASE_URL` to PostgreSQL
- Set a strong `JWT_SECRET_KEY`
- Set `PUBLIC_API_KEY`
- Set `BACKEND_CORS_ORIGINS` for the real frontend domain
- Set `DEEPSEEK_API_KEY` if live model calls are required
- Provision writable storage for uploads if local storage is retained

## Backend Start Command

```powershell
$env:PYTHONPATH = (Resolve-Path '.').Path
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Frontend Build Command

```powershell
cmd /c npm.cmd run build --prefix frontend
```

Serve `frontend/dist/` behind nginx, Caddy, or another static file server.

## Database Migration

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Operational Notes

- Public API endpoints are read-only and use `X-API-Key` auth.
- Audit logs are written for public API reads.
- Imports are synchronous in the current implementation.
- CSV is the supported production-safe import format in the current environment.
- DeepSeek calls fall back locally if the key is missing or the request fails.

## Recommended Next Production Hardening

- Add real rate limiting for public APIs using Redis or gateway rules
- Move upload storage from local disk to MinIO or S3
- Add background workers for imports and long-running parsing tasks
- Add structured deployment secrets management
- Add reverse proxy and HTTPS termination
- Add monitoring for `/health`, API latency, and import job failures
