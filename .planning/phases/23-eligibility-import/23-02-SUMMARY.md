---
phase: 23-eligibility-import
plan: 02
subsystem: eligibility-import-api
tags: [api, celery, feishu, pydantic, eligibility]
dependency_graph:
  requires: []
  provides: [eligibility-import-api, feishu-sync-task]
  affects: [router, celery-app]
tech_stack:
  added: []
  patterns: [celery-task-with-retry, feishu-url-parsing, role-gated-api]
key_files:
  created:
    - backend/app/schemas/eligibility_import.py
    - backend/app/api/v1/eligibility_import.py
    - backend/app/tasks/feishu_sync_tasks.py
  modified:
    - backend/app/api/v1/router.py
    - backend/app/celery_app.py
decisions:
  - URL parsing uses regex with feishu.cn domain restriction (T-23-09 mitigation)
  - parse-url endpoint is pure computation, no DB/FeishuService dependency needed
  - Lazy imports for FeishuService and import_tasks to support parallel wave execution
metrics:
  duration: 4m 11s
  completed: "2026-04-14T02:37:28Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase 23 Plan 02: Eligibility Import API Layer Summary

资格导入 API router 完整实现，包含 5 个端点（Excel 导入、URL 解析、字段获取、飞书同步、模板下载）+ Celery 异步任务 + Pydantic schema

## What Was Done

### Task 1: Pydantic Schema 定义
- 创建 `backend/app/schemas/eligibility_import.py`
- 定义 `ELIGIBILITY_IMPORT_TYPES` 常量（4 种资格数据类型）
- 定义请求/响应 schema: `FeishuSyncRequest`, `FeishuFieldsRequest`, `BitableParseRequest/Response`, `FeishuFieldInfo`, `FeishuFieldsResponse`, `EligibilityImportResult`
- **Commit:** d04da3b

### Task 2: API Router + Celery Task + Router 注册
- 创建 `backend/app/api/v1/eligibility_import.py`，5 个端点全部使用 `require_roles('admin', 'hrbp')` 权限控制
  - `POST /eligibility-import/excel` — Excel 文件导入，复用 `run_import_task.delay`
  - `POST /eligibility-import/feishu/parse-url` — 纯正则解析飞书多维表格 URL
  - `POST /eligibility-import/feishu/fields` — 调用 `FeishuService.list_bitable_fields`
  - `POST /eligibility-import/feishu/sync` — 触发 `feishu_sync_eligibility_task.delay`
  - `GET /eligibility-import/templates/{import_type}` — 下载 Excel/CSV 模板
- 创建 `backend/app/tasks/feishu_sync_tasks.py`，Celery task 支持 4 种 sync_type 调度
- 更新 `router.py` 注册新 router，更新 `celery_app.py` include 新 task 模块
- **Commit:** 8410230

## Decisions Made

1. **URL 解析采用纯正则** — `parse-url` 端点不需要 DB 或 FeishuService，直接用正则提取 app_token 和 table_id，同时限制 feishu.cn 域名（T-23-09 威胁缓解）
2. **延迟导入模式** — FeishuService、import_tasks 等在函数体内 import，避免 wave 1 并行执行时的循环依赖问题
3. **复用现有 import task** — Excel 导入端点直接复用 `run_import_task.delay`，不创建新 task

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

- Schema 导入验证通过
- Router 端点列表正确（5 个端点）
- Celery task 名称正确: `tasks.feishu_sync_eligibility`
- 416 个现有测试通过（7 个预存在失败均与本变更无关）

## Self-Check: PASSED

- [x] `backend/app/schemas/eligibility_import.py` exists
- [x] `backend/app/api/v1/eligibility_import.py` exists
- [x] `backend/app/tasks/feishu_sync_tasks.py` exists
- [x] Commit d04da3b found
- [x] Commit 8410230 found
