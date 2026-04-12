# Phase 22: AI 评估与批量导入异步迁移 - Research

**Researched:** 2026-04-12
**Domain:** Celery 异步任务迁移 (Python/FastAPI/React)
**Confidence:** HIGH

## Summary

本阶段将两个已有的同步阻塞操作（AI 评估生成、批量导入）迁移到 Celery 后台执行。Phase 19 已完成 Celery 基础设施搭建（celery_app.py 配置、worker_process_init 信号处理、test_tasks.py 参考模板），本阶段在此基础上新增业务 task，改造现有 API 端点返回 task_id，并在前端实现轮询。

项目已安装 Celery 5.6.3 + Redis 7.4.0 客户端。Celery 配置中 `task_track_started=True` 已启用，支持 STARTED 状态追踪。`result_expires=3600` 意味着任务结果在 Redis 中保留 1 小时。现有 task 模板使用 `SessionLocal()` + `try/finally` 模式管理独立 DB session。

**Primary recommendation:** 新建 `evaluation_tasks.py` 和 `import_tasks.py` 两个 task 模块，复用现有 `SessionLocal` + `try/finally` 模式；新建 `tasks.py` 路由提供通用轮询端点；前端新建 `taskService.ts` + `useTaskPolling` hook 实现 2 秒固定间隔轮询。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** 进度展示采用状态文字 + Spinner 形式，不使用进度条。AI 评估显示 "AI 评估中..."，批量导入显示 "导入中 45/120 行" 等描述性文字
- **D-02:** 任务完成后轮询自动刷新页面数据，无额外 Toast 或弹窗通知
- **D-03:** 轮询间隔固定 2 秒，不使用递增退避策略
- **D-04:** 复用现有端点（破坏性改动）。POST /evaluations/generate 和 /evaluations/regenerate 改为返回 {task_id, status}，不再同步等待结果
- **D-05:** 新建通用任务轮询端点 GET /tasks/{task_id}，放在 backend/app/api/v1/tasks.py。AI 评估和批量导入共用同一轮询端点
- **D-06:** 任务完成时在轮询响应的 result 字段中直接嵌入业务结果（evaluation 对象或导入统计），前端一次轮询拿到全部数据
- **D-07:** AI 评估使用粗粒度状态：pending -> running -> completed/failed。不报告子步骤百分比
- **D-08:** 批量导入按行报告进度：定期更新 Celery task meta {processed, total, errors}，每处理一批行更新一次。前端显示 "导入中 X/Y 行"
- **D-09:** AI 评估任务自动重试 2 次（Celery autoretry_for + retry_backoff），2 次失败后标记 failed，用户可手动重新触发
- **D-10:** 批量导入单行失败不中断整体导入，最终返回 {success, failed, errors} 汇总
- **D-11:** 批量导入 task 级失败（如文件解析异常）同样自动重试 2 次

### Claude's Discretion
- Celery task 内部的 DB session 管理细节（遵循 Phase 19 已建立的 SessionLocal 模式）
- 前端轮询 hook 的具体实现（useEffect + setInterval 或自定义 hook）
- task meta 更新的具体批次大小
- 任务超时时间设置

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASYNC-02 | AI 评估调用迁移到 Celery task，API 返回 task_id 供前端轮询结果 | Celery task 模式、API 端点改造、前端轮询 hook 均有详细研究 |
| ASYNC-03 | 批量导入通过 Celery task 后台执行，前端可查看导入进度 | ImportService 迁移方案、进度上报机制、前端进度展示均已覆盖 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| celery | 5.6.3 | 分布式任务队列 | 已安装，Phase 19 已配置 [VERIFIED: pip show celery] |
| redis | 7.4.0 | Celery broker/backend | 已安装 [VERIFIED: pip show redis] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| celery.result.AsyncResult | (celery 内置) | 查询任务状态和结果 | 轮询端点从 Redis 读取任务状态 |

### Alternatives Considered
无需引入新依赖。所有所需库已在 Phase 19 中安装完毕。

## Architecture Patterns

### 推荐项目结构变更
```
backend/app/
├── tasks/
│   ├── __init__.py          # 已有
│   ├── test_tasks.py        # 已有 (Phase 19)
│   ├── evaluation_tasks.py  # 新增：AI 评估 Celery task
│   └── import_tasks.py      # 新增：批量导入 Celery task
├── api/v1/
│   ├── tasks.py             # 新增：通用任务轮询端点
│   ├── evaluations.py       # 改造：generate/regenerate 返回 task_id
│   └── imports.py           # 改造：create_import_job 返回 task_id
├── schemas/
│   └── task.py              # 新增：TaskStatusResponse schema
frontend/src/
├── services/
│   └── taskService.ts       # 新增：轮询 API 封装
├── hooks/
│   └── useTaskPolling.ts    # 新增：通用轮询 hook
```

