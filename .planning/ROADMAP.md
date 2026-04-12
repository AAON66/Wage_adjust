# Roadmap: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-10 (shipped 2026-03-30)
- ✅ **v1.1 体验优化与业务规则完善** — Phases 11-17 (shipped 2026-04-07)
- 🚧 **v1.2 生产就绪与数据管理完善** — Phases 18-24 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-10) — SHIPPED 2026-03-30</summary>

- [x] Phase 1: Security Hardening and Schema Integrity — completed 2026-03-26
- [x] Phase 2: Evaluation Pipeline Integrity — completed 2026-03-31
- [x] Phase 3: Approval Workflow Correctness — completed 2026-03-31
- [x] Phase 4: Audit Log Wiring — completed 2026-03-31
- [x] Phase 5: Document Deduplication and Multi-Author — completed 2026-03-31
- [x] Phase 6: Batch Import Reliability — completed 2026-03-31
- [x] Phase 7: Dashboard and Cache Layer — completed 2026-03-31
- [x] Phase 8: Employee Self-Service UI — completed 2026-03-31
- [x] Phase 9: Feishu Attendance Integration — completed 2026-03-31
- [x] Phase 10: External API Hardening — completed 2026-03-31

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 体验优化与业务规则完善 (Phases 11-17) — SHIPPED 2026-04-07</summary>

- [x] Phase 11: Menu & Navigation Restructuring (1/1 plan) — completed 2026-03-31
- [x] Phase 12: Account-Employee Binding (2/2 plans) — completed 2026-04-01
- [x] Phase 13: Eligibility Engine & Data Layer (2/2 plans) — completed 2026-04-02
- [x] Phase 14: Eligibility Visibility & Overrides (2/2 plans) — completed 2026-04-04
- [x] Phase 15: Multimodal Vision Evaluation (2/2 plans) — completed 2026-04-04
- [x] Phase 16: File Sharing Workflow (2/2 plans) — completed 2026-04-06
- [x] Phase 17: Salary Display Simplification (2/2 plans) — completed 2026-04-07

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### 🚧 v1.2 生产就绪与数据管理完善 (In Progress)

**Milestone Goal:** 使系统兼容 Python 3.9 并优化部署，启用 Celery+Redis 异步任务架构，完善调薪资格数据导入管理，修复文件共享拒绝后的显示问题，增加员工所属公司字段。

- [x] **Phase 18: Python 3.9 兼容与依赖修复** - 全量类型注解降级 + 依赖版本锁定 + SQLite FK 修复 (completed 2026-04-08)
- [x] **Phase 19: Celery+Redis 异步基础设施** - 任务队列激活、worker 启动验证、健康检查端点 (completed 2026-04-09)
- [x] **Phase 20: 员工所属公司字段** - Employee 模型扩展 + 档案详情展示 (completed 2026-04-09)
- [x] **Phase 21: 文件共享拒绝清理与状态标签** - 拒绝/超时自动删除副本 + 待同意标签 (completed 2026-04-09)
- [ ] **Phase 22: AI 评估与批量导入异步迁移** - LLM 评估和导入任务迁移到 Celery
- [ ] **Phase 23: 调薪资格统一导入管理** - 4 类数据 Tab 管理 + Excel/飞书双通道 + 飞书限流
- [ ] **Phase 24: 生产部署配置** - gunicorn+uvicorn worker + Dockerfile + docker-compose

## Phase Details

### Phase 18: Python 3.9 兼容与依赖修复
**Goal**: 应用可在 Python 3.9 环境下正常启动并通过现有测试
**Depends on**: Nothing (v1.2 first phase)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-05
**Success Criteria** (what must be TRUE):
  1. 使用 Python 3.9 解释器执行 `uvicorn backend.app.main:app` 可正常启动，无 ImportError 或 SyntaxError
  2. 所有 SQLAlchemy model 文件中的 `Mapped[str | None]` 已替换为 `Mapped[Optional[str]]`，Pydantic schema 中的 `str | None` 也已替换，总计约 440+ 处
  3. numpy==2.0.2 和 Pillow==10.4.0 锁定后，pandas 批量导入和图片压缩/解析功能正常工作
  4. SQLite 连接启用 `PRAGMA foreign_keys=ON`，cascade delete 操作实际触发级联删除
  5. 现有 pytest 测试套件在 Python 3.9 下全部通过
