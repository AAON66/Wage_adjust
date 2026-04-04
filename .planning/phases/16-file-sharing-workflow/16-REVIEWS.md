---
phase: 16
reviewers: [codex]
reviewed_at: 2026-04-04T20:00:00+08:00
plans_reviewed: [16-01-PLAN.md, 16-02-PLAN.md]
---

# Cross-AI Plan Review — Phase 16

## Codex Review

**Cross-Plan Note**

The main issue is contract drift between the two plans. The current system is still hard-rejecting duplicates via `ValueError`/409 in file_service.py and files.py, while the plans alternately say "return duplicate info", "use a force flag", and "keep the reject behavior for now". That needs to be frozen first, or Plan 02 cannot be implemented correctly.

**16-01-PLAN.md**

Summary: The backend plan is structurally strong and fits the existing FastAPI/SQLAlchemy service pattern well. It also correctly reuses the existing contribution-weighting model already consumed by evaluation logic. The weak point is not the decomposition, but the API contract and permission/data-integrity rules around duplicate upload finalization and sharing-request creation.

**Strengths**
- Clean separation of concerns: model, schema, service, router, migration, tests.
- Good reuse of existing contribution machinery; the current evaluation path already respects `owner_contribution_pct` and accepted `ProjectContributor` records.
- Lazy expiry is the right level of complexity for this phase.
- Requirement-to-test mapping is explicit and mostly complete at the service layer.
- Refactoring dedup from `filename + hash` to `hash only` matches the phase decisions and the current dedup hotspot.

**Concerns**
- HIGH: The plan does not define one authoritative upload contract. It says upload should stop raising, then later says the backend upload should still reject duplicates, and elsewhere assumes a force-upload path exists. Those are mutually incompatible.
- HIGH: `check-duplicate` is specified with only `content_hash`, then suggests excluding `current_user.employee_id`. That is wrong for the current app because admin/HR/manager can upload into another employee's submission, and access is submission/employee scoped, not "current user is the uploader".
- HIGH: A separate `POST /sharing-requests` endpoint is a data-integrity risk unless it strictly verifies requester ownership, original ownership, same `content_hash`, non-self-request, and pending status. As written, it is too easy to end up with forged or inconsistent requests.
- HIGH: If sharing-request creation happens after upload as a second step, SHARE-02 can fail partially: duplicate file saved, no sharing request created.
- MEDIUM: Canonical "original uploader" selection is underspecified. `_check_duplicate()` currently returns the first match with no ordering. Once duplicates are allowed, that becomes nondeterministic.
- MEDIUM: The uniqueness rule is phrased as "same content_hash + same original uploader", but the plan's suggested check is centered on submission/file IDs. That is too narrow if the original uploader has multiple submissions/cycles.
- MEDIUM: The migration chain is likely wrong. The repo already has later Alembic revisions; hard-coding `down_revision = c14_add_eligibility_overrides` is risky.
- MEDIUM: Tests are heavy on service/unit coverage but light on endpoint/auth coverage. The new API surface is permission-sensitive and should have API tests.
- LOW: Returning uploader name for any matching hash creates a privacy leak across access scopes. It may be intentional, but it should be an explicit product decision.

**Suggestions**
- Freeze the backend contract to one flow: `check-duplicate(submission_id, content_hash)` for preflight, then `upload_files(..., allow_duplicate=true, original_file_id=...)` for confirm. The backend should re-check the hash and create the `SharingRequest` in the same transaction.
- Make duplicate checks relative to the target submission's employee, not `current_user.employee_id`.
- Define a canonical original file selection rule, preferably oldest `created_at` for that hash.
- Validate `CreateSharingRequest` strictly or remove it entirely from the public contract and let upload orchestration own request creation.
- Add API tests for `check-duplicate`, `approve`, `reject`, `pending-count`, unbound-user behavior, and authorization failures.
- Recompute expiry in `get_pending_count()` too, not just `list_requests()`, or badge counts will drift.

Risk Assessment: HIGH. The architecture is sound, but the contract/auth/data-integrity gaps are significant enough that the backend could pass unit tests and still fail the actual phase goals.

**16-02-PLAN.md**

Summary: The frontend plan is aligned with the desired UX and mostly fits the existing React code style. The problem is that it assumes a duplicate-confirmation flow on top of a frontend that currently does one batch upload call and then parses the returned files. Without a real queue/state model and a settled backend API, this plan is likely to lose files or create inconsistent backend state.

