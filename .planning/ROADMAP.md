# Roadmap: 公司综合调薪工具 (Enterprise Salary Adjustment Platform)

## Milestones

- ✅ **v1.0 MVP** — Phases 1-10 (shipped 2026-03-30)
- ✅ **v1.1 体验优化与业务规则完善** — Phases 11-17 (shipped 2026-04-07)
- ✅ **v1.2 生产就绪与数据管理完善** — Phases 18-24 (shipped 2026-04-16)
- 🚧 **v1.3 飞书登录与登录页重设计** — Phases 25-29 (in progress)

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

<details>
<summary>✅ v1.2 生产就绪与数据管理完善 (Phases 18-24) — SHIPPED 2026-04-16</summary>

- [x] Phase 18: Python 3.9 兼容与依赖修复 (3/3 plans) — completed 2026-04-08
- [x] Phase 19: Celery+Redis 异步基础设施 (3/3 plans) — completed 2026-04-09
- [x] Phase 20: 员工所属公司字段 (2/2 plans) — completed 2026-04-09
- [x] Phase 21: 文件共享拒绝清理与状态标签 (2/2 plans) — completed 2026-04-09
- [x] Phase 22: AI 评估与批量导入异步迁移 (3/3 plans) — completed 2026-04-12
- [x] Phase 23: 调薪资格统一导入管理 (3/3 plans) — completed 2026-04-15
- [x] Phase 24: 生产部署配置 (2/2 plans) — completed 2026-04-16

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

### 🚧 v1.3 飞书登录与登录页重设计 (In Progress)

**Milestone Goal:** 支持飞书扫码/网页授权登录并自动绑定员工账号，同时重新设计登录页面为左右分栏加粒子动态背景。

**Prerequisites (external/manual, not code phases):**
- 飞书开放平台创建企业自建应用，获取 App ID / App Secret
- 注册 OAuth redirect URI（开发环境 localhost + 生产域名）
- 申请 `contact:user.employee_id:readonly` 等权限并发布版本
- 企业管理员审批应用版本

> 上述配置是硬性前置条件，必须在 Phase 26 开始前完成。未完成则 Phase 26 标记为 Blocked。

- [x] **Phase 25: 技术债清理** - 消除 v1.2 遗留的重复代码和轮询不一致问题 (completed 2026-04-16)
- [ ] **Phase 26: 飞书 OAuth2 后端接入** - 后端完成飞书授权码换 token、用户匹配绑定、JWT 签发全流程
- [ ] **Phase 27: 飞书 OAuth2 前端集成** - 前端嵌入飞书扫码面板并处理 OAuth 回调完成登录
- [ ] **Phase 28: 登录页粒子背景** - Canvas 粒子动态背景组件，支持鼠标交互和无障碍
- [ ] **Phase 29: 登录页重设计整合** - 登录页重构为左右双栏布局，整合所有新组件

## Phase Details

### Phase 25: 技术债清理
**Goal**: 消除 v1.2 遗留的两项技术债，为新功能开发提供干净基线
**Depends on**: Nothing (独立于飞书登录功能)
**Requirements**: DEBT-01, DEBT-02
**Success Criteria** (what must be TRUE):
  1. llm_service.py 中不存在本地 InMemoryRateLimiter 类定义，改为从 core/rate_limiter.py 导入
  2. FeishuSyncPanel 使用 useTaskPolling hook 进行轮询，同步过程中显示进度信息
  3. 现有 AI 评估和飞书同步功能正常运行，无回归
**Plans:** 1/1 plans complete
Plans:
- [x] 25-01-PLAN.md — RateLimiter 去重 + FeishuSyncPanel 轮询重构 (completed 2026-04-16)

### Phase 26: 飞书 OAuth2 后端接入
**Goal**: 后端完整支持飞书授权码登录流程，包括安全校验、用户匹配绑定和 JWT 签发
**Depends on**: Phase 25 (代码基线清理); 飞书开放平台配置（外部前置条件）
**Requirements**: FAUTH-01, FAUTH-02, FAUTH-03, FAUTH-04, FAUTH-05
**Success Criteria** (what must be TRUE):
  1. 后端接收飞书授权码后能换取 user_access_token 并获取用户信息（employee_no）
  2. 飞书用户的 employee_no 与系统 Employee 匹配成功后，自动绑定 User 账号并返回有效 JWT
  3. 已绑定 feishu_open_id 的用户再次飞书登录时直接识别，无需重复匹配
  4. OAuth 回调包含 state CSRF 校验，同一 authorization code 不可重复使用
  5. 飞书登录找不到匹配员工时返回中文错误提示"工号未匹配，请联系管理员开通"
