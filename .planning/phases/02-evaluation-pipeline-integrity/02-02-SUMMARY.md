---
phase: 02-evaluation-pipeline-integrity
plan: 02
subsystem: llm-service
tags: [deepseek, retry, backoff, redis, rate-limiter, prompt-hash, sha256]

requires:
  - phase: 02-evaluation-pipeline-integrity/01
    provides: "Base llm_service.py with InMemoryRateLimiter and DeepSeekCallResult"
provides:
  - "compute_prompt_hash(messages) -> str for audit traceability"
  - "_compute_retry_delay() full-jitter exponential backoff"
  - "RedisRateLimiter class with uuid4() unique member per request"
  - "_DEEPSEEK_REDIS_DEGRADED health-check flag"
  - "DeepSeekCallResult.prompt_hash field populated before HTTP call"
affects: [02-evaluation-pipeline-integrity/03, 02-evaluation-pipeline-integrity/04, health-endpoint]

tech-stack:
  added: [redis (conditional), uuid4]
  patterns: [full-jitter-exponential-backoff, redis-sorted-set-sliding-window, graceful-degradation-flag]

key-files:
  created:
    - backend/app/utils/prompt_hash.py
    - backend/tests/test_eval_pipeline.py
  modified:
    - backend/app/services/llm_service.py

key-decisions:
  - "Full-jitter exponential backoff replaces linear 0.2*n sleep to avoid thundering herd"
  - "Redis rate limiter uses uuid4() in sorted-set member to prevent concurrent timestamp collision"
  - "Redis import is lazy (inside __init__ try block) so non-Redis envs do not fail on module import"
  - "_DEEPSEEK_REDIS_DEGRADED module-level flag allows health checks to detect degraded mode"

patterns-established:
  - "Graceful degradation: Redis failure logs WARNING and falls back to in-memory with health flag"
  - "Prompt hash audit: compute_prompt_hash(messages) before HTTP call, store in result dataclass"

requirements-completed: [EVAL-01, EVAL-02, EVAL-05]

duration: 8min
completed: 2026-03-27
---

# Phase 02 Plan 02: LLM Service Hardening Summary

**Full-jitter exponential backoff, Redis-backed cross-worker rate limiter with uuid4() collision prevention, and prompt_hash audit field on DeepSeekCallResult**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T09:15:18Z
- **Completed:** 2026-03-27T09:23:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created compute_prompt_hash utility (SHA-256 of deterministic JSON serialization) for audit traceability
- Replaced linear retry sleep with full-jitter exponential backoff respecting Retry-After headers on 429/503
- Added RedisRateLimiter with sliding-window sorted set using unique f'{now}:{uuid4()}' members
- Redis-or-fallback initialization with _DEEPSEEK_REDIS_DEGRADED health flag
- Added prompt_hash field to DeepSeekCallResult, computed before HTTP call

## Task Commits

Each task was committed atomically:

1. **Task 1: Create compute_prompt_hash utility** - `faa5f59` (feat)
2. **Task 2: LLM service hardening** - `5a3389f` (feat)

_Both tasks used TDD: tests written first (RED), then implementation (GREEN)._

## Files Created/Modified
- `backend/app/utils/prompt_hash.py` - SHA-256 hash of JSON-serialized messages for audit traceability
- `backend/app/services/llm_service.py` - _compute_retry_delay(), RedisRateLimiter, prompt_hash field, Redis-or-fallback init
- `backend/tests/test_eval_pipeline.py` - 11 tests covering prompt hash, retry backoff, Redis fallback, prompt_hash storage

## Decisions Made
- Full-jitter exponential backoff chosen over fixed/equal-jitter to minimize thundering herd risk
- Redis import is lazy (inside __init__ try block) so environments without redis package do not fail on module import
- uuid4() used in sorted-set member key to prevent concurrent timestamp collisions in multi-worker deployments
- _DEEPSEEK_REDIS_DEGRADED is a module-level bool flag readable by health endpoints without service instantiation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Python venv not in worktree; used main repo venv at D:/wage_adjust/.venv/Scripts/python.exe

## Known Stubs

None - all functionality is fully wired.

## Next Phase Readiness
- ParseService (plan 03) and EvaluationService (plan 04) can now consume DeepSeekCallResult.prompt_hash
- RedisRateLimiter is production-ready for multi-worker deployments
- Health endpoint can read _DEEPSEEK_REDIS_DEGRADED for monitoring

## Self-Check: PASSED

- [x] backend/app/utils/prompt_hash.py exists
- [x] backend/tests/test_eval_pipeline.py exists
- [x] backend/app/services/llm_service.py modified
- [x] Commit faa5f59 found
- [x] Commit 5a3389f found
- [x] All 11 tests pass

---
*Phase: 02-evaluation-pipeline-integrity*
*Completed: 2026-03-27*
