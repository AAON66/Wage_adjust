---
phase: 09-feishu-attendance-integration
plan: 02
subsystem: feishu-service-api-scheduler
tags: [feishu-api, attendance-service, apscheduler, rest-api, retry]
dependency_graph:
  requires: [09-01]
  provides: [feishu-service, attendance-service, feishu-scheduler, feishu-api-endpoints, attendance-api-endpoints]
  affects: [09-03]
tech_stack:
  added: []
  patterns: [transactional-upsert, background-thread-sync, overlap-window-incremental, retry-with-escalating-delays]
key_files:
  created:
    - backend/app/services/feishu_service.py
    - backend/app/services/attendance_service.py
    - backend/app/scheduler/__init__.py
    - backend/app/scheduler/feishu_scheduler.py
    - backend/app/api/v1/feishu.py
    - backend/app/api/v1/attendance.py
  modified:
    - backend/app/main.py
    - backend/app/api/v1/router.py
    - backend/app/core/encryption.py
decisions:
  - "Background thread for manual sync trigger (not blocking request)"
  - "Sync trigger creates initial running log then delegates to background thread"
  - "EncryptedString TypeDecorator restored to encryption.py (lost during 09-01 merge)"
metrics:
  duration: 5min
  completed: "2026-03-30T06:19:26Z"
---

# Phase 09 Plan 02: Service Layer + API + Scheduler Summary

FeishuService with token caching, paginated bitable fetch, transactional upsert, and retry [5,15,45]s; AttendanceService with period-aware queries; APScheduler CronTrigger with timezone; 7 feishu + 2 attendance REST endpoints with role-based access.

## What Was Built

### FeishuService (backend/app/services/feishu_service.py)
- **Token management**: `_ensure_token()` caches tenant_access_token with 5-minute refresh buffer
- **Paginated fetch**: `_fetch_all_records()` handles page_token loop (page_size=500), filter fallback to app-layer filtering
- **Field mapping**: `_map_fields()` with type coercion (float for rates, int for counts)
- **Transactional upsert**: `sync_attendance()` does bulk employee lookup, per-record upsert by employee_id+period, single `db.commit()` for all records + log status
- **Retry wrapper**: `sync_with_retry()` with escalating delays [5, 15, 45] seconds, final failure logged
- **Config CRUD**: create/update with encrypted app_secret, field_mapping serialization
- **Concurrent guard**: `is_sync_running()` checks for running sync logs

### AttendanceService (backend/app/services/attendance_service.py)
- **Single employee query**: `get_employee_attendance()` with optional period param, defaults to latest period (ORDER BY period DESC)
- **Paginated list**: `list_attendance()` with latest-period subquery, search by employee_no/name, department filter

### APScheduler (backend/app/scheduler/feishu_scheduler.py)
- CronTrigger with explicit timezone parameter from config
- `start_scheduler()`, `stop_scheduler()`, `reload_scheduler()` lifecycle
- `run_incremental_sync()` job uses independent SessionLocal (not shared request session)

### API Endpoints
**Feishu (7 routes):**
- GET /feishu/config (admin+hrbp)
- GET /feishu/config-exists (admin+hrbp)
- POST /feishu/config (admin only)
- PUT /feishu/config/{id} (admin only)
- POST /feishu/sync (admin+hrbp, mode=full|incremental, 409 on concurrent)
- GET /feishu/sync-logs (admin+hrbp)
- GET /feishu/sync-status (admin+hrbp)

**Attendance (2 routes):**
- GET /attendance/ (admin+hrbp, paginated with search/department)
- GET /attendance/{employee_id} (admin+hrbp+manager, period param, returns 200+null if no data)

### main.py Integration
- Scheduler starts in lifespan if active FeishuConfig exists
- Scheduler stops on shutdown
- Graceful fallback if scheduler fails to start

## Review Fixes Applied

| Review | Fix |
|--------|-----|
| #2 | Scheduler uses configured timezone explicitly in CronTrigger |
| #3 | Single transaction for all upserts + log status update |
| #4 | Attendance list endpoint restricted to admin+hrbp |
| #5 | data_as_of derived from source_modified_at when available |
| #7 | Period parameter on single-employee endpoint, defaults to latest |
| #8 | Full pagination with page_token loop |
| #9 | Unmatched employee_nos tracked (max 100) in sync log |
| #10 | app_secret update: None/empty preserves existing encrypted value |
| #11 | Sync endpoint accepts mode parameter (full/incremental) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored EncryptedString TypeDecorator in encryption.py**
- **Found during:** Task 1 verification
- **Issue:** The 09-01 merge overwrote encryption.py and lost the EncryptedString class, encrypt_national_id, decrypt_national_id, and mask_national_id functions. Employee and User models import EncryptedString, making all service imports fail.
- **Fix:** Merged both the new passphrase-based functions (encrypt_value/decrypt_value) and the original raw-key-based functions + EncryptedString TypeDecorator into a single encryption.py
- **Files modified:** backend/app/core/encryption.py
- **Commit:** 14a704e

## Known Stubs

None - all services are fully wired with real logic.

## Verification

- Backend starts successfully: `uvicorn backend.app.main:app` runs without errors
- All services import cleanly
- Feishu routes: 7 endpoints registered
- Attendance routes: 2 endpoints registered
- Scheduler lifecycle integrated in lifespan
