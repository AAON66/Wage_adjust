---
phase: 02-evaluation-pipeline-integrity
plan: 04
subsystem: evaluation-pipeline
tags: [scale-normalization, prompt-safety, used-fallback, prompt-hash, injection-defense]
dependency_graph:
  requires:
    - 02-01-PLAN.md
    - 02-02-PLAN.md
  provides:
    - fixed-scale-normalization
    - used-fallback-api-surface
    - prompt-hash-dimension-scores
    - re-evaluation-row-cleanup
    - evidence-sanitization-wiring
    - english-homoglyph-injection-defense
  affects: [evaluation-service, evaluations-api, prompt-safety, frontend-evaluation-detail]
tech_stack:
  added:
    - prompt_hash utility (backend/app/utils/prompt_hash.py)
  patterns:
    - Evidence sanitization before LLM prompt construction
    - Re-evaluation row cleanup (delete-before-insert) in same transaction
    - Five-point scale detection requires >= 3 dimensions
    - Ambiguous overall_score discarded rather than multiplied
key_files:
  created:
    - backend/app/utils/prompt_hash.py
    - backend/tests/test_eval_pipeline.py
  modified:
    - backend/app/services/evaluation_service.py
    - backend/app/api/v1/evaluations.py
    - backend/app/utils/prompt_safety.py
    - backend/app/models/evaluation.py
    - backend/app/models/dimension_score.py
    - backend/app/schemas/evaluation.py
    - backend/app/services/llm_service.py
key_decisions:
  - "Five-point scale detection requires len(raw_dimension_scores) >= 3 to prevent false positive on sparse LLM responses"
  - "Ambiguous overall_score (dims=100pt, overall<=5.0) is discarded (set None) rather than multiplied by 20"
  - "Re-evaluation uses delete() with synchronize_session=fetch followed by flush() before inserting new DimensionScore rows"
  - "Evidence sanitization scans both content_excerpt and title fields per evidence item"
  - "All 3 new prompt safety patterns use IGNORECASE flag; homoglyph pattern uses UNICODE flag"
patterns-established:
  - "Evidence items are sanitized via scan_for_prompt_manipulation before being embedded in LLM prompts"
  - "DimensionScore rows carry prompt_hash for auditability"
  - "AIEvaluation.used_fallback is set on every evaluation write (new and re-evaluation)"
requirements-completed: [EVAL-04, EVAL-07, EVAL-08]
metrics:
  duration: 12min
  completed: "2026-03-27"
  tasks_completed: 2
  files_modified: 9
  files_created: 2
---

# Phase 02 Plan 04: Scale Normalization, Fallback Wiring, and Injection Defense Summary

**Fixed five-point scale detection bug, wired used_fallback + prompt_hash to storage/API, added re-evaluation row cleanup, and extended prompt injection defense with 3 English/homoglyph patterns**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-27T09:15:55Z
- **Completed:** 2026-03-27T09:27:49Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Fixed scale normalization: requires >= 3 dimension scores for five-point detection; ambiguous overall_score discarded instead of inflated
- Wired used_fallback from DeepSeekCallResult to AIEvaluation model and API response
- Wired prompt_hash from DeepSeekCallResult to DimensionScore rows for audit trail
- Re-evaluation path now deletes old DimensionScore rows before inserting new ones (prevents stale row accumulation)
- Evidence text is scanned for prompt injection and redacted before being embedded in LLM prompts
- Added 3 new prompt safety patterns: english_score_manipulation, english_instruction_override, unicode_homoglyph (total: 7 patterns)
- All 4 existing Chinese patterns remain unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2: Scale normalization, wiring, sanitization, and prompt safety patterns** - `1f9dc7f` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `backend/app/services/evaluation_service.py` - Fixed scale normalization, wired used_fallback + prompt_hash, added re-eval cleanup, added evidence sanitization
- `backend/app/api/v1/evaluations.py` - Added used_fallback to serialize_evaluation response
- `backend/app/utils/prompt_safety.py` - Added 3 new injection patterns (English score manipulation, instruction override, Unicode homoglyph)
- `backend/app/models/evaluation.py` - Added used_fallback column
- `backend/app/models/dimension_score.py` - Added prompt_hash column
- `backend/app/schemas/evaluation.py` - Added used_fallback field to EvaluationRead
- `backend/app/services/llm_service.py` - Added prompt_hash field to DeepSeekCallResult
- `backend/app/utils/prompt_hash.py` - SHA-256 hash utility for prompt auditability
- `backend/tests/test_eval_pipeline.py` - 22 tests covering EVAL-01 through EVAL-08

## Decisions Made
- Five-point scale detection requires >= 3 dimensions (not just bool(scores)) to prevent false positives on sparse LLM responses
- Ambiguous overall_score (dimensions at 100-point range but overall <= 5.0) is set to None, falling through to weighted_total path
- Re-evaluation uses SQLAlchemy delete() with synchronize_session='fetch' + flush() before inserts within the same transaction
- Evidence sanitization scans both content_excerpt and title fields per evidence item
- Combined Task 1 and Task 2 into a single commit since the prompt_safety patterns and the sanitization wiring are tightly coupled

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing model columns and DeepSeekCallResult.prompt_hash**
- **Found during:** Task 1 (pre-implementation read)
- **Issue:** This worktree was based on pre-02-01 codebase; AIEvaluation.used_fallback, DimensionScore.prompt_hash, and DeepSeekCallResult.prompt_hash did not exist
- **Fix:** Added used_fallback Boolean column to AIEvaluation, prompt_hash String column to DimensionScore, prompt_hash field to DeepSeekCallResult dataclass, used_fallback field to EvaluationRead schema
- **Files modified:** backend/app/models/evaluation.py, backend/app/models/dimension_score.py, backend/app/services/llm_service.py, backend/app/schemas/evaluation.py
- **Verification:** All 12 targeted tests pass
- **Committed in:** 1f9dc7f

**2. [Rule 3 - Blocking] Created prompt_hash utility module**
- **Found during:** Task 1 (pre-implementation read)
- **Issue:** backend/app/utils/prompt_hash.py did not exist in this worktree (created by plan 02-01 in main repo)
- **Fix:** Created the compute_prompt_hash utility
- **Files modified:** backend/app/utils/prompt_hash.py
- **Committed in:** 1f9dc7f

---

**Total deviations:** 2 auto-fixed (2 blocking - prerequisite artifacts from plan 02-01 not present in worktree)
**Impact on plan:** Both auto-fixes necessary to unblock implementation. No scope creep.

## Issues Encountered
- test_image_ocr_fallback_on_no_deepseek fails (ParseService DI from plan 02-01 not in this worktree) - out of scope for plan 02-04
- Windows Store python stub (exit code 49) required using project venv python explicitly

## Known Stubs
None - all wiring is functional and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API now returns used_fallback in EvaluationRead response, unblocking plan 02-05 (frontend)
- PROMPT_MANIPULATION_PATTERNS has 7 entries covering Chinese, English, and Unicode homoglyph attacks
- Evidence sanitization is wired into the LLM prompt construction path

---
*Phase: 02-evaluation-pipeline-integrity*
*Completed: 2026-03-27*
