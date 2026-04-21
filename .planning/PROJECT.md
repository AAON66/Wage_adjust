# Project: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

**Created:** 2026-03-25
**Status:** Active — v1.4 in progress (2026-04-20)

## Current Milestone: v1.4 员工端体验完善与导入链路稳定性

**Goal:** 让员工在自己的页面就能看到本次调薪的资格状态与绩效档次，补齐绩效导入与历史展示链路，并修复工号前导零、飞书同步、Excel 模板下载等已知阻塞性 bug。

**Target features:**
- 员工端调薪资格自助可见（随时可见最新状态；不合格时明确列出未通过规则）
- 绩效导入链路与员工端档次展示（独立「绩效管理」页面 + 修复现有调薪资格导入页的绩效分支；评估详情/调薪建议展示历史绩效；员工端展示 1/2/3 档 = 20/70/10，全公司对比，不显示排名）
- 工号前导零保留修复（Excel / 飞书 / 手动录入三条链路统一，含存量数据修补）
- 调薪资格导入功能修复（飞书同步成功但未落库根因修复；重复导入按员工+周期维度覆盖更新；Excel 导入开通 + 模板下载返回真实文件）
- Phase 11 导航菜单验证补齐（补齐 SUMMARY.md 并按 UAT 清单验证）

---

## What This Is

An internal enterprise platform for HR-driven talent assessment and salary adjustment decisions. The system uses AI (DeepSeek) to evaluate employees' AI capability across five dimensions, produces structured salary recommendations with traceability, routes them through a manager/HR approval workflow, and exposes the results to HR systems via a public REST API.

As of v1.1, the platform includes: account-employee binding with JWT invalidation, automated 4-rule salary eligibility checks (tenure/interval/performance/leave), role-gated eligibility visibility with exception overrides, multimodal vision evaluation for PPT images and standalone photos, file sharing workflow with duplicate detection and contribution ratios, and a simplified salary display with summary/detail panels and eligibility badge.

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
- ✓ Celery+Redis async foundation: shared worker DB lifecycle, health endpoint, Docker-backed runtime proof, requirements closure — v1.2 Phase 19
- ✓ Employee company field: shared backend/frontend contract, import overwrite-clear-preserve semantics, admin form editing, detail-only visibility — validated in Phase 20
- ✓ Login page Canvas particle background: full-viewport animated particles with distance-threshold linking, mouse repulsion, HiDPI, prefers-reduced-motion, and visibilitychange pause — validated in Phase 28 (LOGIN-02/03)
- ✓ 工号前导零写入路径统一：Excel 模板/读入、飞书 `_map_fields` 去 int 误用、手动表单 Pydantic str 约束、飞书 bitable 字段类型 422 校验、容忍匹配计数器 `leading_zero_fallback_count` 与 SyncStatusCard 黄色提示 — 验证于 Phase 30 (EMPNO-01/02/03/04)；存量数据修补按 Phase 30 Success Criterion 4 显式不在范围内

### Active (v1.4 in progress)

- [ ] 员工端调薪资格自助可见：随时在员工页面展示资格状态与未通过规则明细
- [ ] 绩效导入链路：新增「绩效管理」页面（导入/列表/历史）+ 修复调薪资格导入页的绩效分支
- [ ] 绩效档次与历史展示：评估详情/调薪建议展示历史绩效；员工端显示 1/2/3 档（20/70/10，全公司对比）
- [ ] 调薪资格导入功能修复：飞书同步成功但未落库根因；重复导入覆盖更新；Excel 模板下载与导入可用
- [ ] Phase 11 导航菜单验证补齐：SUMMARY.md + UAT 清单验证

### Deferred (Not in v1.4)

- [ ] Performance full cycle: currently only grade import is supported; full review workflow not built
- [ ] Real-time notifications: currently polling on page load; WebSocket push for approval events
- [ ] Production deployment hardening: PostgreSQL migration (finishing live cutover), Redis cluster, MinIO/S3 config
- [ ] E2E integration test suite: key user journeys automated
- [ ] 飞书工作台免登（tt.requestAccess）— 需应用上架工作台
- [ ] 嵌入式飞书 QR 扫码面板（原 FUI-01/FUI-03 deferred） — 需解决飞书应用能力配置（「网页扫码登录」申请 + 发版审批）
- [ ] boto3 Python 3.10+ 迁移（2026-04-29 EOL） — 单独跟踪，不进 v1.4
- [ ] 资格批量查询游标分页 — <10k 员工暂不紧迫

### Out of Scope

- Mobile app — web-first approach, responsive PWA covers mobile needs
- SSO/LDAP authentication — standard JWT is sufficient for current scale
- Draggable menu reordering — not a user priority
- Dynamic eligibility rule UI — 4 rules with configurable thresholds is sufficient; full config UI is over-engineering
- Full performance management module — only grade import is needed for eligibility check
- Auto-approve sharing requests — manual approval preserves intent
- Employee-visible eligibility status — HR/manager-only is a deliberate access control decision

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
- **Backend:** Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, SQLite (dev) / PostgreSQL (prod)
- **AI:** DeepSeek API (LLM for text evaluation + vision model for image evaluation)
- **Auth:** JWT (python-jose), bcrypt, token_version for forced invalidation on bind/unbind
- **File parsing:** python-pptx (with image extraction), Pillow (with compression), pypdf, python-docx
- **Storage:** Local filesystem (dev), MinIO/S3 (prod path wired but not activated)
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
| NAV restructuring deferred (Phase 11 implemented but not fully verified) | — Pending — carry to v1.2 | v1.1 |

---

## Context

**v1.0 shipped 2026-03-30:** 10 phases, 35 plans. Established secure, auditable AI evaluation pipeline from evidence upload to approved salary recommendation. Full RBAC, Feishu sync, external API.

**v1.1 shipped 2026-04-07:** 7 phases, 13 plans, 343 commits. Added eligibility engine with 4 business rules, file sharing workflow, multimodal vision evaluation, account binding with JWT invalidation, and simplified salary display with expandable detail panels.

**Current codebase state:** ~31,000 Python LOC + ~20,500 TypeScript LOC. SQLite in dev (wage_adjust.db). Celery/Redis foundation is runtime-verified; AI evaluation and bulk import now execute as Celery background tasks with frontend polling (2s interval, status text + spinner); employee records support optional `company` field with detail-only visibility.

**Known issues / tech debt:**
- filter-before-paginate for eligibility batch query won't scale beyond ~10k employees — needs server-side cursor pagination
- Phase 11 nav restructuring code is in the repo but planning artifacts are incomplete (no SUMMARY.md); functionality requires verification
- 工号前导零存量数据未修补：Phase 30 只修复写入路径；DB 已有的 `1234` vs `01234` 历史差异需单独一次性清洗任务（暂无 owner/时间表）

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
*Last updated: 2026-04-21 after Phase 30 工号前导零修复 completion*
