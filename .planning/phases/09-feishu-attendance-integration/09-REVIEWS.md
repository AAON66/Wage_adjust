---
phase: 9
reviewers: [codex]
reviewed_at: 2026-03-30T09:30:00+08:00
review_rounds: 3
plans_reviewed: [09-01-PLAN.md, 09-02-PLAN.md, 09-03-PLAN.md]
---

# Cross-AI Plan Review — Phase 9

## Round 3: Codex Review (GPT-5.4, 2026-03-30)

> Round 3 — Codex reviewed the revised plans after 2 prior rounds of feedback. Only NEW concerns are listed.

### Plan 01: 数据基础

**Summary:** Plan 01 is structurally solid. The model split is sensible, the uniqueness strategy is much better than earlier rounds, and the masked-secret/read-vs-write separation is aligned with the phase goals. The remaining gaps are mostly around whether the schema captures the exact business semantics the UI needs later, especially for freshness labeling and secure operability.

**Strengths:**
- Clear separation of config, attendance data, and sync log concerns
- `feishu_record_id` uniqueness plus `(employee_id, period)` uniqueness gives a practical dedup/update foundation
- Secret masking in read models reduces accidental credential exposure
- Adding `source_modified_at` creates a usable basis for incremental sync
- Introducing test stubs in Wave 1 should reduce downstream API/service churn

**Concerns:**
- **MEDIUM** — The schema does not clearly define a dedicated business-facing `data_as_of` timestamp. `source_modified_at` and sync time are not the same thing, and ATT-06 / SC-3 need a user-visible "数据截至" value that is semantically correct.
- **MEDIUM** — The plan names `FEISHU_ENCRYPTION_KEY`, but not its validation/fail-fast behavior. If the key is missing, malformed, or rotated incorrectly, config rows can become unreadable with no clear recovery path.

**Suggestions:**
- Add an explicit `data_as_of_at` field, even if it is mapped from a Feishu field or derived by a documented rule
- Define startup/runtime validation for `FEISHU_ENCRYPTION_KEY`: required, expected format/length, and what happens on decryption failure
- Consider storing an encryption key version or at least leaving room for future key rotation

**Risk Assessment:** MEDIUM — core data model is good, but freshness semantics and encryption operability are still underspecified.

---

### Plan 02: 服务层

**Summary:** Plan 02 covers the main service responsibilities well and fixes several prior weaknesses, but this is still the highest-risk plan. The remaining issues are less about happy-path coding and more about production correctness: scheduler semantics, transaction boundaries, visibility rules, and exact API behavior for "current attendance."

**Strengths:**
- Token refresh and retry strategy are concrete rather than hand-wavy
- Incremental sync with overlap window is a reasonable design
- Atomic sync claiming is the right direction for manual/scheduled overlap
- Reusing `AccessScopeService` is consistent with the current backend architecture
- The endpoint set is close to what the phase needs

**Concerns:**
- **HIGH** — The scheduled daily sync has no explicit timezone contract. "Configurable time" is not enough if APScheduler runs in server-local time rather than the HR business timezone.
- **HIGH** — The plan does not state a strict transaction boundary for record upserts, watermark advancement, and sync-log status changes. A partial failure can otherwise mark sync progress incorrectly and create silent data loss.
- **HIGH** — `GET /attendance/{employee_id}` allows `manager`, which conflicts with D-13 (`admin + hrbp` visible, config only `admin`) unless there was a later role decision not shown here.
- **MEDIUM** — `GET /attendance/{employee_id}` does not define which period is returned. With monthly records, "current attendance" is ambiguous and can drift from the salary-review context.
- **MEDIUM** — The plan does not mention Feishu pagination or truncated-result handling. For a multi-dimensional table sync, that is a realistic source of silently incomplete data.
- **MEDIUM** — Unmatched `employee_no` handling is not described. Those rows should be skipped, counted, and surfaced in sync results rather than failing the whole run.

**Suggestions:**
- Define timezone storage explicitly, or bind scheduler execution to a fixed application timezone
- Make sync execution transactional: only advance watermark and mark success after all record writes commit
- Tighten the attendance-read role model to match D-13, or document the revised role decision
- Specify the attendance read contract clearly: latest available period, requested period, or period tied to the salary review context
- Add an explicit sync request schema with `mode`, and return counts for synced, updated, skipped, unmatched, and failed rows
- Document pagination/rate-limit behavior in the Feishu fetch loop

**Risk Assessment:** HIGH — the service plan is close, but several unresolved behaviors can still produce incorrect or misleading attendance data in production.

---

### Plan 03: 前端

**Summary:** Plan 03 is reasonably scoped, but it has one potentially phase-breaking issue: it appears to focus the embedded attendance work on the wrong screen. In the current frontend, manual salary adjustment lives in `EvaluationDetail.tsx`, while `SalarySimulator.tsx` is the budget sandbox. If that mismatch is real, the plan will miss ATT-05 and SC-3 even if the new pages/components are otherwise well built.

