---
phase: 9
reviewers: [codex]
reviewed_at: 2026-03-30T08:40:00+08:00
plans_reviewed: [09-01-PLAN.md, 09-02-PLAN.md, 09-03-PLAN.md]
---

# Cross-AI Plan Review — Phase 9

## Codex Review (GPT-5.4)

### Plan 09-01: Data Foundation

#### Summary
This is a sensible first wave: it isolates schema, config, and test scaffolding before integration logic. The main weakness is that the data model is not yet precise enough for incremental sync, deduplication, and secure config editing, so there is a real risk of locking in the wrong storage shape too early.

#### Strengths
- Separates config, attendance data, and sync audit concerns into distinct models.
- Puts migration work ahead of service/API work, which reduces churn in later waves.
- Includes sync log persistence early, which is necessary for ATT-07 and incremental sync.
- Explicitly plans encrypted secret storage, which matches the project's existing encryption direction in `backend/app/core/encryption.py`.

#### Concerns
- **[HIGH]** `UniqueConstraint(employee_id, period)` is underspecified. The plan does not define the attendance grain clearly enough to know whether `period` means day, month, pay cycle, or snapshot window. That directly affects upsert correctness.
- **[HIGH]** The model list does not mention source-side identifiers or watermarks such as Feishu record ID and source modified time. Without those, incremental sync and dedupe will be fragile.
- **[MEDIUM]** `FeishuConfig` appears incomplete for the actual API contract. The Feishu records endpoint requires an app token plus table ID; the plan needs exact naming to avoid "App ID vs app_token" ambiguity.
- **[MEDIUM]** The read schemas do not explicitly say secrets are write-only/masked. Returning decrypted App Secret from config APIs would be a security defect.
- **[LOW]** "RED test stubs" can become low-value ceremony if they are only placeholders rather than executable contract tests.

#### Suggestions
- Define the attendance storage grain now. If this is a snapshot summary, model it as snapshot/as-of data; if it is period data, define the exact period key and source of truth.
- Add source metadata fields up front: `source_record_id`, `source_modified_at`, `matched_employee_no`, `sync_mode`, and indexes on `employee_id`, `source_modified_at`, and sync-log timestamps.
- Make config schemas explicitly safe: expose `has_app_secret` or masked values, never the secret itself.
- Decide whether a separate `FEISHU_ENCRYPTION_KEY` is necessary or whether the existing app-wide encryption pattern should be generalized from `backend/app/core/config.py`.
- Replace empty stubs with a small number of executable migration/model/schema tests that lock the API contract.

#### Risk Assessment
**MEDIUM.** The wave ordering is good, but the current model definition leaves too much ambiguity around sync identity and period semantics. If that is wrong, Wave 2 will absorb avoidable rework.

---

### Plan 09-02: Service Layer + API + Scheduler

#### Summary
This wave covers the right capabilities and is close to the real phase goal, but it contains the highest implementation risk. The biggest gaps are scheduler ownership, cross-process concurrency, and incremental-sync semantics. Those are not edge details here; they determine whether daily sync is correct and safe in production.

#### Strengths
- Service split is reasonable: Feishu integration concerns and attendance query concerns are separated.
- Includes token refresh, pagination, retry, manual sync modes, and scheduler rescheduling on config change.
- Fits the current FastAPI startup model in `backend/app/main.py` and layered service structure.
- Sync status API and log persistence align well with ATT-07.

#### Concerns
- **[HIGH]** `threading.Lock` only protects one process. It will not prevent duplicate scheduled runs or overlapping manual/scheduled syncs across multiple app workers or instances.
- **[HIGH]** APScheduler embedded in the FastAPI process needs explicit single-owner behavior. If the app runs more than one process, the daily job can fire multiple times.
- **[HIGH]** Incremental pull semantics are not specified tightly enough. "Based on last sync time" is not enough; the plan needs a source-modified watermark strategy with overlap/tie handling to avoid missing or duplicating records.
- **[MEDIUM]** The API surface does not obviously support the frontend's "test connection" button. That is a contract gap between Wave 2 and Wave 3.
- **[MEDIUM]** HRBP access rules are not called out. Existing backend patterns use scoped access checks, so attendance list/detail endpoints likely need department scoping, not just role checks.
- **[MEDIUM]** Secret handling and auditability are incomplete. Config updates should be admin-only, write-only for secrets, and probably audited.
- **[MEDIUM]** Partial failures are not described well enough: unknown `employee_no`, bad field mappings, invalid numeric conversions, or Feishu rate limits should not fail the whole batch silently.

