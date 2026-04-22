# Phase 32 Deferred Items

记录在 Phase 32 执行期间发现的 out-of-scope 问题，留给后续 plan / phase 处理。

---

## 32-01 Discovery — Pre-existing Test Failures (不在 32-01 范围)

### 1. `test_eligibility_batch.py::test_filter_before_paginate_status_filter` & `test_filter_before_paginate_page_2`

- **状态**: 在 Phase 32 改动**之前**就已 fail（用 `git checkout 80aba34 -- import_job.py salary_adjustment_record.py` 还原前的代码状态后，测试仍然 fail，证实与本期 schema 改动无关）
- **症状**: `assert total == 3, got total=2`（status_filter='ineligible' 时返回的 total 数错位）
- **可能原因**: EligibilityService.check_employees_batch 的 filter-before-paginate 逻辑漂移；与 `attendance_records` / `non_statutory_leaves` 双数据源的迁移有关，与 SalaryAdjustmentRecord UC 无关
- **建议**: 在后续 plan（如 35 员工端自助体验）启动前，由 owner 单独 spike 修复
- **不在 32-01 修复**：scope boundary（不是本 task 改动直接引起）

### 2. `alembic check` Pre-existing Drift

- **状态**: 在 Phase 32 之前就有的 server_default drift 警告（feishu_*/uploaded_files/sharing_requests/certifications/users.must_change_password 等）
- **影响**: Plan 32-01 acceptance criterion `alembic check 不报"pending model changes"警告` 在 pre-existing 状态下不可能满足
- **Phase 32 字段是否在警告中**: 经过 `grep -E "overwrite_mode|actor_id|uq_salary_adj|import_job|32_01"` 验证，**没有**任何 Phase 32 字段被 alembic check 标记
- **建议**: 单独开 chore plan 修复 model server_default 与 Alembic 历史迁移的对齐问题
- **不在 32-01 修复**：scope boundary，pre-existing drift

---

## 32-02 Discovery — Additional Pre-existing Failures（不在 32-02 范围）

### 3. `test_approval_service.py::test_submit_decide_and_list_workflow`

- **状态**: 用 `git stash` 还原本 plan 改动后仍然 fail，证实与 32-02 无关
- **症状**: `assert len(my_items) == 1, got 0`
- **建议**: 单独 spike 修复
- **不在 32-02 修复**：scope boundary

### 4. `test_dashboard_service.py::test_dashboard_service_returns_overview_distribution_and_heatmap`

- **状态**: pre-existing（stash 验证）
- **不在 32-02 修复**：scope boundary

### 5. `test_integration_service.py::test_integration_service_returns_public_payload_sources`

- **状态**: pre-existing（stash 验证）
- **不在 32-02 修复**：scope boundary

### 6. `test_api/test_import_207.py` 全部 7 个测试 + `test_import_api.py` 2 个测试

- **状态**: pre-existing（stash 验证 — 9 个失败均出现在 32-02 改动前）
- **症状**: HTTP 207 partial success 行为与某些 API 响应字段未 match
- **可能原因**: 与 wave 0 ImportJob schema 扩展（新增 overwrite_mode/actor_id NOT NULL 列）相关，但本 plan 已沿用 32-01 的迁移基线，未引入新破坏
- **建议**: 由 32-04（API 端到端）plan owner 在补 confirm/cancel 接口时一并审视
- **不在 32-02 修复**：scope boundary（API 层在 32-04 收口）
