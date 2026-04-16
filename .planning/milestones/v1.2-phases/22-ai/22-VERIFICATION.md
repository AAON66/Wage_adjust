---
phase: 22-ai
verified: 2026-04-12T21:30:00Z
status: human_needed
score: 4/4
gaps: []
human_verification:
  - test: "触发 AI 评估后确认页面显示 'AI 评估中...' + animate-pulse 动画效果，完成后评估数据自动刷新到页面"
    expected: "点击生成评估按钮后，按钮禁用，旁边出现 'AI 评估中...' 文字并闪烁；评估完成后文字消失，评估结果自动填充到维度评分区域"
    why_human: "需要运行完整前后端 + Celery worker + Redis，并验证真实 LLM 调用完成后的 UI 刷新效果"
  - test: "触发批量导入后确认页面显示 '导入中 X/Y 行' 进度，完成后导入列表自动刷新"
    expected: "上传 CSV 后，按钮变为 '导入中...'，随后显示 '导入中 50/120 行' 等进度信息；完成后进度文字消失，导入列表自动刷新显示新任务"
    why_human: "需要运行完整前后端 + Celery worker + Redis，并验证进度回调在前端的实时更新效果"
  - test: "任务失败时确认错误信息显示且用户可重新触发"
    expected: "当 LLM 调用失败达到最大重试次数后，前端显示错误信息，用户可再次点击生成按钮"
    why_human: "需要模拟 LLM 服务不可用场景，验证错误状态传播到前端的完整链路"
---

# Phase 22: AI 评估与批量导入异步迁移 Verification Report

