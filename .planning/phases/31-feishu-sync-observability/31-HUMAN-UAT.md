---
status: partial
phase: 31-feishu-sync-observability
source: [31-VERIFICATION.md, 31-04-PLAN.md Task 3]
started: 2026-04-21T06:38:02Z
updated: 2026-04-21T06:38:02Z
---

## Current Test

[awaiting human testing — start with Checklist A]

## Tests

### 1. Checklist A — 路由与菜单角色守门
expected: admin/hrbp 可见「飞书同步日志」菜单项且能访问 /feishu/sync-logs；manager/employee 角色无菜单项，直接输入 URL 被 ProtectedRoute 重定向到 /dashboard
result: [pending]
how_to_verify: 用 4 个不同角色账号依次登录（admin/hrbp/manager/employee），侧边栏查看菜单是否出现；直接输入 URL 验证 manager/employee 被守门

### 2. Checklist B — Tab 顺序与查询参数
expected: 6 个 Tab 顺序为「全部 · 考勤 · 绩效 · 薪调 · 入职信息 · 社保假勤」；点击每个 Tab 都触发一次 `GET /api/v1/feishu/sync-logs?sync_type=xxx` 请求（「全部」Tab 不带 sync_type）
result: [pending]
how_to_verify: 打开 Chrome DevTools Network 面板；依次点击 6 个 Tab；确认每次请求的 URL 参数

### 3. Checklist C — 五色 Badge Cluster
expected: 每行 5 个 Badge 颜色顺序为 绿(success) / 蓝(updated) / 橙(unmatched) / 紫(mapping_failed) / 红(failed)；数值 0 的 Badge 灰度 muted 渲染；紫色色值 #722ED1（对比度 7.13:1）
result: [pending]
how_to_verify: 触发多种失败模式（工号不匹配 / 字段映射失败）后查看对应行的 Badge 颜色；取色器验证紫色

### 4. Checklist D — 4 色 Status Badge + Running Spinner
expected: status 颜色映射 running(灰+旋转) / success(绿) / partial(橙) / failed(红)；running 状态带 2px 旋转 spinner
result: [pending]
how_to_verify: 手动触发一次同步观察 running→success 状态切换；触发失败同步观察 failed 样式

### 5. Checklist E — CSV 下载（启用/禁用/tooltip/权限）
expected: `unmatched>0` 时按钮启用，点击下载 CSV 文件（文件名 `unmatched_{log_id}.csv`，≤20 行，UTF-8 BOM）；`unmatched=0` 时按钮禁用并显示「此次同步无未匹配工号」tooltip；employee 角色点击返回 403；不存在的 log_id 返回 404
result: [pending]
how_to_verify: admin 账号下载 CSV 用 Excel 打开看中文；禁用场景 hover 看 tooltip；employee 账号点击验证 403

### 6. Checklist F — 详情抽屉（a11y + 交互）
expected: 点击「查看详情」从右侧滑入 480px 宽度抽屉；`role='dialog'` + `aria-modal='true'`；Esc 键关闭；点击遮罩关闭；显示完整未匹配工号列表（不截断为 20）
result: [pending]
how_to_verify: 用 DevTools Elements 验证 role/aria 属性；键盘 Esc 测试；鼠标点击遮罩测试

### 7. Checklist G — SC4 双触发观测
expected: 同一 sync_type 在锁持有期间触发第二次返回 409 且不写 FeishuSyncLog（数据库仅 1 条 running log）；锁释放后第二次触发正常写入，数据库共 2 条独立 log；两次执行分别在 UI 显示
result: [pending]
how_to_verify: 点击「绩效同步」触发，立刻再点一次同按钮观察 409 toast；等 15 秒后再点，观察第 2 条日志出现

### 8. Checklist H — 空态/加载态/错误态
expected: 新 sync_type 无数据时显示「暂无同步日志」+ 「前往飞书配置」CTA；列表加载中显示 skeleton 或 loading indicator；API 500 时显示「加载失败，请刷新重试，或联系管理员」+ 重试按钮
result: [pending]
how_to_verify: 切到「社保假勤」Tab（通常无数据）看空态；节流网络看 loading；手动 kill backend 触发 500 看错误态

### 9. Checklist I — UI-SPEC 6 维度整体签字
expected: Copywriting/Visuals/Color/Typography/Spacing/Registry Safety 六维度全部符合 UI-SPEC；归档 ≥5 张截图（列表/抽屉/CSV/空态/错误态）
result: [pending]
how_to_verify: 对照 31-UI-SPEC.md 逐项签字；使用「全屏截图」工具归档至 `.planning/phases/31-feishu-sync-observability/uat-screenshots/`

## Summary

total: 9
passed: 0
issues: 0
pending: 9
skipped: 0
blocked: 0

## Gaps

[awaiting test execution — gaps will be filled as checklists fail]
