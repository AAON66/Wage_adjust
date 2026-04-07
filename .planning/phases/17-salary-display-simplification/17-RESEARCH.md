# Phase 17: Salary Display Simplification - Research

**Researched:** 2026-04-07
**Domain:** Frontend UI refactoring (React + TypeScript + Tailwind CSS)
**Confidence:** HIGH

## Summary

This phase is a pure frontend refactoring of the salary module rendering within `EvaluationDetail.tsx`. The current implementation displays all salary data (recommendation cards, live preview, explanation, manual adjustment, approval buttons, salary history) in a flat, fully-expanded layout spanning ~210 lines of JSX (lines 2060-2268). The goal is to restructure this into a summary-first layout with expandable details and an eligibility badge component.

The technical risk is LOW -- no new libraries, no backend changes, no data model alterations. The work involves (1) extracting the salary module IIFE content into two new components (`SalarySummaryPanel` and `SalaryDetailPanel`), (2) creating an `EligibilityBadge` component that calls the existing `GET /eligibility/{employee_id}` API, and (3) wiring the expand/collapse state. All CSS classes, design tokens, and API endpoints already exist.

**Primary recommendation:** Extract salary module rendering into `SalarySummaryPanel` + `SalaryDetailPanel` components, add a new `fetchEmployeeEligibility()` frontend service function, and create an inline-expandable `EligibilityBadge` component. No npm installs needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Summary layer shows 3 indicator cards: AttendanceKpiCard (reused), eligibility badge, AI score/level
- D-02: Summary also shows "final adjustment ratio" as featured large number
- D-03: All other data (recommended ratio, AI multiplier, certification bonus, live preview, explanation, dimension details) collapsed into detail layer
- D-04: AttendanceKpiCard reused as-is, no modifications
- D-05: Single "expand details" button, expands ALL detail data at once
- D-06: Expanded state shows "collapse" button, toggles back to summary
- D-07: Expand/collapse via React useState, not native `<details>`
- D-08: Eligibility badge colors: green=eligible, red=ineligible, yellow=data_missing
- D-09: Reuse existing `status-pill` CSS class
- D-10: Click badge to inline-expand 4 rule results below it
- D-11: Rule expand is inline, no modal, no navigation
- D-12: "Manual adjustment" and "Submit approval" buttons always visible in summary layer bottom
- D-13: "Manual adjustment" click reuses existing `isSalaryEditorOpen` state
- D-14: Core action entry points not buried under collapsed details
- D-15: SalaryHistoryPanel moved into detail layer
- D-16: Summary layer does NOT show history chart
- D-17: Empty state shows text + "generate salary recommendation" button
- D-18: Eligibility badge and AI score show if data available even when no salary recommendation
- D-19: Detail layer dimension scores in table format: dimension name, score, weight, weighted score
- D-20: Reuse review module table style for consistency

### Claude's Discretion
- Expand/collapse animation effect (presence, duration)
- Summary layer card spacing and arrangement
- Detail layer internal section ordering
- Eligibility badge placeholder when no data available

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISP-01 | Salary page defaults to key summary (attendance + eligibility status + AI score) | Existing `AttendanceKpiCard`, new `EligibilityBadge`, evaluation `overall_score`/`ai_level` from existing state -- all data sources verified available |
| DISP-02 | Detailed data (dimension details, score explanation, calculation process) via expand button | Current salary module JSX (lines 2060-2268) already renders all this data; restructuring into `SalaryDetailPanel` with `useState<boolean>(false)` toggle |
| DISP-03 | Eligibility status as badge (eligible/ineligible/data_missing), expandable to 4 rule results | Backend `GET /eligibility/{employee_id}` returns `EligibilityResultSchema` with `overall_status` + `rules[]`; role-restricted to admin/hrbp/manager (matching salary page access); frontend types `EligibilityRuleResult` already defined in `types/api.ts` |
</phase_requirements>

## Standard Stack

