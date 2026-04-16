---
phase: 24-production-deploy
plan: 02
subsystem: infra
tags: [docker, nginx, compose, frontend, production]
---

# Plan 24-02: Frontend Nginx Container + Production Docker Compose

## One-liner

Multi-stage frontend Dockerfile with Nginx reverse proxy + 4-service docker-compose.prod.yml for one-command production deployment

## What was built

### frontend/Dockerfile
- Multi-stage build: `node:18-alpine` (build) → `nginx:alpine` (runtime)
- Build-time `ARG VITE_API_BASE_URL=/api/v1` for API endpoint configuration
- Copies built `dist/` to Nginx HTML directory
- Copies custom `nginx.conf` for reverse proxy configuration
- Exposes port 8080

### frontend/nginx.conf
- Reverse proxy `/api/` requests to `backend:8011`
- SPA fallback (`try_files $uri $uri/ /index.html`)
- Gzip compression enabled
- 300s proxy timeout for long-running AI operations
- `client_max_body_size 200M` for file uploads
- `server_tokens off` for security

### docker-compose.prod.yml
- 4 services: redis, backend, celery-worker, frontend
- Backend uses gunicorn with uvicorn workers (from upgraded Dockerfile)
- Frontend Nginx on port 8080 with API reverse proxy
- Redis with healthcheck
- Backend and Celery depend on Redis health
- Frontend depends on backend
- `restart: always` on all services
- Shared `uploads_data` volume for file persistence
- No PostgreSQL container (external DB per D-03)

### docker-compose.yml (updated)
- Added comment pointing to `docker-compose.prod.yml` for production
- Dev configuration unchanged

## Verification

| Check | Result |
|-------|--------|
| Backend image build (`docker build -t wage-adjust-backend .`) | ✓ PASS |
| Frontend image build (`docker build -t wage-adjust-frontend ./frontend`) | ✓ PASS |
| Compose config validation (`docker-compose -f docker-compose.prod.yml config`) | ✓ PASS |

## Self-Check: PASSED

## Key files

### created
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `docker-compose.prod.yml`

### modified
- `docker-compose.yml`

## Deviations

None — all decisions (D-06 through D-08) implemented as specified.
