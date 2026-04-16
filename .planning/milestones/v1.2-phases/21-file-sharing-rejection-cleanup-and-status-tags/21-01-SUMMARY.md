---
phase: 21-file-sharing-rejection-cleanup-and-status-tags
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, sharing, file-cleanup]
requires:
  - phase: 16-file-sharing-workflow
    provides: duplicate-upload sharing requests, pending/approved/rejected lifecycle
provides:
  - history-safe sharing requests with requester hash/name snapshots
  - atomic reject/expire cleanup through a no-commit file delete helper
  - file-list sharing badges and cleanup notices for requester submissions
affects: [21-02, sharing-requests, submission-files]
tech-stack:
  added: []
  patterns: [history-safe nullable requester FK, terminal cleanup orchestration, file-list sharing decoration]
key-files:
  created:
    - alembic/versions/f21a0b8c9d1e_preserve_sharing_history_before_requester_cleanup.py
    - backend/__init__.py
    - conftest.py
  modified:
    - backend/app/models/sharing_request.py
    - backend/app/services/sharing_service.py
    - backend/app/services/file_service.py
    - backend/app/api/v1/files.py
    - backend/app/api/v1/sharing.py
    - backend/app/schemas/file.py
    - backend/app/schemas/sharing.py
    - backend/tests/test_submission/test_sharing_request.py
    - backend/tests/test_api/test_sharing_api.py
key-decisions:
  - "Requester history now survives copy deletion by persisting requester_content_hash and requester_file_name_snapshot on SharingRequest."
  - "Reject and lazy-expiry share one service-owned cleanup path that reuses FileService.delete_file_without_commit()."
  - "Submission file lists expose sharing_status/sharing_status_label and sharing_cleanup_notices instead of overloading parse_status."
patterns-established:
  - "Pattern 1: snapshot requester metadata before deleting requester-owned uploaded_files rows."
  - "Pattern 2: perform terminal sharing cleanup in one transaction and commit only from the outer API layer."
requirements-completed: [SHARE-06, SHARE-08]
duration: 21 min
completed: 2026-04-09
---

# Phase 21 Plan 01: File Sharing Rejection Cleanup Summary

**History-safe sharing requests with requester snapshots, atomic reject/expire copy cleanup, and file-list sharing status contracts**

## Performance

- **Duration:** 21 min
- **Started:** 2026-04-09T07:45:45Z
- **Completed:** 2026-04-09T08:06:20Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- `SharingRequest` 不再因 requester 副本删除而被级联清空，拒绝不可重提与超时可重提规则改为基于持久化 hash/snapshot。
- reject 与 72h expiry 统一走同一套原子 cleanup 模型，删除 requester 副本、evidence 和物理存储时不再发生中途自提交。
- `/submissions/{submission_id}/files` 读取前会主动触发 stale expiry cleanup，并返回 `待同意` 装饰字段与 `sharing_cleanup_notices` contract。

## Task Commits

Each TDD task produced RED/GREEN commits:

1. **Task 1 RED: history-safe sharing cleanup regressions** - `79fc45e` (`test`)
2. **Task 1 GREEN: preserve sharing history after requester cleanup** - `1fe95cd` (`feat`)
3. **Task 2 RED: terminal cleanup + file-list contract regressions** - `52f5526` (`test`)
4. **Task 2 GREEN: unify sharing terminal cleanup on file-list reads** - `dbeafd1` (`feat`)

