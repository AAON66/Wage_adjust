# Phase 25: 技术债清理 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 25-技术债清理
**Areas discussed:** 轮询 API 对齐, 同步进度展示

---

## 轮询 API 对齐

| Option | Description | Selected |
|--------|-------------|----------|
| 统一到通用 fetchTaskStatus（推荐） | 如果飞书同步任务已经走 Celery task 基础设施，直接用通用任务状态接口，保持一致性 | ✓ |
| 让 useTaskPolling 支持自定义 fetcher | 给 hook 加一个可选的 fetchFn 参数，默认用 fetchTaskStatus，也能传入 getSyncStatus | |
| Claude 决定 | 研究阶段确认后端接口实际情况后自行判断 | |

**User's choice:** 统一到通用 fetchTaskStatus
**Notes:** 无额外说明

---

## 同步进度展示

| Option | Description | Selected |
|--------|-------------|----------|
| 进度条 + 数字（推荐） | 显示"已处理 X/Y 条，Z 条错误"＋进度条，充分利用 useTaskPolling 的 onProgress 回调 | ✓ |
| 仅文字状态 | 保持当前的"正在同步"文本，不加进度条，最小改动 | |
| Claude 决定 | 根据后端实际返回的进度数据格式来决定 | |

**User's choice:** 进度条 + 数字
**Notes:** 无额外说明

---

## Claude's Discretion

- RateLimiter 替换后的构造函数参数调整细节
- 进度条的具体 UI 样式
- getSyncStatus 函数是否保留或删除

## Deferred Ideas

None
