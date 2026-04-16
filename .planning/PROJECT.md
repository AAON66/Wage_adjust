# Project: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

**Created:** 2026-03-25
**Status:** Active — v1.3 in progress (2026-04-16)

## Current Milestone: v1.3 飞书登录与登录页重设计

**Goal:** 支持飞书扫码/网页授权登录并自动绑定员工账号，同时重新设计登录页面为左右分栏（左侧账号密码 + 右侧飞书登录）加粒子动态背景。

**Target features:**
- 飞书 OAuth2 集成（扫码登录 + 网页授权两种方式）
- 飞书登录后按工号自动匹配绑定系统账号
- 登录页重设计：左侧账号密码表单，右侧飞书扫码/授权面板
- Canvas 粒子动态背景（参考智慧树风格）
- 保持现有账号密码登录功能不变

---

## What This Is

An internal enterprise platform for HR-driven talent assessment and salary adjustment decisions. The system uses AI (DeepSeek) to evaluate employees' AI capability across five dimensions, produces structured salary recommendations with traceability, routes them through a manager/HR approval workflow, and exposes the results to HR systems via a public REST API.

As of v1.2, the platform includes: Python 3.9 compatibility for production deployment, Celery+Redis async infrastructure for AI evaluation and bulk import tasks, unified eligibility data import management (4 data types via Excel/Feishu sync), employee company field, file sharing rejection/timeout cleanup with pending badges, and Docker-based production deployment (gunicorn + Nginx + 4-service compose).

---

## Core Value

HR can run a complete, auditable salary review cycle — from employee evidence submission to AI evaluation to approved salary adjustment — with every decision explainable and traceable.

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

## Requirements

### Validated

- ✓ JWT security hardening, AES-256-GCM national ID encryption, Alembic-only migrations — v1.0
- ✓ AI evaluation pipeline: 5-dimension weighted scoring, Redis rate limiter, explainable scores — v1.0
- ✓ Approval workflow: status transitions, audit trail, reviewer UI — v1.0
- ✓ Audit log wired into all service mutations — v1.0
- ✓ File deduplication and multi-author contribution support — v1.0
- ✓ Batch import with idempotency and per-row error reporting — v1.0
- ✓ Dashboard with SQL aggregation and Redis caching — v1.0
- ✓ Employee self-service UI (submission status, evaluation results) — v1.0
- ✓ Feishu attendance data sync for salary review — v1.0
- ✓ External API hardening with key auth and stable schemas — v1.0
- ✓ Account-employee binding: admin bind/unbind + employee self-bind + conflict detection — v1.1
- ✓ Salary eligibility engine: 4 rules (tenure/interval/performance/leave), three-state results, configurable thresholds — v1.1
- ✓ Eligibility visibility: HR/manager-only, batch query, Excel export, exception override workflow — v1.1
- ✓ Multimodal vision evaluation: PPT image extraction + standalone image scoring + structured output — v1.1
- ✓ File sharing workflow: duplicate warning + sharing request + approve/reject + contribution ratio + 72h timeout — v1.1
- ✓ Salary display simplification: summary panel, expandable detail, eligibility badge with rule drill-down — v1.1
- ✓ Python 3.9 compatibility: 440+ PEP 604/585 annotation downgrades, numpy/Pillow version pins, SQLite FK pragma — v1.2
- ✓ Celery+Redis async foundation: shared worker DB lifecycle, health endpoint, Docker-backed runtime proof — v1.2
- ✓ Employee company field: import overwrite-clear-preserve semantics, admin form, detail-only visibility — v1.2
- ✓ File sharing rejection/timeout cleanup: atomic copy deletion, history-safe FK, pending badge — v1.2
- ✓ AI evaluation + bulk import async migration: Celery tasks, useTaskPolling hook, frontend progress display — v1.2
- ✓ Eligibility data unified import: 6-tab page, 4 data types, Excel upload + Feishu bitable sync with rate limiting — v1.2
- ✓ Production deployment: gunicorn+uvicorn Dockerfile, Nginx frontend, docker-compose.prod.yml 4-service orchestration — v1.2

### Active (Next Milestone)

- [ ] Menu & navigation restructuring: grouped sidebar, collapsible, role-filtered (NAV-01/02/03 — deferred from v1.1)
- [ ] Performance full cycle: currently only grade import is supported; full review workflow not built
- [ ] Real-time notifications: currently polling on page load; WebSocket push for approval events
- [ ] PostgreSQL production migration: connection pool tuning, read/write split
- [ ] E2E integration test suite: key user journeys automated
- [ ] MinIO/S3 object storage activation: replace local filesystem storage

### Out of Scope

- Mobile app — web-first approach, responsive PWA covers mobile needs
- SSO/LDAP authentication — standard JWT is sufficient for current scale
- Draggable menu reordering — not a user priority
- Dynamic eligibility rule UI — 4 rules with configurable thresholds is sufficient; full config UI is over-engineering
- Full performance management module — only grade import is needed for eligibility check
- Auto-approve sharing requests — manual approval preserves intent
- Employee-visible eligibility status — HR/manager-only is a deliberate access control decision
- K8s orchestration — Docker Compose is sufficient for current deployment scale
- Celery Beat scheduled tasks — only on-demand async tasks needed currently

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

