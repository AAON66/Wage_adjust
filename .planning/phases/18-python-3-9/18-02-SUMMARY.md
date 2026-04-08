---
phase: 18-python-3-9
plan: 02
subsystem: api
tags: [pydantic, typing, python39, schema, compatibility]

# Dependency graph
requires:
  - phase: none
    provides: existing Pydantic schema files
provides:
  - "18 Pydantic schema files downgraded from PEP 604/585 to Python 3.9 compatible typing syntax"
  - "All BaseModel field definitions use Optional[X] instead of X | None"
  - "All BaseModel field definitions use Dict/List/Tuple/Set instead of dict/list/tuple/set"
affects: [18-03, deployment, api-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic schema fields use typing.Optional/Dict/List for Python 3.9 compatibility"
    - "Function signatures retain PEP 604/585 syntax (protected by __future__ annotations)"

key-files:
  created: []
  modified:
    - backend/app/schemas/eligibility.py
    - backend/app/schemas/salary.py
    - backend/app/schemas/submission.py
    - backend/app/schemas/approval.py
    - backend/app/schemas/sharing.py
    - backend/app/schemas/feishu.py
    - backend/app/schemas/handbook.py
    - backend/app/schemas/api_key.py
    - backend/app/schemas/employee.py
    - backend/app/schemas/department.py
    - backend/app/schemas/evaluation.py
    - backend/app/schemas/dashboard.py
    - backend/app/schemas/user.py
    - backend/app/schemas/public.py
    - backend/app/schemas/cycle.py
    - backend/app/schemas/webhook.py
    - backend/app/schemas/audit.py
    - backend/app/schemas/attendance.py

key-decisions:
  - "Only downgrade Pydantic class body field definitions; function signatures preserved (protected by __future__ annotations)"
  - "Also downgraded non-None PEP 604 unions (int | str -> Union[int, str]) in public.py for completeness"

patterns-established:
  - "Schema field annotations: use Optional[X] not X | None for Pydantic fields"
  - "Schema field annotations: use Dict[]/List[] not dict[]/list[] for Pydantic fields"

requirements-completed: [DEPLOY-01]

# Metrics
duration: 4min
completed: 2026-04-08
---

# Phase 18 Plan 02: Schema PEP 604/585 Downgrade Summary

**18 Pydantic schema files downgraded from PEP 604 (X | None) and PEP 585 (dict[]/list[]) to Python 3.9 compatible Optional[X] and typing.Dict/List syntax**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-08T01:01:17Z
- **Completed:** 2026-04-08T01:05:32Z
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments
- Replaced 144 PEP 604 union annotations (X | None -> Optional[X]) across 18 schema files
- Replaced 72 PEP 585 builtin generic annotations (dict[]/list[] -> Dict[]/List[]) across 18 schema files
- Added correct typing imports (Optional, Dict, List, Union) to all modified files
- All schemas verified importable via `from backend.app.schemas import ...`

## Task Commits

Each task was committed atomically:

1. **Task 1: Schema PEP 604 type annotation downgrade** - `6d8b625` (feat)
2. **Task 2: Schema PEP 585 builtin generic downgrade** - `4981d91` (feat)

## Files Created/Modified
- `backend/app/schemas/eligibility.py` - 25 replacements (19 PEP 604 + 6 PEP 585)
- `backend/app/schemas/salary.py` - 9 replacements (7 + 2)
- `backend/app/schemas/submission.py` - 5 replacements (4 + 1)
- `backend/app/schemas/approval.py` - 25 replacements (17 + 8)
- `backend/app/schemas/sharing.py` - 3 replacements (2 + 1)
- `backend/app/schemas/feishu.py` - 16 replacements (12 + 4)
- `backend/app/schemas/handbook.py` - 6 replacements (3 + 3)
- `backend/app/schemas/api_key.py` - 4 replacements (4 + 0)
- `backend/app/schemas/employee.py` - 15 replacements (14 + 1)
- `backend/app/schemas/department.py` - 6 replacements (5 + 1)
- `backend/app/schemas/evaluation.py` - 14 replacements (11 + 3)
- `backend/app/schemas/dashboard.py` - 13 replacements (4 + 9)
- `backend/app/schemas/user.py` - 16 replacements (6 + 10)
- `backend/app/schemas/public.py` - 20 replacements (11 + 9)
- `backend/app/schemas/cycle.py` - 9 replacements (5 + 4)
- `backend/app/schemas/webhook.py` - 7 replacements (5 + 2)
- `backend/app/schemas/audit.py` - 4 replacements (3 + 1)
- `backend/app/schemas/attendance.py` - 12 replacements (12 + 0)
- `backend/app/schemas/import_job.py` - 3 replacements (0 + 3)
- `backend/app/schemas/file.py` - 4 replacements (0 + 4)

## Decisions Made
- Only downgraded annotations inside Pydantic BaseModel class bodies (field definitions evaluated at runtime); function signatures left untouched since `from __future__ import annotations` makes them lazy strings
- Also found and fixed `int | str` non-None PEP 604 unions in `public.py` (3 occurrences) using `Union[int, str]` -- these would also fail at runtime on Python 3.9

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed non-None PEP 604 unions in public.py**
- **Found during:** Task 2 (PEP 585 downgrade verification)
- **Issue:** `public.py` had `Dict[str, int | str]` in 3 field definitions -- the `int | str` is also PEP 604 syntax that fails on Python 3.9 at runtime
- **Fix:** Replaced `int | str` with `Union[int, str]` and added `Union` to typing imports
- **Files modified:** `backend/app/schemas/public.py`
- **Verification:** `python -c "from backend.app.schemas import public"` succeeds
- **Committed in:** 4981d91 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential for correctness -- `int | str` would crash at runtime on Python 3.9 just like `X | None`.

## Issues Encountered
- Several schema files had UTF-8 BOM markers causing `ast.parse` failures with Python 3.14 -- resolved by reading with `utf-8-sig` encoding in the automation script

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 18 schema files are now Python 3.9 compatible for Pydantic runtime evaluation
- Plan 03 can proceed with remaining non-schema Python files (services, engines, models, etc.)
- import_job.py and file.py were also processed (listed in plan files_modified for Task 2)

---
*Phase: 18-python-3-9*
*Completed: 2026-04-08*
