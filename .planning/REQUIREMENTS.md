# Requirements: Milestone v1.2 生产就绪与数据管理完善

**Created:** 2026-04-08
**Milestone:** v1.2

---

## 部署兼容 (DEPLOY)

- [ ] **DEPLOY-01**: 系统可在 Python 3.9 环境下正常启动和运行（Mapped[str|None] 替换为 Optional, 依赖版本兼容）
- [ ] **DEPLOY-02**: numpy 降级至 2.0.2、Pillow 降级至 10.4.0，且现有功能（pandas 导入、图片处理）正常工作
- [ ] **DEPLOY-03**: 生产环境使用 gunicorn+uvicorn worker 启动，配置在 requirements-prod.txt 和启动脚本中
- [ ] **DEPLOY-04**: 提供 Dockerfile 和 docker-compose.yml，支持一键部署后端+前端+Redis
- [ ] **DEPLOY-05**: SQLite 启用 PRAGMA foreign_keys=ON，修复 cascade delete 静默失败问题

## 异步任务 (ASYNC)

- [ ] **ASYNC-01**: Celery app 配置完成（升级至 5.5.1），worker 可正常启动并执行 task
- [ ] **ASYNC-02**: AI 评估调用（LLM 文本评估 + 视觉评估）迁移到 Celery task，API 返回 task_id 供前端轮询结果
- [ ] **ASYNC-03**: 批量导入（Excel/飞书）通过 Celery task 后台执行，前端可查看导入进度
- [ ] **ASYNC-04**: Celery worker 健康检查端点可用，docker-compose 中包含 worker 服务

## 员工档案 (EMP)

- [ ] **EMP-01**: Employee 模型新增 company（所属公司）字段，支持通过批量导入和管理端手动设置
- [ ] **EMP-02**: 所属公司仅在员工档案详情页展示，不出现在员工列表等其他页面

## 文件共享 (SHARE)

- [ ] **SHARE-06**: 共享申请被拒绝后，申请者上传的副本文件自动从系统中删除（物理文件+数据库记录）
- [ ] **SHARE-07**: 未审批的共享作品在列表中显示"待同意"状态标签
- [ ] **SHARE-08**: 72h 超时的共享申请触发时，申请者上传的副本文件也自动删除

## 调薪资格导入 (ELIGIMP)

- [ ] **ELIGIMP-01**: 提供统一的"调薪资格管理"页面，通过 Tab 切换管理 4 种数据类型的导入设置
- [ ] **ELIGIMP-02**: 支持通过本地 Excel 文件导入绩效等级、调薪历史、入职信息、非法定假期数据
- [ ] **ELIGIMP-03**: 支持通过飞书多维表格字段映射同步绩效等级、调薪历史、入职信息、非法定假期数据
- [ ] **ELIGIMP-04**: 每种数据类型的导入结果有明确的成功/失败/跳过统计和错误明细

## 飞书集成 (FEISHU)

- [ ] **FEISHU-01**: FeishuService 添加请求限流（RPM 限制）和指数退避重试，防止 429 错误

---

## Future Requirements (deferred)

- 菜单导航重构（NAV-01/02/03，从 v1.1 延期）
- 实时 WebSocket 通知
- E2E 集成测试套件
- PostgreSQL 专用优化（连接池、读写分离）
- MinIO/S3 对象存储激活

## Out of Scope

- 动态资格规则配置 UI — 4 条规则 + 可配置阈值已满足需求
- 完整绩效管理模块 — 仅导入绩效等级
- K8s 编排 — Docker Compose 已满足当前部署需求
- Celery 定时任务（Beat）— v1.2 仅做按需异步，不做定时调度
- Python 3.10+ 升级 — v1.2 目标是 3.9 兼容，后续再考虑升级

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPLOY-01 | - | Pending |
| DEPLOY-02 | - | Pending |
| DEPLOY-03 | - | Pending |
| DEPLOY-04 | - | Pending |
| DEPLOY-05 | - | Pending |
| ASYNC-01 | - | Pending |
| ASYNC-02 | - | Pending |
| ASYNC-03 | - | Pending |
| ASYNC-04 | - | Pending |
| EMP-01 | - | Pending |
| EMP-02 | - | Pending |
| SHARE-06 | - | Pending |
| SHARE-07 | - | Pending |
| SHARE-08 | - | Pending |
| ELIGIMP-01 | - | Pending |
| ELIGIMP-02 | - | Pending |
| ELIGIMP-03 | - | Pending |
| ELIGIMP-04 | - | Pending |
| FEISHU-01 | - | Pending |

**Coverage:**
- v1.2 requirements: 19 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 19

---
*Requirements defined: 2026-04-08*
