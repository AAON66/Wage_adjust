# Phase 24: 生产部署配置 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 24-production-deploy
**Areas discussed:** 部署方式, 数据库方案, 前端服务, 环境配置

---

## 部署方式

| Option | Description | Selected |
|--------|-------------|----------|
| Docker 为主 (推荐) | 完善 Dockerfile + docker-compose.yml，支持一键 docker-compose up 启动全部服务。裸机脚本保留作备用 | ✓ |
| 裸机为主 | 以现有 deploy.sh 为主，Docker 只作开发环境用。生产用 systemd+Nginx | |
| 两套并行 | Docker 和裸机部署都完善，用户自选 | |

**User's choice:** Docker 为主
**Notes:** 无

---

## 数据库方案

| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL 外部 (推荐) | 数据库不容器化，docker-compose 不包含 PG，通过 DATABASE_URL 连接外部实例。更安全可靠 | ✓ |
| PostgreSQL 容器化 | docker-compose 内包含 PG 容器，数据持久化到 volume。一键启动更方便但数据安全性降低 | |
| 继续用 SQLite | 不引入 PostgreSQL，SQLite 文件挂载到 volume。简单但不适合并发 | |

**User's choice:** PostgreSQL 外部
**Notes:** 无

---

## 前端服务

| Option | Description | Selected |
|--------|-------------|----------|
| Nginx 容器 (推荐) | 新增一个 Nginx 容器，多阶段构建：先 npm build，再将 dist 复制到 nginx:alpine 镜像。同时做 API 反向代理 | ✓ |
| 后端托管静态文件 | FastAPI 直接 serve 前端构建产物，不需要额外 Nginx 容器。简单但性能较差 | |
| 外部 Nginx | 沿用服务器已有的 Nginx，不容器化前端。docker-compose 只管后端服务 | |

**User's choice:** Nginx 容器
**Notes:** 无

---

## 环境配置

| Option | Description | Selected |
|--------|-------------|----------|
| .env 文件 (推荐) | 继续用 .env 文件，提供 .env.production.example 模板，部署时手动配置。简单直接 | ✓ |
| Docker secrets | 使用 Docker secrets 注入敏感配置，更安全但复杂度高 | |
| 环境变量直接写在 compose | 在 docker-compose.yml 中直接配置 environment 块，不用外部文件 | |

**User's choice:** .env 文件（用户要求全部按推荐方案，未逐一确认）
**Notes:** 用户明确表示"全部都按照推荐来不需要问我"

---

## Claude's Discretion

- gunicorn worker 数量
- Nginx 缓存策略和超时
- Docker 健康检查细节
- 容器日志管理

## Deferred Ideas

无
