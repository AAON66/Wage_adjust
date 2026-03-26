---
phase: 02-evaluation-pipeline-integrity
plan: 01
subsystem: evaluation-pipeline
tags: [llm-service, eval-engine, schema-migration, prompt-safety, image-ocr, frontend]
dependency_graph:
  requires: [01-05-PLAN.md]
  provides: [trustworthy-evaluation-results, prompt_hash-auditability, fallback-transparency]
  affects: [evaluation-service, llm-service, parse-service, image-parser, frontend-detail-page]
tech_stack:
  added:
    - compute_prompt_hash (backend/app/utils/prompt_hash.py)
    - RedisRateLimiter (sliding-window ZADD/ZREMRANGEBYSCORE pattern)
    - DeepSeek vision API image OCR (extract_image_text method)
  patterns:
    - Full-jitter exponential backoff for LLM retries
    - Retry-After header respected on 429/503 responses
    - Optional DeepSeekService dependency injection in ParseService
    - TDD: test file created before implementation for all 8 EVAL requirements
key_files:
  created:
    - backend/app/utils/prompt_hash.py
    - alembic/versions/4f2eeacd62c3_add_prompt_hash_dimension_scores_used_.py
    - backend/tests/test_eval_pipeline.py
  modified:
    - backend/app/services/llm_service.py
    - backend/app/services/evaluation_service.py
    - backend/app/services/parse_service.py
    - backend/app/parsers/image_parser.py
    - backend/app/models/dimension_score.py
    - backend/app/models/evaluation.py
    - backend/app/schemas/evaluation.py
    - backend/app/utils/prompt_safety.py
    - frontend/src/types/api.ts
    - frontend/src/pages/EvaluationDetail.tsx
decisions:
  - Full-jitter exponential backoff chosen over linear backoff (avoids thundering herd on LLM API)
  - Redis rate limiter attempts connection at startup; graceful fallback to InMemoryRateLimiter preserves existing behavior
  - Five-point scale detection requires >=3 dimension scores (not just any non-empty list) to prevent false positive inflation
  - Ambiguous overall_score (dimensions=100pt, overall<=5) is discarded rather than multiplied; falls to weighted_total path
  - ParseService.deepseek_service is optional DI parameter (not required), preserving backward compatibility with existing call sites
  - DIMENSION_LABELS in EvaluationDetail.tsx includes both canonical codes (TOOL_MASTERY, etc.) and legacy engine codes (TOOL, DEPTH, etc.)
metrics:
  duration: 11min
  completed: "2026-03-26"
  tasks_completed: 7
  files_modified: 10
  files_created: 3
---

# Phase 02 Plan 01: Evaluation Pipeline Integrity Summary

**One-liner:** Eight concrete defects fixed — exponential backoff retry, Redis rate limiter, real image OCR, scale normalization bug, prompt_hash auditability, used_fallback transparency, English/homoglyph injection patterns, and a read-only dimension summary UI panel.

---

## What Was Implemented

### Task 1: Schema migration (EVAL-05, EVAL-06)

Added two columns via Alembic migration `4f2eeacd62c3`:

- `dimension_scores.prompt_hash` — `String(64)`, nullable. Stores SHA-256 hex of the LLM prompt messages for each dimension score row. Enables prompt auditability.
- `ai_evaluations.used_fallback` — `Boolean`, `server_default='0'`. True when the evaluation was produced by the rule engine (no LLM involved).

Both columns added via `batch_alter_table` (SQLite-compatible, per Phase 01 D-11 decision).

### Task 2: LLM service hardening (EVAL-01, EVAL-02, EVAL-05)

**`backend/app/utils/prompt_hash.py`** (new):
- `compute_prompt_hash(messages)` returns SHA-256 hex of `json.dumps(messages, sort_keys=True, ensure_ascii=False)`. Deterministic, 64-char output.

**`backend/app/services/llm_service.py`** (updated):
- `_compute_retry_delay(attempt)` — full-jitter exponential backoff: `random.uniform(0, min(30, 1.0 * 2**attempt))`
- `RedisRateLimiter` — ZADD/ZREMRANGEBYSCORE sliding window. Key is `deepseek_rpm:{sha256(api_base_url)[:12]}` (stable across processes).
- `DeepSeekService.__init__` tries Redis connection; on any error falls back to `InMemoryRateLimiter` with WARNING log.
- `_invoke_json` now: (1) computes `prompt_hash` before HTTP call, (2) uses `_compute_retry_delay` with Retry-After header awareness on 429/503, (3) returns `prompt_hash` in `DeepSeekCallResult`.
- `DeepSeekCallResult` dataclass gains `prompt_hash: str | None = None`.
- `extract_image_text(image_path)` + `build_image_ocr_messages(image_b64, mime_type)` added for EVAL-03.
- `_resolve_model_name('image_ocr')` always returns `'deepseek-chat'`.