**Strengths**
- Good choice of Web Crypto API for zero-dependency hashing.
- Dedicated sharing page plus incoming/outgoing tabs matches the workflow well.
- Reuses existing page shell, table, button, and modal styling patterns instead of inventing a new UI system.
- `hashCheckStatus` is a sensible degraded-state design for preflight failures.
- Navigation and routing scope are small and easy to reason about.

**Concerns**
- HIGH: The plan depends on an unresolved backend contract. If the upload endpoint still returns 409 on duplicates, "继续上传" cannot succeed.
- HIGH: The proposed modal state only stores `file`, `originalFileId`, and `remainingFiles`. It does not preserve already-checked clean files, so files selected before the first duplicate can be dropped. That is a real risk given the current single-batch flow.
- HIGH: Uploading first and then calling `createSharingRequest()` from the frontend creates partial-success states. If the second call fails, the phase goal is broken.
- MEDIUM: `checkDuplicate(contentHash)` has the same actor-context bug as the backend plan. It needs target submission context, not just the logged-in user.
- MEDIUM: The verification command `npx tsc --noEmit 2>&1 | head -30` can hide TypeScript failures because the pipeline returns `head`'s exit code unless `pipefail` is set.
- MEDIUM: The route/menu is added for all authenticated roles, but non-admin users can exist without `employee_id` in the current system. The plan does not define what the sharing page should do for unbound users.
- MEDIUM: GitHub import stays behaviorally inconsistent. The same upload panel supports GitHub import, but the preflight duplicate UX is only designed for local files.
- LOW: Hashing large files with `arrayBuffer()` on the main thread may freeze the tab. Probably acceptable for v1.1, but worth acknowledging.

**Suggestions**
- Rewrite the upload flow as an explicit queue/state machine: `pending`, `currentDuplicate`, `approvedToUpload`, `skipped`, `completed`. Do not rely on recursive calls plus local arrays.
- Remove the separate frontend `createSharingRequest()` step from the happy path. The upload response should already imply the sharing request was created, ideally returning `sharing_request_id`.
- Include `submission_id` in duplicate-check calls so the backend can exclude the target employee correctly.
- Keep parsing orchestration explicit: define whether files are parsed after each accepted upload or once the full queue finishes.
- Fix verification to `npx tsc --noEmit` without piping, or use `set -o pipefail`.
- Decide unbound-user UX and GitHub-import behavior explicitly before implementation.
- If no UI test framework exists, at least add one thin integration/smoke test around duplicate confirm/cancel behavior; `tsc` alone is weak verification for this flow.

Risk Assessment: HIGH. The UX intent is good, but the current plan is too dependent on an unstable backend contract and has a real state-management hole in batch handling.

---

## Claude Review

*(Claude CLI invocation failed — prompt exceeded argument length limit. Review not available.)*

---

## Consensus Summary

*(Single reviewer — consensus analysis requires 2+ reviewers. Codex findings below serve as the primary review.)*

### Key Concerns (from Codex)

1. **HIGH — Upload contract drift:** Plans alternate between "return duplicate info" and "reject duplicates" without a single authoritative contract. Backend and frontend plans may implement incompatible behaviors.

2. **HIGH — Partial-success data integrity:** If sharing-request creation is a separate step after upload, SHARE-02 can fail partially (file saved, no request created). Should be atomic — same transaction.

3. **HIGH — Batch file state management:** Frontend modal state doesn't preserve already-checked clean files. Files selected before the first duplicate can be dropped.

4. **HIGH — Actor context in dedup check:** `check-duplicate` needs `submission_id` (target employee), not `current_user.employee_id`, because admin/HR can upload on behalf of others.

5. **MEDIUM — Original file selection nondeterminism:** `_check_duplicate()` returns first match with no ordering. Need canonical rule (oldest `created_at`).

6. **MEDIUM — Badge count drift:** `get_pending_count()` should also run lazy expiry, not just `list_requests()`.

### Agreed Strengths
- Clean separation of concerns matching existing project patterns
- Good reuse of existing contribution machinery (ProjectContributor, owner_contribution_pct)
- Web Crypto API choice for zero-dependency frontend hashing
- Lazy expiry is right complexity level
- Dedicated sharing page with tabs matches workflow well

### Divergent Views
*(N/A — single reviewer)*
