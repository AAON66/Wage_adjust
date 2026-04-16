---
phase: 19-celery-redis
plan: 01
subsystem: infra
tags: [celery, redis, pytest, async]
requires: []
provides:
  - Celery 5.5.1 app 实例，复用现有 redis_url 作为 broker/backend
  - worker_process_init fork 后数据库连接池重置
  - tasks.db_health_check 测试任务与 Celery 配置单元测试
affects: [19-02, async-jobs, worker-health]
tech-stack:
  added: [celery-5.5.1]
  patterns: [celery-app-bootstrap, worker-process-init, task-local-db-session]
key-files:
  created:
    - backend/app/celery_app.py
    - backend/app/tasks/__init__.py
    - backend/app/tasks/test_tasks.py
    - backend/tests/test_celery_app.py
  modified:
    - requirements.txt
key-decisions:
  - "在 celery_app.py 末尾显式导入 test_tasks，确保仅导入 app 时任务已完成注册。"
  - "保持 redis 和 hiredis 版本不变，只将 Celery 固定到 5.5.1。"
patterns-established:
  - "Celery app 统一复用 get_settings().redis_url 作为 broker 与 result backend。"
  - "需要访问数据库的 Celery task 独立创建 SessionLocal，并由 worker_process_init 在 fork 后 dispose engine。"
requirements-completed: [ASYNC-01]
duration: 25min
completed: 2026-04-09
---

# Phase 19 Plan 01: Celery app 基础启动与测试 Summary

**基于 Redis 的 Celery 5.5.1 app 启动模块，包含 JSON 序列化配置、worker fork 后数据库连接重置与 DB 健康检查任务**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-09T00:54:03Z
- **Completed:** 2026-04-09T01:19:03Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- 升级 `requirements.txt` 中的 Celery 到 `5.5.1`，并保持 `redis==5.2.1`、`hiredis==3.1.0` 不变。
- 新增 `backend/app/celery_app.py` 与 `backend/app/tasks/` 目录，完成 Celery app、worker signal 与 DB 健康检查 task 基础设施。
- 新增 7 个单元测试，覆盖 broker、序列化、include 配置以及 `tasks.db_health_check` 的注册和命名。

## Task Commits

Each task was committed atomically:

1. **Task 1: 升级 celery 版本 + 创建 celery_app.py + tasks 目录结构** - `e5709a3` (feat)
2. **Task 2: Celery 配置单元测试** - `a6a75b4` (test)

## Files Created/Modified
- `requirements.txt` - 将 Celery 版本从 `5.4.0` 升级到 `5.5.1`
- `backend/app/celery_app.py` - 定义 Celery app、JSON 序列化配置与 `worker_process_init` signal
- `backend/app/tasks/__init__.py` - 初始化 tasks 包
- `backend/app/tasks/test_tasks.py` - 提供 `tasks.db_health_check` DB 健康检查任务
- `backend/tests/test_celery_app.py` - 覆盖 Celery 配置和任务注册的 7 个单元测试

## Decisions Made
- 在 `celery_app.py` 内显式导入 `backend.app.tasks.test_tasks`，让 `celery_app.tasks` 在导入时即可看到 `tasks.db_health_check`，避免仅依赖 include 延迟注册。
- 测试任务只执行 `SELECT 1`，用最小 DB 访问验证 worker 的独立 Session 使用模式。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 仅导入 celery_app 时测试任务未进入任务注册表**
- **Found during:** Task 1（导入验证）
- **Issue:** 初版实现只配置了 `include=['backend.app.tasks.test_tasks']`，但直接访问 `celery_app.tasks` 时未立即看到 `tasks.db_health_check`。
- **Fix:** 在 `backend/app/celery_app.py` 末尾显式导入 `backend.app.tasks.test_tasks`，确保导入 app 即完成任务注册。
- **Files modified:** `backend/app/celery_app.py`
- **Verification:** `python3 -c "from backend.app.celery_app import celery_app; print(list(celery_app.tasks.keys()))"` 输出包含 `tasks.db_health_check`
- **Committed in:** `e5709a3`

**2. [Rule 3 - Blocking] pytest 缺少 timeout 插件导致计划验证命令不可用**
- **Found during:** Task 2（RED 阶段首次执行 pytest）
- **Issue:** `python3 -m pytest backend/tests/test_celery_app.py -v --timeout=30` 报错 `unrecognized arguments: --timeout=30`，当前环境未安装 `pytest-timeout`。
- **Fix:** 改用环境支持的 `python3 -m pytest backend/tests/test_celery_app.py -v` 完成同一组测试验证，不扩散到仓库依赖面。
- **Files modified:** None
- **Verification:** `python3 -m pytest backend/tests/test_celery_app.py -v` 7 个测试全部通过
- **Committed in:** None（验证流程偏差，无代码变更）

---

**Total deviations:** 2 auto-fixed（1 bug，1 blocking）
**Impact on plan:** 偏差均直接服务于可导入性和测试可执行性，没有扩大实现范围。

## Issues Encountered
- Task 2 按 TDD 执行时，首次 pytest 失败原因是验证参数不受支持，而不是业务行为不满足；在移除不可用的 `--timeout` 参数后，7 个测试立即通过，说明 Task 1 已覆盖所需实现。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Celery app 基础设施与测试覆盖已经就绪，可继续实现 worker 健康检查路由和 `docker-compose` 编排。
- 当前仓库测试环境未安装 `pytest-timeout`；若后续计划继续使用 `--timeout` 参数，应统一补齐该插件或调整验证命令。

## Self-Check: PASSED
- `FOUND: .planning/phases/19-celery-redis/19-01-SUMMARY.md`
- `FOUND: e5709a3`
- `FOUND: a6a75b4`

---
*Phase: 19-celery-redis*
*Completed: 2026-04-09*
