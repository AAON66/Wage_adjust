---
status: partial
phase: 30-employee-no-leading-zero
source: [30-VERIFICATION.md]
started: 2026-04-21T00:00:00Z
updated: 2026-04-21T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Excel 桌面软件实际保存-重开前导零
expected: HR 下载 xlsx 模板（任一类型），在 Excel 桌面软件打开，于工号列任意空白行录入 `01234` 后保存 → 重新打开文件，工号单元格显示仍为 `01234`，且 `cell.number_format == '@'` 保持不变（不是变成 `1234` 或科学记数）。
result: [pending]

### 2. 真实飞书多维表格「数字」类型字段触发 422
expected: 管理员进入飞书多维表格绑定配置页，把 employee_no 字段映射到一个「数字」类型的飞书字段，点保存 → 页面弹出中文错误「配置错误：工号字段类型必须为 text」，HTTP 响应 422，配置未落库；切换为 text 类型字段后保存成功。
result: [pending]

### 3. 真实飞书同步触发容忍匹配 > 0 时的黄色提示
expected: DB 中 employee_no 为 `02615`，飞书源数据中对应工号写作 `2615`，触发任意一种飞书同步（考勤 / 绩效 / 调薪 / 入职 / 非法假） → 同步状态卡（SyncStatusCard）出现黄色提示带有 `leading_zero_fallback_count ≥ 1` 文案；`/api/v1/feishu/sync-logs` 返回体内对应记录 `leading_zero_fallback_count` 字段大于 0；业务记录仍按预期落库（fallback 命中不应变成未匹配）。
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