**Strengths:**
- Splitting config, management, and embedded display concerns is clean
- `config-exists` usage avoids overexposing config data to HRBP
- `AttendanceKpiCard` and `SyncStatusCard` are good UI boundaries
- Keeping attendance state independent from salary state is the right instinct
- Route-level permission updates are explicitly called out

**Concerns:**
- **HIGH** — The plan may be wiring attendance into the salary simulator instead of the actual manual salary adjustment page. If the embedded panel is not added to `EvaluationDetail`, the core user-facing success criterion (ATT-05 / SC-3) is missed.
- **MEDIUM** — The config-edit UX does not explicitly say "leave secret blank to keep current value." With a write-only secret field, editing mappings/settings can otherwise wipe credentials or force unnecessary re-entry.
- **MEDIUM** — Frontend sync actions still look singular (`triggerSync()`), but D-08 requires separate full-sync and incremental-sync actions.
- **MEDIUM** — The embedded attendance panel needs an explicit no-data / failed-sync / stale-data fallback that does not block salary review. That behavior is implied by ATT-07 but not clearly planned.
- **LOW** — Independent `useState` + `useEffect` is acceptable, but the plan should include stale-response protection when the selected employee changes quickly.

**Suggestions:**
- Re-anchor the embedded attendance panel to the actual manual salary screen first, then treat attendance management as the secondary UI
- Define update semantics for the secret field end-to-end: blank means unchanged, explicit replace requires new value
- Split sync actions in the UI and service layer into `incremental` and `full`, with labels that match the decision record
- Add explicit UI states for `never synced`, `no attendance yet`, `stale`, and `last sync failed`
- Guard attendance fetches with request cancellation or response identity checks

**Risk Assessment:** HIGH — the plan is close on components and pages, but if it targets the wrong embedded screen or misses the full/incremental UX contract, the phase goal will not actually be met.

---

## Consensus Summary (Round 3 — single reviewer)

### Key Concerns by Severity

| # | Severity | Plan | Concern | Actionable? |
|---|----------|------|---------|-------------|
| 1 | HIGH | 03 | Attendance embedded in SalarySimulator instead of EvaluationDetail — may miss ATT-05/SC-3 | Yes — verify which page is "manual salary adjustment" |
| 2 | HIGH | 02 | No timezone contract for APScheduler daily sync | Yes — explicit timezone config |
| 3 | HIGH | 02 | No transaction boundary for sync upserts + watermark + log status | Yes — wrap in single transaction |
| 4 | HIGH | 02 | Manager role on attendance/{id} conflicts with D-13 | Yes — align roles or document decision |
| 5 | MEDIUM | 01 | No dedicated `data_as_of` timestamp for ATT-06 display | Yes — clarify synced_at semantics |
| 6 | MEDIUM | 01 | FEISHU_ENCRYPTION_KEY validation missing | Yes — fail-fast on startup |
| 7 | MEDIUM | 02 | "Current attendance" period ambiguous | Yes — specify period selection |
| 8 | MEDIUM | 02 | Pagination/truncation handling not documented | Partially addressed in plan |
| 9 | MEDIUM | 02 | Unmatched employee_no handling | Partially addressed in plan |
| 10 | MEDIUM | 03 | Secret field "blank means keep" not explicit in UX | Yes — UX text/logic |
| 11 | MEDIUM | 03 | triggerSync() should accept mode parameter | Partially addressed in plan |
| 12 | MEDIUM | 03 | No fallback UI states for no-data/stale/failed in embedded panel | Yes — add states |

### Triage Notes

**Concern #1 (embedded panel location)** requires verification: check if D-10 指定了 "人工调薪窗口" 是 EvaluationDetail 还是 SalarySimulator。CONTEXT.md D-10 说 "人工调薪窗口内嵌"，ATT-05 说 "人工调薪页面在薪资调整区域展示"。SalarySimulator 是 "调薪模拟/预算沙盘"，可能不是 "人工调薪页面"。需要确认实际页面映射。

**Concerns #8, #9, #11** 在现有计划中已有部分覆盖（Plan 02 Task 1 包含 page_token 循环、unmatched_records 计数、SyncTriggerRequest(mode=...)），Codex 可能未完全读取计划全文。这些标记为 "Partially addressed"。

**Concern #4 (manager 角色)** 需要业务决策：manager 查看自己团队成员考勤是否合理？D-13 说的是"页面权限"（考勤管理页面），而 ATT-05 说的是"人工调薪页面展示考勤概览"——manager 在审批流中需要看到考勤数据。这可能是有意设计而非冲突。

---

*Review completed: 2026-03-30 by Codex (GPT-5.4)*
*Plans reviewed: 09-01-PLAN.md, 09-02-PLAN.md, 09-03-PLAN.md*