### Pattern 1: Celery Task with Independent DB Session

**What:** 每个 Celery task 独立创建 DB session，不复用 FastAPI 请求级 session。
**When to use:** 所有需要数据库操作的 Celery task。
**Example:**
```python
# Source: backend/app/tasks/test_tasks.py (已有模板) [VERIFIED: codebase]
from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal

@celery_app.task(
    name='tasks.generate_evaluation',
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
)
def generate_evaluation_task(self, submission_id: str, force: bool = False) -> dict:
    db = SessionLocal()
    try:
        self.update_state(state='STARTED', meta={'status': 'running'})
        # ... 业务逻辑 ...
        return {'status': 'completed', 'result': serialized_evaluation}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            return {'status': 'failed', 'error': str(exc)}
        raise  # 触发自动重试
    finally:
        db.close()
```
[VERIFIED: test_tasks.py 已使用此模式]

### Pattern 2: Celery Task 中的进度上报

**What:** 使用 `self.update_state()` 更新自定义 meta 数据，轮询端点通过 `AsyncResult.info` 读取。
**When to use:** 批量导入需要按行上报进度。
**Example:**
```python
# [ASSUMED: Celery 标准 API]
@celery_app.task(bind=True, name='tasks.run_import')
def run_import_task(self, import_type: str, file_bytes: bytes, file_name: str, ...) -> dict:
    db = SessionLocal()
    try:
        # 每处理 50 行更新一次进度
        for batch_end in range(batch_size, total_rows + 1, batch_size):
            # 处理 batch...
            self.update_state(
                state='PROGRESS',
                meta={'processed': batch_end, 'total': total_rows, 'errors': error_count}
            )
        return {'status': 'completed', 'result': {...}}
    finally:
        db.close()
```
[ASSUMED: Celery update_state + bind=True 是标准做法]

### Pattern 3: 通用任务轮询端点

**What:** 单一 GET 端点读取任何 Celery task 的状态。
**When to use:** 所有异步任务共享同一轮询端点。
**Example:**
```python
# backend/app/api/v1/tasks.py
from celery.result import AsyncResult
from backend.app.celery_app import celery_app

@router.get('/tasks/{task_id}')
def get_task_status(task_id: str, ...):
    result = AsyncResult(task_id, app=celery_app)
    if result.state == 'PENDING':
        return {'task_id': task_id, 'status': 'pending'}
    if result.state == 'STARTED':
        return {'task_id': task_id, 'status': 'running'}
    if result.state == 'PROGRESS':
        meta = result.info or {}
        return {'task_id': task_id, 'status': 'running', 'progress': meta}
    if result.state == 'SUCCESS':
        payload = result.result or {}
        return {'task_id': task_id, 'status': payload.get('status', 'completed'), 'result': payload.get('result')}
    if result.state == 'FAILURE':
        return {'task_id': task_id, 'status': 'failed', 'error': str(result.result)}
    return {'task_id': task_id, 'status': result.state.lower()}
```
[ASSUMED: AsyncResult 标准用法]

### Pattern 4: 前端轮询 Hook

**What:** 自定义 React hook，固定 2 秒间隔轮询任务状态，完成后自动停止并回调。
**When to use:** 任何触发异步任务后需要跟踪进度的页面。
**Example:**
```typescript
// frontend/src/hooks/useTaskPolling.ts
function useTaskPolling(taskId: string | null, options: {
  onComplete: (result: unknown) => void;
  onError: (error: string) => void;
  onProgress?: (progress: { processed: number; total: number }) => void;
}) {
  useEffect(() => {
    if (!taskId) return;
    const interval = setInterval(async () => {
      const status = await fetchTaskStatus(taskId);
      if (status.status === 'completed') {
        clearInterval(interval);
        options.onComplete(status.result);
      } else if (status.status === 'failed') {
        clearInterval(interval);
        options.onError(status.error);
      } else if (status.progress) {
        options.onProgress?.(status.progress);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [taskId]);
}
```
[ASSUMED: React useEffect + setInterval 标准模式]

