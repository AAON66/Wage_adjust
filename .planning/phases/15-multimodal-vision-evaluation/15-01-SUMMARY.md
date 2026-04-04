---
phase: 15-multimodal-vision-evaluation
plan: 01
subsystem: parsers, llm, engines
tags: [vision, deepseek, pptx, pillow, image-extraction, compression]

requires:
  - phase: 02-ai-evaluation
    provides: DeepSeek LLM service, evaluation engine, image OCR
provides:
  - PPTParser.extract_images() with SHA1 dedup and slide tracking
  - compress_image_if_needed() for >5MB images
  - DeepSeekService.evaluate_image_vision() with structured vision prompt
  - Settings.deepseek_vision_model configuration
  - SOURCE_RELIABILITY vision_evaluation and vision_failed entries
affects: [15-02-PLAN, evaluation-service, parse-service]

tech-stack:
  added: [MSO_SHAPE_TYPE from pptx.enum.shapes]
  patterns: [local import for lazy dependency loading in LLM service, vision prompt with image_url content type]

key-files:
  created:
    - backend/tests/test_parsers/test_ppt_image_extraction.py
    - backend/tests/test_services/test_llm_vision.py
  modified:
    - backend/app/parsers/ppt_parser.py
    - backend/app/parsers/image_parser.py
    - backend/app/services/llm_service.py
    - backend/app/core/config.py
    - backend/app/engines/evaluation_engine.py

key-decisions:
  - "Vision evaluation reuses parsing timeout (120s) since both are long-running LLM calls"
  - "compress_image_if_needed lives in image_parser.py (collocated with image concerns) and is imported locally in llm_service"
  - "ExtractedImage dataclass uses python-pptx native sha1 for dedup rather than recomputing"

patterns-established:
  - "Vision prompt pattern: system message with dimension codes + injection resistance, user message with image_url content list"
  - "Image size guard: compress >5MB before vision API call using Pillow thumbnail + quality=85"

requirements-completed: [VISION-01, VISION-02, VISION-03]

duration: 4min
completed: 2026-04-04
---

# Phase 15 Plan 01: Vision Evaluation Infrastructure Summary

**PPT image extraction with SHA1 dedup, vision evaluation LLM prompt with 5-dimension relevance scoring, and >5MB image compression**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-04T10:40:22Z
- **Completed:** 2026-04-04T10:44:22Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- PPTParser.extract_images() extracts deduplicated images from .pptx with slide tracking, tiny image filtering, and error resilience
- DeepSeekService.evaluate_image_vision() sends structured vision prompt returning description, quality_score, and dimension_relevance
- compress_image_if_needed() handles >5MB images by thumbnailing to 2048px and saving at quality=85
- SOURCE_RELIABILITY updated with vision_evaluation (0.90) and vision_failed (0.0) entries
- Settings.deepseek_vision_model configurable, defaults to deepseek-chat

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: PPT image extraction + ImageParser + config + tests**
   - `706d5d4` (test) - Failing tests for PPT image extraction, compression, config
   - `4044db1` (feat) - PPT image extraction, image compression, vision config, SOURCE_RELIABILITY
2. **Task 2: Vision evaluation LLM prompt and DeepSeekService method + tests**
   - `fc04c8d` (test) - Failing tests for vision evaluation LLM prompt
   - `394b9d4` (feat) - Vision evaluation LLM prompt and DeepSeekService method

## Files Created/Modified
- `backend/app/parsers/ppt_parser.py` - ExtractedImage dataclass, extract_images() with SHA1 dedup
- `backend/app/parsers/image_parser.py` - compress_image_if_needed(), image_path in metadata
- `backend/app/services/llm_service.py` - build_vision_evaluation_messages(), evaluate_image_vision()
- `backend/app/core/config.py` - deepseek_vision_model setting
- `backend/app/engines/evaluation_engine.py` - vision_evaluation and vision_failed in SOURCE_RELIABILITY
- `backend/tests/test_parsers/test_ppt_image_extraction.py` - 11 unit tests for parsers/config
- `backend/tests/test_services/test_llm_vision.py` - 12 unit tests for vision LLM service

## Decisions Made
- Vision evaluation reuses parsing timeout (120s) since both are long-running LLM calls
- compress_image_if_needed lives in image_parser.py and is imported locally in llm_service to avoid circular imports
- ExtractedImage uses python-pptx native sha1 property for dedup

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test mock patching for compress_image_if_needed**
- **Found during:** Task 2 (test execution)
- **Issue:** Test tried to patch at llm_service module level but function is imported locally inside evaluate_image_vision
- **Fix:** Patched at source module (backend.app.parsers.image_parser.compress_image_if_needed)
- **Files modified:** backend/tests/test_services/test_llm_vision.py
- **Committed in:** 394b9d4

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test fix, no scope creep.

## Issues Encountered
None beyond the test patching fix documented above.

## Known Stubs
None - all functionality is fully wired and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 can now wire extract_images() and evaluate_image_vision() into the parse flow
- All building blocks are tested and ready for integration
- ImageParser provides image_path in metadata for downstream vision evaluation

---
*Phase: 15-multimodal-vision-evaluation*
*Completed: 2026-04-04*
