## Pre-existing failures (not caused by 31-02):

### feishu_oauth_service.py:198 _lookup_employee signature mismatch
9 failures in backend/tests/test_services/test_feishu_oauth_service.py due to
`FeishuService._lookup_employee(emp_map, feishu_employee_no)` missing the required
`emp_no` positional argument. This is a pre-existing call-site bug unrelated to
Phase 31 Plan 02 — confirmed via `git stash` baseline test.

Scope: Phase 31 Plan 02 only refactors the 5 sync methods. OAuth employee binding
is out of scope. Deferred for future fix.

