# Requirements: Milestone v1.3 飞书登录与登录页重设计

**Created:** 2026-04-16
**Milestone:** v1.3
**Core Value:** HR can run a complete, auditable salary review cycle — with every decision explainable and traceable

---

## 飞书 OAuth2 认证 (FAUTH)

- [ ] **FAUTH-01**: 后端 OAuth callback 端点接收飞书授权码，换取 user_access_token 并获取用户信息
- [ ] **FAUTH-02**: 飞书用户的 employee_no 与系统 Employee 记录自动匹配，匹配成功后绑定对应 User 账号并签发 JWT
- [ ] **FAUTH-03**: OAuth 回调包含 state 参数 CSRF 校验，authorization code 一次性使用防重放
- [ ] **FAUTH-04**: User 模型新增 feishu_open_id 字段（唯一约束），已绑定用户后续登录直接识别无需重复匹配
- [ ] **FAUTH-05**: 飞书登录找不到匹配员工时返回中文错误提示"工号未匹配，请联系管理员开通"
- [ ] **FAUTH-06**: 已登录用户可在设置页主动绑定飞书账号，填充 users.feishu_open_id；绑定必须校验飞书 employee_no 与当前 User 绑定的 Employee 一致（Phase 27.1）
- [ ] **FAUTH-07**: 已绑定用户可在设置页解除飞书绑定，清空 users.feishu_open_id；操作需二次确认，保留当前 session（Phase 27.1）
- [ ] **FAUTH-08**: 绑定目标 feishu_open_id 已被其他账号占用时返回 409 + 中文提示，不允许强制覆盖（Phase 27.1）
- [ ] **FAUTH-09**: 绑定/解绑写入 AuditLog，记录 user_id、IP、open_id 头尾 8 位（不存完整 open_id）（Phase 27.1）

## 飞书前端集成 (FUI)

- [ ] **FUI-01**: 登录页嵌入飞书账号授权登录入口（整页跳转飞书授权页）；已登录飞书时一键授权，未登录时进入飞书自家登录页（含扫码入口）。**Phase 27 D-17 amendment (2026-04-19)**：原要求的「嵌入式 QR SDK 扫码面板」因飞书应用能力限制移到 deferred。
- [ ] **FUI-02**: 前端 /auth/feishu/callback 路由处理 OAuth 回调，解析 code/state 后调用后端接口完成登录
- [ ] ~~**FUI-03**: QR 二维码支持 3 分钟自动刷新，过期后显示刷新提示~~ → **Deferred** (D-17: QR 链路移除，FUI-03 依赖 QR 可用)
- [ ] **FUI-04**: 飞书登录失败时显示分类中文错误提示（授权取消、工号未匹配、网络错误等）

## 登录页重设计 (LOGIN)

- [~] ~~**LOGIN-01**: 登录页重设计为左右双栏布局，左侧账号密码登录表单，右侧飞书扫码/授权面板~~ → **Won't Do** (2026-04-20)：Phase 29 取消，现有 Login.tsx「左欢迎介绍+角色卡 | 右 LoginForm+FeishuLoginPanel 叠放」+ 粒子背景已满足实用需求，不再做重排
- [ ] **LOGIN-02**: 登录页添加全屏 Canvas 粒子动态背景，参考智慧树风格
- [ ] **LOGIN-03**: 粒子背景支持鼠标跟随交互、HiDPI 适配和 prefers-reduced-motion 响应
- [ ] **LOGIN-04**: 现有邮箱/密码登录功能完整保留，不受飞书登录集成影响

## 技术债清理 (DEBT)

- [ ] **DEBT-01**: llm_service.py 中重复的 InMemoryRateLimiter 改为从 core/rate_limiter.py 导入
- [ ] **DEBT-02**: FeishuSyncPanel 改用共享 useTaskPolling hook 替代手写 setTimeout 轮询，显示同步进度

---

## Future Requirements (deferred)

- **嵌入式飞书 QR 扫码面板 + 3 分钟刷新（原 FUI-01 / FUI-03）— Deferred in Phase 27 D-17**：飞书 QRLogin SDK 返回 4401，飞书「网页扫码登录」能力需独立申请 + 发版审批，当前应用类型可能不支持。已改为整页跳转授权（飞书自家登录页含扫码入口）。未来若需嵌入式 QR，须先解决飞书应用能力配置
- 飞书工作台免登（tt.requestAccess）— 需应用上架工作台，独立里程碑
- 菜单导航重构（NAV-01/02/03，从 v1.1 延期）
- 实时 WebSocket 通知
- E2E 集成测试套件
- PostgreSQL 连接池优化
- MinIO/S3 对象存储激活

## Out of Scope

- 首次飞书登录自动创建系统账号 — 绕过 RBAC，产生无角色灰色状态
- 扫码/密码 Tab 切换模式 — QR SDK 容器销毁重建会闪烁，行业标准为并列
- 持久化存储飞书 user_access_token — 不必要的安全风险，用后即弃
- 飞书内嵌 WebView 免登 — 需要工作台上架，独立里程碑
- K8s 编排 — Docker Compose 已满足当前部署需求

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FAUTH-01 | — | Pending |
| FAUTH-02 | — | Pending |
| FAUTH-03 | — | Pending |
| FAUTH-04 | — | Pending |
| FAUTH-05 | — | Pending |
| FAUTH-06 | 27.1 | Pending |
| FAUTH-07 | 27.1 | Pending |
| FAUTH-08 | 27.1 | Pending |
| FAUTH-09 | 27.1 | Pending |
| FUI-01 | — | Pending |
| FUI-02 | — | Pending |
| FUI-03 | — | Pending |
| FUI-04 | — | Pending |
| LOGIN-01 | — | Won't Do |
| LOGIN-02 | — | Pending |
| LOGIN-03 | — | Pending |
| LOGIN-04 | — | Pending |
| DEBT-01 | — | Pending |
| DEBT-02 | — | Pending |

**Coverage:**
- v1.3 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15

---
*Requirements defined: 2026-04-16*
