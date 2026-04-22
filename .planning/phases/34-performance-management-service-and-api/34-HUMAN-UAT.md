---
status: partial
phase: 34-performance-management-service-and-api
source: [34-VERIFICATION.md]
started: 2026-04-22T08:30:00Z
updated: 2026-04-22T08:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. admin 登录 → /performance 渲染 3 section + ECharts 视觉
expected: admin 登录后，菜单出现「绩效管理」入口；点击进入 `/performance`，页面顶部显示「档次分布视图」section（含 ECharts 3 段水平堆叠条 + 三档计数 chip + 重算按钮带 computed_at 时间戳），中部「绩效记录导入」section（复用 ExcelImportPanel），底部「绩效记录列表」表格（7 列 + 年份/部门 filter + 分页器）；如该年度无快照，分布视图显示「{year} 年尚无档次快照」+「立即生成档次」CTA
result: [pending]

### 2. hrbp 登录 → 菜单可见 + 进入页面
expected: hrbp 角色登录后，左侧导航菜单包含「绩效管理」入口；点击可正常进入 `/performance` 页面，渲染同 admin
result: [pending]

### 3. employee 登录 → 菜单不可见 + URL 直访 403 兜底
expected: employee 角色登录后，左侧导航菜单**不显示**「绩效管理」；手动在地址栏输入 `/performance`，前端 ProtectedRoute 拦截或后端 `require_roles(['admin', 'hrbp'])` 返回 403（双层防御任一生效即可）
result: [pending]

### 4. 端到端 Excel 导入闭环 + W-1 5 状态 toast 文案
expected: admin 上传 perf_grades Excel → 看到 Preview + diff → 确认 → 收到 toast 显示 5 状态之一（completed「导入完成（X 条），档次已刷新」/ in_progress「导入完成（X 条），档次正在后台重算…」/ busy_skipped「导入完成（X 条），系统繁忙后续自动重算」/ failed「导入完成（X 条）但档次重算失败，请手动点击『重算档次』」/ skipped）；档次分布视图刷新后立即反映新数据
result: [pending]

### 5. 手动「重算档次」按钮 loading 动画 + zh-CN 时间戳
expected: 在档次分布视图右上角点击「重算档次」按钮 → 按钮 disabled + 旋转图标 (RefreshIcon) + aria-busy=true → 重算完成后显示 toast「档次重算完成（共 N 人）」+ 按钮恢复 + 「最近重算：YYYY 年 M 月 D 日 HH:MM」zh-CN locale 时间戳更新
result: [pending]

### 6. distribution_warning 偏离 ±5% 时黄色 alert 横幅
expected: 当某年度档次实际分布偏离 20/70/10 超过 ±5% 时（例 1 档实际 25.5%），档次分布视图顶部出现黄色 warning 横幅（`role="alert"`），文本含具体百分比「档次分布偏离 20/70/10 超过 ±5%（实际 X%/Y%/Z%）」
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
