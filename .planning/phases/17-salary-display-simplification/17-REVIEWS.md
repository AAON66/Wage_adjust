---
phase: 17
reviewers: [codex]
reviewed_at: 2026-04-07T18:30:00+08:00
plans_reviewed: [17-01-PLAN.md, 17-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 17

## Codex Review

### Plan 17-01: SalarySummaryPanel + SalaryDetailPanel Extraction

**Summary**
This is the right refactor direction. Splitting the salary block out of EvaluationDetail.tsx should make DISP-01 and DISP-02 much easier to implement cleanly, but the plan is still underspecified about exactly which existing fields move into detail versus remain visible, and that gap is where regressions are most likely.

**Strengths**
- Good scope control: pure frontend refactor, no backend/model churn.
- The summary/detail split matches D-05 and D-07 well: one explicit React state, one expand/collapse control.
- Reusing `AttendanceKpiCard` and `SalaryHistoryPanel` reduces implementation risk.
- Pulling salary rendering out of the 2400-line page is a good maintainability move even beyond this phase.

**Concerns**
- **MEDIUM** The detail inventory is incomplete. The current salary block also shows current salary, recommended salary, and recommendation status, but the plan does not explicitly say where those move. That risks silently dropping data instead of collapsing it.
- **MEDIUM** "Manual adjustment section" in the summary conflicts with D-03 and D-12. If the full editor stays expanded in the summary layer, the page is still dense and the simplification goal is only partially met.
- **MEDIUM** The plan does not explicitly preserve the existing role guard around `AttendanceKpiCard`. That guard matters because the attendance endpoint is restricted.
- **LOW** No explicit accessibility or regression strategy is called out for the custom expand/collapse button. Once D-07 rejects native `<details>`, `aria-expanded`, focus behavior, and keyboard handling become manual responsibilities.
- **LOW** The prop count is a smell. "~25 props" usually means the extraction is only moving JSX around, not clarifying ownership.

**Suggestions**
- Define a summary/detail data matrix before implementation: summary = 3 indicator cards + featured final ratio + always-visible action row; detail = everything else, explicitly including current salary, recommended salary, status, calc trace, explanation, and history.
- Clarify whether the summary only keeps manual-action buttons, or also keeps the full manual editor. If the editor stays, justify why that still counts as "simplified."
- Prefer a small view-model object or a salary-specific hook over passing dozens of handlers/helpers individually.
- Add interaction coverage for default-collapsed render, expand/collapse, empty-state CTA, and always-visible action buttons.

**Risk Assessment:** MEDIUM — the extraction itself is straightforward, but the current plan can still miss the phase goal if it collapses the wrong things or drops existing data/guards during the move.

---

### Plan 17-02: EligibilityBadge Component + Integration

**Summary**
This plan addresses DISP-03 directly, but it has the sharper correctness risk of the two. The UI idea is sound, yet the current approach blurs backend status vocabulary, puts fetch logic inside a display component, and under-specifies non-happy-path handling for an endpoint that already has role and scope restrictions.

**Strengths**
- Good separation of concern: eligibility rendering becomes its own component.
- Dependency on 17-01 is sensible because the badge belongs in the extracted summary layer.
- The plan correctly acknowledges the employee-role 403 pitfall and keeps backend enforcement in place.
- Inline expansion for the 4 rules matches D-10 well.

**Concerns**
- **HIGH** The type/file ownership is wrong as written. Eligibility types already live in `frontend/src/types/api.ts`, while `frontend/src/services/api.ts` is just the Axios client. "Add `EligibilityResult` type to `api.ts`" suggests duplicated or misplaced models.
- **HIGH** Status normalization is not defined. The backend overall status is `eligible | ineligible | pending`, while rule statuses include `data_missing` and `overridden`. Without an explicit UI mapping, badge text/color semantics will drift.
- **MEDIUM** The rule list is described as check/cross icons only, but the actual rule model is at least four-state. Existing eligibility UI in `EligibilityListTab.tsx` already reflects that. A binary icon set would lose fidelity.
- **MEDIUM** A component-owned `useEffect` fetch needs more detail: loading state, abort/cancel, 403/404 handling, and manager cross-scope denial are all missing from the plan.
- **LOW** "Placeholder shown when no eligibility data available" is too vague. "No data," "not allowed," "loading," and actual yellow business-state should not collapse into one UI.

**Suggestions**
- Keep types in `frontend/src/types/api.ts`, not `services/api.ts`, and add a small shared status-mapping utility reused by the badge and the existing eligibility list UI.
- Normalize backend `pending` to the approved yellow UI label at the presentation boundary, and render `overridden` distinctly in the rule list.
- Prefer fetching in `EvaluationDetail` or a dedicated hook. If the badge owns the fetch, require `employeeId` + role guards, use `AbortController`, and define `loading / loaded / unavailable / denied` states explicitly.
- Add automated checks for employee-role no-fetch, manager out-of-scope handling, status mapping, and badge rule expansion.

**Risk Assessment:** MEDIUM — still a frontend-only change, but easy to implement with subtly wrong semantics unless type ownership, status mapping, and error-state behavior are tightened first.

---

## Consensus Summary

### Agreed Strengths
- Pure frontend refactor with no backend changes — low blast radius
- Good reuse of existing components (AttendanceKpiCard, SalaryHistoryPanel, status-pill CSS)
- Correct identification of the employee-role 403 pitfall with defense-in-depth mitigation
- Component extraction improves maintainability of the 2400-line EvaluationDetail.tsx

### Agreed Concerns
- **Status normalization gap** — backend uses `eligible/ineligible/pending` at the overall level but `eligible/ineligible/data_missing/overridden` at the rule level; no explicit mapping defined
- **Prop drilling smell** — ~25 props on SalarySummaryPanel suggests the extraction moves JSX without clarifying ownership; a view-model or hook would be cleaner
- **Summary/detail boundary underspecified** — which exact fields stay in summary vs move to detail needs an explicit matrix to prevent data loss
- **Error state handling vague** — loading, denied, unavailable, and business-state "pending" should not collapse into one placeholder

### Divergent Views
- None (single reviewer)
