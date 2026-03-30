---
phase: 09-feishu-attendance-integration
plan: 01
subsystem: feishu-attendance-data-layer
tags: [orm, schema, migration, tdd-red, encryption]
dependency_graph:
  requires: []
  provides: [feishu-config-model, attendance-record-model, feishu-sync-log-model, feishu-schemas, attendance-schemas, red-test-stubs]
  affects: [09-02, 09-03]
tech_stack:
  added: [APScheduler-3.11.2, cryptography]
  patterns: [AES-256-GCM-encryption, xfail-red-stubs]
key_files:
  created:
    - backend/app/models/feishu_config.py
    - backend/app/models/attendance_record.py
    - backend/app/models/feishu_sync_log.py
    - backend/app/core/encryption.py
    - backend/app/schemas/feishu.py
    - backend/app/schemas/attendance.py
    - backend/tests/test_services/test_feishu_service.py
    - backend/tests/test_services/test_feishu_config.py
    - backend/tests/test_services/test_attendance_service.py
    - backend/tests/test_api/test_attendance.py
    - backend/tests/test_services/test_feishu_scheduler.py
    - backend/tests/fixtures/feishu_fixtures.py
    - alembic/versions/a1b2c3d4e5f6_add_feishu_attendance_tables.py
  modified:
    - backend/app/core/config.py
    - backend/app/main.py
    - requirements.txt
decisions:
  - AES-256-GCM encryption module created (no existing encrypt_national_id found); encrypt_value/decrypt_value with SHA-256 key derivation
  - Startup validation for feishu_encryption_key added in main.py lifespan (warns in dev, raises in production)
metrics:
  duration: 4min
  completed: "2026-03-30T06:11:00Z"
  tasks: 2
  files: 16
---

# Phase 09 Plan 01: Feishu Attendance Data Layer Summary

3 ORM models (FeishuConfig, AttendanceRecord, FeishuSyncLog) with Alembic migration, AES-256-GCM encryption for app_secret, Pydantic schemas for API contract, and 20 RED xfail test stubs covering all 7 ATT requirements.

## What Was Done

### Task 1: ORM Models + Alembic Migration + Config Update
- Created `FeishuConfig` model with encrypted app_secret storage via AES-256-GCM, sync_timezone field (Review #2), and field_mapping JSON column
- Created `AttendanceRecord` model with employee_id+period unique constraint, feishu_record_id unique constraint, data_as_of timestamp (Review #5), and source_modified_at for incremental sync
- Created `FeishuSyncLog` model with unmatched_count and unmatched_employee_nos tracking (Review #9)
- Created `backend/app/core/encryption.py` with encrypt_value/decrypt_value using AES-256-GCM (no pre-existing encryption module found)
- Added `feishu_encryption_key` to Settings with startup validation in main.py lifespan
- Created Alembic migration `a1b2c3d4e5f6` for all three tables
- Added APScheduler==3.11.2 and cryptography to requirements.txt

### Task 2: Pydantic Schemas + RED Test Stubs
- Created `backend/app/schemas/feishu.py` with FeishuConfigCreate, FeishuConfigRead (masked secret), FeishuConfigUpdate (None preserves secret per Review #10), SyncTriggerRequest/Response, SyncLogRead, FeishuConfigExistsResponse
- Created `backend/app/schemas/attendance.py` with AttendanceRecordRead and AttendanceSummaryRead (both include data_as_of)
- Created 6 RED test files with 20 xfail tests covering ATT-01 through ATT-07, plus review concerns #2, #9, #10
- Created feishu_fixtures.py with mock API responses (pagination, error, token)

## Review Concerns Addressed
- **Review #2**: sync_timezone field on FeishuConfig + scheduler timezone test stub
- **Review #5**: data_as_of timestamp on AttendanceRecord + schemas
- **Review #6**: feishu_encryption_key in config.py with fail-fast startup validation
- **Review #9**: unmatched_count + unmatched_employee_nos on FeishuSyncLog
- **Review #10**: FeishuConfigUpdate.app_secret accepts None to preserve current value

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created encryption module from scratch**
- **Found during:** Task 1
- **Issue:** Plan referenced `encrypt_national_id`/`decrypt_national_id` from `backend/app/core/encryption.py` but this module did not exist in the codebase
- **Fix:** Created `encryption.py` with `encrypt_value`/`decrypt_value` using AES-256-GCM via cryptography library; added `cryptography` to requirements.txt
- **Files created:** backend/app/core/encryption.py
- **Commit:** ade6386

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | ade6386 | feat(09-01): ORM models, Alembic migration, encryption module, config update |
| 2 | 3f58053 | feat(09-01): Pydantic schemas and RED test stubs for feishu attendance |

## Known Stubs

None -- all created files contain complete implementations for this plan's scope. RED test stubs are intentional (marked xfail) and will be fulfilled by Plan 02.

## Self-Check: PASSED

All 13 created files verified present. Both commit hashes (ade6386, 3f58053) confirmed in git log.
