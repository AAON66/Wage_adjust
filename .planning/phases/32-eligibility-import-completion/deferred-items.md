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
