# Phase 25: 技术债清理 - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

消除 v1.2 遗留的两项技术债（DEBT-01, DEBT-02），为新功能开发提供干净基线。不涉及任何新功能，仅重构和统一已有代码。

</domain>

<decisions>
## Implementation Decisions

### RateLimiter 去重 (DEBT-01)
- **D-01:** 删除 `llm_service.py` 中的本地 `InMemoryRateLimiter` 类定义（第73行起），改为从 `backend/app/core/rate_limiter.py` 导入共享版本
- **D-02:** `core/rate_limiter.py` 的 `InMemoryRateLimiter` 是超集（额外支持 `wait_and_acquire` 和 `sleeper` 参数），直接替换不影响现有调用方

### FeishuSyncPanel 轮询重构 (DEBT-02)
- **D-03:** FeishuSyncPanel 的手写 `setTimeout` 递归轮询（第57-86行）替换为共享 `useTaskPolling` hook
- **D-04:** 统一使用通用 `fetchTaskStatus` API 进行轮询，不再使用飞书专用的 `getSyncStatus`
- **D-05:** 同步过程中显示进度条 + 数字（"已处理 X/Y 条，Z 条错误"），充分利用 `useTaskPolling` 的 `onProgress` 回调

### Claude's Discretion
- RateLimiter 替换后的构造函数参数调整细节
- 进度条的具体 UI 样式（可复用现有组件模式）
- `getSyncStatus` 函数是否保留或删除（取决于是否有其他调用方）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### RateLimiter
- `backend/app/core/rate_limiter.py` — 共享 InMemoryRateLimiter 定义，支持 acquire() 和 wait_and_acquire() 两种模式
- `backend/app/services/llm_service.py` — 包含待删除的本地 InMemoryRateLimiter 副本（第73行起）和 RedisRateLimiter（保留）

### 轮询 Hook
- `frontend/src/hooks/useTaskPolling.ts` — 共享轮询 hook，支持 onComplete/onError/onProgress 回调
- `frontend/src/components/eligibility-import/FeishuSyncPanel.tsx` — 待重构组件，手写 setTimeout 轮询在第57-86行
- `frontend/src/services/eligibilityImportService.ts` — getSyncStatus 函数定义处

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useTaskPolling` hook: 成熟的通用轮询 hook，已被 `ImportCenter.tsx` 和 `EvaluationDetail.tsx` 使用
- `core/rate_limiter.py`: 已被 `feishu_service.py` 使用（`wait_and_acquire` 模式），证明共享版本稳定可靠

### Established Patterns
- 前端轮询统一使用 `useTaskPolling` + `fetchTaskStatus` 模式（v1.2 建立）
- 后端 rate limiter 统一放在 `core/` 层，服务层通过构造函数注入

### Integration Points
- `llm_service.py` 的 `InMemoryRateLimiter` 被 `LlmService.__init__` 构造时使用
- `FeishuSyncPanel` 通过 `onResult` 回调将同步结果传递给父组件 `ImportTabContent`
- `useTaskPolling` 返回 `TaskStatusResponse` 类型，需确认与飞书同步任务的状态响应兼容

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-tech-debt-cleanup*
*Context gathered: 2026-04-16*
