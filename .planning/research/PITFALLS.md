# Pitfalls Research: v1.2 Feature Integration

**Domain:** 企业调薪平台 v1.2 新功能集成 (Celery 启用、Python 3.9 兼容、部署优化、共享拒绝处理、统一导入)
**Researched:** 2026-04-07
**Confidence:** HIGH (基于代码审计 + 官方文档验证)

> 覆盖 v1.2 五个新增功能的集成陷阱。v1.0/v1.1 基础陷阱（LLM 管道、安全性、批量导入、审批流程、会话管理、资格引擎、文件共享）见之前版本的研究文档。

---

## Critical Pitfalls

### Pitfall 1: SQLAlchemy `Mapped[str | None]` 在 Python 3.9 上运行时崩溃

**What goes wrong:**
全部 models 使用 `Mapped[str | None]` PEP 604 联合类型语法（代码审计确认 20+ 个 model 文件、80+ 处用法）。虽然每个文件都有 `from __future__ import annotations`，SQLAlchemy 2.0 在运行时会对 `Mapped` 类型参数调用 `eval()`，绕过 `__future__` 的延迟求值。在 Python 3.9 上，`str | None` 会抛出 `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`。应用根本无法启动。

**Why it happens:**
`from __future__ import annotations` 只阻止 Python 解释器本身求值注解。但 SQLAlchemy 2.0 的 `Mapped` 类型系统在 `DeclarativeBase` 初始化时主动 `eval()` 注解字符串来推断列类型和 nullable 属性。Python 3.9 的 `eval()` 不支持 `|` 运算符用于类型。

**How to avoid:**
1. 全局搜索替换所有 model 文件中 `Mapped[X | None]` 为 `Mapped[Optional[X]]`
2. 添加 `from typing import Optional` 到每个修改的文件
3. 在 CI 中强制用 Python 3.9 运行 `python -c "from backend.app.models import *"` 验证所有 model 可导入
4. 注意：普通函数签名中的 `str | None` 因为 `__future__` 的存在是安全的，不需要修改

**Warning signs:**
- 应用启动时立即崩溃，错误发生在 import 阶段
- 错误堆栈指向 `sqlalchemy.orm.decl_api` 或 `typing._eval_type`

**Phase to address:**
Python 3.9 兼容性 phase — 必须在所有其他功能之前完成，否则应用无法启动。

---

### Pitfall 2: Pydantic v2 Schema 同样受 `str | None` 运行时求值影响

**What goes wrong:**
代码审计发现 schemas 目录有 361 处 PEP 604 联合类型语法（`str | None`, `int | None` 等分布在 81 个文件中）。Pydantic v2 同样在运行时 `eval()` 注解来构建验证 schema。在 Python 3.9 上，所有 Pydantic BaseModel 子类定义都会失败。

**Why it happens:**
与 SQLAlchemy 相同原因：Pydantic v2 的 `ModelMetaclass` 在类创建时调用 `typing.get_type_hints()` 或等效机制对字段注解进行运行时求值，绕过 `__future__` 的延迟求值。

**How to avoid:**
1. 与 models 同步，全局替换所有 schema 文件中的 `X | None` 为 `Optional[X]`
2. 注意 `config.py` 中的 `Settings` 类（`pydantic_settings.BaseSettings` 子类）也需要修改：
   - `backend_cors_origins: list[str]` -- 这个因为 `__future__` 安全，但需验证
   - `_token: str | None = None`（在 `feishu_service.py` line 38）需要修改
3. 跑完整 pytest 验证所有 schema 可正常初始化

**Warning signs:**
- `TypeError` 在 schema import 时发生
- FastAPI 路由注册时因 schema 类创建失败而报错

**Phase to address:**
Python 3.9 兼容性 phase — 与 Pitfall 1 在同一 phase 一并处理。

---

### Pitfall 3: SQLite 不执行 `ON DELETE CASCADE` — 共享拒绝删除产生孤儿记录

