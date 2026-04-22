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
- ✓ 飞书同步可观测性：`FeishuSyncLog` 扩展 `sync_type` + `mapping_failed_count`；`FeishuService` 抽出 `_with_sync_log` helper + `_SyncCounters` dataclass 统一 5 类同步的 log 生命周期；`unmatched + mapping_failed + failed > 0 → partial` 硬切派生；per-sync_type 锁（409 不写 log）；HR 独立「同步日志」页面含 6 Tab + 5 色 badge + CSV 下载 + 详情抽屉 — 验证于 Phase 31 (IMPORT-03/04)；代码层 12/12 must-haves 全绿，9 项浏览器 UAT 留在 `31-HUMAN-UAT.md`
- ✓ 调薪资格导入功能补齐：`ImportService` 扩 6 类（含 `hire_info` / `non_statutory_leave`，复用 D-02/D-03 飞书同步字段映射 + Excel 序列号日期双分支）；4 类资格 import 全支持 `overwrite_mode='merge'|'replace'`；两阶段提交（preview + 暂存 sha256 + confirm + cancel）；per-import_type 锁（409 不写 log）+ APScheduler `expire_stale_import_jobs` 双时限清理；`AuditLog` 用真实字段 `target_type='import_job'` / `target_id` / `operator_id` 写 `import_confirmed`；`SalaryAdjustmentRecord` 加 `(employee_id, adjustment_date, adjustment_type)` UniqueConstraint，`_import_salary_adjustments` 改 upsert；前端 `ExcelImportPanel` 7 态 discriminated union + 6 个独立子组件（PreviewCountersStrip / PreviewDiffTable / OverwriteModeRadio / ReplaceModeConfirmModal / ImportActiveJobBanner / ImportPreviewPanel）+ blob 下载；旧 `POST /excel` 标 deprecated — 验证于 Phase 32 (IMPORT-01/02/05/06/07)；13/13 must-haves 全绿，4/4 浏览器 UAT 通过（截图归档 `.planning/phases/32-eligibility-import-completion/uat-screenshots/`），2 个 minor a11y defect（focus trap 未过滤 disabled、ESC 后焦点未恢复）记录在 32-VERIFICATION.md followup
- ✓ 员工端调薪资格自助可见：后端 `GET /api/v1/eligibility/me`（无参，复用 `EligibilityService.check_employee()`，`require_roles` 仅允许 `employee` 等已登录角色，越权天然不可达 — `/eligibility/{id}` 仍限 admin/hrbp/manager，employee 无法绕过）；`EligibilityResultSchema` 扩 `data_updated_at` 字段取 4 数据源 (employee.updated_at / salary_adjustment / performance / leave) 的 `max(updated_at)`；前端 `MyEligibilityPanel` 组件（302 行，11 个 data-testid）以 5 态 discriminated union（loading/success/unbound/employee_missing/error）覆盖 4 态徽章 + 4 色规则行（eligible 绿 / ineligible 红 / data_missing 灰 / manual_review 黄）+ zh-CN 时间戳「数据更新于 YYYY 年 M 月 D 日 HH:MM」+ 重试按钮；MyReview 顶部独立 section（line 545，独立于 employee 匹配）；detail 文本完全脱敏（无 ISO 日期、无薪资数字）— 验证于 Phase 32.1 (ESELF-01/02/04/05)；11/11 must-haves 全绿，4/4 浏览器 UAT 通过（Playwright 自动化），ESELF-03 绩效档次推迟到 Phase 35
- ✓ 绩效档次纯引擎：`PerformanceTierEngine` 纯计算（`backend/app/engines/performance_tier_engine.py`，162 LOC，零 I/O 零 DB），按 `PERCENT_RANK` 口径切 20/70/10 三档；4-branch ties 算法（横跨多档 → D-02 中位数归档 / first<20% → D-01 首位扩张 / first>=90% → 末档 / 单档边界 → D-02 中位数归档），ties 永不机械拆分；样本 < `Settings.performance_tier_min_sample_size`（默认 50）时全员 tier=null + `insufficient_sample=true` + 强制 `distribution_warning=false`；分布偏离 ±5% 绝对百分点（1 档 ∈ [15%, 25%]、2 档 ∈ [65%, 75%]、3 档 ∈ [5%, 15%]）任一超出触发 `distribution_warning=true`；异常 grade（None/''/不在 GRADE_ORDER）跳过且不计入 sample_size，`skipped_invalid_grades` 计数；输出 `@dataclass TierAssignmentResult`（6 字段：tiers / insufficient_sample / distribution_warning / actual_distribution / sample_size / skipped_invalid_grades）；复用 `eligibility_engine.GRADE_ORDER` 单一事实源；30 个 pytest 用例全 pass（150% 超 ROADMAP SC-5 的 20+ 最低线），engines 全套 64 tests 无回归 — 验证于 Phase 33 (PERF-03/04/06)；9/9 must-haves 全绿，1 个自动修复（IEEE 754 float drift in `_check_distribution_warning`，已修），Phase 34 Service 可通过 `from backend.app.engines import PerformanceTierEngine, PerformanceTierConfig, TierAssignmentResult` 零负担消费
- ✓ 绩效管理服务与 API：HR/admin 独立「绩效管理」页面 `/performance`（顶部分布视图 + 中部 Excel 导入复用 Phase 32 ExcelImportPanel + 底部 7 列分页表格）；后端 `PerformanceService` 414 LOC（recompute_tiers + list_available_years 等 6 方法）+ 5 REST 端点（`/performance/{records,tier-summary,recompute-tiers,available-years}` + Phase 35 留位 `/me/tier`）+ `import_service.confirm_import` hook 同步重算 5s 阻塞（超时 202 后台续）；并发控制：`PerformanceTierSnapshot.year` 行锁 `SELECT ... FOR UPDATE NOWAIT`，竞争方 409 + retry_after；持久化：单年一行 `PerformanceTierSnapshot(tiers_json + 9 字段)` + Redis 24h 缓存 + 写穿透；`PerformanceRecord.department_snapshot` 新字段（PERF-08，写入时取 `employee.department` 当时值，含 Excel 导入路径 - B-1 修复）；`ConfirmResponse.tier_recompute_status: Literal['completed','in_progress','busy_skipped','failed','skipped']`（W-1，前端 5 状态分支 toast）；前端 13 文件（PerformanceManagementPage + 6 components + ECharts horizontal stacked bar + 3 内联 SVG NavIcons + toast.ts 单实例 helper + roleAccess `/performance` → admin/hrbp + ProtectedRoute），UI-SPEC §0 反向勘误（项目实际栈 ECharts + inline SVG，禁止 lucide-react/recharts）— 验证于 Phase 34 (PERF-01/02/05/08)；55 后端测试全绿（Service 21 + API 13 + import_hook 6 + tier_cache 12 + model 4，含 Plan-checker 5 blockers + 4 warnings 修复后回归）+ engines 64 tests 0 回归 + frontend lint+build PASS；6/6 浏览器 UAT 通过（Playwright 自动化，含 Item 5 minor gap「idempotent recompute updated_at 不刷新」已修复 + 回归测试覆盖）

### Active (v1.4 in progress)

- [ ] 员工端绩效档次自助可见：`MyReview` 页面追加 `MyPerformanceTierBadge`（Phase 35，复用 32.1 panel 结构 + 33 engine + 34 API）
- [ ] 绩效档次与历史展示：评估详情/调薪建议展示历史绩效；员工端显示 1/2/3 档（20/70/10，全公司对比）
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
*Last updated: 2026-04-22 after Phase 34 绩效管理服务与 API completion*
