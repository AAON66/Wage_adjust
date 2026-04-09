# Phase 21: 文件共享拒绝清理与状态标签 - Research

**Researched:** 2026-04-09
**Domain:** Sharing-request terminal cleanup, audit-preserving file deletion, and file-list status decoration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 当共享申请进入 `rejected` 或 `expired` 终态时，自动删除申请者副本，删除范围包括物理文件、`UploadedFile` 记录，以及该副本关联的 evidence / parse 衍生数据。 [VERIFIED: 21-CONTEXT.md]
- **D-02:** 自动清理只影响申请者副本，不影响原上传者文件、原文件上的贡献关系，且不会误删共享申请历史记录。 [VERIFIED: 21-CONTEXT.md]
- **D-03:** 即使副本被清理，共享申请记录仍保留在 `/sharing-requests` 里，作为双方都能查看的历史与审计轨迹。 [VERIFIED: 21-CONTEXT.md]
- **D-04:** “待同意”标签显示在申请者副本所在的文件列表项上，而不是只留在共享申请页中。 [VERIFIED: 21-CONTEXT.md]
- **D-05:** 由于 `FileList` 同时被 `MyReview` 和 `EvaluationDetail` 复用，管理员查看该员工材料时也应看到同一“待同意”标签。 [VERIFIED: 21-CONTEXT.md]
- **D-06:** 该标签只表示共享申请状态仍为 `pending`，不扩展成新的解析状态体系，也不要求在原上传者自己的文件列表中镜像显示。 [VERIFIED: 21-CONTEXT.md]
- **D-07:** 拒绝仍然是终局结果；即使副本被自动删除，针对“相同 content_hash + 相同原上传者”的请求也不允许再次申请。 [VERIFIED: 21-CONTEXT.md]
- **D-08:** 超时仍然允许重新发起；副本在超时后被自动删除，但申请者可以重新上传同一文件触发新的共享申请。 [VERIFIED: 21-CONTEXT.md]
- **D-09:** 超时删除后，需要同时保留共享申请历史，并给申请者明确的删除原因反馈，避免用户只看到“文件消失”却不知道原因。 [VERIFIED: 21-CONTEXT.md]
- **D-10:** 不新增独立通知中心、站内信或推送机制；超时反馈应落在现有页面与交互表面内完成。 [VERIFIED: 21-CONTEXT.md]