**Plans:** 3/3 plans complete
Plans:
- [x] 18-01-PLAN.md — Model 类型注解降级 + SQLite FK 启用 + 依赖版本锁定
- [x] 18-02-PLAN.md — Schema 类型注解降级（PEP 604 + PEP 585）
- [x] 18-03-PLAN.md — 全量集成验证（启动测试 + pytest + 功能验证）

### Phase 19: Celery+Redis 异步基础设施
**Goal**: Celery worker 可独立启动并成功执行异步任务
**Depends on**: Phase 18
**Requirements**: ASYNC-01, ASYNC-04
**Success Criteria** (what must be TRUE):
  1. `celery -A backend.app.celery_app worker` 命令可正常启动 worker 进程，无导入错误
  2. 提交一个测试 task 后，worker 日志显示任务被接收并执行完成
  3. `/api/v1/health/celery` 健康检查端点返回 worker 在线状态
  4. docker-compose.yml 中包含 celery-worker 服务定义，启动后 worker 自动连接 Redis
**Plans:** 3/3 plans complete
Plans:
- [x] 19-01-PLAN.md — Celery app 实例 + tasks 目录 + 测试 task + celery 升级
- [x] 19-02-PLAN.md — 健康检查端点 + docker-compose 服务编排
- [x] 19-03-PLAN.md — Worker DB engine/session 对齐 + 真实 broker/worker 运行时验证 + ASYNC traceability 闭环

### Phase 20: 员工所属公司字段
**Goal**: HR 可为员工设置所属公司，并在档案详情中查看
**Depends on**: Phase 18
**Requirements**: EMP-01, EMP-02
**Success Criteria** (what must be TRUE):
  1. Employee 模型包含 `company` 字段，Alembic 迁移脚本可正常执行
  2. 通过批量导入 Excel（含 company 列）后，员工记录的 company 字段正确写入
  3. 管理端员工编辑表单可手动设置/修改所属公司
  4. 员工档案详情页显示所属公司信息，但员工列表页不显示该字段
**Plans**: 2/2 plans complete
Plans:
- [x] 20-01-PLAN.md — Backend company schema + migration + import semantics + regression coverage
- [x] 20-02-PLAN.md — Frontend admin/detail rollout + list-page non-display guardrails

### Phase 21: 文件共享拒绝清理与状态标签
**Goal**: 共享申请被拒绝或超时后，申请者的副本文件被自动清理，未审批的共享文件显示待同意标签
**Depends on**: Phase 18
**Requirements**: SHARE-06, SHARE-07, SHARE-08
**Success Criteria** (what must be TRUE):
  1. 文件所有者拒绝共享申请后，申请者上传的副本文件（物理文件+数据库记录）被自动删除
  2. 72h 超时触发的过期处理中，申请者上传的副本文件同样被自动删除
  3. 在文件列表中，尚未审批的共享作品旁边显示"待同意"状态标签
  4. 副本删除后，申请者的文件列表中不再显示该文件
**Plans**: 2 plans
Plans:
- [x] 21-01-PLAN.md — Backend history-safe cleanup foundation + atomic reject/expire model + file-list trigger contract
- [x] 21-02-PLAN.md — Shared FileList pending badge + MyReview cleanup feedback wiring

### Phase 22: AI 评估与批量导入异步迁移
**Goal**: AI 评估和批量导入通过 Celery 后台执行，前端可跟踪任务进度
**Depends on**: Phase 19
**Requirements**: ASYNC-02, ASYNC-03
**Success Criteria** (what must be TRUE):
  1. 触发 AI 评估后，API 返回 task_id，前端通过轮询获取评估进度和最终结果
  2. 批量导入（Excel/飞书）提交后在后台执行，前端可查看导入进度百分比
  3. Celery task 使用独立的 DB session，不复用 FastAPI 请求级 session
  4. 单个任务失败不影响 worker 继续处理其他任务