### Anti-Patterns to Avoid
- **在 Celery task 中复用 FastAPI 请求级 session:** Session 绑定在请求生命周期，task 在独立进程运行，复用会导致 DetachedInstanceError 或连接泄漏。必须用 SessionLocal() 创建独立 session。[VERIFIED: test_tasks.py 已遵循此模式]
- **在 task 中传递 ORM 对象:** Celery 使用 JSON 序列化，ORM 对象无法序列化。只传 ID (submission_id, import_type) 和原始数据 (file_bytes)。[VERIFIED: celery_app.py 配置 task_serializer='json']
- **使用 `result.get()` 同步等待:** 在 FastAPI 端点中调用 `result.get()` 会阻塞 worker 线程，失去异步意义。必须用 `AsyncResult` 读状态。
- **忘记在 celery_app.py include 列表中注册新 task 模块:** 未注册的模块中的 task 不会被 worker 发现。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 任务状态存储 | 自建 Redis/DB 任务状态表 | Celery result backend (已配置 Redis) | Celery 内建状态追踪，`task_track_started=True` 已启用 |
| 进度上报 | 自建进度推送通道 | `self.update_state(state='PROGRESS', meta={...})` | Celery 标准 API，通过 `AsyncResult.info` 读取 |
| 任务重试 | 自建重试循环 | `autoretry_for` + `retry_backoff` + `max_retries` | Celery 内建重试机制，支持指数退避 |
| 任务超时 | 自建超时计时器 | `soft_time_limit` / `time_limit` task 参数 | Celery 内建，soft limit 允许 task 清理资源后退出 |

## Common Pitfalls

### Pitfall 1: Task 参数不可 JSON 序列化
**What goes wrong:** 传递 UploadFile、Session、ORM 对象等不可序列化参数，task 入队时报 TypeError。
**Why it happens:** Celery 使用 JSON 序列化（已配置 `task_serializer='json'`），只支持基本类型。
**How to avoid:** 只传 str、int、float、dict、list、bytes (base64)。文件内容需在 API 端点中读取为 bytes，传给 task。
**Warning signs:** `TypeError: Object of type ... is not JSON serializable`

### Pitfall 2: 批量导入文件数据传递
**What goes wrong:** UploadFile 对象无法传递给 Celery task；文件过大时 Redis 消息体膨胀。
**Why it happens:** Celery 消息通过 Redis 传递，大文件会占用大量 broker 内存。
**How to avoid:** 在 API 端点中先将文件保存到本地/对象存储，只传文件路径给 task。或对于 <5MB 的 CSV/Excel 文件，base64 编码后直接传递（当前项目 MAX_ROWS=5000，文件通常较小）。
**Warning signs:** Redis 内存突增，task 入队延迟增大。

### Pitfall 3: API 契约破坏性改动未同步前端
**What goes wrong:** generate/regenerate 端点返回值从 EvaluationRead 变为 {task_id, status}，但前端仍期望完整评估对象。
**Why it happens:** D-04 明确要求破坏性改动，前端必须同步更新。
**How to avoid:** 后端和前端在同一 wave 中同时改造，确保 evaluationService.ts 中 generateEvaluation/regenerateEvaluation 改为返回 task_id，然后启动轮询。
**Warning signs:** 前端 TypeScript 编译报错、运行时 undefined 属性访问。

### Pitfall 4: Celery task 中 Settings 获取
**What goes wrong:** Task 进程中 `get_settings()` 缓存可能持有过期实例。
**Why it happens:** `@lru_cache` 的 Settings 在 fork 后的 worker 进程中被继承。
**How to avoid:** 这在当前项目中实际上是安全的——settings 在启动后不变。但如果需要，可在 task 内部直接调用 `Settings()` 创建新实例。当前代码中 `get_settings()` 是标准做法。[VERIFIED: config.py 使用 @lru_cache]

### Pitfall 5: 前端轮询未清理
**What goes wrong:** 组件卸载后 setInterval 继续执行，导致内存泄漏和 "setState on unmounted component" 警告。
**Why it happens:** useEffect 清理函数未正确 clearInterval。
**How to avoid:** useEffect 返回清理函数中 clearInterval，并使用 ref 跟踪组件挂载状态。

### Pitfall 6: FAILURE 状态下 result.info 类型
**What goes wrong:** 当 task 抛异常时，`AsyncResult.result` 是 Exception 对象而非 dict，直接当 dict 用会报错。
**Why it happens:** Celery 在 FAILURE 状态下将异常对象存储为 result。
**How to avoid:** 在轮询端点中对 FAILURE 状态单独处理：`str(result.result)` 获取错误信息。

