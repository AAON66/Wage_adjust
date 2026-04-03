---
phase: 14
reviewers: [codex]
reviewed_at: 2026-04-04T08:00:00Z
plans_reviewed: [14-01-PLAN.md, 14-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 14

## Codex Review

### Plan 14-01: Backend

#### Summary
The backend plan is well-structured and mostly aligned to the phase goal. The main weaknesses are around authorization precision and result semantics: scope checks on employee-specific endpoints, filter-before-pagination ordering, and override workflow permissiveness.

#### Strengths
- Clear separation of model, schema, service, API, and tests
- Good handling of route ordering to avoid `/{employee_id}` swallowing `/batch` and `/overrides`
- Correctly treats batch eligibility as a bulk-query problem instead of looping `check_employee()`
- Covers both backend protection and frontend-hiding for ELIG-05
- Encodes override lifecycle explicitly, including HRBP rejection short-circuit
- Includes tests for export and overridden-status projection

#### Concerns
- [HIGH] `GET /eligibility/{employee_id}` only role-gated, no AccessScopeService check — manager could fetch any employee by ID
- [HIGH] `status_filter` and `rule_filter` applied after pagination — wrong `total` counts and partially empty pages
- [HIGH] `decide_override()` does not bind role to workflow step — admin could act at `pending_hrbp`, or hrbp at `pending_admin`
- [HIGH] Override creation does not require: requester can access target employee, employee is currently ineligible, selected rules are actually failing
- [MEDIUM] Plan allows admin to create override requests, but D-03 says only manager/HRBP initiate
- [MEDIUM] HRBP scope ambiguous — D-09 says HR/Admin see all, but AccessScopeService scopes hrbp by department
- [MEDIUM] "One active override per employee per year" only application-level, no DB-level protection
- [MEDIUM] Export semantics underspecified — full dataset or current page? No row-limit guard
- [MEDIUM] Existing sub-resource endpoints under `/eligibility/{employee_id}/...` remain possible data-leak path

#### Suggestions
- Add scope enforcement to every employee-specific eligibility endpoint
- Move derived-status filtering before pagination
- Restrict override creation to manager and hrbp only, validate subordinate access plus current ineligible rule set
- Enforce step-specific decisions: pending_hrbp → only hrbp, pending_admin → only admin
- Add DB-level protection for active override uniqueness
- Define export contract: same filters as list, full filtered result set, max row cap

#### Risk Assessment
**HIGH** — Authorization and pagination-semantics issues can break ELIG-05/06/07 or create security regressions.

---

### Plan 14-02: Frontend

#### Summary
The frontend plan is appropriately scoped and matches product decisions. Biggest issues are role/action precision and verification depth.

#### Concerns
- [HIGH] Override button too broad — D-03 says only manager/HRBP initiate, admin should not see that action
- [HIGH] Approve/reject actions not step-aware — should not show admin actions on pending_hrbp or vice versa
- [MEDIUM] Manager scope not concretely handled in UI — existing departmentScope.ts treats hrbp as scoped too, conflicts with D-09
- [MEDIUM] No frontend automated tests for menu hiding, route redirect, scoped filtering, role-step action gating
- [MEDIUM] Department filter source unspecified
- [MEDIUM] Loading, empty, and mutation-refresh states not called out

#### Suggestions
- Hide "申请特殊审批" for admin; show only for manager and hrbp
- Make approve/reject buttons status-aware: pending_hrbp for HRBP only, pending_admin for admin only
- Resolve HRBP visibility rule explicitly before implementation
- Extend human checkpoint to include manager and HRBP accounts

#### Risk Assessment
**MEDIUM** — UI structure is fine, but role-step behavior and scope rules need tightening.

---

## Consensus Summary

### Agreed Strengths
- Architecture is sound: model/service/API separation, bulk queries, dual protection
- Override lifecycle with short-circuit rejection is well-designed
- Wave decomposition (backend → frontend) is correct

### Agreed Concerns
1. **Authorization gaps** — Employee-specific endpoints lack AccessScopeService checks; override workflow doesn't bind role to step
2. **Pagination semantics** — Status/rule filters applied after pagination produce wrong counts
3. **Override creation too permissive** — No validation that employee is actually ineligible or that requester has access
4. **Role-step UI visibility** — Override actions and approval buttons not step-aware
5. **HRBP scope ambiguity** — D-09 says HR sees all, but AccessScopeService may scope HRBP by department

### Divergent Views
N/A (single reviewer)
