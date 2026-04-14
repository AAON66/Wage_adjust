# Phase 19: Celery+Redis 异步基础设施 - Research

**Researched:** 2026-04-08
**Domain:** Celery 异步任务队列 + Redis broker + FastAPI 集成
**Confidence:** HIGH

## Summary

本阶段目标是搭建 Celery 异步任务基础设施，包括 Celery app 配置、worker 独立启动、测试 task 验证端到端链路、健康检查端点、以及 docker-compose 服务定义。不涉及任何业务 task 迁移。

项目已在 `requirements.txt` 中声明 `celery==5.4.0`、`redis==5.2.1`、`hiredis==3.1.0`，且 `backend/app/core/config.py` 中已有 `redis_url` 配置，`backend/app/core/redis.py` 已有 Redis 客户端单例。基础设施层面已有良好基础，本阶段主要是创建 Celery app 实例、tasks 目录结构、健康检查路由和 docker-compose 编排。

**Primary recommendation:** 使用标准的 Celery app 独立模块 + `worker_process_init` signal 处理 DB 连接 + `celery.control.inspect().ping(timeout=3)` 实现健康检查。

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Celery app 实例放在 `backend/app/celery_app.py`，启动命令 `celery -A backend.app.celery_app worker`
- **D-02:** Task 模块放在 `backend/app/tasks/` 目录下，按业务域分文件，本阶段先创建测试 task
- **D-03:** Broker 和 result backend 均复用 `config.py` 中已有的 `redis_url`
- **D-04:** Task 序列化格式使用 JSON
- **D-05:** 使用 `celery.control.inspect().ping()` 检测 worker 在线状态，3 秒超时
- **D-06:** 健康检查端点无需认证，公开访问
- **D-07:** 返回 worker 在线数量、整体状态、检查时间戳，不暴露 worker 主机名
- **D-08:** 新建 `backend/app/api/v1/health.py`，路径 `/api/v1/health/celery`
- **D-09:** docker-compose.yml 包含 redis、celery-worker、backend API 三个服务
- **D-10:** Celery worker 使用 prefork 并发模式，开发环境 concurrency=2
- **D-11:** celery 从 5.4.0 升级到 5.5.1
- **D-12:** redis==5.2.1 和 hiredis==3.1.0 保持现有版本不变

### Claude's Discretion
- docker-compose.yml 中的网络配置和卷挂载细节
- Celery 配置中的其他调优参数（task_acks_late、worker_prefetch_multiplier 等）
- 测试 task 的具体 DB 操作内容（只要能验证 worker 独立连接 DB 即可）
- health.py 中是否同时包含 Redis 健康检查端点

### Deferred Ideas (OUT OF SCOPE)
无
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASYNC-01 | Celery app 配置完成（升级至 5.5.1），worker 可正常启动并执行 task | Standard Stack + Architecture Patterns 部分覆盖 celery_app.py 配置、task 模块结构、worker 启动命令 |
| ASYNC-04 | Celery worker 健康检查端点可用，docker-compose 中包含 worker 服务 | Architecture Patterns 部分覆盖 health.py 路由设计、docker-compose 服务编排 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| celery | 5.5.1 | 分布式任务队列 | 决策 D-11 锁定；PyPI 确认可用 [VERIFIED: pip dry-run] |
| redis | 5.2.1 | Redis Python 客户端 | 决策 D-12 锁定；项目已安装 [VERIFIED: requirements.txt] |
| hiredis | 3.1.0 | Redis 高性能 C 解析器 | 决策 D-12 锁定；redis-py 自动利用 [VERIFIED: requirements.txt] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kombu | 5.5.x | Celery 消息传输层（自动依赖） | celery 5.5.1 依赖 kombu<5.6,>=5.5.2 [VERIFIED: pip dry-run] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| celery.control.inspect().ping() | celery-healthcheck PyPI 包 | 独立 HTTP server 更适合 K8s，但本项目直接通过 FastAPI 端点实现更简单 |
| prefork pool | solo pool | solo 池单线程无并发，仅适用于调试 |

