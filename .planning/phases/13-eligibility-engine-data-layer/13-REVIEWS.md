---
phase: 13
reviewers: [codex]
reviewed_at: 2026-04-02T12:00:00Z
plans_reviewed: [13-01-PLAN.md, 13-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 13

## Codex Review

### Plan 13-01 Review

#### Summary
Plan 13-01 has the right architectural shape for the core of this phase: it separates persistence from rule evaluation, makes thresholds configurable, and puts test depth where it matters most. The main weakness is not structure but specification clarity: several business semantics that the engine must encode are still ambiguous, so the plan risks producing a clean implementation that still fails acceptance on edge cases.

#### Strengths
- Pure engine pattern aligns well with D-05 and D-06, and reduces coupling between business rules and storage.
- Wave split is sensible: schema and engine first, service/API/import after.
- Configurable thresholds addresses D-04 and avoids hardcoded rule drift.
- TDD for the engine is appropriate because the eligibility logic is the highest-risk part of the phase.
- Rule-level three-state output is a good basis for distinguishing `eligible`, `ineligible`, and missing inputs.

#### Concerns
- [HIGH] The plan does not resolve key rule semantics the engine needs to be correct:
  - exactly how to compute ">= 6 months"
  - what to do when an employee has never had a salary adjustment
  - what time window applies to non-statutory leave days
  - which performance record is authoritative if multiple exist
- [HIGH] There is a terminology mismatch between ELIG-08 (`data_missing`) and D-10 (`pending` overall status). If this mapping is not explicit, downstream API/UI behavior will diverge.
- [HIGH] Adding to `AttendanceRecord` is underexplained and may be the wrong abstraction if the leave rule depends on an aggregated period rather than per-record data.
- [MEDIUM] The model plan should include uniqueness and indexing strategy now, not later:
  - `PerformanceRecord(employee_id, year)` likely needs uniqueness
  - `SalaryAdjustmentRecord(employee_id, adjustment_date)` needs indexed lookup for latest record
- [MEDIUM] "Configurable thresholds" is straightforward for month/day thresholds, but less so for performance grades. Grade ordering and normalization are not specified.
- [MEDIUM] Migration/backfill behavior is not mentioned. Existing employees will immediately hit missing-data states unless defaults and rollout behavior are defined.
- [LOW] "19+ unit tests" sounds arbitrary; coverage quality matters more than hitting a number.

#### Suggestions
- Define the engine contract before coding: input DTO shape, per-rule result shape, overall result mapping from rule-level `data_missing` to overall `pending`
- Add explicit acceptance cases for boundary conditions: exactly 6 calendar months, future dates, null dates, no salary adjustment history, performance grade case/format variations, leave exactly 30 days
- Decide and document the leave evaluation period now
- Add DB constraints and indexes in the migration, not as a follow-up
- Treat performance grade threshold as a normalized enum/rank mapping, not free-form string comparison
- Replace the fixed test count target with a required scenario matrix tied directly to ELIG-01/02/03/04/08

#### Risk Assessment
**MEDIUM** — The architecture is solid, but the business-rule ambiguities are serious enough to create rework. If those semantics are clarified before implementation starts, risk drops quickly.

---

### Plan 13-02 Review

#### Summary
Plan 13-02 is the phase-closing plan, so it must prove the feature actually works end to end. It has the right major components, but it currently underspecifies the operational details that determine whether the phase goal is truly met.

#### Concerns
- [HIGH] Manual entry is required by ELIG-09/D-07, but the plan does not explicitly include manual write flows.
- [HIGH] Feishu sync coverage looks incomplete — only performance data sync, not hire date, salary adjustment history, and leave data.
- [HIGH] Excel import coverage is underspecified — how do hire date and non-statutory leave data enter the system?
- [HIGH] Missing-data handling at the service/API layer is not specified.
- [MEDIUM] Import/sync idempotency is not addressed.
- [MEDIUM] Partial failure handling is missing.
- [MEDIUM] Performance risk with N+1 queries for batch eligibility.
- [MEDIUM] Security and governance absent — authz and audit logging.

#### Suggestions
- Explicitly enumerate endpoints and map each to a requirement
- Add a source-of-truth matrix for each required input field with channel support
- Require idempotent upsert semantics for imports
- Define service-level query semantics (latest adjustment selection, performance record selection, leave aggregation)
- Add authorization and audit logging requirements
- Plan query optimization for batch eligibility checks

#### Risk Assessment
**HIGH** — Several acceptance-critical behaviors are implied rather than specified. The biggest gap is ELIG-09: the current plan does not yet clearly prove that all required data is supported across all three channels.

---

## Consensus Summary

### Agreed Strengths
- Pure engine pattern (D-05/D-06) is well-designed
- Wave decomposition (models+engine → service+API+import) is correct
- Configurable thresholds via Settings is sound
- TDD approach for engine is appropriate

### Agreed Concerns
- Business rule semantics need clarification (month calculation, no-history fallback, leave aggregation period)
- ELIG-08/D-10 terminology mapping (data_missing vs pending) needs to be explicit
- Three import channels (ELIG-09) are not fully specified — hire_date and leave data import paths unclear
- Import idempotency and partial failure handling need attention

### Divergent Views
N/A (single reviewer)