## Files Created/Modified
- `alembic/versions/f21a0b8c9d1e_preserve_sharing_history_before_requester_cleanup.py` - SQLite-safe migration for nullable requester FK plus snapshot backfill.
- `backend/app/models/sharing_request.py` - requester history fields and nullable requester FK.
- `backend/app/services/sharing_service.py` - duplicate guard persistence, reject/expire shared cleanup, file-list-triggered expiry entry point.
- `backend/app/services/file_service.py` - reusable no-commit delete helper used by sharing terminal cleanup.
- `backend/app/api/v1/files.py` - stale expiry trigger, pending badge serialization, cleanup notices payload.
- `backend/app/api/v1/sharing.py` - settings-aware sharing service usage and history-safe rejected request serialization.
- `backend/app/schemas/file.py` - file-row decoration fields and `sharing_cleanup_notices` contract.
- `backend/app/schemas/sharing.py` - nullable requester_file_id plus persisted snapshot/hash fields in response schema.
- `backend/tests/test_submission/test_sharing_request.py` - reject/expired cleanup, rollback, history retention regressions.
- `backend/tests/test_api/test_sharing_api.py` - file-list-triggered expiry cleanup, pending badge, cleanup notice regressions.
- `backend/__init__.py` - explicit backend package marker for pytest import stability.
- `conftest.py` - root path injection so `./.venv/bin/pytest ...` works directly from repo root.

## Decisions Made
- `requester_file_id` 改为 nullable + `ondelete='SET NULL'`，同时把 `requester_content_hash` / `requester_file_name_snapshot` 作为拒绝/历史展示的持久事实源。
- `SharingService._finalize_request_with_cleanup()` 成为 reject/expire 统一收尾点，`FileService.delete_file_without_commit()` 负责底层删除但不提交事务。
- file-list API 只对 `requester_file_id == 当前文件 && status == pending` 的文件返回 `待同意`，并将清理原因提升为 submission 级 notices，而不是污染 `parse_status`。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pytest import-path instability for the plan's exact verify commands**
- **Found during:** Task 1 RED
- **Issue:** `./.venv/bin/pytest ...` 在当前环境下无法导入 `backend`，计划指定验证命令无法进入真实业务断言。
- **Fix:** Added `backend/__init__.py` and root `conftest.py` so the repo root is on `sys.path` for direct pytest entrypoint runs.
- **Files modified:** `backend/__init__.py`, `conftest.py`
- **Verification:** The exact plan pytest commands later ran successfully without `PYTHONPATH` overrides.
- **Committed in:** `79fc45e`

---

**Total deviations:** 1 auto-fixed (`Rule 3`: 1)
**Impact on plan:** Necessary to execute the planned verification commands as written. No product-scope drift.

## Issues Encountered

- Parallel `git add` operations hit transient `.git/index.lock` contention inside the dirty main workspace. Resolved by serializing staging for plan files only.
- Task 1 RED tests that manually deleted the requester file were updated during Task 2 GREEN because reject cleanup became automatic by design.

## Verification

- `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py -k "reject or expired or duplicate or revoke" -x` -> passed (`11 passed, 4 deselected`)
- `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k "sharing or reject or revoke" -x` -> passed (`14 passed`)
- `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py backend/tests/test_api/test_sharing_api.py -x` -> passed (`34 passed`)
- `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py -k "reject or expired or duplicate" -x` -> passed (`13 passed, 4 deselected`)
- `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k "sharing or reject or files" -x` -> passed (`17 passed`)
- `grep -n "requester_content_hash" backend/app/models/sharing_request.py` -> matched line 34
- `grep -n "expire" backend/app/api/v1/files.py` -> matched file-list expiry trigger on line 269

## Known Stubs

None.

## Threat Flags

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 2 can proceed. Backend now guarantees history-safe requester cleanup, stale file-list-triggered expiry, and the payload needed for frontend `待同意` / cleanup messaging.
- No new blocker was found that should stop Plan 21-02. Frontend still needs to consume the new file-list contract and remove revoke-rejection UI.

## Notes

- `.planning/STATE.md` and `.planning/ROADMAP.md` were intentionally left untouched per execution instruction from the orchestrator/user.

## Self-Check: PASSED

- `FOUND: .planning/phases/21-file-sharing-rejection-cleanup-and-status-tags/21-01-SUMMARY.md`
- `FOUND: 79fc45e`
- `FOUND: 1fe95cd`
- `FOUND: 52f5526`
- `FOUND: dbeafd1`
