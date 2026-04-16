# Phase 19: Celery+Redis 异步基础设施 - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

搭建 Celery 异步任务基础设施：Celery app 配置、worker 可独立启动、测试 task 验证端到端链路、健康检查端点、docker-compose 服务定义。不包含任何业务 task 迁移（AI 评估、批量导入等异步化属于后续阶段）。

</domain>

<decisions>
## Implementation Decisions

### Celery 应用结构
- **D-01:** Celery app 实例放在 `backend/app/celery_app.py`，独立于 FastAPI main.py，启动命令 `celery -A backend.app.celery_app worker`
- **D-02:** Task 模块按业务域分文件，放在 `backend/app/tasks/` 目录下（如 evaluation_tasks.py、import_tasks.py），本阶段先创建一个包含 DB 操作的测试 task
- **D-03:** Broker 和 result backend 均复用 `config.py` 中已有的 `redis_url`（redis://localhost:6379/0），不新增独立配置
- **D-04:** Task 序列化格式使用 JSON（安全、可读、跨语言兼容，且本项目 task 参数都是简单类型）

### 健康检查设计
- **D-05:** 使用 `celery.control.inspect().ping()` 检测 worker 在线状态，设置 3 秒超时防止阻塞 API
- **D-06:** 健康检查端点无需认证，公开访问，便于运维监控和负载均衡器探测
- **D-07:** 返回基础状态信息：worker 在线数量、整体状态（healthy/unhealthy）、检查时间戳。不暴露 worker 主机名等敏感信息
- **D-08:** 新建 `backend/app/api/v1/health.py` 路由文件，路径 `/api/v1/health/celery`。后续可扩展 DB、Redis 等健康检查

### Docker 部署方案
- **D-09:** docker-compose.yml 包含三个服务：redis、celery-worker、backend API，一次 `docker-compose up` 全部启动
- **D-10:** Celery worker 使用 prefork 并发模式（Celery 默认），开发环境 concurrency=2

### Celery 版本升级
- **D-11:** 直接将 celery 从 5.4.0 升级到 5.5.1（小版本升级，向后兼容，含 Python 3.9 兼容改进）
- **D-12:** redis==5.2.1 和 hiredis==3.1.0 保持现有版本不变，与 Celery 5.5.1 兼容

### Claude's Discretion
- docker-compose.yml 中的网络配置和卷挂载细节
- Celery 配置中的其他调优参数（task_acks_late、worker_prefetch_multiplier 等）
- 测试 task 的具体 DB 操作内容（只要能验证 worker 独立连接 DB 即可）
- health.py 中是否同时包含 Redis 健康检查端点

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Celery 配置
- `backend/app/core/config.py` — Settings 类中的 `redis_url` 配置，Celery broker/backend 将复用此值
- `backend/app/core/redis.py` — 现有 Redis 客户端单例实现，了解连接模式

### 依赖
- `requirements.txt` — celery==5.4.0（需升级至 5.5.1）、redis==5.2.1、hiredis==3.1.0

### 应用入口
- `backend/app/main.py` — FastAPI 应用工厂，了解 lifespan、中间件注册模式
- `backend/app/api/v1/__init__.py` — API 路由注册方式，新增 health.py 路由需在此注册

### 数据库
- `backend/app/core/database.py` — SQLAlchemy engine 和 session 工厂，测试 task 需独立获取 DB session

### 需求定义
- `.planning/REQUIREMENTS.md` §ASYNC-01 — Celery app 配置完成，worker 可正常启动
- `.planning/REQUIREMENTS.md` §ASYNC-04 — Celery worker 健康检查端点可用，docker-compose 包含 worker 服务

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/core/redis.py`: Redis 客户端单例，`get_redis()` 可用于验证 Redis 连接
- `backend/app/core/config.py`: `Settings.redis_url` 已配置，Celery 直接复用
- `.env.example`: 已包含 `REDIS_URL=redis://localhost:6379/0`

### Established Patterns
- Settings 通过 `pydantic_settings.BaseSettings` 从 `.env` 加载，`get_settings()` LRU 缓存
- API 路由在 `backend/app/api/v1/` 下按域分文件，通过 `__init__.py` 注册到 `api_router`
- 数据库 session 通过 `get_db()` 依赖注入获取

### Integration Points
- `backend/app/api/v1/__init__.py` — 注册新的 health router
- `requirements.txt` — 升级 celery 版本
- 项目根目录 — 新建 docker-compose.yml

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

*Phase: 19-celery-redis*
*Context gathered: 2026-04-08*