## Code Examples

### Task 触发与 task_id 返回

```python
# backend/app/api/v1/evaluations.py (改造后)
# Source: D-04 决策 + 现有代码模式 [VERIFIED: codebase]
from backend.app.tasks.evaluation_tasks import generate_evaluation_task

@router.post('/generate', status_code=status.HTTP_202_ACCEPTED)
def generate_evaluation(
    payload: EvaluationGenerateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    current_user: User = Depends(get_current_user),
) -> dict:
    # 权限校验仍在 API 层同步完成
    try:
        submission = AccessScopeService(db).ensure_submission_access(current_user, payload.submission_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if submission is None:
        raise HTTPException(status_code=404, detail='Submission not found.')

    # 触发异步任务
    task = generate_evaluation_task.delay(payload.submission_id, False)
    return {'task_id': task.id, 'status': 'pending'}
```

### 批量导入 task 中的进度上报

```python
# backend/app/tasks/import_tasks.py
# Source: D-08 决策 + ImportService 现有逻辑 [VERIFIED: codebase + CONTEXT]
PROGRESS_BATCH_SIZE = 50  # 每 50 行更新一次进度

@celery_app.task(bind=True, name='tasks.run_import', ...)
def run_import_task(self, import_type: str, file_bytes_b64: str, file_name: str, operator_id: str | None, operator_role: str | None) -> dict:
    db = SessionLocal()
    try:
        import base64
        raw_bytes = base64.b64decode(file_bytes_b64)
        # 解析文件为 DataFrame
        service = ImportService(db, operator_id=operator_id, operator_role=operator_role)
        dataframe = service._load_table(file_name, raw_bytes)
        total_rows = len(dataframe)

        # 按批次处理并上报进度
        self.update_state(state='PROGRESS', meta={'processed': 0, 'total': total_rows, 'errors': 0})
        # ... 逐批处理逻辑 ...
        return {'status': 'completed', 'result': job_read_dict}
    finally:
        db.close()
```

### 前端轮询服务

```typescript
// frontend/src/services/taskService.ts
// Source: D-05 决策 [VERIFIED: CONTEXT]
import api from './api';

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: { processed: number; total: number; errors: number };
  result?: unknown;
  error?: string;
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await api.get<TaskStatus>(`/tasks/${taskId}`);
  return response.data;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 同步 120s 超时等待 AI 评估 | Celery task + 轮询 | Phase 22 (本次) | 用户体验大幅改善，不再阻塞浏览器 |
| 同步批量导入等待完成 | Celery task + 进度上报 | Phase 22 (本次) | 支持大批量导入而不超时 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Celery `self.update_state(state='PROGRESS', meta={...})` 可被 `AsyncResult.info` 读取 | Architecture Pattern 2 | 进度上报机制不工作，需改用其他方式存储进度 |
| A2 | `AsyncResult.state` 返回 'PENDING'/'STARTED'/'SUCCESS'/'FAILURE' 等标准状态字符串 | Architecture Pattern 3 | 轮询端点状态映射错误 |
| A3 | FAILURE 状态下 `AsyncResult.result` 是 Exception 对象 | Pitfall 6 | 错误消息提取逻辑不正确 |
| A4 | 文件 base64 编码后通过 Celery JSON 消息传递对 <5MB 文件可行 | Pitfall 2 | 需改为先存文件再传路径 |

**注:** A1-A3 是 Celery 长期稳定的核心 API，风险极低。A4 取决于实际文件大小，当前项目 MAX_ROWS=5000，CSV/Excel 通常远小于 5MB。

## Open Questions

1. **批量导入文件传递方式**
   - What we know: 当前 ImportService.run_import() 接收 UploadFile，直接读取 bytes。MAX_ROWS=5000 限制下文件通常较小。
   - What's unclear: 是否应先保存到 uploads/ 目录再传文件路径，还是 base64 编码直接传。
   - Recommendation: base64 直接传递。5000 行 CSV 通常 <1MB，base64 后 <1.5MB，在 Redis 消息大小限制内（默认 512MB）。简化实现，无需额外的文件生命周期管理。

2. **任务超时时间**
   - What we know: 当前 DeepSeek API 超时为 120 秒 (evaluation_timeout_seconds)。
   - What's unclear: Celery task 的 soft_time_limit 应设多少。
   - Recommendation: AI 评估设 `soft_time_limit=300, time_limit=360`（5/6 分钟，考虑重试和网络波动）。批量导入设 `soft_time_limit=600, time_limit=660`（10/11 分钟，5000 行需要时间）。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Celery | 异步任务执行 | Yes | 5.6.3 | -- |
| Redis (Python client) | Celery broker/backend | Yes | 7.4.0 | -- |
| Redis (server) | Celery 运行时 | No (ping failed) | -- | 开发时需启动 Redis；测试可用 `ALWAYS_EAGER=True` |

**Missing dependencies with no fallback:**
- Redis server 未运行。开发和生产环境必须启动 Redis。开发测试可通过设置 `CELERY_ALWAYS_EAGER=True` 绕过（但不测试真实异步行为）。

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | 无独立 pytest 配置文件，使用默认配置 |
| Quick run command | `pytest backend/tests/test_celery_app.py -x` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASYNC-02a | evaluation task 注册在 celery_app 中 | unit | `pytest backend/tests/test_celery_app.py -x` | Wave 0 需扩展 |
| ASYNC-02b | generate 端点返回 202 + task_id | unit | `pytest backend/tests/test_api/test_evaluations_async.py -x` | Wave 0 新建 |
| ASYNC-02c | 轮询端点返回正确状态 | unit | `pytest backend/tests/test_api/test_tasks.py -x` | Wave 0 新建 |
| ASYNC-03a | import task 注册在 celery_app 中 | unit | `pytest backend/tests/test_celery_app.py -x` | Wave 0 需扩展 |
| ASYNC-03b | import task 上报进度 meta | unit | `pytest backend/tests/test_tasks/test_import_tasks.py -x` | Wave 0 新建 |
| ASYNC-02/03 | 前端轮询集成 | manual-only | 启动完整栈 + Redis，手动触发评估/导入并观察 | -- |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_celery_app.py backend/tests/test_api/ -x --timeout=30`
- **Per wave merge:** `pytest backend/tests/ -x`
- **Phase gate:** Full suite green + 手动 E2E 验证