**What goes wrong:**
`SharingRequest` 的 ForeignKey 配置了 `ondelete='CASCADE'`（sharing_request.py lines 21/24/27/30）。但代码审计确认 **`database.py` 中没有 `PRAGMA foreign_keys = ON`**。在 SQLite 开发环境中：
- 删除 `UploadedFile` 时，数据库级别的 `ON DELETE CASCADE` 完全静默失败
- `SharingRequest` 记录变成孤儿，`requester_file_id` 指向已删除的文件
- 查询 `list_requests()` 中的 JOIN 可能返回空结果或 IntegrityError

v1.2 的"文件共享拒绝后自动删除 requester 文件"功能直接依赖正确的级联删除行为。

**Why it happens:**
SQLite 默认关闭外键约束执行。必须在每次连接时执行 `PRAGMA foreign_keys = ON`。项目中 `_engine_kwargs` 只设置了 `check_same_thread: False`，遗漏了外键激活。

**How to avoid:**
1. 在 `database.py` 中为 SQLite 添加连接事件监听器：
   ```python
   from sqlalchemy import event
   @event.listens_for(Engine, "connect")
   def _set_sqlite_pragma(dbapi_conn, connection_record):
       if 'sqlite' in str(dbapi_conn.__class__.__module__):
           cursor = dbapi_conn.cursor()
           cursor.execute("PRAGMA foreign_keys=ON")
           cursor.close()
   ```
2. 或者：在共享拒绝处理中使用 ORM 级别显式删除，不依赖数据库级联
3. 添加集成测试：删除文件后断言关联的 `SharingRequest` 也被清理
4. 同时检查现有 `UploadedFile.contributors` 的 ORM cascade（`cascade='all, delete-orphan'`）是否覆盖了所有需要清理的关系

**Warning signs:**
- 数据库中 `requester_file_id` 指向不存在的 `uploaded_files.id`
- 共享请求列表查询时出现空结果（JOIN 目标不存在）
- 删除父记录后子表记录数不减少

**Phase to address:**
文件共享拒绝处理 phase — 在实现删除逻辑前必须先修复外键约束。

---

### Pitfall 4: Celery Worker 与 FastAPI 共享 DB Session/Engine 导致连接问题

**What goes wrong:**
当前 `database.py` 在模块级别创建全局 Engine 和 SessionLocal（line 56-57）。Celery worker 作为独立进程 fork 时，会继承这些全局对象。问题：
- SQLite：`check_same_thread=False` 允许跨线程，但 fork 后的子进程与父进程共享文件描述符可能导致 `database is locked`
- PostgreSQL：fork 后连接池中的连接变为无效（TCP 连接属于父进程），导致 `OperationalError`
- Celery task 内的 Session 生命周期与 FastAPI 请求的 `get_db_session()` 完全不同（无自动清理）

**Why it happens:**
Python multiprocessing（Celery 默认用 prefork）在 fork 时复制父进程的文件描述符和内存，但数据库连接是有状态的 TCP/文件句柄，不能安全地跨进程共享。

**How to avoid:**
1. 为 Celery worker 创建独立的 Session 工厂，在 `worker_process_init` 信号中初始化：
   ```python
   from celery.signals import worker_process_init
   @worker_process_init.connect
   def init_worker_db(**kwargs):
       global worker_engine, WorkerSessionLocal
       worker_engine = create_db_engine()
       WorkerSessionLocal = sessionmaker(bind=worker_engine, ...)
   ```
2. 每个 task 内显式创建和关闭 Session：
   ```python
   @shared_task
   def my_task():
       db = WorkerSessionLocal()
       try:
           # business logic
           db.commit()
       finally:
           db.close()
   ```
3. 绝对不在 Celery task 中使用 FastAPI 的 `Depends(get_db_session)`
4. 不要在 task 中使用 `async def`

**Warning signs:**
- Worker 启动后数据库操作间歇性失败
- `OperationalError: database is locked`（SQLite）或 `OperationalError: connection already closed`（PostgreSQL）
- Task 超时但无明确错误

**Phase to address:**
Celery 启用 phase — 基础架构搭建时就要确立正确的 Session 管理模式。

---

### Pitfall 5: Celery Task 注册失败 — autodiscover 与项目结构不匹配