### Core (already in project -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.3.1 | UI framework | Already installed [VERIFIED: package.json] |
| TypeScript | 5.8.3 | Type safety | Already installed [VERIFIED: tsconfig.json] |
| Tailwind CSS | 3.4.17 | Utility classes | Already installed [VERIFIED: tailwind.config.js] |

### No New Dependencies

This phase requires zero new npm packages. All functionality is achievable with existing React state management, existing CSS classes, and existing API endpoints.

## Architecture Patterns

### Component Extraction Strategy

```
frontend/src/
├── components/
│   ├── salary/
│   │   ├── SalarySummaryPanel.tsx    # NEW: summary layer (3 cards + featured ratio + buttons)
│   │   ├── SalaryDetailPanel.tsx     # NEW: detail layer (dimensions, preview, explanation, history)
│   │   ├── SalaryHistoryPanel.tsx    # EXISTING: moved from summary to detail layer
│   │   └── BudgetSimulationPanel.tsx # EXISTING: untouched
│   └── eligibility/
│       └── EligibilityBadge.tsx      # NEW: clickable status pill with inline rule list
├── services/
│   └── eligibilityService.ts         # EXISTING: add fetchEmployeeEligibility() function
└── types/
    └── api.ts                        # EXISTING: EligibilityRuleResult already defined
```

[VERIFIED: codebase grep] All referenced files and types exist.

### Pattern 1: Module IIFE Extraction

**What:** The salary module is currently rendered as an IIFE inside `EvaluationDetail.tsx` (line 1535 `activeModuleContent` switch, salary case starting at line 2061). Extract the ~210 lines of JSX into dedicated components.

**When to use:** When a single module's rendering exceeds 100 lines and has clear summary/detail separation.

**Current structure (line 2061-2268):**
```typescript
// Inside activeModuleContent IIFE
return (
  <>
    {/* AttendanceKpiCard */}
    <section className="surface px-6 py-6 lg:px-7">
      {/* header + status badge */}
      {salaryRecommendation ? (
        <>
          {/* 4-col grid: current salary, recommended, final ratio, status */}
          {/* 3-col grid: recommended ratio, AI multiplier, certification bonus */}
          {/* live preview panel */}
          {/* explanation details */}
          {/* manual adjustment section */}
          {/* approval buttons */}
        </>
      ) : (
        {/* empty state */}
      )}
      {/* SalaryHistoryPanel */}
    </section>
  </>
);
```

**New structure:**
```typescript
return (
  <>
    <SalarySummaryPanel
      salaryRecommendation={salaryRecommendation}
      evaluation={evaluation}
      employee={employee}
      user={user}
      // ... action handlers
    />
    {isDetailExpanded ? (
      <div className="animate-fade-soft">
        <SalaryDetailPanel
          salaryRecommendation={salaryRecommendation}
          evaluation={evaluation}
          liveSalaryPreview={liveSalaryPreview}
          salaryHistory={salaryHistory}
          // ...
        />
      </div>
    ) : null}
  </>
);
```

### Pattern 2: Eligibility Badge with Inline Expand

**What:** A clickable status pill that fetches eligibility data and expands to show 4 rule results inline.

**Key integration point:** The eligibility API `GET /eligibility/{employee_id}` requires `admin`, `hrbp`, or `manager` role [VERIFIED: eligibility.py line 357]. This matches the salary module's access pattern -- employee role users don't see the salary module's full data. The `EligibilityBadge` must handle 403 errors gracefully (show nothing or placeholder for employee role).

**Data flow:**
```typescript
// New service function needed in eligibilityService.ts
export async function fetchEmployeeEligibility(
  employeeId: string
): Promise<EligibilityResultSchema> {
  const response = await api.get<EligibilityResultSchema>(
    `/eligibility/${employeeId}`
  );
  return response.data;
}
```

[VERIFIED: codebase grep] No `fetchEmployeeEligibility` function exists yet -- must be created.

