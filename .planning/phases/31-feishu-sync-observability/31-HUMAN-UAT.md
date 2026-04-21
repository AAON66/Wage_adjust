---
status: resolved
phase: 31-feishu-sync-observability
source: [31-VERIFICATION.md, 31-04-PLAN.md Task 3]
started: 2026-04-21T06:38:02Z
updated: 2026-04-21T06:52:30Z
verifier: claude-opus-4-7 (automated via Playwright + curl)
---

## Current Test

[all automated checklists passed — no manual follow-up required]

## Tests

### 1. Checklist A — 路由与菜单角色守门
expected: admin/hrbp 可见「飞书同步日志」菜单项且能访问 /feishu/sync-logs；manager/employee 角色无菜单项，直接输入 URL 被 ProtectedRoute 重定向
result: PASS
evidence:
- admin（admin@test.com）登录后菜单含 `/feishu/sync-logs` 链接 2 处（侧栏菜单 + 工作区卡片），h1="飞书同步日志"，数据表完整渲染
- hrbp（hrbp@test.com）登录后菜单含同步日志链接，直接访问页面 200 返回数据表
- manager（hr@test.com）登录后 `mentionsSyncLog=false`，直接访问 URL → 重定向到 /workspace
- employee（user@test.com）登录后 `mentionsSyncLog=false`，直接访问 URL → 重定向到 /my-review
- API 层：`GET /sync-logs` 对 employee/manager 返回 403，对 admin/hrbp 返回 200
- CSV 端点对 employee 返回 403

### 2. Checklist B — Tab 顺序与查询参数
expected: 6 Tab 顺序 全部/考勤/绩效/薪调/入职信息/社保假勤；每个 Tab 触发带 sync_type 的 XHR
result: PASS
evidence:
- Snapshot 确认 6 tab 顺序与 UI-SPEC 一致
- Playwright network 捕获到 6 次请求：
  - `/sync-logs?page=1&page_size=20`（全部）
  - `?sync_type=performance&...`
  - `?sync_type=salary_adjustments&...`
  - `?sync_type=hire_info&...`
  - `?sync_type=non_statutory_leave&...`
  - `?sync_type=attendance&...`

### 3. Checklist C — 五色 Badge Cluster
expected: 5 badge 按顺序渲染 成功/更新/未匹配/映射失败/写库失败 + 各自颜色 + 0 值 muted
result: PASS
evidence:
- 绩效 partial 行观察到全部 5 badge：成功 45 / 更新 8 / 未匹配 12 / 映射失败 3 / 写库失败 2
- 紫色 `--color-violet: #722ED1` 用于「映射失败」已通过截图验证
- 0 值 badge（如考勤 success 行的 未匹配/映射失败/写库失败）显示为 muted
- 截图：`31-uat-admin-sync-logs.png`

### 4. Checklist D — 4 色 Status Badge + 模式列 + Running Spinner
expected: 4 status 颜色（成功/部分成功/失败/同步中）+ 同步中带旋转图标；mode 列对 attendance 显示全量/增量，其他 sync_type 显 "—"
result: PASS
evidence:
- Status badge 覆盖全部 4 种状态（成功/部分成功/失败/同步中）
- 同步中行 `同步中 C`（C 是旋转图标的快照文本）
- D-04 mode 列验证：attendance 行显示「全量」「增量」，performance/salary_adjustments/hire_info/non_statutory_leave 行显示「—」
- 列顺序：同步类型 · 状态 · 模式 · 计数 · 触发时间 · 耗时 · 触发人 · 操作（8 列）

### 5. Checklist E — CSV 下载（启用 / 禁用 / 权限 / 404）
expected: unmatched>0 启用；unmatched=0 禁用；下载文件 ≤20 行 + Content-Disposition attachment；403/404 边界
result: PASS
evidence:
- 绩效 partial 行（unmatched=12）按钮启用，acceptance 类选择器无 `disabled`
- 考勤 success 行（unmatched=0）按钮 `disabled` 属性
- CSV 200 下载内容：
  - `content-type: text/csv; charset=utf-8`
  - `content-disposition: attachment; filename=sync-log-ce437175-...-unmatched.csv`
  - Body: `employee_no` 头 + 12 行（`E00123`...`E02678`），共 13 行，content-length=109
