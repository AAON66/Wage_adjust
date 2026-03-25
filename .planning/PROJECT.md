# Project: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

**Created:** 2026-03-25
**Status:** Active development — brownfield, mostly working

---

## What We're Building

An internal enterprise platform for HR-driven talent assessment and salary adjustment decisions. The system uses AI (DeepSeek) to evaluate employees' AI capability across five dimensions, produces structured salary recommendations with traceability, routes them through a manager/HR approval workflow, and exposes the results to HR systems via a public REST API.

The codebase is architecturally sound (FastAPI + React, layered architecture, role-based access) but several core user-facing features are incomplete or unreliable: the AI evaluation pipeline, approval workflow, dashboard analytics, and batch import. Security issues also need to be addressed before production use.

---

## Why It Exists

Companies running AI transformation programs need a structured way to:
1. Measure employees' actual AI capability (not self-reported)
2. Link AI capability to salary adjustments with a defensible, auditable methodology
3. Give HR and managers a shared workspace for review and approval
4. Feed outcomes into existing HR/performance systems via API

Without this system, salary decisions around AI capability are ad hoc, inconsistent, and impossible to audit.

---

## Users

| Role | What They Do |
|------|-------------|
| **Employee** | Submits evidence materials (PPT, images, code, docs); views their own evaluation status and salary recommendation |
| **Manager** | Reviews AI evaluation results for their team; approves or overrides salary recommendations |
| **HR / HRBP** | Manages salary review cycles; has full visibility across departments; configures adjustment rules |
| **Admin** | System configuration, user management, audit log access |

---

## Core Capabilities

### Already Built (Mostly Working)
- Auth system (JWT, role-based access control, protected routes)
- Employee management (create, list, filter by dept/level/job family)
- File upload and parsing (PPT, PDF, images, code, documents)
- AI evaluation engine (5-dimension weighted scoring, AI level matrix)
- Salary calculation engine (multipliers, certification bonuses)
- Approval workflow (status transitions: draft → submitted → manager_review → hr_review → approved/rejected)
- Batch import (Excel/CSV upload flow)
- Public API endpoints (key-authenticated, versioned at `/api/v1/public/`)
- Dashboard service layer (DashboardService with aggregation methods)

### Incomplete / Unreliable (What This Plan Addresses)
1. **AI Evaluation Pipeline** — DeepSeek integration may not be end-to-end; evaluation result display and explanability need work
2. **Approval Workflow** — Status transitions, audit trail, and reviewer UI need completion
3. **Dashboard & Analytics** — Service layer exists but frontend visualizations and data aggregation have gaps
4. **Batch Import** — Upload exists but validation error feedback, partial success handling, and idempotency need work
5. **Security** — HIGH issues: JWT guard on startup, rate limiting on login, PII encryption for national ID numbers, role-aware salary response filtering
6. **External API** — Public API endpoints exist but integration with real external systems hasn't been validated

---

## AI Evaluation Model

### Five-Dimension Scoring (Weighted)
| Dimension | Weight | Data Source |
|-----------|--------|-------------|
| AI工具掌握度 (Tool Mastery) | 15% | Practical test, project records |
| AI应用深度 (Application Depth) | 15% | Case analysis, outcome reports |
| AI学习能力 (Learning Ability) | 20% | Training records, certifications |
| AI分享贡献 (Sharing/Contribution) | 20% | Internal training count, knowledge base |
| AI成果转化 (Result Conversion) | 30% | Business metrics, ROI analysis |

### AI Level Matrix
| Level | Label | Salary Multiplier |
|-------|-------|-------------------|
| 5 | AI大师级 | 1.5 – 2.0× |
| 4 | AI专家级 | 1.3 – 1.5× |
| 3 | AI应用级 | 1.1 – 1.3× |
| 2 | AI入门级 | 1.0 – 1.1× |
| 1 | AI未入门 | 0.9 – 1.0× |

### Certification Bonuses
| Stage | Duration | Bonus |
|-------|----------|-------|
| AI意识唤醒 | 0-3 months | +2% |
| AI技能应用 | 3-12 months | +5% |
| AI方法创新 | 1-2 years | +8% |
| AI领导影响 | 2+ years | +12% |

---

## Tech Stack

- **Frontend:** React 18 + TypeScript, React Router v6, Tailwind CSS, Recharts
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite (dev) / PostgreSQL (prod)
- **AI:** DeepSeek API (LLM for evaluation and structured output)
- **Auth:** JWT (python-jose), bcrypt
- **File parsing:** python-pptx, Pillow, python-docx, PyPDF2
- **Dev tools:** Vite, ESLint, pytest, Alembic (migration setup needed)

---

## Architecture

Layered monorepo: React SPA → FastAPI REST (`/api/v1/`) → Service layer → Engine layer → SQLAlchemy models.

- Strict dependency direction: `api/ → services/ → engines/ → models/`
- All AI evaluation is pure computation in engine layer (no I/O, testable)
- Role-based access enforced both frontend (`ProtectedRoute`) and backend (`require_roles()`)
- Public API surface at `/api/v1/public/` for external HR system integration

---

## Key Constraints

1. All scoring rules, coefficients, and certification bonuses must be **configurable** (not hardcoded)
2. Every AI evaluation result must be **explainable** — traceable to dimension scores and evidence
3. Salary recommendations must distinguish **system suggestion** vs **final approved value**
4. All overrides must produce an **audit log entry**
5. Batch import must handle partial success gracefully (report failures, commit successes)
6. Public API must be versioned and return stable schemas
7. Dashboard data must be consistent with underlying evaluation data
8. National ID numbers are high-sensitivity PII under China's PIPL — require encryption

---

## Success Definition for v1 Complete

- HR can run a full salary review cycle: create cycle → employees submit evidence → AI evaluates → managers approve → final salaries exported
- Evaluations are explainable and auditable
- Dashboard shows accurate talent distribution and salary adjustment statistics
- Batch import works reliably with clear error reporting
- No HIGH security vulnerabilities in production path
- External HR system can pull approved salary recommendations via public API