### Wave 0 Gaps
- [ ] `backend/tests/test_api/test_tasks.py` -- 通用轮询端点测试
- [ ] `backend/tests/test_api/test_evaluations_async.py` -- 评估异步触发测试
- [ ] `backend/tests/test_tasks/test_import_tasks.py` -- 导入 task 进度上报测试
- [ ] 扩展 `backend/tests/test_celery_app.py` -- 验证新 task 模块注册

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | 权限校验在 API 层同步完成，task 本身不做鉴权 |
| V3 Session Management | no | -- |
| V4 Access Control | yes | generate/regenerate 端点保留现有 AccessScopeService 校验 |
| V5 Input Validation | yes | Pydantic schema 校验 submission_id 格式 |
| V6 Cryptography | no | -- |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 伪造 task_id 查询他人任务结果 | Information Disclosure | 轮询端点需验证当前用户是否有权查看该 task 的结果（通过 task meta 中存储 user_id） |
| 大量触发 task 导致 worker 过载 | Denial of Service | 限制同一用户同时只能有一个进行中的评估/导入 task |

## Sources

### Primary (HIGH confidence)
- `backend/app/celery_app.py` -- Celery 配置，已验证 task_track_started=True、JSON 序列化、result_expires=3600
- `backend/app/tasks/test_tasks.py` -- 现有 task 模板，SessionLocal + try/finally 模式
- `backend/app/core/database.py` -- SessionLocal 工厂定义
- `backend/app/api/v1/evaluations.py` -- 当前同步 generate/regenerate 端点
- `backend/app/services/evaluation_service.py` -- EvaluationService.generate_evaluation() 完整逻辑
- `backend/app/services/import_service.py` -- ImportService.run_import() 完整逻辑
- `backend/app/api/v1/imports.py` -- 当前同步导入端点
- `frontend/src/services/evaluationService.ts` -- 当前 120s 同步超时调用
- `frontend/src/services/importService.ts` -- 当前同步导入调用
- `pip show celery` -- 5.6.3 [VERIFIED]
- `pip show redis` -- 7.4.0 [VERIFIED]

### Secondary (MEDIUM confidence)
- Celery `update_state` / `AsyncResult` API -- 标准且稳定的 Celery 核心功能 [ASSUMED: training knowledge]

### Tertiary (LOW confidence)
- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- 所有依赖已安装并在 Phase 19 中验证
- Architecture: HIGH -- 基于已有 test_tasks.py 模板扩展，模式已验证
- Pitfalls: HIGH -- 基于项目已有代码结构和 Celery 标准实践

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (稳定基础设施，30 天有效)
