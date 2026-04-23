---
phase: 35-employee-self-service-experience
plan: "03"
subsystem: frontend/performance-service
tags: [frontend, types, api-contract, eself-03]
dependency_graph:
  requires:
    - 35-02 (/performance/me/tier API contract)
  provides:
    - MyTierResponse TypeScript interface
    - fetchMyTier frontend service
  affects:
    - 35-04 (UI component consumes the new type and service)
key_files:
  created: []
  modified:
    - frontend/src/types/api.ts
    - frontend/src/services/performanceService.ts
requirements:
  - ESELF-03
---

# Phase 35 Plan 03 Summary

Added the frontend contract for employee self-service performance tiers. `frontend/src/types/api.ts` now exports `MyTierResponse` with the same four fields and literal unions as the backend schema, and `frontend/src/services/performanceService.ts` now exports `fetchMyTier()` which performs a parameterless `GET /performance/me/tier` and rethrows axios errors unchanged for UI-level branching.

Verification:
- `cd frontend && npx tsc --noEmit`
