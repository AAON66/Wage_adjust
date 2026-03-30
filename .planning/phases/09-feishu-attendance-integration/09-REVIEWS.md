---
phase: 9
reviewers: [codex]
reviewed_at: 2026-03-30T09:10:00+08:00
review_rounds: 2
plans_reviewed: [09-01-PLAN.md, 09-02-PLAN.md, 09-03-PLAN.md]
---

# Cross-AI Plan Review — Phase 9

## Round 2: Codex Review (GPT-5.4) — Post-Revision

### Plan 09-01: Data Foundation

**Summary**
The revision materially improves the data contract. Period grain is explicit, masking contract is clear, schema/model additions are aligned with Plan 02 needs. The foundation is improved but not fully hardened — dedupe enforcement deferred to service layer.

**Revision Verdict**

| Original Concern | Verdict | Notes |
|---|---|---|
| 1. threading.Lock → DB guard | PARTIALLY RESOLVED | FeishuSyncLog is necessary groundwork, but Plan 01 does not add an atomic claim mechanism |
| 2. Incremental sync watermark | PARTIALLY RESOLVED | source_modified_at and feishu_record_id are the right fields; enforcement deferred to Plan 02 |
| 3. Period grain | RESOLVED | period is explicitly String(7) with 'YYYY-MM' |
| 4. test-connection endpoint | N/A | Not applicable to data layer plan |
| 5. Secret masking | RESOLVED | FeishuConfigRead uses app_secret_masked, excludes plaintext |
| 6. HRBP scoping | N/A | Not applicable to data layer plan |
| 7. SalarySimulator | N/A | Not applicable to data layer plan |

**New Concerns**
- **[MEDIUM]** `feishu_record_id` has no uniqueness constraint in DB — dedupe depends entirely on service correctness

**Risk Assessment: MEDIUM**

---

### Plan 09-02: Service Layer + API + Scheduler

**Summary**
Strongest revision area, much clearer on token flow, retries, watermarking, API surface, and scope handling. However, the concurrency fix is not truly atomic, period assignment logic is wrong for backfill/full-sync, and test-connection can't validate unsaved credentials.

**Revision Verdict**

| Original Concern | Verdict | Notes |
|---|---|---|
| 1. threading.Lock → DB guard | PARTIALLY RESOLVED | DB query is better than threading.Lock, but _is_sync_running() is still check-then-start race |
| 2. Incremental sync watermark | PARTIALLY RESOLVED | Watermark + 5-min overlap specific now, but period assignment is flawed |
| 3. Period grain | PARTIALLY RESOLVED | Type defined, but `current_period = now('%Y-%m')` stamps sync month, not source month |
| 4. test-connection endpoint | PARTIALLY RESOLVED | Endpoint exists but only tests stored config, not unsaved/new form values |
| 5. Secret masking | RESOLVED | get_config_read() and masked schema close the gap |
| 6. HRBP scoping | RESOLVED | AttendanceService + AccessScopeService explicitly integrated |
| 7. SalarySimulator | N/A | Backend plan |

**New Concerns**
- **[HIGH]** Concurrency guard not atomic — two workers can both observe "no running sync" before either inserts a `running` row. Fix: use SELECT FOR UPDATE or INSERT with ON CONFLICT for atomic claim.
- **[HIGH]** `current_period = datetime.now().strftime('%Y-%m')` misclassifies records during full sync, backfill, or cross-month windows. Period should come from source data or explicit derivation rule.
- **[MEDIUM]** `POST /feishu/test-connection` has no request body — first-time setup and unsaved edits can't be tested from UI before saving.
- **[MEDIUM]** Scheduler registers daily job even when no Feishu config exists — creates avoidable failed runs.
- **[MEDIUM]** `GET /feishu/config` readable by HRBP exposes connection metadata without stated need — lighter "config exists" contract would be safer.

**Risk Assessment: HIGH** (concentrated in concurrency and period logic)

---

### Plan 09-03: Frontend

**Summary**
Directionally correct: sync states explicit, secret field write-only, salary page integration decoupled. Remaining issues are readiness, not intent — test-connection depends on incomplete backend contract, lazy-load description doesn't match current SalarySimulator state shape.

**Revision Verdict**

| Original Concern | Verdict | Notes |
|---|---|---|
| 1-3 | N/A | Backend concerns |
| 4. test-connection endpoint | PARTIALLY RESOLVED | UI wires button to endpoint, but contract can't test unsaved credentials |
| 5. Secret masking | RESOLVED | Write-only field with placeholder mask |
| 6. HRBP scoping | PARTIALLY RESOLVED | Route/module visibility defined, data scoping backend-only |
| 7. SalarySimulator | PARTIALLY RESOLVED | Independent state/effect right fix, but `selectedEmployee?.id` may not match current simulator shape |

**New Concerns**
- **[MEDIUM]** testConnection() UI flow misleading unless backend accepts draft form values
- **[MEDIUM]** Lazy-load dependency not implementation-ready — current code uses employee identifiers differently
- **[MEDIUM]** AttendanceManagement infers config via full config read, coupling HRBP page to admin API

**Risk Assessment: MEDIUM**

---

## Consensus Summary (Round 2)

### Round 1 Concerns — Resolution Status

| # | Original Concern | Round 2 Verdict |
|---|-----------------|-----------------|
| 1 | threading.Lock → DB guard | PARTIALLY RESOLVED — race condition remains |
| 2 | Incremental sync watermark | PARTIALLY RESOLVED — watermark good, period assignment flawed |
| 3 | Period grain | RESOLVED |
| 4 | test-connection endpoint | PARTIALLY RESOLVED — exists but limited |
| 5 | Secret masking | RESOLVED |
| 6 | HRBP scoping | RESOLVED |
| 7 | SalarySimulator lazy load | PARTIALLY RESOLVED — pattern correct, implementation details need adjustment |

### New HIGH Concerns (Round 2)

1. **Concurrency guard race condition** — _is_sync_running() is check-then-start; two workers can both pass the check before either inserts. Fix: atomic INSERT with status='running' using ON CONFLICT or SELECT FOR UPDATE.
2. **Period derivation from sync time** — `datetime.now().strftime('%Y-%m')` stamps the month the sync runs, not the month the attendance data represents. Full sync in April will mark all records as '2026-04'. Fix: derive period from source data field or allow admin to specify target period.

### New MEDIUM Concerns (Round 2)

3. **test-connection can't test unsaved credentials** — Accept optional request body with draft credentials
4. **Scheduler runs without config** — Skip job registration if no active config exists
5. **feishu_record_id not unique in DB** — Consider unique index for stronger dedupe guarantee
6. **HRBP sees full config metadata** — Use lighter endpoint for config existence check

### Recommendations Before Execution

The two blocking items (both in Plan 02):
1. Make sync ownership atomic (INSERT-based claim, not check-then-insert)
2. Derive period from source data, not `datetime.now()`

The MEDIUM items are addressable during implementation without plan restructuring.

---

## Round 1 Review (archived)

<details>
<summary>Click to expand Round 1 review</summary>

### Plan 09-01 (Round 1)
- MEDIUM risk. Period grain unclear, secret masking implicit, source watermark fields missing.

### Plan 09-02 (Round 1)
- HIGH risk. threading.Lock insufficient, incremental sync vague, test-connection missing, HRBP scoping absent.

### Plan 09-03 (Round 1)
- MEDIUM risk. API mismatch risk, SalarySimulator complexity, incomplete UI states.

All Round 1 concerns were addressed in the revision. See Round 2 above for current status.

</details>