**Frontend type already exists:**
```typescript
// types/api.ts line 877-882
export interface EligibilityRuleResult {
  rule_code: string;
  rule_label: string;
  status: 'eligible' | 'ineligible' | 'data_missing' | 'overridden';
  detail: string;
}
```
[VERIFIED: types/api.ts]

**Response type needed (not yet in types/api.ts):**
```typescript
export interface EligibilityResult {
  overall_status: 'eligible' | 'ineligible' | 'pending';
  rules: EligibilityRuleResult[];
}
```
[VERIFIED: backend schema returns this shape, frontend type not yet defined]

### Pattern 3: Status Color Mapping

**What:** Existing color map pattern from `EligibilityListTab.tsx`.

```typescript
const ELIGIBILITY_STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  eligible: { bg: '#dcfce7', text: '#16a34a' },
  ineligible: { bg: '#fee2e2', text: '#dc2626' },
  pending: { bg: '#fef9c3', text: '#ca8a04' },
};
```
[VERIFIED: UI-SPEC.md confirms these exact values from existing EligibilityListTab.tsx]

### Pattern 4: Dimension Score Table

**What:** 5-row table using existing `table-shell` + `table-lite` CSS classes.

**Data source:** `evaluation.dimension_scores` (already available in EvaluationDetail state) [VERIFIED: line 1978-2012 renders these scores in review module]

**Weight data:** `DIMENSION_WEIGHTS` from `frontend/src/utils/dimensionConstants.ts` [VERIFIED: file exists with exact weight values]

### Anti-Patterns to Avoid
- **Passing 15+ props to extracted components:** Group related props into a single object or pass the full record. The current salary module accesses `salaryRecommendation`, `evaluation`, `employee`, `user`, plus ~8 handler functions and ~5 state variables.
- **Fetching eligibility inside EligibilityBadge on every render:** Use `useEffect` with `employeeId` dependency and guard with role check before fetching.
- **Creating a separate route for eligibility data:** The badge fetches inline; no new page or route needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status badge styling | Custom badge CSS | Existing `.status-pill` class | Project-wide consistency [VERIFIED: index.css line 475] |
| Dimension weight lookup | Inline weight numbers | `DIMENSION_WEIGHTS` from `dimensionConstants.ts` | Single source of truth [VERIFIED: file exists] |
| Dimension label formatting | Inline label mapping | `DIMENSION_LABELS` from `dimensionConstants.ts` or existing `DIMENSION_LABELS` in EvaluationDetail | Already defined [VERIFIED: line 48-59] |
| Fade animation | Custom CSS keyframes | Existing `.animate-fade-soft` class | Already defined (0.18s ease) [VERIFIED: index.css line 596] |
| Table styling | Custom table CSS | Existing `.table-shell` + `.table-lite` classes | Project convention [VERIFIED: index.css lines 521-556] |

## Common Pitfalls

### Pitfall 1: Prop Drilling from EvaluationDetail

**What goes wrong:** Extracting components from a 2400-line file requires passing many state variables and handlers as props, leading to massive prop interfaces.
**Why it happens:** EvaluationDetail manages ALL module state in one component.
**How to avoid:** Group props by concern: (1) data props (recommendation, evaluation, employee), (2) action handlers (generate, save, submit), (3) UI state (editing flags, loading flags). Consider a single `salaryContext` object prop for less-critical props.
**Warning signs:** Component interface exceeds 12 props.

### Pitfall 2: Eligibility API 403 for Employee Role

**What goes wrong:** Employee-role users viewing this page get a 403 when the badge tries to fetch eligibility data.
**Why it happens:** `GET /eligibility/{employee_id}` is restricted to admin/hrbp/manager (Phase 14 D-07) [VERIFIED: eligibility.py line 357].
**How to avoid:** Check `user.role` before making the eligibility API call. Only fetch for admin/hrbp/manager. Show placeholder or hide badge for employee role.
**Warning signs:** Console 403 errors on employee role login.

### Pitfall 3: Summary/Detail State Not Persisting Across Module Switches