- **Frontend:** React 18 + TypeScript, React Router v7, Tailwind CSS, Recharts
- **Backend:** Python 3.9+, FastAPI 0.115, SQLAlchemy 2.0, SQLite (dev) / PostgreSQL (prod)
- **Async:** Celery 5.5.1 + Redis (evaluation tasks, bulk import, Feishu sync)
- **AI:** DeepSeek API (LLM for text evaluation + vision model for image evaluation)
- **Auth:** JWT (python-jose), bcrypt, token_version for forced invalidation on bind/unbind
- **File parsing:** python-pptx (with image extraction), Pillow 10.4.0 (with compression), pypdf, python-docx
- **Storage:** Local filesystem (dev), MinIO/S3 (prod path wired but not activated)
- **Deploy:** Docker (gunicorn+uvicorn backend, Nginx frontend), docker-compose.prod.yml
- **Dev tools:** Vite 6, pytest, Alembic (sole migration path)

---

## Architecture

Layered monorepo: React SPA → FastAPI REST (`/api/v1/`) → Service layer → Engine layer → SQLAlchemy models.

- Strict dependency direction: `api/ → services/ → engines/ → models/`
- All AI evaluation and eligibility checking is pure computation in engine layer (no I/O, fully testable)
- Role-based access enforced both frontend (`ProtectedRoute`) and backend (`require_roles()`)
- `AccessScopeService` gates all resource endpoints (admins see all; HRBP/managers see department; employees see self)
- Public API surface at `/api/v1/public/` for external HR system integration
- Vision evaluation wired after text parsing; single file failure does not block others

---

## Key Constraints

1. All scoring rules, coefficients, and certification bonuses must be **configurable** (not hardcoded)
2. Every AI evaluation result must be **explainable** — traceable to dimension scores and evidence
3. Salary recommendations must distinguish **system suggestion** vs **final approved value**
4. All overrides must produce an **audit log entry**
5. Batch import must handle partial success gracefully (report failures, commit successes)
6. Public API must be versioned and return stable schemas
7. Dashboard data must be consistent with underlying evaluation data
8. National ID numbers are high-sensitivity PII under China's PIPL — require AES-256-GCM encryption

---

## Key Decisions

| Decision | Outcome | Milestone |
|----------|---------|-----------|
| AES-256-GCM for national ID PII encryption | ✓ Good — compliant, no performance impact | v1.0 |
| Alembic as sole migration path; init_database() calls create_all only as fallback | ✓ Good — consistent schema evolution | v1.0 |
| Redis rate limiter with in-memory fallback for LLM calls | ✓ Good — no hard Redis dependency in dev | v1.0 |
| batch_alter_table for SQLite-compatible Alembic migrations | ✓ Good — dev/prod parity on schema changes | v1.0 |
| token_version column for JWT invalidation on bind/unbind | ✓ Good — simpler than token blacklist, no Redis needed | v1.1 |
| Vision evaluation wired after text parsing; independent failure | ✓ Good — text evidence not blocked by vision failures | v1.1 |
| Hash-only dedup with oldest-first ordering for sharing requests | ✓ Good — deterministic, no race conditions | v1.1 |
| Atomic upload+SharingRequest creation in single transaction | ✓ Good — eliminates orphan sharing requests | v1.1 |
| filter-before-paginate for batch eligibility query (SQLite limitation) | ⚠️ Revisit — will need server-side pagination for large datasets | v1.1 |
| Role-step binding for override approval (HRBP then admin) | ✓ Good — matches existing approval pattern | v1.1 |
| Employee `company` stays on the shared contract but is rendered only on detail surfaces | ✓ Good — avoids API split while preserving visibility boundaries | v1.2 |
| NAV restructuring deferred (Phase 11 implemented but not fully verified) | — Pending — carry to next milestone | v1.1 |
| Celery worker_process_init disposes shared engine after fork | ✓ Good — prevents stale DB connections in forked workers | v1.2 |
| Separate docker-compose.prod.yml instead of modifying dev compose | ✓ Good — dev/prod separation, no risk of breaking local workflow | v1.2 |
| FeishuService uses shared InMemoryRateLimiter from core | ✓ Good — centralized rate limiting; llm_service still has local copy (tech debt) | v1.2 |
| useTaskPolling shared hook for all async operations | ⚠️ Revisit — FeishuSyncPanel uses custom polling, misses progress display | v1.2 |

---

## Context

**v1.0 shipped 2026-03-30:** 10 phases, 35 plans. Established secure, auditable AI evaluation pipeline from evidence upload to approved salary recommendation. Full RBAC, Feishu sync, external API.

**v1.1 shipped 2026-04-07:** 7 phases, 13 plans, 343 commits. Added eligibility engine with 4 business rules, file sharing workflow, multimodal vision evaluation, account binding with JWT invalidation, and simplified salary display with expandable detail panels.

**v1.2 shipped 2026-04-16:** 7 phases, 18 plans, 144 commits. Python 3.9 compatibility (440+ annotation downgrades), Celery+Redis async infrastructure with AI evaluation and bulk import migration, unified eligibility data import management (4 types via Excel/Feishu), file sharing rejection cleanup, employee company field, and Docker production deployment.

**Current codebase state:** ~33,164 Python LOC + ~21,398 TypeScript LOC. SQLite in dev (wage_adjust.db), PostgreSQL in prod. Celery+Redis for async tasks (evaluation, import, Feishu sync). Docker-based production deployment with gunicorn+uvicorn backend, Nginx frontend, 4-service docker-compose.

**Known issues / tech debt:**
- filter-before-paginate for eligibility batch query won't scale beyond ~10k employees — needs server-side cursor pagination
- Phase 11 nav restructuring code is in the repo but planning artifacts are incomplete; functionality requires verification
- llm_service.py has local duplicate of InMemoryRateLimiter (should import from core/rate_limiter.py)
- FeishuSyncPanel uses custom polling instead of shared useTaskPolling hook (no progress display during sync)
- boto3 Python 3.9 support ends 2026-04-29 — plan 3.10+ migration within 6 months

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after v1.3 milestone start*