**Plans:** 2 plans
Plans:
- [ ] 26-01-PLAN.md — User 模型 + Settings 配置 + Alembic 迁移
- [ ] 26-02-PLAN.md — FeishuOAuthService 服务 + API 端点 + 单元测试

### Phase 27: 飞书 OAuth2 前端集成
**Goal**: 用户可在登录页通过飞书扫码完成登录，前端处理完整的 OAuth 回调流程
**Depends on**: Phase 26 (后端 OAuth API 就绪)
**Requirements**: FUI-01, FUI-02, FUI-03, FUI-04
**Success Criteria** (what must be TRUE):
  1. 登录页展示飞书 QR 扫码面板，用户扫码后自动跳转完成授权
  2. 前端 /auth/feishu/callback 路由正确解析 code/state 并调用后端接口完成登录跳转
  3. 二维码过期后（3 分钟）自动刷新并显示刷新提示
  4. 飞书登录失败时显示分类中文错误提示（授权取消、工号未匹配、网络错误等场景均覆盖）
**Plans**: TBD
**UI hint**: yes

### Phase 28: 登录页粒子背景
**Goal**: 登录页具备全屏 Canvas 粒子动态背景，提供现代化视觉体验
**Depends on**: Nothing (与 OAuth 逻辑完全解耦，可在 Phase 26/27 之后或并行)
**Requirements**: LOGIN-02, LOGIN-03
**Success Criteria** (what must be TRUE):
  1. 登录页显示全屏 Canvas 粒子动态背景，粒子间有连线效果
  2. 鼠标移动时粒子产生跟随交互效果
  3. 粒子背景在 HiDPI 屏幕上清晰不模糊，在 prefers-reduced-motion 开启时自动停止动画
**Plans**: TBD
**UI hint**: yes

### Phase 29: 登录页重设计整合
**Goal**: 登录页完成从单一表单到左右双栏布局的重设计，所有登录方式统一集成
**Depends on**: Phase 27 (飞书前端集成), Phase 28 (粒子背景)
**Requirements**: LOGIN-01, LOGIN-04
**Success Criteria** (what must be TRUE):
  1. 登录页为左右双栏布局：左侧账号密码登录表单，右侧飞书扫码/授权面板
  2. 现有邮箱/密码登录功能完整保留，登录流程与重设计前行为一致
  3. 粒子动态背景作为全屏底层正确显示，不遮挡登录内容
  4. 两种登录方式（密码 + 飞书）均可独立完成登录并正确跳转到对应角色首页
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 25 → 26 → 27 → 28 → 29

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
| 18. Python 3.9 兼容 | v1.2 | 3/3 | Complete | 2026-04-08 |
| 19. Celery+Redis 基础设施 | v1.2 | 3/3 | Complete | 2026-04-09 |
| 20. 员工所属公司 | v1.2 | 2/2 | Complete | 2026-04-09 |
| 21. 共享拒绝清理 | v1.2 | 2/2 | Complete | 2026-04-09 |
| 22. 异步迁移 | v1.2 | 3/3 | Complete | 2026-04-12 |
| 23. 资格导入管理 | v1.2 | 3/3 | Complete | 2026-04-15 |
| 24. 生产部署 | v1.2 | 2/2 | Complete | 2026-04-16 |
| 25. 技术债清理 | v1.3 | 1/1 | Complete | 2026-04-16 |
| 26. 飞书 OAuth2 后端 | v1.3 | 0/2 | Not started | - |
| 27. 飞书 OAuth2 前端 | v1.3 | 0/? | Not started | - |
| 28. 粒子背景 | v1.3 | 0/? | Not started | - |
| 29. 登录页重设计 | v1.3 | 0/? | Not started | - |