**What goes wrong:**
当前项目中没有任何 Celery 相关代码（grep "celery|Celery" 在 backend 目录返回零结果）。业务逻辑全部在 `services/` 目录中。如果按 Celery 默认约定将 task 放在各 package 的 `tasks.py` 中，项目结构为扁平 service 模式（无子 package），autodiscover 无法工作。

**Why it happens:**
`autodiscover_tasks()` 默认扫描每个 package 下的 `tasks.py`。但 `backend/app/services/` 不是 package 集合，而是单个 package 内的多个模块文件。

**How to avoid:**
1. 创建独立的 `backend/app/tasks/` package 集中管理所有 Celery task
2. Task 文件调用 service 层方法，不重复实现业务逻辑
3. 在 Celery app 初始化时显式指定 autodiscover 路径：
   ```python
   celery_app.autodiscover_tasks(['backend.app.tasks'])
   ```
4. 或使用 `include` 参数显式列出：
   ```python
   celery_app = Celery('wage_adjust', include=['backend.app.tasks.evaluation_tasks', ...])
   ```
5. 使用 `@shared_task` 装饰器而非 `@celery_app.task`

**Warning signs:**
- Worker 启动日志中 `[tasks]` 列表为空
- `.delay()` 调用抛出 `celery.exceptions.NotRegistered`
- Worker 运行但无 task 被执行

**Phase to address:**
Celery 启用 phase — 项目结构设计阶段。

---

### Pitfall 6: 共享拒绝后删除文件未清理物理存储

**What goes wrong:**
`reject_request()` 当前只更新 `SharingRequest.status = 'rejected'`（sharing_service.py line 183）。v1.2 要实现"拒绝后自动删除 requester 的文件"。如果只删除 `UploadedFile` 数据库记录而不删除磁盘上的实际文件：
- `uploads/` 目录持续增长（孤儿文件）
- `storage_key` 唯一约束（uploaded_file.py line 17）：重新上传相同路径的文件会冲突

**Why it happens:**
ORM `session.delete()` 只处理数据库记录。`LocalStorageService`（当前使用本地文件系统）与 ORM 删除是分离的，没有自动钩子。

**How to avoid:**
1. 删除流程顺序：获取 `storage_key` -> 删除 DB 记录并 commit -> 删除物理文件
2. 物理文件删除用 try/except 包裹，记录日志但不阻塞（文件可能已被手动清理）
3. 添加 Celery 定期清理任务（beat），扫描 uploads 目录中无 DB 记录对应的孤儿文件
4. 事务顺序至关重要：先 commit DB 删除，再删物理文件。反过来会导致 DB 回滚但文件已删的不一致

**Warning signs:**
- `uploads/` 目录大小持续增长
- `IntegrityError: UNIQUE constraint failed: uploaded_files.storage_key`

**Phase to address:**
文件共享拒绝处理 phase

---

## Moderate Pitfalls

### Pitfall 7: 生产部署使用 `uvicorn --reload` 或单 Worker

**What goes wrong:**
当前启动命令 `uvicorn backend.app.main:app --reload`（见 CLAUDE.md）。生产环境中单进程无法利用多核 CPU，进程崩溃后无自动恢复。

**How to avoid:**
1. 使用 `gunicorn` + `uvicorn.workers.UvicornWorker`
2. 不要在 gunicorn 和 uvicorn 两层都配置 workers（双重 worker 陷阱 = 进程倍增）
3. `--timeout` 设为 120+ 秒覆盖 DeepSeek API 超时（当前 evaluation_timeout=120s）
4. 前置 Nginx 做反向代理

**Phase to address:** 部署优化 phase

---

### Pitfall 8: Celery Redis 连接与现有 Rate Limiter 共用 DB 0

**What goes wrong:**
当前 `redis_url = "redis://localhost:6379/0"` 被 Rate Limiter 使用。如果 Celery broker 也用 db 0：
- `FLUSHDB` 操作会同时清除限流数据和任务队列
- Key 命名空间冲突

**How to avoid:**
- Rate limiter / cache: `redis://localhost:6379/0`
- Celery broker: `redis://localhost:6379/1`
- Celery result backend: `redis://localhost:6379/2`
- 在 `config.py` 中增加 `celery_broker_url` 和 `celery_result_backend` 配置项
- 设置 `result_expires` 避免 Redis 内存无限增长

