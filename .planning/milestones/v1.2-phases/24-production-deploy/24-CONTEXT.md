# Phase 24: 生产部署配置 - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

通过 Docker 实现系统一键部署到生产环境。完善现有 Dockerfile 和 docker-compose.yml，新增前端 Nginx 容器，使用 gunicorn 替代 uvicorn 作为生产 ASGI 服务器。

</domain>

<decisions>
## Implementation Decisions

### 部署方式
- **D-01:** Docker 为主要部署方式。完善 Dockerfile + docker-compose.yml，支持 `docker-compose up` 一键启动全部服务
- **D-02:** 保留现有 `deploy/deploy.sh` 裸机部署脚本作为备用方案，不删除

### 数据库方案
- **D-03:** 生产环境使用外部 PostgreSQL，不在 docker-compose 中包含 PG 容器
- **D-04:** 通过 `DATABASE_URL` 环境变量连接外部 PostgreSQL 实例
- **D-05:** 开发环境可继续使用 SQLite，生产环境强制 PostgreSQL

### 前端服务
- **D-06:** 新增 Nginx 容器，使用多阶段构建：先 `npm run build`，再将 `dist/` 复制到 `nginx:alpine` 镜像
- **D-07:** Nginx 容器同时做 API 反向代理（`/api/` → backend:8011）和前端静态文件托管
- **D-08:** 前端容器对外暴露 8080 端口

### 环境配置
- **D-09:** 继续使用 `.env` 文件管理配置，提供 `.env.production.example` 模板
- **D-10:** `.env.production.example` 包含所有生产必需变量及说明注释

### 生产服务器配置
- **D-11:** 后端使用 `gunicorn -k uvicorn.workers.UvicornWorker` 启动，配置在 `requirements-prod.txt`
- **D-12:** 创建 `requirements-prod.txt`，在 `requirements.txt` 基础上增加 gunicorn
- **D-13:** 添加 `.dockerignore` 排除 `.venv/`、`node_modules/`、`uploads/`、`.git/` 等

### Claude's Discretion
- gunicorn worker 数量配置（默认 4）
- Nginx 缓存策略和超时设置
- Docker 健康检查配置细节
- 容器日志管理方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 部署需求
- `.planning/REQUIREMENTS.md` — DEPLOY-03（gunicorn+uvicorn worker）和 DEPLOY-04（Dockerfile+docker-compose）需求定义

### 现有部署文件
- `Dockerfile` — 现有基础版，需升级为多阶段构建 + gunicorn
- `docker-compose.yml` — 现有版本含 redis、backend、celery-worker，需新增 frontend 服务
- `deploy/deploy.sh` — 裸机部署参考，Nginx 配置和 systemd 服务定义可复用
- `.env.example` — 现有环境变量模板

### 技术栈参考
- `.planning/codebase/STACK.md` — 项目技术栈完整说明
- `backend/app/core/config.py` — pydantic-settings 配置定义，所有环境变量
- `backend/app/celery_app.py` — Celery 应用配置，broker URL 设置

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/deploy.sh` — Nginx 配置块（反向代理、静态文件缓存、超时设置）可直接复用到 Nginx 容器配置
- `docker-compose.yml` — 已有 redis + backend + celery-worker 服务定义，需在此基础上扩展
- `Dockerfile` — 已有基础结构，需升级

### Established Patterns
- 配置通过 `pydantic-settings` ��� `.env` 加载，`get_settings()` LRU 缓存
- Celery broker 通过 `REDIS_URL` 环境变量配置
- 前端 API 地址通过 `VITE_API_BASE_URL` 构建时注入
- `backend/app/main.py` 的 `validate_startup_config()` 在生产环境会检查弱密码并拒绝启动

### Integration Points
- `backend/app/main.py:create_app()` — FastAPI 应用入口
- `backend/app/celery_app` — Celery 应用入口
- `frontend/vite.config.ts` — 前端构建配置，API 代理设置

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

*Phase: 24-production-deploy*
*Context gathered: 2026-04-16*