**What goes wrong:** User expands details, switches to another module tab, switches back -- expand state is lost.
**Why it happens:** `activeModuleContent` IIFE re-evaluates on each module switch, remounting components.
**How to avoid:** This is acceptable behavior (D-07 says default collapsed). If persistence is desired, lift `isDetailExpanded` state to the parent level. Current decision is to default to collapsed, so this is a non-issue.
**Warning signs:** User feedback about losing expand state.

### Pitfall 4: Missing Weighted Score Calculation

**What goes wrong:** Dimension table needs a "weighted score" column (score * weight) but this is not stored in the database -- only raw scores are stored.
**Why it happens:** The backend stores `raw_score` per dimension; weighted calculation happens in the engine.
**How to avoid:** Calculate `weighted_score = raw_score * DIMENSION_WEIGHTS[dimension_code]` on the frontend using the constants from `dimensionConstants.ts`.
**Warning signs:** Weighted score column showing undefined or NaN.

### Pitfall 5: Empty State When Recommendation Exists but Evaluation Doesn't

**What goes wrong:** Edge case where salary data exists but evaluation dimension scores are empty.
**Why it happens:** Possible during data migration or manual salary creation paths.
**How to avoid:** Guard each section independently -- summary shows recommendation data if available, dimension table shows "no data" message if `dimension_scores` is empty, eligibility badge shows placeholder if API returns error.
**Warning signs:** Blank sections in partially-loaded state.

## Code Examples

### Eligibility Service Function (to add)

```typescript
// Source: Existing pattern in eligibilityService.ts + backend API contract
export interface EligibilityResult {
  overall_status: 'eligible' | 'ineligible' | 'pending';
  rules: EligibilityRuleResult[];
}

export async function fetchEmployeeEligibility(
  employeeId: string,
): Promise<EligibilityResult> {
  const response = await api.get<EligibilityResult>(
    `/eligibility/${employeeId}`,
  );
  return response.data;
}
```
[VERIFIED: matches backend `EligibilityResultSchema` shape and existing service patterns]

### Eligibility Badge Component Pattern

```typescript
// Source: Existing status-pill pattern + EligibilityListTab.tsx color map
interface EligibilityBadgeProps {
  employeeId: string;
  userRole: string;
}

export function EligibilityBadge({ employeeId, userRole }: EligibilityBadgeProps) {
  const [result, setResult] = useState<EligibilityResult | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!employeeId || !['admin', 'hrbp', 'manager'].includes(userRole)) return;
    setIsLoading(true);
    fetchEmployeeEligibility(employeeId)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setIsLoading(false));
  }, [employeeId, userRole]);

  // ... render status-pill + inline expand
}
```
[ASSUMED: Component structure follows project patterns observed in AttendanceKpiCard and EligibilityListTab]

### Dimension Score Table Pattern

```typescript
// Source: dimensionConstants.ts + table-lite CSS class
import { DIMENSION_LABELS, DIMENSION_WEIGHTS, DIMENSION_ORDER } from '../../utils/dimensionConstants';

// Inside SalaryDetailPanel
<div className="table-shell">
  <table className="table-lite">
    <thead>
      <tr>
        <th>维度名</th>
        <th style={{ width: 80, textAlign: 'right' }}>得分</th>
        <th style={{ width: 80, textAlign: 'right' }}>权重</th>
        <th style={{ width: 80, textAlign: 'right' }}>加权分</th>
      </tr>
    </thead>
    <tbody>
      {DIMENSION_ORDER.map((code) => {
        const ds = dimensionScores.find((d) => d.dimension_code === code);
        const weight = DIMENSION_WEIGHTS[code] ?? 0;
        const score = ds?.raw_score ?? 0;
        return (
          <tr key={code}>
            <td>{DIMENSION_LABELS[code] ?? code}</td>
            <td style={{ textAlign: 'right' }}>{score.toFixed(1)}</td>
            <td style={{ textAlign: 'right' }}>{(weight * 100).toFixed(0)}%</td>
            <td style={{ textAlign: 'right' }}>{(score * weight).toFixed(2)}</td>
          </tr>
        );
      })}
    </tbody>
  </table>
</div>
```
[VERIFIED: DIMENSION_ORDER, DIMENSION_LABELS, DIMENSION_WEIGHTS all exist in dimensionConstants.ts]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat full-data display | Summary + expandable details | This phase | Reduces visual cognitive load for HR users |
| No eligibility visibility in salary page | Eligibility badge in summary | This phase (builds on Phase 14) | HR sees eligibility status at a glance |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | EligibilityBadge component structure follows project patterns (useEffect fetch, conditional render) | Code Examples | LOW -- standard React pattern, easy to adjust |
| A2 | `animate-fade-soft` is suitable for detail layer expand animation | Architecture Patterns | LOW -- UI-SPEC already specifies this, fallback is no animation |