**Phase to address:** Celery 启用 phase

---

### Pitfall 9: 飞书多维表格 API 分页拉取无频率限制

**What goes wrong:**
`_fetch_all_records` 方法在 while 循环中连续发请求（feishu_service.py line 104-148），无任何速率控制。飞书对自定义应用有频率限制（具体值因 API 和套餐而异）。大表格分页拉取可能触发限流。

当前代码只处理了业务错误码（`code != 0`），但没有处理 HTTP 429 状态码或飞书的限流错误码 `99991400`。

**How to avoid:**
1. 在分页循环中添加请求间隔（如 `time.sleep(0.6)`）
2. 检测限流错误码后实现指数退避重试
3. 将飞书同步任务迁移到 Celery，利用内置重试机制
4. 缓存 token 已正确实现（line 38-60），无需改动

**Phase to address:** Celery 启用 phase（飞书任务异步化）+ 统一导入 phase

---

### Pitfall 10: 统一导入页面合并端点时破坏幂等性

**What goes wrong:**
当前各导入功能独立运行，各有幂等性保障（基于 employee_no 的 upsert）。统一导入页面如果：
- 用同步方式串行调用多个导入 API：超时风险
- 部分成功部分失败：无法整体回滚，用户不知道哪些成功了
- 用户误重复提交：已成功部分不应重复执行

**How to avoid:**
1. 统一导入使用 Celery task 异步执行，返回 task_id
2. 前端轮询 task 状态显示进度
3. 每个子导入保留原有幂等机制
4. 导入 job 记录详细的逐行结果（成功/失败/跳过），支持查看和下载

**Phase to address:** 统一导入 phase（依赖 Celery 启用完成后）

---

### Pitfall 11: `lru_cache(get_settings)` 在 Gunicorn prefork 后缓存不刷新

**What goes wrong:**
`get_settings()` 使用 `@lru_cache` 装饰器（config.py line 109）。Gunicorn prefork 模式下，父进程初始化时缓存的 Settings 实例会被 fork 到所有 worker。如果需要不同 worker 使用不同配置（如动态环境变量），缓存不会刷新。

**How to avoid:**
- 对于当前场景（所有 worker 共享同一配置）这是安全的
- 但 Celery worker 如果也导入了 `get_settings()`，确保 `.env` 文件在 worker 启动目录可访问
- 如果后续需要热更新配置，需要移除 `lru_cache` 或添加缓存失效机制

**Phase to address:** 部署优化 phase（低优先级，监控即可）

---

### Pitfall 12: CORS 配置缺少生产环境域名

**What goes wrong:**
`backend_cors_origins` 默认只有 localhost 地址（config.py lines 56-66）。部署到生产后前端跨域请求会被拒绝。

**How to avoid:**
- 确保 `.env` 中的 `BACKEND_CORS_ORIGINS` 包含生产前端域名
- 不使用 `["*"]`（安全风险，尤其是 JWT auth 场景）
- 部署 checklist 中加入 CORS 验证

