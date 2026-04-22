---
status: resolved
phase: 34-performance-management-service-and-api
source: [34-VERIFICATION.md]
started: 2026-04-22T08:30:00Z
updated: 2026-04-22T09:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. admin 登录 → /performance 渲染 3 section + ECharts 视觉
expected: admin 登录后，菜单出现「绩效管理」入口；点击进入 `/performance`，页面顶部显示「档次分布视图」section（含 ECharts 3 段水平堆叠条 + 三档计数 chip + 重算按钮带 computed_at 时间戳），中部「绩效记录导入」section（复用 ExcelImportPanel），底部「绩效记录列表」表格（7 列 + 年份/部门 filter + 分页器）；如该年度无快照，分布视图显示「{year} 年尚无档次快照」+「立即生成档次」CTA
result: passed (Playwright 自动化, 2026-04-22)

### 2. hrbp 登录 → 菜单可见 + 进入页面
expected: hrbp 角色登录后，左侧导航菜单包含「绩效管理」入口；点击可正常进入 `/performance` 页面，渲染同 admin
result: passed (Playwright 自动化, 2026-04-22)

### 3. employee 登录 → 菜单不可见 + URL 直访 403 兜底
expected: employee 角色登录后，左侧导航菜单**不显示**「绩效管理」；手动在地址栏输入 `/performance`，前端 ProtectedRoute 拦截或后端 `require_roles(['admin', 'hrbp'])` 返回 403（双层防御任一生效即可）
result: passed (Playwright 自动化, 2026-04-22)

### 4. 端到端 Excel 导入闭环 + W-1 5 状态 toast 文案
expected: admin 上传 perf_grades Excel → 看到 Preview + diff → 确认 → 收到 toast 显示 5 状态之一（completed「导入完成（X 条），档次已刷新」/ in_progress「导入完成（X 条），档次正在后台重算…」/ busy_skipped「导入完成（X 条），系统繁忙后续自动重算」/ failed「导入完成（X 条）但档次重算失败，请手动点击『重算档次』」/ skipped）；档次分布视图刷新后立即反映新数据
result: passed (Playwright 自动化, 2026-04-22)

### 5. 手动「重算档次」按钮 loading 动画 + zh-CN 时间戳
expected: 在档次分布视图右上角点击「重算档次」按钮 → 按钮 disabled + 旋转图标 (RefreshIcon) + aria-busy=true → 重算完成后显示 toast「档次重算完成（共 N 人）」+ 按钮恢复 + 「最近重算：YYYY 年 M 月 D 日 HH:MM」zh-CN locale 时间戳更新
result: passed (Playwright 自动化, 2026-04-22)

### 6. distribution_warning 偏离 ±5% 时黄色 alert 横幅
expected: 当某年度档次实际分布偏离 20/70/10 超过 ±5% 时（例 1 档实际 25.5%），档次分布视图顶部出现黄色 warning 横幅（`role="alert"`），文本含具体百分比「档次分布偏离 20/70/10 超过 ±5%（实际 X%/Y%/Z%）」
result: passed (Playwright 自动化, 2026-04-22)

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### Gap-1: recompute_tiers idempotent 调用时 computed_at 不刷新（Item 5 minor finding, RESOLVED）

**Status:** resolved (2026-04-22)
**Severity:** minor
**Discovered during:** Item 5 (manual 重算档次 button UAT)

**Symptom:** HR 在 distribution view 顶部点击「重算档次」按钮 → 收到 alert 成功 toast →但「最近重算：YYYY 年 M 月 D 日 HH:MM」时间戳显示的是数据最后变化时间，不是按钮最后点击时间。

**Root cause:** SQLAlchemy `UpdatedAtMixin.onupdate` 仅在字段值发生变化时触发 SQL UPDATE。当业务数据完全不变时（idempotent recompute，例如 414 条 grade=B records 重复重算），所有 snapshot 字段值与原值相同 → ORM 不发 UPDATE 语句 → `updated_at` 列保持原值 → UI 时间戳不能反映最新一次按钮点击。

**Fix:** `backend/app/services/performance_service.py` line 297-299 — `recompute_tiers()` 在 commit 前显式赋值 `snapshot.updated_at = datetime.now(timezone.utc)`，强制刷新时间戳。

**Regression test:** `backend/tests/test_services/test_performance_service.py::test_recompute_tiers_idempotent_call_still_refreshes_updated_at` — 调用 recompute_tiers 两次（业务数据完全相同），断言 second_updated_at > first_updated_at。

**Verification:** 21 PerformanceService tests pass（+1 vs 之前 20）；120 Phase 33+34 tests 全绿 0 回归。

