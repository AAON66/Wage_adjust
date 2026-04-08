# Phase 19: Celery+Redis 异步基础设施 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 19-celery-redis
**Areas discussed:** Celery 应用结构, 健康检查设计, Docker 部署方案, Celery 版本升级

---

## Celery 应用结构

### App 实例位置

| Option | Description | Selected |
|--------|-------------|----------|
| backend/app/celery_app.py | 独立文件，职责清晰，不与 FastAPI 耦合 | ✓ |
| backend/app/core/celery.py | 放在 core/ 下与 redis.py 并列 | |
| backend/app/tasks/__init__.py | 在 tasks 包中创建实例并自动发现 | |

**User's choice:** backend/app/celery_app.py
**Notes:** 启动命令 celery -A backend.app.celery_app worker

### Task 模块组织

| Option | Description | Selected |
|--------|-------------|----------|
| 按业务域分文件 | tasks/ 目录下按域分文件，本阶段创建测试 task | ✓ |
| 单文件 tasks.py | 所有 task 放一个文件 | |

**User's choice:** 按业务域分文件

### Broker/Backend 配置

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 redis_url | broker 和 backend 都用 config.py 的 redis_url | ✓ |
| 独立配置 | 新增 CELERY_BROKER_URL 和 CELERY_RESULT_BACKEND 环境变量 | |

**User's choice:** 复用 redis_url

### 序列化格式

| Option | Description | Selected |
|--------|-------------|----------|
| JSON | 安全可读，Celery 默认，参数都是简单类型 | ✓ |
| msgpack | 更紧凑高效，但需额外依赖 | |

**User's choice:** JSON

### 测试 Task 内容

| Option | Description | Selected |
|--------|-------------|----------|
| 简单加法 task | 纯验证 worker 可执行任务 | |
| 包含 DB 操作的 task | 验证 worker 可独立连接 DB，更接近实际场景 | ✓ |

**User's choice:** 包含 DB 操作的 task

---

## 健康检查设计

### 检测方式

| Option | Description | Selected |
|--------|-------------|----------|
| celery.control.inspect | 内置 inspect().ping() 检测在线 worker，3 秒超时 | ✓ |
| Redis 键值心跳 | worker 定期写心跳，健康检查读取判断 | |
| 发送探针 task | 提交轻量 task 等待结果，端到端验证 | |

**User's choice:** celery.control.inspect

### 认证要求

| Option | Description | Selected |
|--------|-------------|----------|
| 无需认证 | 公开访问，便于运维监控 | ✓ |
| 需要认证 | 仅登录用户可访问 | |

**User's choice:** 无需认证

### 响应内容

| Option | Description | Selected |
|--------|-------------|----------|
| 基础状态 | worker 数量、状态、检查时间，不暴露敏感信息 | ✓ |
| 详细信息 | 每个 worker 主机名、活跃 task 数、队列深度等 | |
| 仅状态码 | 只返回 200/503，无 body | |

**User's choice:** 基础状态

### 路由位置

| Option | Description | Selected |
|--------|-------------|----------|
| 新建 health.py | api/v1/ 下新建专用路由文件 | ✓ |
| 放在现有 router | 加到 dashboard.py 或 public.py 中 | |

**User's choice:** 新建 health.py

---

## Docker 部署方案

### 服务组成

| Option | Description | Selected |
|--------|-------------|----------|
| worker + Redis + backend | 完整开发环境，一键启动 | ✓ |
| 仅 worker + Redis | backend 用本地 uvicorn | |
| 仅 worker | Redis 假定已外部运行 | |

**User's choice:** worker + Redis + backend

### 并发模式

| Option | Description | Selected |
|--------|-------------|----------|
| prefork | 多进程模式，Celery 默认，开发环境 concurrency=2 | ✓ |
| solo | 单线程，调试友好但不适合生产 | |

**User's choice:** prefork

---

## Celery 版本升级

### 升级策略

| Option | Description | Selected |
|--------|-------------|----------|
| 直接升级到 5.5.1 | 小版本升级，向后兼容 | ✓ |
| 先验证再升级 | 先用 5.4.0 搭建，确认后再升级 | |

**User's choice:** 直接升级到 5.5.1

### 依赖同步

| Option | Description | Selected |
|--------|-------------|----------|
| 保持现有版本 | redis==5.2.1、hiredis==3.1.0 不变 | ✓ |
| 一并升级到最新 | 全套依赖升到最新版本 | |

**User's choice:** 保持现有版本

---

## Claude's Discretion

- docker-compose.yml 网络配置和卷挂载细节
- Celery 调优参数
- 测试 task 具体 DB 操作内容
- health.py 是否同时包含 Redis 健康检查

## Deferred Ideas

None
