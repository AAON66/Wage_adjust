# Deferred Items — Phase 03

## Pre-existing test failure (out of scope for Plan 03)

**Test:** `backend/tests/test_services/test_approval_service.py::test_submit_decide_and_list_workflow`

**Issue:** `seed_workflow_entities` does not bind the HRBP user to the 'Engineering' department. `list_approvals` calls `can_access_employee` which filters out records when the HRBP has no department binding. The test asserts `len(my_items) == 1` but gets 0.

**Confirmed pre-existing:** Verified via `git stash` — test was failing before Plan 03 changes.

**Fix:** Add `_bind_user_to_department(session_factory, user_id=ids['hrbp_id'], department_name='Engineering')` call in `test_submit_decide_and_list_workflow` after `seed_workflow_entities`, following the same pattern used in `test_concurrent_decide_rejected` and other tests in the same file.

**Scope:** Phase 04 or a dedicated test-fixture cleanup task.