## Open Questions

1. **Should eligibility data be fetched once at page load or lazily on badge render?**
   - What we know: AttendanceKpiCard fetches its own data on mount. The eligibility API is fast (no LLM call).
   - What's unclear: Whether to fetch in EvaluationDetail and pass down, or let EligibilityBadge self-fetch.
   - Recommendation: Let EligibilityBadge self-fetch (matches AttendanceKpiCard pattern, keeps component self-contained).

2. **How many props will SalarySummaryPanel need?**
   - What we know: Current salary IIFE accesses ~15 variables from parent scope.
   - What's unclear: Exact prop interface until extraction is attempted.
   - Recommendation: Start extraction, group handlers. If props exceed 12, consider a context object or grouping.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 (backend) / tsc --noEmit (frontend) |
| Config file | `backend/tests/` directory structure, `frontend/tsconfig.json` |
| Quick run command | `cd frontend && npx tsc --noEmit` |
| Full suite command | `cd frontend && npx tsc --noEmit && cd .. && python -m pytest backend/tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISP-01 | Summary layer renders 3 cards + featured ratio | manual (visual) | `cd frontend && npx tsc --noEmit` (type check only) | N/A |
| DISP-02 | Detail layer toggles on button click | manual (visual) | `cd frontend && npx tsc --noEmit` | N/A |
| DISP-03 | Eligibility badge renders and expands rules | manual (visual) + type check | `cd frontend && npx tsc --noEmit` | N/A |

### Sampling Rate
- **Per task commit:** `cd frontend && npx tsc --noEmit`
- **Per wave merge:** Full backend + frontend type check
- **Phase gate:** Visual verification of all 3 requirements + type check green

### Wave 0 Gaps
- No frontend unit test framework (no jest/vitest configured) -- visual testing is manual
- Type checking via `tsc --noEmit` is the primary automated validation for frontend changes

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (no auth changes) |
| V3 Session Management | no | N/A |
| V4 Access Control | yes | Eligibility API already enforces role restriction (admin/hrbp/manager); frontend must also guard fetch call by role |
| V5 Input Validation | no | No user input changes |
| V6 Cryptography | no | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Employee accessing eligibility data | Information Disclosure | Backend `require_roles('admin', 'hrbp', 'manager')` + frontend role check before API call [VERIFIED: eligibility.py line 357] |

## Sources

### Primary (HIGH confidence)
- Codebase files: `EvaluationDetail.tsx` (salary module lines 2060-2268), `eligibility.py` (API endpoints), `eligibilityService.ts`, `types/api.ts`, `dimensionConstants.ts`, `index.css` (CSS classes)
- `17-CONTEXT.md` -- all locked decisions
- `17-UI-SPEC.md` -- visual and interaction contract

### Secondary (MEDIUM confidence)
- `REQUIREMENTS.md` -- DISP-01, DISP-02, DISP-03 definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing
- Architecture: HIGH -- straightforward component extraction with verified existing patterns
- Pitfalls: HIGH -- based on direct codebase analysis of role restrictions and data shapes

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable -- no external dependency changes expected)
