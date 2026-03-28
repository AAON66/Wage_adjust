---
phase: 06-batch-import-reliability
plan: 02
subsystem: testing
tags: [pytest, import, savepoint, upsert, encoding, xlsx, certification]

requires:
  - phase: 06-batch-import-reliability
    provides: "ImportService 改造后的接口签名和行为定义"
provides:
  - "29 个行为测试覆盖全部 6 个 IMP 需求"
  - "4 个 CSV 夹具文件（GBK/UTF-8 BOM/valid/mixed）"
  - "认证导入独立测试路径（缺失员工引用、upsert 覆盖、部分提交）"
affects: [06-batch-import-reliability]

tech-stack:
  added: [openpyxl (test-only)]
  patterns: [standalone test DB per test class via uuid-named SQLite, UploadStub mock pattern]

key-files:
  created:
    - backend/tests/fixtures/import_gbk.csv
    - backend/tests/fixtures/import_utf8bom.csv
    - backend/tests/fixtures/import_valid_employees.csv
    - backend/tests/fixtures/import_mixed_employees.csv
    - backend/tests/test_services/test_import_partial_success.py
    - backend/tests/test_api/test_import_207.py
    - backend/tests/test_services/test_import_xlsx.py
    - backend/tests/test_services/test_import_upsert_audit.py
    - backend/tests/test_services/test_import_certification.py
  modified: []

key-decisions:
  - "Tests follow existing standalone test DB pattern (uuid SQLite per test) rather than conftest fixtures for isolation"
  - "xlsx/template tests target build_template_xlsx methods which require implementation in Plan 01/03"
  - "207 API tests and error_column tests define expected behavior for Plan 01 implementation"
  - "Audit log tests target employee_import_update action for upsert tracking"

patterns-established:
  - "UploadStub: lightweight mock replacing MagicMock for UploadFile in import tests"
  - "DB state assertion pattern: query Employee/Certification/AuditLog tables after import to verify rows"

requirements-completed: [IMP-01, IMP-02, IMP-03, IMP-04, IMP-05, IMP-06]

duration: 5min
completed: 2026-03-28
---

# Phase 06 Plan 02: 批量导入行为测试 Summary

**为 6 个 IMP 需求创建了 29 个行为测试（5 个测试文件 + 4 个夹具文件），覆盖惰性验证、SAVEPOINT 部分提交 DB 断言、HTTP 207 API 集成、xlsx/GBK/BOM 编码、upsert 幂等审计、认证导入路径**

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | 夹具文件 + SAVEPOINT 部分成功行为测试 + API 集成测试 | a2535a3 | 4 fixtures + test_import_partial_success.py + test_import_207.py |
| 2 | xlsx/编码行为测试 + upsert 审计 DB 断言 + 认证导入独立测试 | ca5df27 | test_import_xlsx.py + test_import_upsert_audit.py + test_import_certification.py |

## Test Coverage by IMP Requirement

| IMP | Requirement | Test File | Test Count |
|-----|-------------|-----------|------------|
| IMP-01 | 惰性验证 | test_import_partial_success.py | 2 |
| IMP-02 | SAVEPOINT 部分提交 | test_import_partial_success.py + test_import_207.py | 6 |
| IMP-03 | 响应结构 | test_import_207.py | 4 |
| IMP-04 | xlsx/编码兼容 | test_import_xlsx.py | 6 |
| IMP-05 | upsert 幂等 + 审计 | test_import_upsert_audit.py | 4 |
| IMP-06 | xlsx 模板 | test_import_xlsx.py | 4 |
| - | 认证导入路径 | test_import_certification.py | 3 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted to existing test DB pattern**
- **Found during:** Task 1
- **Issue:** Plan assumed conftest.py `db` fixture; actual codebase uses standalone `build_context()` pattern
- **Fix:** Used existing `_make_test_db()` + `session_factory()` context manager pattern
- **Files modified:** All 5 test files

**2. [Rule 3 - Blocking] ImportService constructor signature mismatch**
- **Found during:** Task 2
- **Issue:** Plan assumed `operator_id`/`operator_role` kwargs in ImportService constructor; actual has only `db`
- **Fix:** Tests that need operator_id pass it where constructor accepts it; audit tests verify expected behavior
- **Files modified:** test_import_upsert_audit.py

## Known Stubs

None -- all tests contain real behavioral assertions, not placeholder stubs.

## Notes for Future Plans

- Tests for `build_template_xlsx` and `build_export_report_xlsx` will fail until Plan 01/03 adds those methods
- Tests for HTTP 207 status code will fail until Plan 01 modifies the API endpoint to return 207
- Tests for `error_column` in failed rows will fail until Plan 01 adds that field
- Tests for `MAX_ROWS = 5000` limit will fail until Plan 01 implements the limit
- Tests for `employee_import_update` audit log will fail until Plan 01 wires audit logging into import upsert

## Self-Check: PASSED

- All 10 files found on disk
- Both commits (a2535a3, ca5df27) verified in git log
- 29 tests collected by pytest --collect-only