**Phase to address:** 部署优化 phase

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| SQLite `PRAGMA foreign_keys` 未启用 | 开发方便 | 级联删除静默失败，数据不一致 | Never — 必须修复 |
| `Mapped[str \| None]` 依赖 `__future__` | 代码简洁 | Python 3.9 完全不可用 | 仅当确定不降级到 3.9 |
| 同步 httpx 调用飞书 API 无并发 | 实现简单 | 大数据量同步耗时长 | MVP 阶段可接受 |
| 全局 Engine/Session 模块级初始化 | FastAPI 启动简单 | Celery fork 后连接不安全 | 无 Celery 时 OK |
| `lru_cache` Settings | 避免重复 IO | fork 后缓存不刷新 | 所有 worker 配置相同时 OK |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Celery + SQLAlchemy (prefork) | 直接导入 FastAPI 的全局 Engine/SessionLocal | `worker_process_init` 信号中创建独立 Engine |
| Celery + Redis | Broker 和 Rate Limiter 共用 db 0 | 分配不同 Redis DB（0/1/2） |
| Celery task + DB 事务 | Task 内不 commit 也不 close Session | 每个 task 用 try/finally 管理 Session 生命周期 |
| Gunicorn + Uvicorn | 两层同时配置 workers 导致进程倍增 | 只在 Gunicorn 层配 workers |
| 飞书 API + httpx | 只检查 `data['code'] != 0`，忽略 HTTP 层错误 | 同时处理 HTTP 状态码和飞书业务错误码 |
| 飞书 token | 每次请求都获取新 token（浪费配额） | 缓存至接近过期（当前实现正确） |
| Alembic + 新 Model | model 变更后忘记生成迁移 | model 变更后立即 `alembic revision --autogenerate` |
| UploadedFile 删除 | 只删 DB 记录不删物理文件 | DB commit 后再删物理文件，异常不阻塞 |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 飞书全量拉取无限流 | 同步任务耗时超 5 分钟 | 添加 page 间延迟 + Celery 异步化 | 表格超过 5000 条记录 |
| Celery task 同步调用 DeepSeek 阻塞 worker | Worker 池耗尽 | 合理配置 worker 并发数 + task timeout | 并发评估超 worker 数 |
| 统一导入大 Excel 同步解析 | 请求超时 | Celery 异步解析 | Excel 超过 1000 行 |
| 单 uvicorn worker | CPU 利用率低 | Gunicorn 多 worker | 并发请求 > 10 |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Redis 无密码暴露 | 任何人可连接并执行 task / 读取缓存 | 生产 Redis 配密码 + 绑定内网 IP |
| `.env` 打包进 Docker 镜像 | 密钥泄露到镜像仓库 | Docker secrets 或运行时环境变量注入 |
| CORS `["*"]` | 任意域可调 API（含 JWT 认证接口） | 精确列出允许的前端域名 |
| Gunicorn 绑定 `0.0.0.0` 无反向代理 | 直接暴露应用服务器 | Nginx 反代 + gunicorn 绑 127.0.0.1 |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 统一导入无进度反馈 | 用户不知是否在执行，重复提交 | Celery task ID + 前端轮询进度 |
| 共享拒绝后文件无提示消失 | 用户困惑文件去哪了 | 明确 toast + 操作日志记录 |
| 导入错误只显示"失败" | 用户不知如何修正 | 逐行错误详情 + 可下载错误报告 |
| 飞书同步无结果反馈 | 管理员不知同步效果 | 同步完成后显示统计（新增/更新/跳过/失败） |

## "Looks Done But Isn't" Checklist

- [ ] **Python 3.9 兼容:** 所有 `Mapped[X | None]` 已替换 — 验证：Python 3.9 下 `python -c "from backend.app.models import *; from backend.app.schemas import *"`
- [ ] **SQLite FK 约束:** `PRAGMA foreign_keys=ON` 已配置 — 验证：删除父记录后子表记录自动清理
- [ ] **Celery task 注册:** Worker 启动日志列出所有 task — 验证：`celery inspect registered`
- [ ] **Celery DB Session 隔离:** Worker 使用独立 Engine — 验证：FastAPI + Worker 同时运行 + 执行 task 无错误
- [ ] **共享拒绝删除:** DB 记录 + 物理文件都清理 — 验证：拒绝后检查 uploads 目录
- [ ] **Redis DB 隔离:** Celery broker 不在 db 0 — 验证：`redis-cli -n 1 KEYS '*'` 有 Celery key
- [ ] **CORS 配置:** 包含生产前端域名 — 验证：生产环境浏览器控制台无跨域错误
- [ ] **Gunicorn worker 数:** 未双重配置 — 验证：`ps aux | grep uvicorn` 进程数 = 配置数
- [ ] **飞书限流处理:** 分页有间隔且处理 429 — 验证：大表同步无限流报错

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `Mapped[str \| None]` 崩溃 | LOW | 全局搜索替换 + 测试，无需数据迁移 |
| SQLite FK 未启用 — 孤儿数据 | MEDIUM | 启用 FK + 编写清理脚本扫描删除孤儿记录 |
| Celery Worker 连接池问题 | LOW | 重启 worker + 修改 Session 工厂 |
| 物理文件孤儿 | LOW | 定期清理脚本对比 DB storage_key 和 uploads 目录 |
| CORS 配置错误 | LOW | 更新 .env + 重启服务 |
| Redis DB 冲突 | LOW | 修改 broker URL + 重启 worker |
| 飞书限流 | LOW | 添加延迟 + 重试 + 重新执行同步 |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1: `Mapped[str \| None]` 崩溃 | Python 3.9 兼容性 | Python 3.9 下 model/schema 全部可导入 |
| P2: Pydantic `X \| None` 崩溃 | Python 3.9 兼容性 | Python 3.9 下 pytest 全部通过 |
| P3: SQLite FK 不生效 | 共享拒绝处理 | 集成测试验证级联删除 |
| P4: Celery Worker DB Session | Celery 启用 | Worker + FastAPI 同时运行无 DB 错误 |
| P5: Celery task 注册 | Celery 启用 | `inspect registered` 输出完整 task 列表 |
| P6: 物理文件未清理 | 共享拒绝处理 | 拒绝后 uploads 目录文件数减少 |
| P7: 单 worker 部署 | 部署优化 | 多 worker 进程 + 健康检查 |
| P8: Redis DB 冲突 | Celery 启用 | Celery 和 Rate Limiter 分别在不同 DB |
| P9: 飞书限流 | Celery 启用 / 统一导入 | 大数据量同步无 429 |
| P10: 统一导入幂等性 | 统一导入 | 重复提交同一文件结果一致 |
| P11: Settings 缓存 | 部署优化 | 监控即可 |
| P12: CORS 配置 | 部署优化 | 生产跨域请求正常 |

