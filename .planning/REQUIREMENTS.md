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

## 飞书前端集成 (FUI)

- [ ] **FUI-01**: 登录页嵌入飞书 QR SDK 扫码面板，用户扫码后自动触发 OAuth 授权流程
- [ ] **FUI-02**: 前端 /auth/feishu/callback 路由处理 OAuth 回调，解析 code/state 后调用后端接口完成登录
- [ ] **FUI-03**: QR 二维码支持 3 分钟自动刷新，过期后显示刷新提示
- [ ] **FUI-04**: 飞书登录失败时显示分类中文错误提示（授权取消、工号未匹配、网络错误等）

## 登录页重设计 (LOGIN)

- [ ] **LOGIN-01**: 登录页重设计为左右双栏布局，左侧账号密码登录表单，右侧飞书扫码/授权面板
- [ ] **LOGIN-02**: 登录页添加全屏 Canvas 粒子动态背景，参考智慧树风格
- [ ] **LOGIN-03**: 粒子背景支持鼠标跟随交互、HiDPI 适配和 prefers-reduced-motion 响应
- [ ] **LOGIN-04**: 现有邮箱/密码登录功能完整保留，不受飞书登录集成影响

## 技术债清理 (DEBT)

- [ ] **DEBT-01**: llm_service.py 中重复的 InMemoryRateLimiter 改为从 core/rate_limiter.py 导入
- [ ] **DEBT-02**: FeishuSyncPanel 改用共享 useTaskPolling hook 替代手写 setTimeout 轮询，显示同步进度

---

## Future Requirements (deferred)

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
| FUI-01 | — | Pending |
| FUI-02 | — | Pending |
| FUI-03 | — | Pending |
| FUI-04 | — | Pending |
| LOGIN-01 | — | Pending |
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