**Installation:**
```bash
pip install celery==5.5.1
# redis==5.2.1 和 hiredis==3.1.0 已在 requirements.txt 中，保持不变
```

**Version verification:**
- celery 5.5.1: PyPI 可用，`pip install celery==5.5.1 --dry-run` 确认可下载 [VERIFIED: pip dry-run]
- 依赖 kombu 5.5.4 将自动安装 [VERIFIED: pip dry-run]

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── celery_app.py          # Celery app 实例（D-01）
│   ├── tasks/
│   │   ├── __init__.py        # 导出所有 task 模块
│   │   └── test_tasks.py      # 测试 task（D-02，本阶段）
│   ├── api/
│   │   └── v1/
│   │       ├── health.py      # 健康检查端点（D-08）
│   │       └── router.py      # 注册 health router
│   └── core/
│       ├── config.py          # redis_url 已存在
│       ├── redis.py           # Redis 客户端已存在
│       └── database.py        # DB session 工厂已存在
docker-compose.yml              # 新建（D-09）
```

### Pattern 1: Celery App 独立模块
**What:** 将 Celery app 实例定义在独立文件中，与 FastAPI app 分离
**When to use:** 所有 Celery 项目都应如此，避免循环导入
**Example:**
```python
# backend/app/celery_app.py
# Source: Celery 官方文档 + FastAPI 社区最佳实践
from __future__ import annotations

from celery import Celery

from backend.app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    'wage_adjust',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['backend.app.tasks.test_tasks'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    worker_hijack_root_logger=False,  # 不覆盖项目日志配置
)
```

### Pattern 2: Worker 进程中的 DB Session 管理
**What:** 使用 `worker_process_init` signal 在每个 fork 子进程中重建 DB engine，避免跨进程共享连接池
**When to use:** 任何使用 prefork 池且需要访问数据库的 Celery 任务
**Example:**
```python
# backend/app/celery_app.py 中添加
from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker_process(**kwargs):
    """Dispose engine after fork to get fresh connections per worker process."""
    from backend.app.core.database import engine
    engine.dispose()
```
[CITED: https://celery.school/sqlalchemy-session-celery-tasks]

### Pattern 3: Task 中获取独立 DB Session
**What:** 每个 task 函数独立获取 session 并在完成后关闭
**When to use:** 所有需要数据库访问的 Celery task
**Example:**
```python
# backend/app/tasks/test_tasks.py
from __future__ import annotations

from backend.app.celery_app import celery_app
from backend.app.core.database import SessionLocal


@celery_app.task(name='tasks.db_health_check')
def db_health_check() -> dict:
    """Test task: verify worker can independently connect to DB."""
    db = SessionLocal()
    try:
        result = db.execute(text('SELECT 1')).scalar()
        return {'status': 'ok', 'db_check': result == 1}
    finally:
        db.close()
```

### Pattern 4: 健康检查端点
**What:** 通过 `celery_app.control.inspect().ping(timeout=3)` 检测 worker 存活
**When to use:** 运维监控、负载均衡器探测
**Example:**
```python
# backend/app/api/v1/health.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/health', tags=['health'])


@router.get('/celery')
def celery_health() -> dict:
    """Check Celery worker online status. No auth required (D-06)."""
    try:
        inspector = celery_app.control.inspect(timeout=3)
        ping_result = inspector.ping()
    except Exception:
        logger.exception('Celery health check failed')
        ping_result = None

    if ping_result:
        worker_count = len(ping_result)
        # Strip hostnames for security (D-07)
        return {
            'status': 'healthy',
            'workers_online': worker_count,
            'checked_at': datetime.now(timezone.utc).isoformat(),
        }
    return {
        'status': 'unhealthy',
        'workers_online': 0,
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }
```
[CITED: https://docs.celeryq.dev/en/stable/reference/celery.app.control.html]

### Pattern 5: Docker Compose 服务编排
**What:** 三服务编排：redis + celery-worker + backend
**When to use:** 开发和部署环境
**Example:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: .
    command: uvicorn backend.app.main:app --host 0.0.0.0 --port 8011 --reload
    ports:
      - "8011:8011"
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - .:/app

  celery-worker:
    build: .
    command: celery -A backend.app.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - .:/app

volumes:
  redis_data:
```

