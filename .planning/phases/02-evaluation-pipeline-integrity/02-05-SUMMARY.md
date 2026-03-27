---
plan: 02-05
status: complete
started: 2026-03-27T22:45:00+08:00
completed: 2026-03-27T22:55:00+08:00
---

## Summary

Frontend fallback banner and dimension summary panel added to EvaluationDetail page.

## Tasks

| # | Task | Status |
|---|------|--------|
| 1 | TypeScript type updates (api.ts) | ✓ |
| 2 | Fallback banner + dimension panel (EvaluationDetail.tsx) | ✓ |
| 3 | Human verification (checkpoint) | ✓ Approved |

## Key Files

### Created
(none)

### Modified
- `frontend/src/types/api.ts` — added `used_fallback?: boolean` to EvaluationRecord, `prompt_hash?: string | null` to DimensionScoreRecord
- `frontend/src/pages/EvaluationDetail.tsx` — DIMENSION_LABELS constant, yellow fallback banner, read-only dimension summary panel with scores/weights/rationale/prompt_hash
- `frontend/src/components/evaluation/EvidenceWorkspaceOverview.tsx` — unified stats row layout (evidence count / score / risk in single row)
- `backend/app/core/config.py` — added port 5175 to CORS origins

## Deviations
- Stats row in EvidenceWorkspaceOverview changed from 3 separate cards to unified horizontal layout per user feedback during checkpoint

## Self-Check: PASSED
- [x] `used_fallback` type in api.ts
- [x] Fallback banner conditional render
- [x] Dimension panel with Chinese labels
- [x] tsc --noEmit passes
- [x] Human visual verification approved
