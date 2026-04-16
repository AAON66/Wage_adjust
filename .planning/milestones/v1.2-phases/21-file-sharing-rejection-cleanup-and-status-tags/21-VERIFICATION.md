---
phase: 21-file-sharing-rejection-cleanup-and-status-tags
verified: 2026-04-09T09:15:36Z
status: human_needed
score: 10/10 must-haves verified
human_verification:
  - test: "在 MyReview 中验证待同意标签与解析状态并存"
    expected: "申请者待审批共享副本所在文件行同时显示解析状态 pill 与“待同意” pill；无关文件和原上传者文件不显示该标签。"
    why_human: "这是最终 UI 呈现与页面可见性检查，代码可追踪到，但仍需人工确认真实页面表现。"
  - test: "在 EvaluationDetail 中验证共享 FileList 的同一标签复用"
    expected: "管理员查看同一 submission 时，FileList 行内也能看到“待同意”标签，且布局无错位。"
    why_human: "需要人工确认复用组件在另一页面上下文中的真实渲染效果。"
  - test: "在 MyReview 中验证 reject / 72h timeout 的删除反馈"
    expected: "副本消失后，页面使用现有 toast 给出清晰原因；拒绝与超时文案可区分，且同一 notice 不会重复刷屏。"
    why_human: "提示文案可理解性、去重体验和时机属于用户体验验证，不能仅靠静态代码完全确认。"
---

# Phase 21: 文件共享拒绝清理与状态标签 Verification Report