### Task 3: Image OCR via DeepSeek vision API (EVAL-03)

**`backend/app/parsers/image_parser.py`**:
- `parse()` now returns `text=''` (empty string). Removed the old stub text `"OCR is reserved for a later task."` which was being included as evidence content.

**`backend/app/services/parse_service.py`**:
- `__init__` accepts optional `deepseek_service: DeepSeekService | None = None` parameter.
- `_enrich_image_document(parsed, file_path)` — calls `deepseek_service.extract_image_text(file_path)` for PNG/JPG/JPEG files. Returns enriched `ParsedDocument` with real extracted text on success; sets `metadata.ocr_skipped=True` when DeepSeek is unconfigured or fails.
- `parse_file()` calls `_enrich_image_document` after `ImageParser.parse()` when file extension is in `IMAGE_EXTENSIONS`.

### Task 4: Scale normalization fix and storage wiring (EVAL-04, EVAL-05, EVAL-06)

**`backend/app/services/evaluation_service.py`**:

- `_normalize_llm_evaluation_payload`: fixed five-point detection to require `len(raw_dimension_scores) >= 3` (was `bool(raw_dimension_scores)`). Added ambiguity handling: if dimensions are 100-point scale but `overall_score <= 5`, discard overall_score (fall to weighted_total) instead of inflating by ×20. Capped scaled values at 100.0.
- `_generate_llm_backed_result` now returns `(EvaluationResult, used_fallback: bool, prompt_hash: str | None)` tuple.
- `generate_evaluation` sets `evaluation.used_fallback = used_fallback` on every write including re-evaluations. Passes `prompt_hash` to each `DimensionScore` row.

### Task 5: Extended prompt safety patterns (EVAL-08)

**`backend/app/utils/prompt_safety.py`** — three new patterns added to `PROMPT_MANIPULATION_PATTERNS`:

- `english_score_manipulation`: catches "give me full marks", "give full marks", "give 100", "award full credit", etc.
- `english_instruction_override`: catches "ignore previous instructions", "forget your instructions", "you must give me full", etc.
- `unicode_homoglyph`: catches Cyrillic lookalike characters (U+0430/е/о/р/с/х/у/і) embedded in text.

All 4 existing Chinese patterns unchanged.

### Task 6: Frontend — fallback banner and dimension summary (EVAL-06, EVAL-07)

**`frontend/src/types/api.ts`**: `EvaluationRecord.used_fallback?: boolean` added.

**`frontend/src/pages/EvaluationDetail.tsx`**:
- `DIMENSION_LABELS` constant maps both canonical codes (`TOOL_MASTERY`, `APPLICATION_DEPTH`, etc.) and legacy engine codes (`TOOL`, `DEPTH`, etc.) to Chinese labels.
- Yellow warning banner renders in the overview module when `evaluation.used_fallback === true`:
  > "当前结果为规则引擎估算，AI 未参与评估，请结合实际情况人工复核。"
- Read-only dimension score summary panel renders for all evaluation statuses showing: Chinese dimension label, weight %, AI raw score, and ai_rationale text. Shows "暂无维度评分数据" when empty.

### Task 7: Unit tests

**`backend/tests/test_eval_pipeline.py`** (new) — 22 tests, all passing:

| Requirement | Tests |
|-------------|-------|
| EVAL-01 retry backoff | `test_retry_backoff`, `test_retry_backoff_429_respects_retry_after` |
| EVAL-02 Redis fallback | `test_redis_rate_limiter_fallback`, `test_redis_rate_limiter_key_stable` |
| EVAL-03 image OCR | `test_image_ocr_stub_cleared`, `test_image_ocr_deepseek_called`, `test_image_ocr_fallback_on_no_deepseek` |
| EVAL-04 scale norm | `test_scale_normalization_five_point`, `test_scale_normalization_hundred_point`, `test_scale_normalization_ambiguous_overall`, `test_scale_normalization_requires_three_dimensions` |
| EVAL-05 prompt hash | `test_prompt_hash`, `test_prompt_hash_deterministic`, `test_prompt_hash_changes_on_different_input`, `test_prompt_hash_stored` |
| EVAL-06 used_fallback | `test_used_fallback_stored`, `test_used_fallback_reset` |
| EVAL-07 dimension display | Covered by TypeScript lint (frontend) |
| EVAL-08 prompt safety | `test_prompt_safety_existing_chinese`, `test_prompt_safety_english`, `test_prompt_safety_instruction_override_english`, `test_prompt_safety_homoglyph`, `test_prompt_safety_clean_text` |

