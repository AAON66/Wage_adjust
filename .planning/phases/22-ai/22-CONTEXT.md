# Phase 22: AI 评估与批量导入异步迁移 - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

将 AI 评估（LLM 文本评估 + 视觉评估）和批量导入（Excel/飞书）从同步阻塞迁移到 Celery 后台执行。前端通过轮询跟踪任务状态，完成后自动刷新展示结果。不包含新的评估逻辑或导入类型。

</domain>

<decisions>
## Implementation Decisions

### 前端进度展示
- **D-01:** 进度展示采用状态文字 + Spinner 形式，不使用进度条。AI 评估显示 "AI 评估中..."，批量导入显示 "导入中 45/120 行" 等描述性文字
- **D-02:** 任务完成后轮询自动刷新页面数据，无额外 Toast 或弹窗通知
- **D-03:** 轮询间隔固定 2 秒，不使用递增退避策略

### API 契约设计
- **D-04:** 复用现有端点（破坏性改动）。POST /evaluations/generate 和 /evaluations/regenerate 改为返回 {task_id, status}，不再同步等待结果
- **D-05:** 新建通用任务轮询端点 GET /tasks/{task_id}，放在 backend/app/api/v1/tasks.py。AI 评估和批量导入共用同一轮询端点
- **D-06:** 任务完成时在轮询响应的 result 字段中直接嵌入业务结果（evaluation 对象或导入统计），前端一次轮询拿到全部数据

### 任务粒度与进度计算
- **D-07:** AI 评估使用粗粒度状态：pending → running → completed/failed。不报告子步骤百分比，因为 LLM 调用本身无法量化进度
- **D-08:** 批量导入按行报告进度：定期更新 Celery task meta {processed, total, errors}，每处理一批行（如 50 行）更新一次。前端显示 "导入中 X/Y 行"

### 失败处理与重试
- **D-09:** AI 评估任务自动重试 2 次（Celery autoretry_for + retry_backoff），2 次失败后标记 failed，用户可手动重新触发
- **D-10:** 批量导入单行失败不中断整体导入，最终返回 {success, failed, errors} 汇总。与现有 ImportService per-row 错误记录逻辑一致
- **D-11:** 批量导入 task 级失败（如文件解析异常）同样自动重试 2 次

### Claude's Discretion
- Celery task 内部的 DB session 管理细节（遵循 Phase 19 已建立的 SessionLocal 模式）
- 前端轮询 hook 的具体实现（useEffect + setInterval 或自定义 hook）
- task meta 更新的具体批次大小
- 任务超时时间设置

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Celery 基础设施（Phase 19 已建立）
- `backend/app/celery_app.py` — Celery app 实例、worker_process_init 信号处理、JSON 序列化配置
- `backend/app/tasks/test_tasks.py` — 现有 task 模式参考：SessionLocal 获取 DB session、try/finally 关闭
- `backend/app/core/database.py` — SessionLocal 工厂，task 中需独立创建 session

### 需要迁移的同步代码
- `backend/app/api/v1/evaluations.py` — generate_evaluation / regenerate_evaluation 端点（当前同步，需改为异步触发）
- `backend/app/services/evaluation_service.py` — EvaluationService.generate_evaluation() 方法（核心评估逻辑，需包装为 Celery task）
- `backend/app/services/import_service.py` — ImportService（当前同步处理，需包装为 Celery task 并添加进度上报）
- `backend/app/api/v1/imports.py` — 批量导入 API 端点

### 前端需改造的文件
- `frontend/src/services/evaluationService.ts` — generateEvaluation / regenerateEvaluation 当前使用 120s 同步超时，需改为触发+轮询模式
- `frontend/src/pages/EvaluationDetail.tsx` — 评估触发和结果展示页面

### 需求定义
- `.planning/REQUIREMENTS.md` §ASYNC-02 — AI 评估迁移到 Celery task，API 返回 task_id
- `.planning/REQUIREMENTS.md` §ASYNC-03 — 批量导入通过 Celery task 后台执行，前端可查看进度

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/celery_app.py`: Celery app 已配置完毕，含 worker_process_init 信号处理和 engine.dispose()
- `backend/app/tasks/test_tasks.py`: 可作为新 task 的模板——SessionLocal + try/finally 模式
- `frontend/src/services/api.ts`: Axios 实例，可扩展轮询逻辑

### Established Patterns
- Task 模块按业务域分文件：`backend/app/tasks/` 下 evaluation_tasks.py、import_tasks.py
- API 路由按域注册：`backend/app/api/v1/__init__.py` 中添加新的 tasks router
- Settings 通过 `get_settings()` LRU 缓存获取
- 服务层接收 `Session` 注入：EvaluationService(db, settings)

### Integration Points
- `backend/app/celery_app.py` include 列表需添加新 task 模块
- `backend/app/api/v1/__init__.py` 需注册 tasks.py router
- `frontend/src/services/` 需新建 taskService.ts 用于轮询
- `frontend/src/services/evaluationService.ts` 需从同步改为异步触发+轮询

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

*Phase: 22-ai*
*Context gathered: 2026-04-12*