#### Suggestions
- Replace `threading.Lock` with a distributed or durable guard: DB advisory lock, Redis lock, or a sync-log state transition that enforces one active job.
- Define deployment assumptions explicitly: single worker only, or a leader-election/locking strategy for the scheduler.
- Store and use source watermarks, not local `synced_at`, for incremental sync. Include a small overlap window and deterministic dedupe.
- Add a dedicated `POST /feishu/config/test` endpoint or drop the frontend test button.
- Make sync results richer: processed count, updated count, skipped count, unmatched employee count, and last error summary.
- Ensure attendance lookup failures degrade cleanly on the salary page instead of breaking the salary workflow.

#### Risk Assessment
**HIGH.** This wave is the core integration, and the unresolved scheduler/concurrency/incremental-sync details are production correctness risks, not polish items.

---

### Plan 09-03: Frontend

#### Summary
The frontend plan is directionally correct and maps well to the approved UX decisions, but it depends heavily on backend contract clarity. The main risks are API mismatch, underestimating the cost of modifying the already-large salary simulator page, and missing edge-state handling for stale/empty/failed attendance data.

#### Strengths
- Covers both required surfaces: embedded salary-page summary and standalone attendance management page.
- Route and permission split matches the user decisions: admin+hrbp view, admin-only config.
- Component breakdown is reasonable and should keep most UI work modular.
- Recognizes role-access updates, which matter because discoverability is driven by both routing and module links in `App.tsx` and `roleAccess.ts`.

#### Concerns
- **[MEDIUM]** The config page includes "test/save buttons," but the backend plan does not currently expose a test endpoint.
- **[MEDIUM]** `SalarySimulator.tsx` is already large and state-heavy. Embedding attendance there without a clean fetch boundary risks making the page harder to maintain.
- **[MEDIUM]** The plan mentions stale warning, but not the other required states: never synced, sync failed, no record for employee, sync in progress, and permission-restricted config entry.
- **[LOW]** Route registration alone is insufficient. The workspace/home module lists also need updates or the new pages will be hard to discover.
- **[LOW]** Timezone/display semantics for "Data as of" are not called out. That can create confusing UI if server and browser timezones differ.

#### Suggestions
- Add explicit UI states for `never_synced`, `syncing`, `failed`, `stale`, and `no_data`.
- Keep attendance fetching lazy on the salary page: only load when an employee is selected.
- Treat the App Secret as write-only in the form. Use masked placeholder UX rather than pre-filling decrypted values.
- Update both route guards and module navigation entries together.
- Define the blocking "human verification checkpoint" as concrete acceptance criteria, not just a gate label.

#### Risk Assessment
**MEDIUM.** The UI work is achievable, but only if Wave 2 locks the API contract early. The biggest frontend risk is dependency churn rather than raw implementation difficulty.

---

## Consensus Summary

> Note: Only one external reviewer (Codex/GPT-5.4) was available. Claude (current runtime) was skipped for independence; Gemini CLI is not installed.

### Top Concerns (by severity)

1. **[HIGH] Scheduler concurrency** — `threading.Lock` is insufficient for multi-worker deployments; APScheduler needs single-owner enforcement or distributed locking
2. **[HIGH] Incremental sync semantics** — "last sync time" watermark is too vague; needs source-modified timestamps with overlap window and deterministic dedupe
3. **[HIGH] Attendance period grain** — `UniqueConstraint(employee_id, period)` doesn't define what "period" means (day/month/cycle), which affects all upsert logic
4. **[MEDIUM] API contract gap** — Frontend test-connection button has no corresponding backend endpoint in Plan 02
5. **[MEDIUM] Secret masking** — Config read schemas must ensure App Secret is never returned in plaintext
6. **[MEDIUM] HRBP department scoping** — Attendance endpoints need department-level access control, not just role checks
7. **[MEDIUM] SalarySimulator complexity** — Embedding attendance in an already-large page needs clean fetch boundaries

### Agreed Strengths
- Wave sequencing (schema → service → frontend) is correct
- Separation of concerns across models and services
- Alignment with existing project patterns (encryption, role guards, layered architecture)
- Sync logging for ATT-07 compliance

### Recommendations Before Execution
1. Clarify `period` semantics and add `source_modified_at` watermark field to AttendanceRecord
2. Document single-worker deployment assumption or add DB advisory lock for scheduler
3. Add `POST /feishu/test-connection` endpoint to Plan 02 explicitly
4. Define all UI states (never_synced, syncing, failed, stale, no_data) in Plan 03
