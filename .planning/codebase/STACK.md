# Technology Stack

**Analysis Date:** 2026-03-25

## Summary

Full-stack web application for enterprise AI capability evaluation and salary adjustment. Python/FastAPI backend with React/TypeScript frontend. SQLite in development; designed to work with PostgreSQL in production. DeepSeek LLM is the sole AI provider.

---

## Languages

**Primary:**
- Python 3.x (implied by `from __future__ import annotations` and `match` style patterns) - Backend API, engines, parsers, services
- TypeScript 5.8.3 - Frontend React application (`frontend/tsconfig.json` targets ES2020)

**Secondary:**
- HTML/CSS - Frontend markup and Tailwind utility classes

---

## Runtime

**Backend Environment:**
- Python virtual environment (`.venv/`)
- ASGI server: `uvicorn[standard]` 0.32.0
- Start command: `uvicorn backend.app.main:app --reload`

**Frontend Environment:**
- Node.js (version not pinned; no `.nvmrc` found)
- Dev server: Vite 6.2.6 on `127.0.0.1:5174`
- Preview server on port `4174`

**Package Managers:**
- Backend: `pip` with `requirements.txt`
- Frontend: `npm` with `package-lock.json` (lockfile present)

---

## Frameworks

**Backend Core:**
- FastAPI 0.115.0 - REST API framework; versioned under `/api/v1`
- Pydantic 2.10.3 - Data validation and serialization for all schemas
- pydantic-settings 2.6.1 - Settings loaded from `.env` via `backend/app/core/config.py`

**ORM / Database:**
- SQLAlchemy 2.0.36 - ORM with `DeclarativeBase`; synchronous sessions
- Alembic 1.14.0 - Database migrations; config at `alembic.ini`

**Frontend Core:**
- React 18.3.1 - UI framework
- React Router DOM 7.6.0 - Client-side routing
- Axios 1.8.4 - HTTP client with JWT interceptors (`frontend/src/services/api.ts`)

**Frontend Build:**
- Vite 6.2.6 with `@vitejs/plugin-react` 4.4.1 - Dev server and bundler (`frontend/vite.config.ts`)
- TypeScript compiler - `tsc -b && vite build` for production builds

**Frontend Styling:**
- Tailwind CSS 3.4.17 - Utility-first CSS (`frontend/tailwind.config.js`)
- PostCSS 8.5.3 with Autoprefixer 10.4.21 (`frontend/postcss.config.js`)

**Testing:**
- pytest 8.3.5 - Backend test runner; tests organized under `backend/tests/`

---

## Key Dependencies

**AI / LLM:**
- httpx 0.28.1 - Synchronous HTTP client used exclusively for DeepSeek API calls (`backend/app/services/llm_service.py`)
- aiohttp 3.11.10 - Async HTTP client (present in requirements; available for future async LLM paths)

**Authentication:**
- python-jose[cryptography] 3.3.0 - JWT encoding/decoding (`backend/app/core/security.py`)
- passlib[bcrypt] 1.7.4 - Password hashing; configured with `pbkdf2_sha256` scheme

**File Parsing:**
- pypdf 5.1.0 - PDF text extraction (`backend/app/parsers/document_parser.py`)
- python-pptx 1.0.2 - PowerPoint slide text extraction (`backend/app/parsers/ppt_parser.py`)
- Pillow 11.0.0 - Image metadata (PNG/JPG); OCR noted as reserved for later task (`backend/app/parsers/image_parser.py`)

**Data Processing:**
- pandas 2.2.3 - DataFrame operations for bulk import
- numpy 2.2.1 - Numerical support for pandas
- email-validator 2.2.0 - Email field validation in Pydantic schemas
- python-multipart 0.0.12 - Multipart file upload support in FastAPI

**Storage (Declared, Partially Used):**
- minio 7.2.11 - MinIO/S3 object storage SDK (declared but current `LocalStorageService` uses local filesystem)
- boto3 1.35.90 - AWS S3 SDK (declared; not actively wired in current storage layer)

**Task Queue (Declared, Not Actively Wired):**
- celery 5.4.0 - Async task queue
- redis 5.2.1 + hiredis 3.1.0 - Redis broker/backend for Celery

**Utilities:**
- python-dotenv 1.0.1 - `.env` file loading
- loguru 0.7.3 - Declared logging library; active logging uses stdlib `logging` via `dictConfig` (`backend/app/core/logging.py`)

---

## Configuration

**Backend:**
- All settings in `backend/app/core/config.py` via `pydantic_settings.BaseSettings`
- Reads from `.env` file in project root; falls back to defaults
- `.env.example` documents all required variables
- Settings accessed via `get_settings()` (LRU-cached) and injected with FastAPI `Depends`

**Database (Development Default):**
- SQLite: `sqlite+pysqlite:///./wage_adjust.db`
- File `wage_adjust.db` exists in project root

**Database (Production Target):**
- PostgreSQL; drivers `psycopg2-binary` 2.9.10 and `asyncpg` 0.30.0 are installed
- `.env.example` shows `DATABASE_URL=postgresql://user:password@localhost:5432/wage_adjust`

**Frontend:**
- API base URL configured via `VITE_API_BASE_URL` env var; defaults to `http://127.0.0.1:8011/api/v1`
- No `.env` file detected in `frontend/`

---

## Build Scripts

**Backend:**
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
pytest
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev        # Vite dev server on port 5174
npm run build      # tsc -b && vite build
npm run lint       # tsc --noEmit
npm run preview    # Vite preview on port 4174
```

**Convenience Scripts:**
- `start_backend_local.cmd` - Windows batch file
- `start_project_local.cmd` - Windows batch file
- `start_project_local.ps1` - PowerShell script
- `scripts/start_backend.ps1` - PowerShell for backend only
- `scripts/start_frontend.ps1` - PowerShell for frontend only

---

## Platform Requirements

**Development:**
- Windows (primary; all startup scripts are `.cmd`/`.ps1`)
- Python virtual environment in `.venv/`
- SQLite available by default (no external DB needed in dev)
- Local `uploads/` directory for file storage

**Production (Intended):**
- PostgreSQL database
- Redis for Celery task queue
- MinIO or S3-compatible object storage
- All configuration via environment variables

---

*Stack analysis: 2026-03-25*