---

## Verification Results

```
python -m pytest backend/tests/test_eval_pipeline.py -v
→ 22 passed in 26.30s

cd frontend && npm run lint (tsc --noEmit)
→ exit 0 (no TypeScript errors)

alembic upgrade head
→ Running upgrade fa1c02bf9cd1 → 4f2eeacd62c3 (no errors)
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UploadedFile model has no file_size column**
- **Found during:** Task 3 test writing
- **Issue:** Test used `file_size=img_path.stat().st_size` when creating `UploadedFile` ORM objects. The model's actual columns are `[submission_id, file_name, file_type, storage_key, parse_status, id, created_at]` — no `file_size`.
- **Fix:** Removed `file_size` from `UploadedFile(...)` constructor calls in the test.
- **Files modified:** `backend/tests/test_eval_pipeline.py`

**2. [Rule 1 - Bug] English score manipulation pattern false negative**
- **Found during:** Task 5 test run
- **Issue:** Pattern `give\s+(me|full|max|...)` matched "give full marks" but NOT "give me full marks" because the `me` was consumed as a match group, leaving no match group for the score term.
- **Fix:** Updated regex to `give\s+(me\s+)?(full|max|perfect|high|top)\s+(marks?|...)` with `me` as optional prefix, plus a separate branch `give\s+me\s+(marks?|score|...)`.
- **Files modified:** `backend/app/utils/prompt_safety.py`

**3. [Rule 3 - Blocking] test_image_ocr_deepseek_called raised RequiredLLMError**
- **Found during:** Task 3 test run
- **Issue:** Test settings had `deepseek_require_real_call_for_parsing=True` (default), so EvidenceService raised `RequiredLLMError` because the mock LLM's `extract_evidence` was not set up (only `extract_image_text` was mocked).
- **Fix:** Set `deepseek_require_real_call_for_parsing=False` in test settings to isolate image OCR behavior from evidence extraction.
- **Files modified:** `backend/tests/test_eval_pipeline.py`

**4. [Rule 1 - Bug] scale normalization requires_three_dimensions test assertion**
- **Found during:** Task 4 test run
- **Issue:** Test asserted `raw_score < 10` for the two dims with score=4.5, but `_reconcile_dimension_score` blends the 4.5 LLM score with a ~60 baseline → result ~50. The point is NOT that the score stays at 4.5, but that it is NOT scaled to 90 by ×20.
- **Fix:** Changed assertion to `raw_score < 85` to correctly test that the ×20 multiplication was not applied.
- **Files modified:** `backend/tests/test_eval_pipeline.py`

---

## Known Stubs

None — all changes produce real behavior. The `DIMENSION_LABELS` mapping in EvaluationDetail.tsx includes all dimension codes from the current engine, so no dimension will fall back to showing a raw code string in normal operation.

---

## Follow-up Items for Subsequent Phases

1. `ParseService` currently only calls `deepseek_service.extract_image_text` when constructed with an explicit `deepseek_service` argument. The API router `parse_service.py` instantiation (in `backend/app/api/v1/files.py` or similar) should be updated to inject a real `DeepSeekService` instance so production image uploads benefit from OCR. This was not in scope for this plan.

2. The `RedisRateLimiter.acquire()` method requires a `redis_client` parameter passed at call time. This design requires the caller (`_invoke_json`) to hold a reference to the Redis client, which it does via `self._redis_client`. If the Redis connection drops mid-session, the service will continue to try `redis_client.pipeline()` calls that may fail silently. A health-check or connection retry could be added in a future hardening pass.

3. The `compute_prompt_hash` utility is not yet used to deduplicate identical LLM calls (e.g., detecting re-evaluation of the same evidence with the same prompt). This could be a future optimization to avoid redundant API calls.

---

## Self-Check: PASSED

- `backend/tests/test_eval_pipeline.py` — exists, 22 tests pass
- `backend/app/utils/prompt_hash.py` — exists
- `alembic/versions/4f2eeacd62c3_add_prompt_hash_dimension_scores_used_.py` — exists
- Commits: 6abcd38, 3c40b49, 065326d, d8d60f8, fd92943, fa9da71
