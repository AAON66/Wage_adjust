---
phase: 19-celery-redis
plan: 03
subsystem: infra
tags: [celery, redis, docker, sqlalchemy, verification, traceability]
requires:
  - phase: 19-01
    provides: Celery app、worker signal、db_health_check 任务与基础测试
  - phase: 19-02
    provides: Dockerfile、docker-compose 编排与健康检查端点
provides:
  - SessionLocal 与全局 engine 对齐的单一 SQLAlchemy bind
  - 可重复执行的 Celery Redis->worker 运行时 proof 脚本与日志
  - ASYNC-01 / ASYNC-04 的闭环 traceability
affects: [22, 24, async-jobs, worker-runtime]
tech-stack:
  added: []
  patterns: [shared-engine-session-factory, runtime-proof-compose-stack]
key-files:
  created:
    - scripts/celery_runtime_probe.py
    - scripts/verify_celery_runtime.sh
    - .planning/phases/19-celery-redis/19-03-runtime-proof.log
  modified:
    - backend/app/core/database.py
    - backend/app/celery_app.py
    - backend/tests/test_celery_app.py
    - .planning/REQUIREMENTS.md
key-decisions:
  - "SessionLocal 改为显式绑定模块级 engine，避免 Celery worker fork 后 dispose 错对象。"
  - "运行时 proof 使用独立、无宿主端口绑定的临时 Compose 栈，避免本机 6379/8011 冲突影响 Phase 19 真值验证。"
patterns-established:
  - "需要跨进程访问数据库的 Celery task 必须与 worker_process_init dispose 的 SQLAlchemy bind 保持一致。"
  - "异步基础设施 phase 的完成标准必须包含可复跑的 broker -> queue -> worker -> result 证据，而不是只看配置和单元测试。"
requirements-completed: [ASYNC-01, ASYNC-04]
duration: 13 min
completed: 2026-04-09
---

# Phase 19 Plan 03: Celery 运行时闭环与 Gap Closure Summary

**共享 engine 的 Celery DB 生命周期修复，外加可重复执行的 Redis 到 worker 运行时 proof 与 Phase 19 traceability 闭环**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-09T02:42:23Z
- **Completed:** 2026-04-09T02:55:43Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- 修复了 `SessionLocal` 与模块级 `engine` 分离的问题，使 Celery worker fork 后 dispose 的连接池就是 task 实际使用的 bind。
- 为 `backend/tests/test_celery_app.py` 增加 3 个回归测试，覆盖共享 bind、显式 engine 复用和 dispose 后重新查询。
- 新增 `scripts/celery_runtime_probe.py` 与 `scripts/verify_celery_runtime.sh`，生成 `19-03-runtime-proof.log`，证明 `db_health_check.delay()` 真实经过 `broker -> queue -> worker -> result`。
- 将 `.planning/REQUIREMENTS.md` 中 `ASYNC-01` 和 `ASYNC-04` 更新为 `Complete`，使 Phase 19 的验证证据和需求追踪一致。

## Task Commits

Each task was committed atomically:

1. **Task 1: 对齐 Celery worker 的 DB engine/session 生命周期并补回归测试** - `329c124` (fix)
2. **Task 2: 增加 Docker 驱动的 Celery 运行时验收脚本并闭合 ASYNC Traceability** - `95f919b` (feat)

## Files Created/Modified

- `backend/app/core/database.py` - 让 `create_session_factory()` 支持显式 engine 注入，并让 `SessionLocal` 复用全局 engine
- `backend/app/celery_app.py` - 让 `worker_process_init` dispose task 实际使用的 bind，而不是只 dispose 模块级回退对象
- `backend/tests/test_celery_app.py` - 增加共享 bind / 显式 engine / dispose 重连回归测试
- `scripts/celery_runtime_probe.py` - 提交 `db_health_check.delay()` 并打印稳定的 task/result 证据
- `scripts/verify_celery_runtime.sh` - 启动临时无端口占用的 proof 栈，抓取 worker 日志并写入 proof 文件
- `.planning/phases/19-celery-redis/19-03-runtime-proof.log` - 保存 task_id、payload、worker receipt、worker success 和 proof marker
- `.planning/REQUIREMENTS.md` - 将 `ASYNC-01` / `ASYNC-04` 标记为 `Complete`

## Decisions Made

- 将 `create_session_factory(..., engine_instance=...)` 作为共享 bind 注入点，避免默认路径下再次构建独立 engine。
- 运行时 proof 不直接复用项目根 compose 的端口映射，而是由脚本生成临时 Compose 定义来规避本机已有 Redis 进程对 6379 的占用。
- Traceability 只在 `PHASE19_PROOF=ok` 落地之后更新，防止再次出现“代码写了但真值未闭合”的假完成状态。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 本机 6379 端口已被占用，默认 compose proof 无法启动**
- **Found during:** Task 2（首次执行 `bash scripts/verify_celery_runtime.sh`）
- **Issue:** `redis` 服务使用项目默认端口映射时启动失败，导致 proof 栈无法进入 worker/task 验证阶段。
- **Fix:** 将 proof 脚本改为生成独立的临时 Compose 文件和项目名，保留三服务结构，但去掉宿主端口依赖。
- **Files modified:** `scripts/verify_celery_runtime.sh`
- **Verification:** 更新后的 proof 脚本成功启动 `redis` 和 `celery-worker`，并生成 `PHASE19_PROOF=ok`
- **Committed in:** `95f919b`

**2. [Rule 3 - Blocking] 临时 Compose / probe 初版在容器内无法正确解析仓库路径**
- **Found during:** Task 2（第二次 proof 运行）
- **Issue:** `/tmp` 下的临时 Compose 文件将 `.env`、`build: .` 和脚本导入路径都解析错了，`python scripts/celery_runtime_probe.py` 也因 `backend` 包不在 `sys.path` 而失败。
- **Fix:** proof 脚本改为写入绝对仓库路径；probe 脚本在启动时把仓库根目录加入 `sys.path`。
- **Files modified:** `scripts/verify_celery_runtime.sh`, `scripts/celery_runtime_probe.py`
- **Verification:** `bash scripts/verify_celery_runtime.sh` 成功结束，proof log 记录了 `PHASE19_TASK_RESULT={"db_check": true, "status": "ok"}` 与 worker success 日志
- **Committed in:** `95f919b`

---

**Total deviations:** 2 auto-fixed（2 blocking）
**Impact on plan:** 偏差都属于执行环境阻塞，不改变 Phase 19 的功能目标；相反，它们让 proof 脚本在真实开发机上可重复运行。

## Issues Encountered

- Celery worker 容器在本地 proof 期间仍以 root 用户启动，并打印 Celery 的 `SecurityWarning`。这不影响 Phase 19 的开发环境真值验证，但生产镜像仍应在后续部署 phase 中切换到非 root 用户。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 19 的异步基础设施现在有真实运行时证据，Phase 22 可以基于已验证的 worker/Redis 路径迁移业务 task。
- `scripts/verify_celery_runtime.sh` 可作为后续异步相关变更的回归验收入口，避免再次退化成只看单元测试。

## Self-Check: PASSED

- `FOUND: .planning/phases/19-celery-redis/19-03-SUMMARY.md`
- `FOUND: 329c124`
- `FOUND: 95f919b`

---
*Phase: 19-celery-redis*
*Completed: 2026-04-09*