## Recommended Phase Ordering (Based on Pitfall Dependencies)

1. **Python 3.9 兼容性** — P1/P2 是 blocker，不解决则无法启动
2. **Celery+Redis 启用** — P4/P5/P8 建立异步基础架构，后续 phase 依赖
3. **共享拒绝处理** — P3/P6 需要正确的 FK + 物理文件清理
4. **统一导入** — P9/P10 依赖 Celery 基础架构
5. **部署优化** — P7/P11/P12 最后阶段，上线前处理

## Sources

- [SQLAlchemy Issue #9110: Mapped[str | None] 在 Python 3.9 不可用](https://github.com/sqlalchemy/sqlalchemy/issues/9110) — HIGH confidence
- [SQLAlchemy Issue #8478: PEP 604 unions as Mapped type arguments](https://github.com/sqlalchemy/sqlalchemy/issues/8478) — HIGH confidence
- [Pydantic Issue #7923: Can't use | unions on Python 3.9](https://github.com/pydantic/pydantic/issues/7923) — HIGH confidence
- [SQLAlchemy 2.0 Cascades 文档](https://docs.sqlalchemy.org/en/20/orm/cascades.html) — HIGH confidence
- [SQLAlchemy Cascading Deletes (SQLite FK 陷阱)](https://dev.to/zchtodd/sqlalchemy-cascading-deletes-8hk) — HIGH confidence
- [TestDriven.io: FastAPI and Celery](https://testdriven.io/blog/fastapi-and-celery/) — HIGH confidence
- [Celery autodiscover_tasks 讨论](https://github.com/celery/celery/discussions/9664) — HIGH confidence
- [FastAPI 官方部署文档](https://fastapi.tiangolo.com/deployment/concepts/) — HIGH confidence
- [Gunicorn+Uvicorn 部署最佳实践](https://medium.com/@iklobato/mastering-gunicorn-and-uvicorn-the-right-way-to-deploy-fastapi-applications-aaa06849841e) — MEDIUM confidence
- [飞书 API 频率限制文档](https://open.feishu.cn/document/server-docs/api-call-guide/frequency-control) — HIGH confidence
- [飞书通用错误码文档](https://open.feishu.cn/document/server-docs/api-call-guide/generic-error-code) — HIGH confidence
- 代码审计：`backend/app/models/` (20+ files), `backend/app/schemas/` (81 files), `backend/app/services/sharing_service.py`, `backend/app/services/feishu_service.py`, `backend/app/core/database.py`, `backend/app/core/config.py`

---
*Pitfalls research for: 公司综合调薪工具 v1.2 新功能集成*
*Researched: 2026-04-07*