**Phase Goal:** AI 评估和批量导入通过 Celery 后台执行，前端可跟踪任务进度
**Verified:** 2026-04-12T21:30:00Z
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 触发 AI 评估后，API 返回 task_id，前端通过轮询获取评估进度和最终结果 | VERIFIED | `POST /evaluations/generate` 返回 202 + TaskTriggerResponse；`EvaluationDetail.tsx` 使用 `useTaskPolling(evaluationTaskId, ...)` 轮询 `GET /tasks/{task_id}`；onComplete 回调自动 setEvaluation |
| 2 | 批量导入提交后在后台执行，前端可查看导入进度百分比 | VERIFIED | `POST /imports/jobs` 返回 202 + TaskTriggerResponse；`ImportCenter.tsx` 使用 `useTaskPolling(importTaskId, ...)` 并显示 `导入中 X/Y 行`；import_tasks.py 通过 `progress_callback` 上报 PROGRESS 状态 |
| 3 | Celery task 使用独立的 DB session，不复用 FastAPI 请求级 session | VERIFIED | `evaluation_tasks.py:31` 和 `import_tasks.py:37` 均使用 `db = SessionLocal()` + `try/finally: db.close()`，完全独立于 FastAPI 的 `Depends(get_db)` |
| 4 | 单个任务失败不影响 worker 继续处理其他任务 | VERIFIED | 两个 task 均有 `try/except/finally` 完整异常处理；失败时返回 `{'status': 'failed', 'error': str(exc)}`，不会向上抛出未捕获异常；`autoretry_for=(Exception,)` + `max_retries=2` 确保重试后优雅降级 |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/schemas/task.py` | TaskStatusResponse + TaskTriggerResponse | VERIFIED | 两个 Pydantic schema 完整定义，包含 task_id/status/progress/result/error 字段 |
| `backend/app/tasks/evaluation_tasks.py` | generate_evaluation_task Celery task | VERIFIED | bind=True, max_retries=2, retry_backoff=True, soft_time_limit=300，调用 EvaluationService + serialize_evaluation |
| `backend/app/tasks/import_tasks.py` | run_import_task Celery task | VERIFIED | bind=True, max_retries=2, soft_time_limit=600，base64 解码 + UploadFile 适配 + progress_callback |
| `backend/app/api/v1/tasks.py` | GET /tasks/{task_id} 轮询端点 | VERIFIED | AsyncResult 状态映射 + T-22-01 ownership check |
| `frontend/src/services/taskService.ts` | fetchTaskStatus API 封装 | VERIFIED | 调用 `api.get<TaskStatusResponse>(/tasks/${taskId})` |
| `frontend/src/hooks/useTaskPolling.ts` | 通用轮询 hook | VERIFIED | 2s setInterval + cleanup + optionsRef + cancelled flag |
| `frontend/src/services/evaluationService.ts` | generateEvaluation 返回 TaskTriggerResponse | VERIFIED | 返回类型为 `Promise<TaskTriggerResponse>`，LONG_RUNNING_TIMEOUT 已移除 |
| `frontend/src/services/importService.ts` | createImportJob 返回 TaskTriggerResponse | VERIFIED | 返回类型为 `Promise<TaskTriggerResponse>` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| celery_app.py | evaluation_tasks.py | include list + tail import | WIRED | `include` 列表包含 `backend.app.tasks.evaluation_tasks`，尾部 `from ... import evaluation_tasks` 存在 |
| celery_app.py | import_tasks.py | include list + tail import | WIRED | `include` 列表包含 `backend.app.tasks.import_tasks`，尾部导入存在 |
| router.py | tasks.py | include_router(tasks_router) | WIRED | `tasks_router` 导入并注册 |
| evaluations.py | evaluation_tasks.py | generate_evaluation_task.delay() | WIRED | `HTTP_202_ACCEPTED` + `.delay()` 调用确认 |
| imports.py | import_tasks.py | run_import_task.delay() | WIRED | `HTTP_202_ACCEPTED` + `.delay()` 调用确认 |
| useTaskPolling.ts | taskService.ts | import fetchTaskStatus | WIRED | hook 内部调用 fetchTaskStatus |
| EvaluationDetail.tsx | useTaskPolling.ts | import useTaskPolling | WIRED | `useTaskPolling(evaluationTaskId, ...)` 调用确认 |
| ImportCenter.tsx | useTaskPolling.ts | import useTaskPolling | WIRED | `useTaskPolling(importTaskId, ...)` 调用确认 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| EvaluationDetail.tsx | evaluationTaskId | generateEvaluation().task_id | Celery task -> AsyncResult | FLOWING |
| ImportCenter.tsx | importTaskId + importProgress | createImportJob().task_id | Celery task -> progress_callback -> PROGRESS state | FLOWING |
| tasks.py (polling) | AsyncResult | Celery broker (Redis) | 实际 task state + meta | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Schema 可导入 | `python3 -c "from backend.app.schemas.task import ..."` | schema ok | PASS |
| Evaluation task 注册正确 | `python3 -c "...generate_evaluation_task.name"` | tasks.generate_evaluation, retries: 2 | PASS |
| Import task 注册正确 | `python3 -c "...run_import_task.name"` | tasks.run_import, retries: 2 | PASS |
| Celery include 列表完整 | `python3 -c "...celery_app.conf.include"` | 含 evaluation_tasks + import_tasks | PASS |
| 30 个单元测试通过 | `pytest backend/tests/test_celery_app.py ... -x -q` | 30 passed in 1.13s | PASS |
| TypeScript 编译通过 | `npx tsc --noEmit` | 无错误退出 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ASYNC-02 | 22-01, 22-02, 22-03 | AI 评估调用迁移到 Celery task，API 返回 task_id 供前端轮询结果 | SATISFIED | evaluation_tasks.py 实现 Celery task；evaluations.py 返回 202 + task_id；EvaluationDetail.tsx 通过 useTaskPolling 轮询 |
| ASYNC-03 | 22-01, 22-02, 22-03 | 批量导入通过 Celery task 后台执行，前端可查看导入进度 | SATISFIED | import_tasks.py 实现 Celery task + progress_callback；imports.py 返回 202 + task_id；ImportCenter.tsx 显示 "导入中 X/Y 行" |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | - | - | 无 anti-pattern 发现 |

### Human Verification Required

### 1. AI 评估异步流程端到端验证

**Test:** 启动前后端 + Celery worker + Redis，提交一份评估材料，点击生成 AI 评估
**Expected:** 页面显示 "AI 评估中..." + 闪烁动画；评估完成后评估数据自动填充到维度评分区域
**Why human:** 需要运行完整的前后端 + Celery worker + Redis + LLM 服务，验证真实异步任务的全链路 UI 交互

### 2. 批量导入异步流程端到端验证

**Test:** 上传一个包含 100+ 行的 CSV 文件进行批量导入
**Expected:** 显示 "导入中..." 后逐步更新为 "导入中 50/100 行" 等进度信息；完成后列表自动刷新
**Why human:** 需要运行完整服务栈，验证 progress_callback 驱动的实时进度更新在前端的展示效果

### 3. 任务失败恢复验证

**Test:** 在 LLM 服务不可用的情况下触发 AI 评估
**Expected:** 重试 2 次后前端显示错误信息，用户可重新触发
**Why human:** 需要模拟外部服务故障，验证失败状态通过 Celery -> 轮询 -> UI 的完整传播

### Gaps Summary

无 gap 发现。所有 4 个 roadmap success criteria 均通过代码层面验证：

1. AI 评估异步触发 + 前端轮询：后端返回 202 + task_id，前端 useTaskPolling 每 2 秒轮询，完成后自动刷新
2. 批量导入异步 + 进度百分比：import_tasks 使用 progress_callback 上报进度，ImportCenter 显示 "导入中 X/Y 行"
3. 独立 DB session：两个 task 均使用 `SessionLocal()` + `try/finally: db.close()`
4. 单任务失败隔离：完整 try/except/finally + max_retries=2 + 优雅降级

3 项需要人工端到端验证（需要运行完整服务栈）。

---

_Verified: 2026-04-12T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