- CSV 对 unmatched=0 的成功 log（薪调 success）200 返回仅 `employee_no` 头，body=13 bytes
- CSV 对 employee 角色 403 `Insufficient permissions.`
- CSV 对不存在的 log_id 404 `sync log not found`

### 6. Checklist F — 详情抽屉（a11y + 交互）
expected: 抽屉 480px 宽 + role='dialog' + aria-modal='true' + aria-labelledby + Esc 关闭 + unmatched 完整列表
result: PASS
evidence:
- 点击绩效 partial 行「查看详情」后 `[role="dialog"]` 出现，计算尺寸 width=480 height=900
- `aria-modal='true'` ✓
- `aria-labelledby='drawer-title-ce437175-...'` ✓
- 抽屉内 12 个 unmatched 工号完整列出（没有 20 截断）
- Esc 键按下后 `[role="dialog"]` 从 DOM 移除
- 截图：`31-uat-drawer.png`

### 7. Checklist G — SC4 双触发观测
expected: 同一 sync_type 在锁持有期间第二次触发返回 409 且不写 FeishuSyncLog；锁释放后第二次触发正常写入两条独立 log
result: PASS (code-level)
evidence:
- `backend/tests/test_api/test_feishu_unmatched_csv.py` 包含 per-sync_type 锁 409 测试（Plan 03 Task 2 绿 13/13）
- `is_sync_running(sync_type)` 单元测试（Plan 02）覆盖不同 sync_type 独立锁
- 409 响应不写 FeishuSyncLog：`trigger_sync` 在 raise HTTPException 前不调用 `_with_sync_log`
- 生产 SC4 真实 Celery+Redis 双触发压测建议在联调环境复验（开发环境 SQLite + eager mode 不代表生产争用）

### 8. Checklist H — 空态/加载态/错误态
expected: 空态显示「暂无同步日志」+ 「前往飞书配置」CTA；loading / error 状态存在
result: PASS
evidence:
- 删除 non_statutory_leave 所有记录后切到社保假勤 Tab → 空态卡片渲染：
  - Heading: `暂无同步日志`
  - Body: `HR 触发飞书同步后，每次执行的结果会在此列出。可前往「飞书配置」页面手动触发一次同步。`
  - CTA: `前往飞书配置` button
  - `<tbody tr>` count = 0
- 截图：`31-uat-empty-state.png`
- 测试后已恢复 non_statutory_leave failed log

### 9. Checklist I — UI-SPEC 6 维度整体签字
expected: Copywriting/Visuals/Color/Typography/Spacing/Registry Safety 六维度全部符合 UI-SPEC
result: PASS
evidence:
- **Copywriting**: 页标题「飞书同步日志」、副标题、列头、Tab 标签、CTA、tooltip、空态文案 — 与 31-UI-SPEC.md 字面一致
- **Visuals**: 页面结构（breadcrumb + h1 + 分隔线 + Tab + 表 + 分页）、抽屉从右侧滑入、Tab 激活下划线
- **Color**: 60/30/10（页背景/surface/primary #1456F0）、5 badge 色 token + 1 新紫色 #722ED1（对比度 7.13:1）、4 status 色、0 值 muted
- **Typography**: h1 20px 600、列头 12px eyebrow、正文 14px、辅助 12px — 复用 index.css 既有类
- **Spacing**: px-5 py-4 / mb-4 / gap-3 — 全部 4 的倍数
- **Registry Safety**: 0 shadcn / 0 radix-ui（grep 结果为 0），vite build 成功 808 modules 3.33s

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None — all checklists automated-PASS.

## Notes

- 自动化验证通过 Playwright MCP + curl 在 Darwin 本机 macOS 环境执行（2026-04-21）
- 使用的账号：`admin@test.com`（admin）、`hrbp@test.com`（hrbp，本次新建）、`hr@test.com`（manager）、`user@test.com`（employee），统一密码 `Password123!`
- 种子数据：7 条 FeishuSyncLog 覆盖 5 种 sync_type × 4 种 status（含同步中 running 态）
- 截图归档在项目根目录：`31-uat-admin-sync-logs.png`、`31-uat-drawer.png`、`31-uat-empty-state.png`
- 生产 SC4 双触发压测 (Celery + Redis 真实争用) 建议在预发环境复验，开发 SQLite 环境不具代表性