**Plans:** 3 plans
Plans:
- [ ] 22-01-PLAN.md — Backend Celery task 模块 + schema + 通用轮询端点 + 单元测试
- [ ] 22-02-PLAN.md — evaluations/imports API 端点异步迁移
- [ ] 22-03-PLAN.md — Frontend taskService + useTaskPolling hook + 页面集成
**UI hint**: yes

### Phase 23: 调薪资格统一导入管理
**Goal**: HR 可在统一页面管理 4 类调薪资格数据的导入（本地 Excel + 飞书多维表格）
**Depends on**: Phase 19, Phase 22
**Requirements**: ELIGIMP-01, ELIGIMP-02, ELIGIMP-03, ELIGIMP-04, FEISHU-01
**Success Criteria** (what must be TRUE):
  1. "调薪资格管理"页面包含 4 个 Tab（绩效等级、调薪历史、入职信息、非法定假期），可切换查看
  2. 每个 Tab 支持通过本地 Excel 文件上传导入对应数据类型
  3. 每个 Tab 支持配置飞书多维表格字段映射并执行同步
  4. 导入完成后显示成功/失败/跳过的统计数字和可展开的错误明细
  5. 飞书 API 调用具备 RPM 限流和指数退避重试，连续请求不触发 429 错误
**Plans**: TBD
**UI hint**: yes

### Phase 24: 生产部署配置
**Goal**: 系统可通过 Docker 一键部署到生产环境
**Depends on**: Phase 19, Phase 22
**Requirements**: DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. `requirements-prod.txt` 包含 gunicorn，启动脚本使用 `gunicorn -k uvicorn.workers.UvicornWorker` 启动
  2. `Dockerfile` 构建成功，容器内后端服务可正常响应请求
  3. `docker-compose up` 一键启动后端、前端、Redis、Celery worker 四个服务
  4. 容器间网络通信正常：FastAPI 可连接 Redis，Celery worker 可连接 Redis 和数据库
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 18 → 19 → 20 → 21 → 22 → 23 → 24

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Security Hardening | v1.0 | 5/5 | Complete | 2026-03-26 |
| 2. Evaluation Pipeline | v1.0 | 6/6 | Complete | 2026-03-31 |
| 3. Approval Workflow | v1.0 | 3/3 | Complete | 2026-03-31 |
| 4. Audit Log Wiring | v1.0 | 3/3 | Complete | 2026-03-31 |
| 5. Document Dedup | v1.0 | 4/4 | Complete | 2026-03-31 |
| 6. Batch Import | v1.0 | 3/3 | Complete | 2026-03-31 |
| 7. Dashboard & Cache | v1.0 | 3/3 | Complete | 2026-03-31 |
| 8. Employee Self-Service | v1.0 | 2/2 | Complete | 2026-03-31 |
| 9. Feishu Attendance | v1.0 | 3/3 | Complete | 2026-03-31 |
| 10. External API | v1.0 | 3/3 | Complete | 2026-03-31 |
| 11. Menu & Navigation | v1.1 | 1/1 | Complete | 2026-03-31 |
| 12. Account Binding | v1.1 | 2/2 | Complete | 2026-04-01 |
| 13. Eligibility Engine | v1.1 | 2/2 | Complete | 2026-04-02 |
| 14. Eligibility Visibility | v1.1 | 2/2 | Complete | 2026-04-04 |
| 15. Vision Evaluation | v1.1 | 2/2 | Complete | 2026-04-04 |
| 16. File Sharing | v1.1 | 2/2 | Complete | 2026-04-06 |
| 17. Display Simplification | v1.1 | 2/2 | Complete | 2026-04-07 |
| 18. Python 3.9 兼容 | v1.2 | 3/3 | Complete    | 2026-04-08 |
| 19. Celery+Redis 基础设施 | v1.2 | 3/3 | Complete    | 2026-04-09 |
| 20. 员工所属公司 | v1.2 | 2/2 | Complete    | 2026-04-09 |
| 21. 共享拒绝清理 | v1.2 | 2/2 | Complete   | 2026-04-09 |
| 22. 异步迁移 | v1.2 | 0/3 | Not started | - |
| 23. 资格导入管理 | v1.2 | 0/0 | Not started | - |
| 24. 生产部署 | v1.2 | 0/0 | Not started | - |
