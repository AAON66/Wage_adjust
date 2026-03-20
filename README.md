# Wage Adjust Platform

AI evaluation and compensation operations platform built with FastAPI and React.

## What It Covers

- Employee and evaluation cycle management
- File upload, parsing, and structured evidence extraction
- AI capability evaluation with explainable five-dimension scoring
- Salary recommendation, budget simulation, and approval workflow
- Dashboard insights, import center, and external read APIs
- Public API key based integration endpoints and audit logging

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: React, TypeScript, Vite, Tailwind CSS
- Database: SQLite for local development, PostgreSQL-ready configuration
- Parsing: pypdf, python-pptx, Pillow, pandas
- Auth: JWT access/refresh tokens, API key for public endpoints

## Local Setup

### 1. Create environment

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cmd /c npm.cmd install --prefix frontend
```

### 2. Configure environment

Copy `.env.example` to `.env` and adjust values.

Important variables:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `DEEPSEEK_API_KEY`
- `PUBLIC_API_KEY`
- `BACKEND_CORS_ORIGINS`

## Run Locally

### Backend

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### Frontend

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_frontend.ps1
```

Default frontend URL:

- `http://127.0.0.1:5173`

## Test and Build

### Backend

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q -p no:cacheprovider
```

### Frontend

```powershell
cmd /c npm.cmd run build --prefix frontend
cmd /c npm.cmd run lint --prefix frontend
```

## Current Delivery Notes

- All functional tasks are implemented.
- `xlsx/xls` import is not enabled in the current environment because `openpyxl` is not installed; CSV is the stable format.
- `DeepSeekService` is wired with retry, rate limit, and fallback behavior. If `DEEPSEEK_API_KEY` is not configured, the system uses local fallback heuristics.
- Public APIs are read-only and protected by `X-API-Key`.

## Key Routes

- `/`
- `/workspace`
- `/employees`
- `/cycles/create`
- `/salary-simulator`
- `/approvals`
- `/dashboard`
- `/import-center`

## Key Backend Endpoints

- `/health`
- `/api/v1/auth/*`
- `/api/v1/employees`
- `/api/v1/cycles`
- `/api/v1/evaluations/*`
- `/api/v1/salary/*`
- `/api/v1/approvals/*`
- `/api/v1/dashboard/*`
- `/api/v1/imports/*`
- `/api/v1/public/*`
