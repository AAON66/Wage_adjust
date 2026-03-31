# Feature Landscape: v1.1 体验优化与业务规则完善

**Domain:** Enterprise HR salary adjustment platform -- incremental feature additions
**Researched:** 2026-03-30

## Table Stakes

Features required for v1.1 milestone completion. All directly specified in PROJECT.md.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Manual account-employee binding UI | Users/admins need to bind accounts without relying on id_card_no auto-match | Low | Backend service exists, needs UI and 3 API endpoints |
| File duplicate warning (not rejection) | Current hard-reject breaks UX when co-authors upload same file | Medium | Modifies `FileService._check_duplicate()` behavior |
| File share request workflow | Co-authors need a way to legitimately use shared files | Medium-High | New model, service, API, and frontend components |
| Grouped navigation sidebar | 13 flat links for admin is unmanageable | Low | Pure frontend, modify roleAccess.ts + AppShell.tsx |
| Salary eligibility pre-check | HR needs to verify eligibility before salary computation | Medium | New engine + service + API, missing data handling |
| Collapsible salary details | Current flat display overwhelms; key info should be default, details on demand | Low | Pure frontend, expand SalaryResultCard props |

## Differentiators

Features that add value beyond basic requirements.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Self-service binding for employees | Employees can bind their own account via id_card_no match without admin intervention | Low | Extension of Feature 1, uses existing `auto_bind_user_and_employee()` |
| Batch eligibility check | HR can view eligibility status for entire department at once | Low | Uses same engine, adds batch endpoint |
| Missing data import path from eligibility UI | When eligibility check shows "data unavailable", link directly to import center | Low | UX convenience, just a navigation link |
| Contribution percentage negotiation | Share request includes proposed contribution %, owner can counter-propose | Medium | Adds negotiation step to share workflow |

## Anti-Features

Features to explicitly NOT build in v1.1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time notifications (WebSocket) | No existing WebSocket infrastructure; overkill for share request notifications | Polling-based check on page load |
| SSO/LDAP binding integration | Enterprise identity systems vary wildly; manual binding covers 90% of cases | Manual bind + id_card_no auto-match |
| Configurable eligibility rules UI | 4 rules are sufficient; making them configurable adds complexity without immediate value | Hardcode 4 rules in engine, externalize thresholds only |
| Performance rating model | No existing data source; building a full performance system is out of scope | Mark performance rule as "data unavailable" until import exists |
| Drag-and-drop nav reordering | Over-engineering for admin-configured navigation | Hardcode group ordering in roleAccess.ts |

## Feature Dependencies

```
Feature 3 (Navigation) -> Feature 1 (Binding UI needs nav slot)
Feature 3 (Navigation) -> Feature 4 (Eligibility page needs nav slot)
Feature 4 (Eligibility Engine) -> Feature 5 (EligibilityBadge used in salary display)
Feature 2 (File Sharing) is independent but benefits from Feature 3 being done first
```

## MVP Recommendation

Prioritize:
1. Feature 3 (Navigation grouping) -- foundation for all other UI work
2. Feature 1 (Account binding) -- quick win, high user demand
3. Feature 4 (Eligibility engine) -- core business logic, independent of other features

Defer if time-pressured:
- Feature 2 (File sharing): Most complex, can ship as v1.2 if needed
- Feature 5 (Display simplification): Polish, not blocking any workflow

## Sources

- Direct codebase analysis of existing models, services, and frontend components
- PROJECT.md milestone requirements