**Phase Goal:** 共享申请被拒绝或超时后，申请者的副本文件被自动清理，未审批的共享文件显示待同意标签
**Verified:** 2026-04-09T09:15:36Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | reject 会自动删除申请者副本的物理文件、`UploadedFile` 记录和关联 evidence，且不会误删 original file | ✓ VERIFIED | `backend/app/services/sharing_service.py:34`, `backend/app/services/file_service.py:694`, `backend/tests/test_submission/test_sharing_request.py:427`, spot-check `test_reject_cleanup_removes_requester_copy_evidence_and_storage_but_keeps_original` 通过 |
| 2 | 72h timeout 的懒过期会在文件列表读取链路触发，并删除申请者副本 | ✓ VERIFIED | `backend/app/api/v1/files.py:269`, `backend/app/services/sharing_service.py:46`, `backend/tests/test_api/test_sharing_api.py:470`, spot-check `test_list_files_triggers_expired_cleanup_and_returns_notice` 通过 |
| 3 | 副本删除后，请求者的文件列表里不再显示该文件 | ✓ VERIFIED | `backend/tests/test_api/test_sharing_api.py:470`, `backend/tests/test_api/test_sharing_api.py:503` 都断言 `items == []` |
| 4 | 清理副本后，共享历史仍保留并可从 incoming/outgoing 查询到 | ✓ VERIFIED | `backend/app/models/sharing_request.py:22`, `backend/app/services/sharing_service.py:132`, `backend/tests/test_submission/test_sharing_request.py:291`, `backend/tests/test_api/test_sharing_api.py:378` |
| 5 | reject 后，相同 `content_hash + original_submission_id` 仍被阻止再次申请 | ✓ VERIFIED | `backend/app/services/sharing_service.py:65`, `backend/app/services/sharing_service.py:76`, `backend/tests/test_submission/test_sharing_request.py:341` |
| 6 | expired 后，相同 `content_hash + original_submission_id` 允许重新申请 | ✓ VERIFIED | `backend/app/services/sharing_service.py:69`, `backend/tests/test_submission/test_sharing_request.py:369` |
| 7 | rejected 是终态，后端不会把 rejected 恢复为 pending | ✓ VERIFIED | `backend/app/services/sharing_service.py:206`, `backend/app/api/v1/sharing.py:128`, `backend/tests/test_submission/test_sharing_request.py:403` |
| 8 | 文件列表 API 会为待审批共享副本返回独立的 `sharing_status` / `待同意` 装饰字段，而不是污染 `parse_status` | ✓ VERIFIED | `backend/app/api/v1/files.py:72`, `backend/app/api/v1/files.py:87`, `backend/app/schemas/file.py:29`, `backend/tests/test_api/test_sharing_api.py:425` |
| 9 | `待同意` 标签在共享 `FileList` 中渲染，并被 MyReview 与 EvaluationDetail 共同复用 | ✓ VERIFIED | `frontend/src/components/evaluation/FileList.tsx:60`, `frontend/src/components/evaluation/FileList.tsx:75`, `frontend/src/pages/MyReview.tsx:745`, `frontend/src/pages/EvaluationDetail.tsx:1701` |
| 10 | requester 在 MyReview 中能看到 reject / timeout 自动删除原因，且前端不再暴露撤销拒绝入口 | ✓ VERIFIED | `frontend/src/pages/MyReview.tsx:176`, `frontend/src/pages/MyReview.tsx:307`, `frontend/src/pages/MyReview.tsx:323`, `frontend/src/types/api.ts:218`, `frontend/src/services/sharingService.ts`, `frontend/src/components/sharing/SharingRequestCard.tsx:147`; `grep -RIn "revokeSharingRejection\\|撤销拒绝" ...` 无命中 |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/app/models/sharing_request.py` | history-safe requester FK + snapshot fields | ✓ VERIFIED | `requester_file_id` 改为 nullable + `SET NULL`，并新增 `requester_content_hash` / `requester_file_name_snapshot` |
| `alembic/versions/f21a0b8c9d1e_preserve_sharing_history_before_requester_cleanup.py` | SQLite-safe migration + backfill | ✓ VERIFIED | `batch_alter_table()`、回填 SQL、FK 改为 `SET NULL`；`gsd-tools verify artifacts` 对通配符路径误报未找到，手工核验通过 |
| `backend/app/services/file_service.py` | non-committing delete helper | ✓ VERIFIED | `_delete_file_record()` + `delete_file_without_commit()` 存在，公开 `delete_file()` 仍单独 `commit()` |
| `backend/app/services/sharing_service.py` | reject / expire 共用 cleanup，duplicate guard 解耦 live requester file | ✓ VERIFIED | `_finalize_request_with_cleanup()`、`expire_and_cleanup_stale_requests()`、`_find_conflicting_request()` 都已改用持久字段 |
| `backend/app/api/v1/files.py` | file-list 触发 expiry + 装饰 badge + cleanup notices | ✓ VERIFIED | `list_submission_files()` 先调用 expire，再返回 `sharing_status` 和 `sharing_cleanup_notices` |
| `backend/app/api/v1/sharing.py` | requester_file_id 为空时仍可序列化 history；compat revoke route 仅阻止动作 | ✓ VERIFIED | `_enrich_sharing_request()` 在 requester file 缺失时仍能构造响应；`revoke-rejection` 路由存在但会走阻止逻辑 |
| `backend/app/schemas/file.py` | `sharing_status` / `sharing_cleanup_notices` contract | ✓ VERIFIED | schema 与前端 contract 对齐 |
| `backend/app/schemas/sharing.py` | nullable `requester_file_id` + snapshot fields | ✓ VERIFIED | response schema 已反映模型变化 |
| `frontend/src/types/api.ts` | frontend file-list contract 对齐 backend | ✓ VERIFIED | `UploadedFileRecord` 和 `UploadedFileListResponse` 增加 sharing 字段 |
| `frontend/src/components/evaluation/FileList.tsx` | 独立 `待同意` pill | ✓ VERIFIED | 保留 parse status 体系，同时额外渲染 sharing pill |
| `frontend/src/pages/MyReview.tsx` | requester-facing cleanup feedback | ✓ VERIFIED | `handleSharingCleanupNotices()` + `showToast()` 消费 notice |
| `frontend/src/components/sharing/SharingRequestCard.tsx` | 不再提供撤销拒绝 UI，但保留撤销审批 | ✓ VERIFIED | 仅保留 approved 状态下的 `撤销审批` 入口 |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `backend/app/services/sharing_service.py` | `backend/app/models/sharing_request.py` | snapshot metadata + duplicate-precheck | WIRED | `requester_content_hash` / `requester_file_name_snapshot` 在 create 和 finalize 时写入并参与冲突检查 |
| `backend/app/services/sharing_service.py` | `backend/app/services/file_service.py` | reject/expire cleanup calls no-commit helper | WIRED | `_finalize_request_with_cleanup()` 调用 `delete_file_without_commit()` |
| `backend/app/api/v1/files.py` | `backend/app/services/sharing_service.py` | file-list read triggers stale expiry cleanup | WIRED | `list_submission_files()` 在列文件前调用 `expire_and_cleanup_stale_requests(submission_id=...)` |
| `backend/app/api/v1/sharing.py` | `backend/app/schemas/sharing.py` | nullable requester history response | WIRED | `_enrich_sharing_request()` 能在 `requester_file_id is None` 时构造 `SharingRequestRead` |
| `backend/app/api/v1/sharing.py` | `backend/app/services/sharing_service.py` | rejected stays terminal | WIRED | compat `revoke-rejection` route 仍在，但只会返回错误，不会回退状态 |
| `frontend/src/types/api.ts` | `frontend/src/components/evaluation/FileList.tsx` | per-row sharing decoration | WIRED | `sharing_status` / `sharing_status_label` 被 FileList 直接消费 |
| `frontend/src/components/evaluation/FileList.tsx` | `frontend/src/pages/EvaluationDetail.tsx` | shared FileList reuse | WIRED | `EvaluationDetail` 直接渲染同一个 `FileList` 组件 |
| `frontend/src/pages/MyReview.tsx` | `frontend/src/services/fileService.ts` | submission file response drives notices | WIRED | `fetchSubmissionFiles()` 返回 `sharing_cleanup_notices` 后被 `handleSharingCleanupNotices()` 消费 |
| `frontend/src/pages/SharingRequests.tsx` | `frontend/src/components/sharing/SharingRequestCard.tsx` | reject terminal behavior in UI | WIRED | 页面仍传 `onRevoke`，但卡片仅在 approved 状态渲染 `撤销审批`，无撤销拒绝入口 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `backend/app/api/v1/files.py` | `pending_file_ids` | `select(SharingRequest.requester_file_id ... status == 'pending')` | Yes | ✓ FLOWING |
| `backend/app/api/v1/files.py` | `sharing_cleanup_notices` | `select(SharingRequest ... requester_file_id IS NULL AND status IN ('rejected','expired'))` | Yes | ✓ FLOWING |
| `frontend/src/components/evaluation/FileList.tsx` | `file.sharing_status` / `file.sharing_status_label` | `fetchSubmissionFiles()` -> backend file-list payload | Yes | ✓ FLOWING |
| `frontend/src/pages/MyReview.tsx` | `fileResponse.sharing_cleanup_notices` | `fetchSubmissionFiles()` -> backend notice query -> `showToast()` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| reject cleanup 删除 requester 副本、evidence、storage 且保留 original | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py::test_reject_cleanup_removes_requester_copy_evidence_and_storage_but_keeps_original -q` | `1 passed in 0.85s` | ✓ PASS |
| file-list read 触发 expired cleanup 并返回 notice | `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py::test_list_files_triggers_expired_cleanup_and_returns_notice -q` | `1 passed in 1.45s` | ✓ PASS |
| sharing 相关后端回归集 | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py backend/tests/test_api/test_sharing_api.py -x` | `34 passed` | ✓ PASS (user-provided, same turn) |
| frontend contract/usage lint | `npm --prefix frontend run lint` | `passed` | ✓ PASS (user-provided, same turn) |
| schema drift | `node "$HOME/.codex/get-shit-done/bin/gsd-tools.cjs" verify schema-drift "21"` | `drift_detected=false` | ✓ PASS (user-provided, same turn) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `SHARE-06` | `21-01-PLAN.md` | 共享申请被拒绝后，申请者上传的副本文件自动从系统中删除（物理文件+数据库记录） | ✓ SATISFIED | reject cleanup 服务实现与测试：`backend/app/services/sharing_service.py:34`, `backend/app/services/file_service.py:694`, `backend/tests/test_submission/test_sharing_request.py:427` |
| `SHARE-07` | `21-02-PLAN.md` | 未审批的共享作品在列表中显示"待同意"状态标签 | ✓ SATISFIED | file-list contract + UI 渲染：`backend/app/api/v1/files.py:72`, `frontend/src/components/evaluation/FileList.tsx:60`, `backend/tests/test_api/test_sharing_api.py:425` |
| `SHARE-08` | `21-01-PLAN.md`, `21-02-PLAN.md` | 72h 超时的共享申请触发时，申请者上传的副本文件也自动删除 | ✓ SATISFIED | file-list read expiry trigger + notice contract：`backend/app/api/v1/files.py:269`, `backend/tests/test_api/test_sharing_api.py:470`, `frontend/src/pages/MyReview.tsx:176` |

No orphaned Phase 21 requirements were found in `REQUIREMENTS.md`: `SHARE-06`, `SHARE-07`, `SHARE-08` are all claimed by the phase plans and all have code evidence.

### Anti-Patterns Found

No blocker or warning-level stub patterns were found in the phase files.

One raw grep hit was reviewed manually:

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `frontend/src/pages/MyReview.tsx` | 539 | `return null` | ℹ️ Info | 这是条件渲染分支，不是 phase stub，也不影响 Phase 21 goal |

### Human Verification Required

### 1. MyReview 待同意标签

**Test:** 以申请者身份上传触发共享申请的副本文件，打开 `MyReview` 文件列表。  
**Expected:** 同一文件行同时显示原有解析状态和 `待同意` 标签；未共享文件和原上传者文件不显示该标签。  
**Why human:** 需要确认真实页面视觉层级、位置、间距和误标情况。

### 2. EvaluationDetail 复用标签

**Test:** 以管理员身份打开同一 submission 的 `EvaluationDetail` 页面。  
**Expected:** 复用的 `FileList` 也显示同样的 `待同意` 标签，且页面布局没有异常。  
**Why human:** 这是共享组件在第二个页面上下文中的真实渲染检查。

### 3. Reject / Timeout 删除反馈

**Test:** 分别验证 reject 和 72h timeout 两条路径后回到 `MyReview`。  
**Expected:** 文件已从列表消失，并出现可理解、可区分的 toast 文案；同一条 notice 不应在一次浏览中反复弹出。  
**Why human:** 文案清晰度、提示时机和重复提示体验属于人工 UX 验证。

### Gaps Summary

未发现会阻断 Phase 21 目标达成的代码缺口。后端清理语义、历史保留、重提规则、前端状态标签和 requester 反馈链路都已经落到实际代码并有测试支撑。

当前状态为 `human_needed`，仅因为仍有最终 UI 呈现与提示体验需要人工确认；不是因为发现了实现缺失。

---

_Verified: 2026-04-09T09:15:36Z_  
_Verifier: Claude (gsd-verifier)_
