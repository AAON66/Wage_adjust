---
phase: 02-evaluation-pipeline-integrity
plan: 03
subsystem: parsers, llm
tags: [deepseek, vision-api, ocr, image-parsing, pillow]

requires:
  - phase: 02-evaluation-pipeline-integrity plan 01
    provides: "test infrastructure, ParsedDocument contract"
  - phase: 02-evaluation-pipeline-integrity plan 02
    provides: "LLM retry/rate-limiter hardening in llm_service.py"
provides:
  - "DeepSeekService.extract_image_text() for image text extraction via vision API"
  - "DeepSeekPromptLibrary.build_image_ocr_messages() multimodal prompt"
  - "ParseService._enrich_image_document() optional OCR enrichment for image files"
  - "ImageParser stub string removed, returns text=''"
affects: [02-evaluation-pipeline-integrity, parse-service-callers]

tech-stack:
  added: []
  patterns:
    - "Optional DI for LLM services in ParseService (deepseek_service parameter)"
    - "Image resize guard: >1MB source -> Pillow thumbnail 1024x1024 before base64"
    - "_resolve_model_name dispatch for vision tasks always returns deepseek-chat"

key-files:
  created:
    - backend/tests/test_eval_pipeline.py
  modified:
    - backend/app/parsers/image_parser.py
    - backend/app/services/llm_service.py
    - backend/app/services/parse_service.py

key-decisions:
  - "ParseService.deepseek_service is optional DI parameter (not required), preserving backward compatibility with existing call sites"
  - "Image OCR uses deepseek-chat model always (not configurable) since vision requires multimodal support"
  - "Fallback returns ocr_skipped=True with reason codes for observability"

patterns-established:
  - "Optional service injection: ParseService accepts DeepSeekService|None, callers opt-in"
  - "IMAGE_EXTENSIONS frozenset for file type dispatch at ParseService level"

requirements-completed: [EVAL-03]

duration: 8min
completed: 2026-03-27
---

# Phase 02 Plan 03: Image OCR via DeepSeek Vision API Summary

**Replaced ImageParser OCR stub with real DeepSeek vision API text extraction, routed through ParseService with optional DI and graceful fallback**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T09:15:37Z
- **Completed:** 2026-03-27T09:24:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Removed "OCR is reserved for a later task" stub string from ImageParser -- parse() now returns text=''
- Added DeepSeekService.extract_image_text() with Pillow-based resize guard for images >1MB
- Added DeepSeekPromptLibrary.build_image_ocr_messages() with multimodal message format and injection-resistance prompt
- Wired ParseService._enrich_image_document() with optional DeepSeek DI, calling extract_image_text for PNG/JPG/JPEG files
- All 10 tests pass (TDD: RED then GREEN)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `e4ac335` (test)
2. **Task 1 GREEN: ImageParser stub + extract_image_text** - `712cc40` (feat)
3. **Task 2 GREEN: ParseService image OCR wiring** - `083ebd5` (feat)

_TDD approach: tests written first, then implementation to pass them._

## Files Created/Modified
- `backend/tests/test_eval_pipeline.py` - 10 tests covering stub removal, vision API call, prompt format, model resolution, fallback scenarios, backward compat
- `backend/app/parsers/image_parser.py` - Removed OCR stub string, returns text=''
- `backend/app/services/llm_service.py` - Added build_image_ocr_messages(), extract_image_text(), image_ocr model resolution
- `backend/app/services/parse_service.py` - Added optional deepseek_service DI, _enrich_image_document(), IMAGE_EXTENSIONS constant

## Decisions Made
- ParseService.deepseek_service is optional DI parameter (not required), preserving backward compatibility with existing call sites
- Image OCR always uses 'deepseek-chat' model since vision requires multimodal support
- Fallback returns structured ocr_skipped=True with reason codes (deepseek_not_configured, no_text_detected, ocr_failed, file_not_found) for observability

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All planned functionality is implemented. Note: production call sites in `backend/app/api/v1/files.py` still instantiate `ParseService(db, settings)` without `deepseek_service`, so image OCR is effectively disabled in production until those call sites are updated. This is an acknowledged follow-up documented in 02-01-SUMMARY.md.

## Issues Encountered
- pytest tmp_path fixture hit Windows PermissionError on default basetemp path; resolved by using --basetemp flag pointing to project directory

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Image OCR infrastructure is complete and tested
- Production wiring of deepseek_service into ParseService call sites is a follow-up item
- Ready for subsequent plans in phase 02

---
*Phase: 02-evaluation-pipeline-integrity*
*Completed: 2026-03-27*
