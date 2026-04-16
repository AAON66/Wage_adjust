# Milestones

## v1.1 体验优化与业务规则完善 (Shipped: 2026-04-07)

**Phases completed:** 7 phases, 13 plans, 17 tasks

**Key accomplishments:**

- 4 binding API endpoints with token_version-based JWT invalidation for forced re-login on unbind
- Admin bind/unbind in UserAdmin, employee 3-step self-bind in Settings, yellow warning banner for unbound non-admin users
- PerformanceRecord + SalaryAdjustmentRecord models, pure-computation EligibilityEngine with 4 three-state rules (tenure/interval/performance/leave), 28 unit tests, configurable thresholds
- EligibilityService wiring DB to engine with 5 API endpoints, ImportService extended for performance grades and salary adjustments, FeishuService extended for performance record sync -- completing all three ELIG-09 data import channels
- Batch eligibility query with filter-before-paginate, two-level override approval with role-step binding, Excel export with 5000 row cap, and full RBAC hardening via AccessScopeService
- Role-aware eligibility management page with filterable batch list, Excel export, step-aware override approval, and employee access restriction
- PPT image extraction with SHA1 dedup, vision evaluation LLM prompt with 5-dimension relevance scoring, and >5MB image compression
- ParseService wires PPT image extraction and standalone image evaluation into the parse flow with batch failure isolation, plus EvidenceCard renders vision metadata with Chinese labels and quality badge coloring
- SharingRequest model + hash-only dedup refactor + atomic upload+request creation + 72h lazy expiry — all HIGH review concerns resolved.
- 1. [Rule 1 - Bug] Fixed Unicode curly quotes in generated JSX

---