### Anti-Patterns to Avoid
- **在 FastAPI main.py 中创建 Celery app：** 会导致循环导入和 worker 启动时加载不必要的 Web 中间件。Celery app 必须独立 [ASSUMED]
- **跨 fork 共享 SQLAlchemy engine：** prefork 模式下 Celery fork 子进程，数据库连接池不能跨进程共享，必须在 `worker_process_init` 中 dispose [CITED: https://celery.school/sqlalchemy-session-celery-tasks]
- **在 task 中使用 FastAPI 的 `Depends` 注入：** Celery task 运行在独立进程，不经过 FastAPI 依赖注入链。需直接调用 `SessionLocal()` [ASSUMED]
- **使用 pickle 序列化：** 安全风险，决策 D-04 已锁定 JSON 序列化 [CITED: Celery 安全文档]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 消息队列 | 自建基于 Redis pub/sub 的任务分发 | Celery | 重试、结果存储、并发控制、监控等功能需要数千行代码 |
| Worker 进程管理 | 自建 multiprocessing 管理 | Celery prefork pool | 进程生命周期、信号处理、graceful shutdown 极其复杂 |
| 任务结果存储 | 自建 Redis key 管理 | Celery result backend | 结果序列化、过期、清理都已内置 |
| 健康检查协议 | 自建心跳/探针机制 | `celery.control.inspect().ping()` | 内置广播机制，跨多 worker 自动发现 |

## Common Pitfalls

### Pitfall 1: Worker 启动时的导入错误
**What goes wrong:** `celery -A backend.app.celery_app worker` 报 `ModuleNotFoundError`
**Why it happens:** 工作目录不在项目根目录，或 `PYTHONPATH` 未包含项目根
**How to avoid:** docker-compose 中设置 `WORKDIR /app`；本地开发时从项目根目录启动
**Warning signs:** worker 启动后立即退出，日志中有 ImportError

### Pitfall 2: Fork 后的数据库连接错误
**What goes wrong:** Task 执行时出现 `OperationalError: connection already closed` 或连接池耗尽
**Why it happens:** prefork 模式 fork 时复制了父进程的 DB 连接池引用，fork 后这些连接不可用
**How to avoid:** 在 `worker_process_init` signal 中调用 `engine.dispose()`
**Warning signs:** 间歇性 DB 错误，worker 重启后暂时正常
[CITED: https://celery.school/sqlalchemy-session-celery-tasks]

### Pitfall 3: inspect().ping() 在 broker 不可用时挂起
**What goes wrong:** 健康检查端点长时间不返回，阻塞 API 线程
**Why it happens:** `inspect().ping()` 的 timeout 参数只控制等待 worker 响应的时间，不控制连接 broker 的超时
**How to avoid:** 在外层加 try/except 捕获异常；考虑使用 `asyncio.wait_for` 或线程超时包装。实际场景中如果 Redis broker 不可用，`redis-py` 自身的 `socket_timeout` 会在几秒内触发异常
**Warning signs:** 健康检查在 Redis 宕机时返回特别慢
[CITED: https://github.com/celery/celery/issues/5067]

### Pitfall 4: worker_hijack_root_logger 覆盖项目日志
**What goes wrong:** Celery worker 启动后项目自定义的日志格式和 handler 全部失效
**Why it happens:** Celery 默认接管 root logger
**How to avoid:** 设置 `worker_hijack_root_logger=False`
**Warning signs:** worker 日志格式突然变成 Celery 默认格式

### Pitfall 5: Task 模块未在 include 中注册
**What goes wrong:** 通过 API 发送 task 后 worker 报 `Received unregistered task`
**Why it happens:** Celery app 的 `include` 列表遗漏了 task 模块路径
**How to avoid:** 每添加新 task 文件都要在 `celery_app.py` 的 `include` 中注册，或使用 `autodiscover_tasks()`
**Warning signs:** task 发送成功（有 task_id），但 worker 不执行

## Code Examples

### 完整的 celery_app.py 配置
```python
# Source: Celery 5.5 官方文档 + 项目约定
from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from backend.app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    'wage_adjust',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        'backend.app.tasks.test_tasks',
    ],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_expires=3600,          # 结果保留 1 小时
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # 任务完成后再 ack，防止 worker 崩溃丢任务
    worker_prefetch_multiplier=1, # 每个 worker 预取 1 个任务，适合长耗时任务
    worker_hijack_root_logger=False,
)


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Dispose SQLAlchemy engine after fork for fresh connections."""
    from backend.app.core.database import engine
    engine.dispose()
```

### 注册 health router 到 api_router
```python
# backend/app/api/v1/router.py 中添加
from backend.app.api.v1.health import router as health_router
# ...
api_router.include_router(health_router)
```

### 在 main.py 已有的 /health 端点旁的关系说明
```
/health                     → main.py 中已有，返回 app 基本信息（无需修改）
/api/v1/health/celery       → 新建 health.py，返回 worker 状态（D-08）
```
注意：`/health` 是根路径上的已有端点（第 175 行 main.py），新的 `/api/v1/health/celery` 在 v1 API 前缀下，不冲突。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| celery 5.4.x | celery 5.5.1 | 2025 | Python 3.9 兼容改进，bug 修复 [CITED: PyPI celery changelog] |
| pickle 序列化 | JSON 序列化 | 长期趋势 | 安全性提升，跨语言兼容 |
| RabbitMQ broker | Redis broker | 项目选择 | Redis 同时做 broker+backend，简化运维 |

**Deprecated/outdated:**
- `CELERY_` 前缀配置（旧版）：现在使用小写 `task_serializer` 风格 [ASSUMED]
- `@app.task(bind=True)` 中的 `self.retry()`：仍然有效，但新增了 `autoretry_for` 声明式重试 [ASSUMED]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Celery app 放在独立模块可避免循环导入 | Anti-Patterns | 低 — 这是广泛接受的最佳实践 |
| A2 | FastAPI Depends 注入链在 Celery task 中不可用 | Anti-Patterns | 低 — Celery task 运行在独立进程中，不经过 ASGI |
| A3 | `CELERY_` 前缀配置已废弃 | State of the Art | 低 — Celery 4.0+ 切换到小写配置 |
| A4 | `autoretry_for` 声明式重试可用 | State of the Art | 低 — Celery 4.2+ 引入 |

## Open Questions

1. **Dockerfile 是否需要本阶段创建？**
   - What we know: docker-compose.yml 的 backend 和 celery-worker 服务都用 `build: .`，需要 Dockerfile
   - What's unclear: 项目中目前没有 Dockerfile，但 DEPLOY-04（Phase 24）也要求 Dockerfile
   - Recommendation: 本阶段创建一个基础 Dockerfile（仅后端），Phase 24 再完善。否则 docker-compose 无法工作

2. **SQLite 在 Celery prefork 模式下的限制**
   - What we know: 开发环境使用 SQLite；SQLite 对并发写入支持有限
   - What's unclear: prefork concurrency=2 时两个 worker 进程同时写 SQLite 是否会出现锁定
   - Recommendation: 测试 task 的 DB 操作使用只读查询（SELECT 1），避免并发写入问题；文档注明生产环境应使用 PostgreSQL

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | docker-compose 服务编排 | Yes | 29.3.1 | — |
| Docker Compose | 服务编排 | Yes | v5.1.1 | — |
| Redis (本地) | Celery broker/backend | No (未运行) | — | docker-compose 中的 redis 服务 |
| Python 3.9+ | Celery 5.5.1 运行时 | Yes (3.14 本地) | 3.14.0 | Docker 镜像中用 3.9 |
| celery 5.5.1 | 异步任务 | Yes (PyPI) | 5.5.1 | — |

**Missing dependencies with no fallback:**
- 无

**Missing dependencies with fallback:**
- Redis 本地未运行 — 通过 docker-compose 中的 redis 服务提供；或手动 `docker run -p 6379:6379 redis:7-alpine` 启动

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | 无独立 pytest.ini，使用默认配置 |
| Quick run command | `pytest backend/tests/test_core/ -x -q` |
| Full suite command | `pytest backend/tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASYNC-01 | celery_app 可导入，配置正确 | unit | `pytest backend/tests/test_core/test_celery_config.py -x` | No — Wave 0 |
| ASYNC-01 | test task 可被 worker 执行 | integration (manual) | `celery -A backend.app.celery_app worker` + 手动发送 task | manual-only |
| ASYNC-04 | /api/v1/health/celery 返回正确结构 | unit | `pytest backend/tests/test_api/test_health.py -x` | No — Wave 0 |
| ASYNC-04 | docker-compose up 启动全部服务 | smoke (manual) | `docker-compose up -d && docker-compose ps` | manual-only |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_core/test_celery_config.py backend/tests/test_api/test_health.py -x -q`
- **Per wave merge:** `pytest backend/tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_core/test_celery_config.py` — 验证 celery_app 可导入、配置值正确（ASYNC-01）
- [ ] `backend/tests/test_api/test_health.py` — 验证健康检查端点返回结构（ASYNC-04，mock inspect.ping）

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | 健康检查端点无需认证（D-06） |
| V3 Session Management | No | — |
| V4 Access Control | No | 健康检查端点公开访问 |
| V5 Input Validation | Yes | Task 参数使用 JSON 序列化，Celery 内置验证 |
| V6 Cryptography | No | — |

### Known Threat Patterns for Celery+Redis

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pickle 反序列化攻击 | Tampering | 使用 JSON 序列化（D-04），`accept_content=['json']` 拒绝 pickle |
| Redis 未授权访问 | Information Disclosure | docker-compose 内网通信；生产环境加 Redis AUTH |
| 健康检查信息泄露 | Information Disclosure | 不暴露 worker 主机名等敏感信息（D-07） |

## Project Constraints (from CLAUDE.md)

- 后端 Python + FastAPI，模块边界清晰
- 所有配置必须配置化，不硬编码
- 使用 `from __future__ import annotations` 开头
- API 版本化 `/api/v1/...`
- 函数参数和返回类型显式标注
- 错误处理使用 `HTTPException` + `build_error_response` 模式
- Settings 通过 `pydantic_settings.BaseSettings` 加载

## Sources

### Primary (HIGH confidence)
- requirements.txt — 确认现有依赖版本
- backend/app/core/config.py — 确认 redis_url 配置存在
- backend/app/core/redis.py — 确认 Redis 客户端模式
- backend/app/core/database.py — 确认 DB session 工厂模式
- backend/app/api/v1/router.py — 确认路由注册模式
- backend/app/main.py — 确认已有 /health 端点和 lifespan 模式
- pip install celery==5.5.1 --dry-run — 确认版本可用和依赖兼容

### Secondary (MEDIUM confidence)
- [Celery School: SQLAlchemy Session Handling](https://celery.school/sqlalchemy-session-celery-tasks) — DB 连接管理最佳实践
- [Celery 官方 control.inspect 文档](https://docs.celeryq.dev/en/stable/reference/celery.app.control.html) — ping() API
- [Celery issue #5067](https://github.com/celery/celery/issues/5067) — inspect hang 问题
- [OneUpTime: FastAPI+PostgreSQL+Celery Docker Compose](https://oneuptime.com/blog/post/2026-02-08-how-to-set-up-a-fastapi-postgresql-celery-stack-with-docker-compose/view) — docker-compose 编排参考

### Tertiary (LOW confidence)
- 无

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 版本已通过 pip 验证，依赖兼容性已确认
- Architecture: HIGH — 基于 Celery 官方文档和项目已有模式
- Pitfalls: HIGH — 基于官方 issue 和社区经验文章，已引用来源

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (30 days — Celery 生态稳定)
