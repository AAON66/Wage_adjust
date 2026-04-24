---
status: completed
phase: 35-employee-self-service-experience
source:
  - 35-01-schema-service-SUMMARY.md
  - 35-02-api-handler-SUMMARY.md
  - 35-03-frontend-types-service-SUMMARY.md
  - 35-04-component-integration-SUMMARY.md
started: "2026-04-23T00:45:00Z"
updated: "2026-04-23T01:48:16Z"
---

## Current Test

number: null
name: null
expected: null
awaiting: none

## Tests

### 1. 已绑定员工看到绩效档次徽章
expected: 使用已绑定员工账号进入 `/my-review` 后，在「本人调薪资格」面板正下方看到新的「本人绩效档次」section；当当前年快照里存在该员工档次时，应显示 1/2/3 档徽章之一、右上角时间戳，以及“YYYY 年度档次（按全公司 20/70/10 分档）”说明。
result: pass

### 2. 样本不足时显示灰色暂不分档提示
expected: 当 `/performance/me/tier` 返回 `reason='insufficient_sample'` 时，页面仍显示「本人绩效档次」section，但徽章区域不显示 1/2/3 档，而是显示“本年度全公司绩效样本不足，暂不分档”。
result: pass
notes: 自动化登录绑定员工后验证到灰色“暂不分档”徽章与说明文案同时出现。

### 3. 无档次数据或未排名时显示解释文案
expected: 当接口返回 `reason='no_snapshot'` 时显示“本年度尚无档次数据，请等待 HR 录入后查看”；当返回 `reason='not_ranked'` 时显示“未找到您本年度的绩效记录，如有疑问请联系 HR”；两种状态都不显示年度档次说明行。
result: pass
notes: 自动切换 `no_snapshot` 与 `not_ranked` 场景并刷新页面，分别看到“暂无档次”与“未找到档次”提示，均未出现年度档次说明。

### 4. 未绑定或档案缺失时显示引导卡片
expected: 当账号未绑定员工时，徽章区域显示引导去“账号设置”的提示卡；当账号绑定了不存在的员工记录时，显示“未找到您的员工档案，请联系 HR 核对”的提示卡；两种场景都不会泄露其他员工数据。
result: pass
notes: 自动登录 `phase35-unbound@example.com` 与 `phase35-stale@example.com`，分别看到“账号设置”绑定引导卡与“未找到您的员工档案”告警卡，页面未出现他人档次数据。

### 5. 异常时可重试
expected: 当 `/performance/me/tier` 请求失败时，section 显示错误提示和“重试”按钮；点击“重试”会重新发起请求，并在服务恢复后正常显示徽章或提示文案。
result: pass
notes: 将本地代理切到 `fail_me_tier` 后，页面出现“档次信息暂时不可用，请稍后重试”和“重试”按钮；恢复代理为 `normal` 后点击“重试”，页面成功恢复为 `2 档` 与年度说明。

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
- 无。上述 5 项已通过自动化浏览器回归验证。