### Claude's Discretion
- “待同意”标签在文件行中的具体摆放位置与视觉样式，只要与现有 `FileList` 风格一致即可。 [VERIFIED: 21-CONTEXT.md]
- 超时删除原因的具体承载方式可由后续设计决定，例如 toast、inline hint、空状态说明或历史页提示，但必须清晰可见。 [VERIFIED: 21-CONTEXT.md]
- 后端向前端暴露 pending sharing 状态时使用布尔字段、枚举字段或聚合显示字段，由后续 research / planning 决定。 [VERIFIED: 21-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope. [VERIFIED: 21-CONTEXT.md]
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support | Provenance |
|----|-------------|------------------|------------|
| SHARE-06 | 共享申请被拒绝后，申请者上传的副本文件自动从系统中删除（物理文件+数据库记录） | Requires a reject-path cleanup that deletes requester storage, `UploadedFile`, and evidence rows without deleting the `SharingRequest` audit record. | [VERIFIED: REQUIREMENTS.md] [VERIFIED: codebase grep] |
| SHARE-07 | 未审批的共享作品在列表中显示"待同意"状态标签 | Requires a file-list response contract extension because current file APIs only expose parse status and current `FileList` only renders parse-state pills. | [VERIFIED: REQUIREMENTS.md] [VERIFIED: codebase grep] |
| SHARE-08 | 72h 超时的共享申请触发时，申请者上传的副本文件也自动删除 | Requires extending the existing lazy-expiry path so expiry performs the same history-safe requester-copy cleanup as rejection, and exposing that cleanup on user-hit surfaces instead of only `/sharing-requests`. | [VERIFIED: REQUIREMENTS.md] [VERIFIED: codebase grep] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Frontend work must stay inside the existing `React + TypeScript` app and backend work must stay inside the existing `FastAPI + Python` service layout. [VERIFIED: CLAUDE.md]
- The planner should prefer reusing existing schema, service, and component patterns instead of creating parallel flows for file sharing. [VERIFIED: CLAUDE.md]
- File-processing changes must be validated on normal and failure paths, not just the happy path. [VERIFIED: CLAUDE.md]
- The implementation must pass Python syntax checks, backend tests, frontend lint/build, and backend startup validation before the phase is considered done. [VERIFIED: CLAUDE.md]
- The project decision record still treats Alembic as the sole migration path, so any schema fix for `SharingRequest` must be planned as a migration, not as ad-hoc table recreation. [VERIFIED: .planning/PROJECT.md]

## Summary

Phase 21 is not mainly a UI polish task. The codebase already centralizes sharing transitions in `SharingService`, file deletion semantics in `FileService`, shared file rendering in `FileList`, and requester-owner history in `/sharing-requests`, so the safest implementation path is to extend those existing seams instead of adding new pages, new schedulers, or a second status system. [VERIFIED: codebase grep]

The hidden blocker is referential integrity. `SharingRequest.requester_file_id` and `SharingRequest.original_file_id` both use `ondelete='CASCADE'`, SQLite foreign keys are explicitly enabled in `backend/app/core/database.py`, outgoing history queries currently join through `requester_file_id`, and duplicate re-apply checks currently recover `content_hash` by joining `SharingRequest` back to the requester `UploadedFile`. If the planner deletes the requester copy without first changing that data model, the system will either delete the history row, lose the D-07 “拒绝后不可重提” rule, or both. [VERIFIED: codebase grep] [CITED: https://sqlite.org/foreignkeys.html] [CITED: https://docs.sqlalchemy.org/20/orm/cascades.html]

The second hidden blocker is trigger placement. The existing 72h timeout is lazy and is only run by `list_requests()` and `get_pending_count()`, while the current frontend surfaces that matter for this phase, `MyReview` and `EvaluationDetail`, load only `/submissions/{id}/files` and do not call `getPendingSharingCount()`. If Phase 21 keeps expiry cleanup behind `/sharing-requests` only, stale requester copies will survive until someone opens the sharing page, which is too late for Success Criterion 2 and for D-09 user feedback. [VERIFIED: codebase grep]

**Primary recommendation:** plan Phase 21 as three tightly-coupled tracks executed in this order: `schema + history preservation`, then `service/API cleanup + pending-tag contract`, then `targeted backend regressions + frontend shared-surface smoke verification`. [VERIFIED: codebase grep]

## Standard Stack

### Core

| Library / Module | Version | Purpose | Why Standard | Provenance |
|------------------|---------|---------|--------------|------------|
| FastAPI | 0.115.0 | Extend `/files` and `/sharing-requests` response contracts | The current API layer already denormalizes sharing fields and owns file-list serialization, so Phase 21 should stay there. | [VERIFIED: requirements.txt] [VERIFIED: codebase grep] |
| SQLAlchemy | 2.0.36 | Model and query changes for history-safe requester-file deletion | The primary implementation risk is FK delete behavior and query coupling inside ORM models/services. | [VERIFIED: requirements.txt] [VERIFIED: codebase grep] [CITED: https://docs.sqlalchemy.org/20/orm/cascades.html] |
| Alembic | 1.14.0 | Schema migration for `SharingRequest` history preservation | The project uses Alembic as the only migration path, and SQLite-safe FK changes should use batch alter semantics. | [VERIFIED: requirements.txt] [VERIFIED: .planning/PROJECT.md] [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html?highlight=operations] |
| Pydantic | 2.10.3 | Shared file and sharing response models | Current file/sharing APIs already rely on Pydantic response models for denormalized fields; the pending-share tag should extend that contract, not bypass it. | [VERIFIED: requirements.txt] [VERIFIED: codebase grep] |
| React | 18.3.1 | Shared file-row rendering in `MyReview` and `EvaluationDetail` | The existing `FileList` component is already reused by both target surfaces. | [VERIFIED: frontend/package.json] [VERIFIED: codebase grep] |

### Supporting

| Library / Module | Version | Purpose | When to Use | Provenance |
|------------------|---------|---------|-------------|------------|
| TypeScript | 5.9.3 installed locally, `^5.8.3` declared | Contract safety for `UploadedFileRecord` and UI rendering | Run the local type-check after adding file-list sharing fields. | [VERIFIED: frontend/package.json] [VERIFIED: local command] |
| `SharingService` | repo internal | Reject and 72h expiry hook points | Use `reject_request()` and the stale-expiry path as the only business-entry points for terminal cleanup. | [VERIFIED: codebase grep] |
| `FileService` | repo internal | Physical file, evidence, and submission-state cleanup semantics | Reuse only after extracting a non-committing helper that can be safely called from sharing transitions. | [VERIFIED: codebase grep] |
| Existing toast / inline message surfaces | repo internal | D-09 timeout/rejection reason feedback | Prefer `MyReview`'s toast surface or an inline history hint instead of inventing a notification center. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Provenance |
|------------|-----------|----------|------------|
| Existing lazy expiry | Celery Beat or a new scheduled job | Out of scope for v1.2 and unnecessary because the codebase already models 72h expiry lazily. | [VERIFIED: REQUIREMENTS.md] [VERIFIED: codebase grep] |
| Extending shared `FileList` | A new sharing-only file widget | Violates D-04 and D-05 and duplicates the shared surface already used by both pages. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |
| Extracted delete helper | Ad-hoc storage delete + SQL delete inside `SharingService` | Risks missing evidence cleanup and submission-status resets that the current file deletion path already handles. | [VERIFIED: codebase grep] |

**Installation:**

```bash
pip install -r requirements.txt
npm --prefix frontend install
```

[VERIFIED: CLAUDE.md] [VERIFIED: requirements.txt] [VERIFIED: local command]

**Version verification:** Phase 21 does not require any new dependency to be introduced. Use the repo-pinned backend versions from `requirements.txt`, the frontend versions from `frontend/package.json`, and the verified local toolchain already present in this workspace. [VERIFIED: requirements.txt] [VERIFIED: frontend/package.json] [VERIFIED: local command]

## Existing Integration Map

| File | Role Today | Planning Implication | Provenance |
|------|------------|----------------------|------------|
| `backend/app/models/sharing_request.py` | Stores status, file FKs, and submission FKs | This model needs the history-preserving change because current `requester_file_id` deletion semantics are incompatible with D-02 and D-03. | [VERIFIED: codebase grep] |
| `backend/app/services/sharing_service.py` | Owns reject, approve, revoke, and lazy expiry | This is the correct place to add terminal cleanup orchestration and to expose a reusable expiry-cleanup entry point. | [VERIFIED: codebase grep] |
| `backend/app/services/file_service.py` | Owns storage deletion, evidence deletion, and submission status rollback | This service should provide the low-level delete primitive used by sharing cleanup. | [VERIFIED: codebase grep] |
| `backend/app/api/v1/files.py` | Lists submission files and uploads duplicate requester copies atomically | This endpoint must trigger expiry cleanup on relevant surfaces and decorate returned file rows with pending-share metadata. | [VERIFIED: codebase grep] |
| `backend/app/api/v1/sharing.py` | Lists history and handles approve/reject/revoke | These queries must stop depending on requester-file joins for history that survives requester-file deletion. | [VERIFIED: codebase grep] |
| `backend/app/schemas/file.py` | Defines `UploadedFileRead` | Needs optional sharing-derived display fields for the badge. | [VERIFIED: codebase grep] |
| `frontend/src/types/api.ts` | Defines `UploadedFileRecord` and `SharingRequestRecord` | File list rendering cannot change until this shared contract grows a sharing-status field. | [VERIFIED: codebase grep] |
| `frontend/src/components/evaluation/FileList.tsx` | Renders parse-status pills and actions for each file row | This is the only component that should gain the “待同意” tag. | [VERIFIED: codebase grep] |
| `frontend/src/pages/MyReview.tsx` | Employee-facing file list and existing toast surface | This page is the best place to surface D-09 feedback without adding a new notification system. | [VERIFIED: codebase grep] |
| `frontend/src/pages/EvaluationDetail.tsx` | Admin/manager view of the same file list | This page gets the same pending tag automatically via the shared component. | [VERIFIED: codebase grep] |
| `frontend/src/pages/SharingRequests.tsx` | Existing history surface | Keep this page as the audit/history source of truth after requester-copy cleanup. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |

## Architecture Patterns

### Recommended Project Structure

```text
backend/
├── app/models/sharing_request.py      # FK/nullability + archival fields if needed
├── app/services/sharing_service.py    # reject/expire lifecycle + cleanup orchestration
├── app/services/file_service.py       # non-committing delete helper
├── app/api/v1/files.py                # expiry trigger + file-list decoration
├── app/api/v1/sharing.py              # history queries resilient to deleted requester files
├── app/schemas/file.py                # sharing badge fields on file rows
└── tests/
    ├── test_submission/test_sharing_request.py
    └── test_api/test_sharing_api.py
frontend/
├── src/types/api.ts                   # UploadedFileRecord extension
├── src/components/evaluation/FileList.tsx
├── src/pages/MyReview.tsx
├── src/pages/EvaluationDetail.tsx
└── src/pages/SharingRequests.tsx
```

[VERIFIED: codebase grep]

### Pattern 1: Audit-Preserving Terminal Cleanup

**What:** When a sharing request becomes `rejected` or `expired`, update the request status and delete only the requester copy in the same transaction, while preserving enough request-side data to keep history readable and to preserve the D-07 no-reapply rule after the requester `UploadedFile` row is gone. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

**When to use:** `SharingService.reject_request()` and the stale-expiry cleanup path should share the same cleanup routine. [VERIFIED: codebase grep]

**Example:**

```python
# Source: derived from backend/app/services/sharing_service.py + backend/app/services/file_service.py
def _finalize_with_cleanup(sr: SharingRequest, status: str) -> SharingRequest:
    _snapshot_requester_metadata(sr)  # at minimum content_hash for D-07
    sr.status = status
    sr.resolved_at = utc_now()
    _delete_requester_copy_without_commit(sr.requester_file_id)
    db.flush()
    return sr
```

### Pattern 2: Submission-ID Based History Queries

**What:** Use `requester_submission_id` and `original_submission_id` as the durable ownership filter for history queries instead of joining through `requester_file_id` or `original_file_id` when the intent is only to resolve “whose request is this?”. [VERIFIED: codebase grep]

**When to use:** `list_requests(direction='incoming'|'outgoing')` and `get_pending_count()` should not require the requester copy to exist in order to show or count the request. [VERIFIED: codebase grep]

**Example:**

```python
# Source: recommended replacement for current file-join filters
if direction == "outgoing":
    query = select(SharingRequest).where(SharingRequest.requester_submission_id.in_(employee_submission_ids))
```

### Pattern 3: File-List Decoration, Not Parse-Status Mutation

**What:** Add optional sharing-derived fields such as `sharing_status: "pending" | null` and `sharing_status_label: "待同意" | null` to `UploadedFileRead` / `UploadedFileRecord`, and render a second pill in `FileList`. Do not overload `parse_status`. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

**When to use:** `list_submission_files()` should decorate only the requester-owned file rows whose active sharing request is still `pending`. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

**Example:**

```python
# Source: recommended extension of backend/app/api/v1/files.py
pending_ids = set(
    db.scalars(
        select(SharingRequest.requester_file_id).where(
            SharingRequest.requester_file_id.in_(file_ids),
            SharingRequest.status == "pending",
        )
    )
)
```

### Pattern 4: Trigger Expiry From Surfaces Users Actually Hit

**What:** Run stale-expiry cleanup before file-list responses in addition to sharing-history responses, because current employee/admin file pages do not call the pending-count endpoint and often will not open `/sharing-requests`. [VERIFIED: codebase grep]

**When to use:** `backend/app/api/v1/files.py::list_submission_files()` should invoke a public expiry-cleanup method before listing files and computing pending tags. [VERIFIED: codebase grep]

**Example:**

```python
# Source: recommended change to backend/app/api/v1/files.py
SharingService(db).expire_and_cleanup_stale_requests()
items = FileService(db, settings).list_files(submission_id)
```

### Anti-Patterns to Avoid

- **Calling `FileService.delete_file()` directly from reject/expire logic:** it commits internally today, which makes terminal cleanup non-atomic and unsafe for shared transition logic. [VERIFIED: codebase grep]
- **Deleting the requester copy while `SharingRequest.requester_file_id` is still `ON DELETE CASCADE`:** SQLite will delete the dependent request row when foreign keys are enforced. [VERIFIED: codebase grep] [CITED: https://sqlite.org/foreignkeys.html]
- **Keeping D-07 dedup logic dependent on the requester file row:** current `check_can_create_request()` joins back to `UploadedFile.content_hash`, so it will stop blocking rejected re-requests if the requester file is deleted first. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]
- **Reusing `parse_status` for pending sharing:** D-06 explicitly says “待同意” is not a new parse-status system. [VERIFIED: 21-CONTEXT.md]
- **Leaving timeout cleanup only behind `/sharing-requests`:** current user pages do not hit that endpoint on normal load. [VERIFIED: codebase grep]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why | Provenance |
|---------|-------------|-------------|-----|------------|
| Requester-copy deletion | Ad-hoc `storage.delete` + evidence delete SQL inside `SharingService` | An extracted non-committing helper from `FileService` | The current file service already knows how to delete storage, delete evidence rows, and roll submission status back when no files remain. | [VERIFIED: codebase grep] |
| 72h timeout engine | A new scheduler, cron job, or Celery Beat flow | The existing lazy-expiry pattern, extended to perform cleanup and exposed on file-list reads | The repo already models 72h expiry lazily, and v1.2 explicitly defers scheduled-task work. | [VERIFIED: REQUIREMENTS.md] [VERIFIED: codebase grep] |
| Pending-share UI | A new list surface or a new parse-status enum | Shared `FileList` plus a sharing-derived field on `UploadedFileRead` | D-04, D-05, and D-06 already lock this behavior to the existing file row surface. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |

**Key insight:** the planner should treat Phase 21 as a referential-integrity and data-contract change with a small UI tail, not as a badge-only frontend task. [VERIFIED: codebase grep]

## Common Pitfalls

### Pitfall 1: Audit History Disappears During Cleanup

**What goes wrong:** deleting the requester `UploadedFile` also deletes the `SharingRequest` row. [VERIFIED: codebase grep]

**Why it happens:** both sharing-file foreign keys are currently declared with `ondelete='CASCADE'`, and SQLite FK enforcement is explicitly enabled in the engine setup. [VERIFIED: codebase grep] [CITED: https://sqlite.org/foreignkeys.html]

**How to avoid:** change the requester-file persistence strategy before enabling cleanup, for example by making the requester-file FK nullable or otherwise decoupling history from live file deletion via an Alembic migration. [VERIFIED: .planning/PROJECT.md] [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html?highlight=operations]

**Warning signs:** `/sharing-requests` stops showing rejected or expired history immediately after cleanup, or tests observe the request row count drop with the file row count. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

### Pitfall 2: Rejected Requests Become Re-Submittable

**What goes wrong:** after requester-copy cleanup, a user can re-upload the same hash to the same original uploader even though D-07 says reject is terminal. [VERIFIED: 21-CONTEXT.md]

**Why it happens:** current pre-check and create-request logic recover `content_hash` by joining `SharingRequest` back to the requester `UploadedFile`, which disappears after cleanup. [VERIFIED: codebase grep]

**How to avoid:** persist the hash needed for D-07 on the `SharingRequest` itself before deleting the requester file, and switch the duplicate-precheck query to use that persisted value for `pending` / `approved` / `rejected`. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

**Warning signs:** rejected-request tests start passing cleanup assertions but no longer fail on re-apply. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

### Pitfall 3: Timeout Cleanup Never Runs on the File Pages

**What goes wrong:** the requester file still exists after 72h until someone manually opens `/sharing-requests`. [VERIFIED: codebase grep]

**Why it happens:** stale expiry currently runs only in `list_requests()` and `get_pending_count()`, and the current frontend does not call the pending-count endpoint on page load. [VERIFIED: codebase grep]

**How to avoid:** expose a public expiry-cleanup entry point and call it from `list_submission_files()` before file decoration. [VERIFIED: codebase grep]

**Warning signs:** MyReview shows a 73h-old duplicate file with a pending tag after refresh, while the sharing page later flips it to expired. [VERIFIED: codebase grep]

### Pitfall 4: Reject / Expire Cleanup Becomes Partially Committed

**What goes wrong:** request status changes, file deletion, and evidence cleanup do not succeed or fail together. [VERIFIED: codebase grep]

**Why it happens:** `FileService.delete_file()` calls `self.db.commit()` internally, but sharing transitions also expect the API layer to commit after service completion. [VERIFIED: codebase grep]

**How to avoid:** refactor a no-commit helper that both `delete_file()` and sharing cleanup can call, and let the outer transition own the transaction boundary. [VERIFIED: codebase grep]

**Warning signs:** request status is `rejected` or `expired` but the requester file or evidence rows still exist after an exception, or the reverse. [VERIFIED: codebase grep]

### Pitfall 5: “待同意” Leaks to the Wrong Files

**What goes wrong:** the original uploader’s file or unrelated files in the same submission show the pending tag. [VERIFIED: 21-CONTEXT.md]

**Why it happens:** the planner derives the badge from submission-level sharing presence instead of from `SharingRequest.requester_file_id == current file.id` and `status == 'pending'`. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

**How to avoid:** compute the badge per returned file row and only for active requester copies. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

**Warning signs:** both sides of the duplicate pair show the same badge, or a file keeps the badge after approval/reject/expiry. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

## Code Examples

Verified patterns from the current codebase:

### Existing Lazy Expiry Hook

```python
# Source: backend/app/services/sharing_service.py
def _expire_stale_requests(self) -> None:
    cutoff = utc_now() - timedelta(hours=72)
    now = utc_now()
    stale_ids = list(self.db.scalars(
        select(SharingRequest.id)
        .where(SharingRequest.status == 'pending', SharingRequest.created_at < cutoff)
    ).all())
    if stale_ids:
        self.db.execute(
            update(SharingRequest)
            .where(SharingRequest.id.in_(stale_ids))
            .values(status='expired', resolved_at=now)
        )
```

[VERIFIED: codebase grep]

### Existing File-Derived Evidence Cleanup

```python
# Source: backend/app/services/file_service.py
def delete_submission_evidence_for_file(self, submission_id: str, file_id: str) -> None:
    items = self.list_evidence(submission_id)
    for item in items:
        if item.metadata_json.get('file_id') == file_id:
            self.db.delete(item)
```

[VERIFIED: codebase grep]

### Existing Shared File Row Status Pill

```tsx
// Source: frontend/src/components/evaluation/FileList.tsx
<span className="status-pill" style={PARSE_STATUS_STYLES[file.parse_status]}>
  {PARSE_STATUS_LABELS[file.parse_status]}
</span>
```

[VERIFIED: codebase grep]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact | Provenance |
|--------------|------------------|--------------|--------|------------|
| Reject / expire left the requester copy in place | Phase 21 locks auto-cleanup of the requester copy on `rejected` and `expired` | Context gathered on 2026-04-09 | Planner must schedule schema and lifecycle work, not only UI updates. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: ROADMAP.md] [VERIFIED: codebase grep] |
| Sharing timeout cleanup only mutates request status | Phase 21 must also remove requester files and derived data on timeout | Context gathered on 2026-04-09 | Existing lazy-expiry hook needs a cleanup branch. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |
| File list only exposes parse status | Phase 21 adds an independent `待同意` badge on requester copies while keeping parse status unchanged | Context gathered on 2026-04-09 | Planner should extend the file contract, not redefine parse-state enums. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |

**Deprecated / outdated:**

- Treating `SharingRequest -> requester UploadedFile` as the only durable source of truth is outdated for this phase because the requester file becomes intentionally deletable. [VERIFIED: codebase grep]

## Assumptions Log

None — all implementation-critical claims above were verified from repository code, planning artifacts, local environment checks, or official docs. [VERIFIED: codebase grep] [CITED: https://sqlite.org/foreignkeys.html] [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html?highlight=operations]

## Open Questions

1. **D-09 feedback should live on which existing requester-facing surface?**
   - What we know: `MyReview` already has a toast surface, `SharingRequests` already preserves history, and D-10 forbids a new notification center. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]
   - What's unclear: whether the planner should fetch outgoing requests on `MyReview`, extend the file-list response with cleanup notices, or rely on an inline hint plus history-page explanation. [VERIFIED: codebase grep]
   - Recommendation: lock this in planning before task split, because it changes whether the backend contract grows a notice payload or whether the frontend adds a second data fetch. [VERIFIED: codebase grep]

2. **How much immutable request metadata should be snapshotted before deleting the requester file?**
   - What we know: D-07 requires `content_hash` durability after delete, and current history UI derives `file_name` from live file rows. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]
   - What's unclear: whether Phase 21 should snapshot only `content_hash`, or also `file_name` / display text for audit stability if the original file later changes. [VERIFIED: codebase grep]
   - Recommendation: treat persisted `content_hash` as mandatory for D-07, and decide in planning whether file-name snapshotting is worth the extra migration surface. [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback | Provenance |
|------------|------------|-----------|---------|----------|------------|
| `python3` / `.venv/bin/python` | Backend implementation and tests | ✓ | 3.14.4 | — | [VERIFIED: local command] |
| `.venv/bin/pytest` | Backend regression suite | ✓ | 9.0.2 | `python -m pytest` inside the same venv | [VERIFIED: local command] |
| `node` | Frontend lint/build | ✓ | v24.14.1 | — | [VERIFIED: local command] |
| `npm` | Frontend scripts | ✓ | 11.11.0 | — | [VERIFIED: local command] |
| `frontend/node_modules` + local `tsc` | Frontend type-checking | ✓ | TypeScript 5.9.3 | Re-run `npm --prefix frontend install` if removed | [VERIFIED: local command] |

**Missing dependencies with no fallback:**

- None identified for this phase. [VERIFIED: local command]

**Missing dependencies with fallback:**

- None identified for this phase. [VERIFIED: local command]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.0.2` for backend behavior; TypeScript compile gate via `npm --prefix frontend run lint` for frontend contract safety. [VERIFIED: local command] |
| Config file | `pytest.ini` for backend; no dedicated frontend unit-test config is present. [VERIFIED: codebase grep] |
| Quick run command | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py backend/tests/test_api/test_sharing_api.py -x` and `npm --prefix frontend run lint` [VERIFIED: local command] |
| Full suite command | `./.venv/bin/pytest backend/tests -x` and `npm --prefix frontend run lint` [VERIFIED: local command] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHARE-06 | Rejecting a request deletes the requester copy, evidence rows, and list visibility while preserving history | service + API integration | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py -k reject -x` and `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k reject -x` [VERIFIED: local command] | ✅ extend existing files [VERIFIED: codebase grep] |
| SHARE-07 | Pending requester copies show `待同意` in both `MyReview` and `EvaluationDetail` without changing parse status | backend contract + frontend manual smoke + typecheck | `npm --prefix frontend run lint` plus targeted backend API assertions for file-list payload shape [VERIFIED: local command] | backend ✅ / frontend manual-only [VERIFIED: codebase grep] |
| SHARE-08 | 72h expiry cleanup deletes the requester copy and removes it from file lists while keeping history visible | service + API integration | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py -k expired -x` and `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k sharing -x` [VERIFIED: local command] | ✅ extend existing files [VERIFIED: codebase grep] |

### Sampling Rate

- **Per task commit:** `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py backend/tests/test_api/test_sharing_api.py -x` and `npm --prefix frontend run lint` [VERIFIED: local command]
- **Per wave merge:** `./.venv/bin/pytest backend/tests -x` and `npm --prefix frontend run lint` [VERIFIED: local command]
- **Phase gate:** backend sharing regressions green, frontend type-check green, and manual confirmation that `待同意` appears on both shared file-list surfaces before `/gsd-verify-work`. [VERIFIED: codebase grep]

### Wave 0 Gaps

- No dedicated frontend component test harness exists for asserting the rendered badge in `FileList`, so SHARE-07 still needs manual visual verification on both `MyReview` and `EvaluationDetail`. [VERIFIED: codebase grep]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control | Provenance |
|---------------|---------|------------------|------------|
| V2 Authentication | no | Existing JWT/auth stack remains unchanged in this phase. | [VERIFIED: codebase grep] |
| V3 Session Management | no | No session-token behavior changes are required for this phase. | [VERIFIED: codebase grep] |
| V4 Access Control | yes | Keep owner checks in `reject_request()` and submission/file scope checks via `AccessScopeService`. | [VERIFIED: codebase grep] |
| V5 Input Validation | yes | Keep file/sharing contracts typed with FastAPI + Pydantic schemas and avoid client-supplied cleanup targets. | [VERIFIED: requirements.txt] [VERIFIED: codebase grep] |
| V6 Cryptography | no | This phase does not add new crypto behavior. | [VERIFIED: codebase grep] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation | Provenance |
|---------|--------|---------------------|------------|
| Unauthorized cleanup of another employee's duplicate file | Tampering / Elevation | Derive the target file from the authorized `SharingRequest`, not from a client-supplied file id in the reject call. | [VERIFIED: codebase grep] |
| Audit trail loss via FK cascade | Repudiation / Tampering | Change the requester-file persistence strategy before performing cleanup. | [VERIFIED: codebase grep] [CITED: https://sqlite.org/foreignkeys.html] |
| Pending-share state disclosure on unrelated files | Information Disclosure | Decorate only the returned requester-owned file rows whose sharing request is still `pending`. | [VERIFIED: 21-CONTEXT.md] [VERIFIED: codebase grep] |
| Stale pending state after timeout | Integrity | Trigger expiry cleanup before listing files and exclude expired rows from the pending-tag query. | [VERIFIED: codebase grep] |

## Sources

### Primary (HIGH confidence)

- `backend/app/models/sharing_request.py` - verified current FK strategy and history-coupling risk. [VERIFIED: codebase grep]
- `backend/app/services/sharing_service.py` - verified current reject/approve/lazy-expiry behavior and query coupling. [VERIFIED: codebase grep]
- `backend/app/services/file_service.py` - verified storage/evidence delete behavior and internal commit boundary. [VERIFIED: codebase grep]
- `backend/app/api/v1/files.py` - verified current file-list contract and duplicate-upload request creation path. [VERIFIED: codebase grep]
- `backend/app/api/v1/sharing.py` - verified current history queries and response enrichment. [VERIFIED: codebase grep]
- `backend/app/schemas/file.py` and `frontend/src/types/api.ts` - verified that file-list contracts currently expose parse status only. [VERIFIED: codebase grep]
- `frontend/src/components/evaluation/FileList.tsx` - verified the shared render surface for `MyReview` and `EvaluationDetail`. [VERIFIED: codebase grep]
- `frontend/src/pages/MyReview.tsx` and `frontend/src/pages/EvaluationDetail.tsx` - verified current data-fetch patterns and available feedback surfaces. [VERIFIED: codebase grep]
- `frontend/src/pages/SharingRequests.tsx` and `frontend/src/components/sharing/SharingRequestCard.tsx` - verified current history surface and existing sharing status pills. [VERIFIED: codebase grep]
- `backend/tests/test_submission/test_sharing_request.py` and `backend/tests/test_api/test_sharing_api.py` - verified the current regression baseline and existing test extension points. [VERIFIED: codebase grep]
- https://sqlite.org/foreignkeys.html - verified that `ON DELETE CASCADE` deletes dependent child rows and that SQLite FK enforcement must be explicitly enabled. [CITED: https://sqlite.org/foreignkeys.html]
- https://docs.sqlalchemy.org/20/orm/cascades.html - verified SQLAlchemy guidance around database-level `ON DELETE` behavior and delete-vs-set-null semantics. [CITED: https://docs.sqlalchemy.org/20/orm/cascades.html]
- https://alembic.sqlalchemy.org/en/latest/ops.html?highlight=operations - verified `batch_alter_table()` as the SQLite-safe migration mechanism for unsupported table-alter operations. [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html?highlight=operations]

### Secondary (MEDIUM confidence)

- None. [VERIFIED: research session]

### Tertiary (LOW confidence)

- None. [VERIFIED: research session]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - no new libraries are needed and the active backend/frontend versions were verified from local manifests and installed tools. [VERIFIED: requirements.txt] [VERIFIED: frontend/package.json] [VERIFIED: local command]
- Architecture: HIGH - the critical behaviors, query paths, and transaction boundaries were all verified directly in the current codebase. [VERIFIED: codebase grep]
- Pitfalls: HIGH - the main risks come from concrete FK, query, and endpoint coupling that is already present today, and were cross-checked against official SQLite and SQLAlchemy docs. [VERIFIED: codebase grep] [CITED: https://sqlite.org/foreignkeys.html] [CITED: https://docs.sqlalchemy.org/20/orm/cascades.html]

**Research date:** 2026-04-09
**Valid until:** 2026-05-09
