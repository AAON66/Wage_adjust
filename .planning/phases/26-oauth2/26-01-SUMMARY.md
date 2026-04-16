---
phase: 26-oauth2
plan: 01
title: "飞书 OAuth 数据层与配置基础"
subsystem: auth
tags: [feishu, oauth, model, config, migration]
dependency_graph:
  requires: []
  provides: [feishu_open_id_field, feishu_oauth_config, feishu_callback_schema]
  affects: [backend/app/models/user.py, backend/app/core/config.py, backend/app/schemas/user.py]
tech_stack:
  added: []
  patterns: [batch_alter_table_for_sqlite]
key_files:
  created:
    - alembic/versions/7de9baee16f0_merge_heads_before_feishu.py
    - alembic/versions/a26_01_add_feishu_open_id_to_users.py
  modified:
    - backend/app/models/user.py
    - backend/app/core/config.py
    - backend/app/schemas/user.py
    - .env.example
decisions:
  - "Merged two existing alembic heads before creating feishu migration"
  - "Used batch_alter_table for SQLite compatibility (consistent with project convention)"
metrics:
  duration: "2m 37s"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 26 Plan 01: 飞书 OAuth 数据层与配置基础 Summary

User 模型新增 feishu_open_id 唯一索引字段，Settings 新增 3 个飞书 OAuth 配置项（app_id/app_secret/redirect_uri），Schema 层扩展 UserRead 和新增 FeishuCallbackRequest，Alembic 迁移成功在 users 表添加列。

## What Was Done

### Task 1: User 模型 + Settings 配置 + Schema 扩展 (0e1a267)

- **User 模型**: 添加 `feishu_open_id: Mapped[str | None]` 字段，nullable=True, unique=True, index=True
- **Settings**: 在 `feishu_encryption_key` 之后添加 `feishu_app_id`、`feishu_app_secret`、`feishu_redirect_uri` 三个配置项
- **UserRead schema**: 添加 `feishu_open_id: Optional[str] = None` 字段
- **FeishuCallbackRequest schema**: 新增，包含 `code`（1-512字符）和 `state`（1-128字符）字段
- **.env.example**: 添加飞书 OAuth 配置区块

### Task 2: Alembic 迁移脚本 (08922c4)

- 合并两个已有的 alembic head（`e23_non_statutory_leaves` 和 `f21a0b8c9d1e`）为单一 head
- 创建 `a26_01_feishu_open_id` 迁移：在 users 表添加 feishu_open_id 列（nullable, unique constraint, index）
- 使用 `batch_alter_table` 确保 SQLite 兼容性
- 迁移执行验证通过：列已存在于数据库

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Alembic multiple heads 合并**
- **Found during:** Task 2
- **Issue:** Alembic 版本目录存在两个 head (`e23_non_statutory_leaves`, `f21a0b8c9d1e`)，无法直接 autogenerate 或创建新迁移
- **Fix:** 先创建 merge 迁移 (`7de9baee16f0`) 合并两个 head，再基于 merge head 创建 feishu_open_id 迁移
- **Files created:** `alembic/versions/7de9baee16f0_merge_heads_before_feishu.py`
- **Commit:** 08922c4

**2. [Rule 3 - Blocking] .env.example 中缺少 FEISHU_ENCRYPTION_KEY**
- **Found during:** Task 1
- **Issue:** `.env.example` 中没有 `FEISHU_ENCRYPTION_KEY` 行（虽然 config.py 有该字段），无法在其后追加
- **Fix:** 添加完整的飞书配置区块，包含 `FEISHU_ENCRYPTION_KEY` 及三个新配置项
- **Files modified:** `.env.example`
- **Commit:** 0e1a267

## Verification

- Model import 验证通过：`User.feishu_open_id` 属性存在
- Config 验证通过：`Settings()` 包含 `feishu_app_id`、`feishu_app_secret`、`feishu_redirect_uri`
- Schema 验证通过：`UserRead` 和 `FeishuCallbackRequest` 可正常导入
- Alembic 迁移验证通过：`alembic upgrade head` 成功执行，users 表包含 `feishu_open_id` 列
- 现有测试：1 个预先存在的测试失败（`test_approval_can_be_deferred_with_time_or_target_score`），与本次更改无关

## Self-Check: PASSED
