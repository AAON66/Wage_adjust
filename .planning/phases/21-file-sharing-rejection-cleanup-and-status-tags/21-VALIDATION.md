---
phase: 21
slug: file-sharing-rejection-cleanup-and-status-tags
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-09
updated: 2026-04-09
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.x` + TypeScript lint/type gate via `npm --prefix frontend run lint` |
| **Config file** | `pytest.ini` and `frontend/package.json` |
| **Quick run command** | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py backend/tests/test_api/test_sharing_api.py -x && npm --prefix frontend run lint` |
| **Full suite command** | `./.venv/bin/pytest backend/tests -x && npm --prefix frontend run lint` |
| **Estimated runtime** | targeted feedback ~45s; full suite ~120s |

---

## Sampling Rate

- **After backend task commits:** Run the targeted sharing pytest set within 45 seconds
- **After frontend task commits:** Run `npm --prefix frontend run lint` plus API-shape assertions already covered by the targeted sharing suite
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** sharing regressions must be green and `待同意` must be manually confirmed on both file-list surfaces
- **Max feedback latency:** 45 seconds for targeted checks; 120 seconds for full phase validation

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | SHARE-06 | T-21-01, T-21-02 | reject path deletes only requester copy and derived data while preserving `SharingRequest` audit history | service/api | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py -k reject -x && ./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k reject -x` | ✅ | pending |
| 21-01-02 | 01 | 1 | SHARE-06, SHARE-08 | T-21-02, T-21-04 | schema/query changes preserve history, keep rejected terminal, and keep no-reapply semantics after requester-file deletion | service/api | `./.venv/bin/pytest backend/tests/test_submission/test_sharing_request.py -k "reject or expired or revoke" -x && ./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k "reject or sharing or revoke" -x` | ✅ | pending |
| 21-02-01 | 02 | 2 | SHARE-08 | T-21-04 | lazy 72h expiry cleanup is triggered on file-list surfaces and removes stale requester copies from visible lists | api | `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k "expired or files" -x` | ✅ | pending |
| 21-02-02 | 02 | 2 | SHARE-07 | T-21-03 | only requester-owned pending shared copies get the `待同意` badge; parse status remains unchanged; rejected rows expose no revoke-rejection UI | api/typecheck/manual | `./.venv/bin/pytest backend/tests/test_api/test_sharing_api.py -k "pending or files or revoke" -x && npm --prefix frontend run lint && if grep -q "revokeSharingRejection\\|撤销拒绝" frontend/src/services/sharingService.ts frontend/src/pages/SharingRequests.tsx frontend/src/components/sharing/SharingRequestCard.tsx; then exit 1; fi` | ✅ | pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `backend/tests/test_submission/test_sharing_request.py` — existing sharing service regression scaffold
- [x] `backend/tests/test_api/test_sharing_api.py` — existing sharing API regression scaffold
- [x] `frontend/package.json` lint script — existing TypeScript contract gate
- [x] `frontend/src/components/evaluation/FileList.tsx` — existing shared render surface for both target pages

*Existing infrastructure covers all automated phase requirements; SHARE-07 visual confirmation remains manual-only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `待同意` 标签在 `MyReview` 文件行中出现且不替代解析状态 | SHARE-07 | repo has no UI component/E2E test harness for this shared surface | open employee `MyReview`, upload a duplicate that creates a pending sharing request, refresh, confirm the requester copy row shows `待同意` alongside the existing parse-status pill |
| 管理端 `EvaluationDetail` 查看同一员工材料时看到同一 `待同意` 标签 | SHARE-07 | no automated DOM verification for the reused `FileList` component | open the same submission in `EvaluationDetail`, confirm the same file row carries `待同意` and unrelated files do not |
| 72h 超时删除后用户能看懂文件为何消失 | SHARE-08 | feedback surface choice depends on existing page behavior rather than a dedicated test harness | create or seed an expired pending request, load the requester-facing surface, confirm the file is gone and an explicit timeout-cleanup reason is visible on an existing page surface |
| 共享申请历史页不再提供 `撤销拒绝` 入口 | SHARE-08 | repo has no frontend E2E coverage for action-button presence/absence | open `/sharing-requests`, find a rejected request, confirm there is no `撤销拒绝` button while approved requests still keep their existing `撤销审批` behavior |

---

## Validation Sign-Off

- [x] All planned tasks have `<automated>` verify or an existing Wave 0 dependency
- [x] Sampling continuity maintained across backend cleanup and frontend display changes
- [x] Wave 0 covers all referenced automated verification surfaces
- [x] No watch-mode flags
- [x] Feedback latency stays under 120s for full phase validation
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-09
