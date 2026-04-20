# Milestones

## v1.3 飞书登录与登录页重设计 (Shipped: 2026-04-20)

**Phases completed:** 5 phases (25, 26, 27, 27.1 inserted, 28 — Phase 29 cancelled), 11 plans, 15 tasks
**Requirements:** 17/19 satisfied, 1 deferred (FUI-03 嵌入式 QR 刷新), 1 Won't Do (LOGIN-01 双栏重排)

**Key accomplishments:**

- **Phase 25 技术债清理** — llm_service.py 的 InMemoryRateLimiter 去重收敛到 core/rate_limiter.py；FeishuSyncPanel 切换到共享 useTaskPolling hook
- **Phase 26 飞书 OAuth2 后端** — `/api/v1/auth/feishu/{authorize,callback}` 完整链路：state CSRF、code 防重放、employee_no 匹配、feishu_open_id 持久化绑定、JWT 签发、Redis 503 降级、中文错误码映射
- **Phase 27 飞书 OAuth2 前端** — auth service + feishuErrors 映射 + useAuth.loginWithFeishu + 独立 /auth/feishu/callback 路由 + 三态 FeishuCallbackPage；**D-17 amendment**：QR SDK 申请受限后简化为整页跳转授权方案（FeishuLoginPanel）
- **Phase 27.1 设置页飞书绑定（INSERTED）** — 登录后主动绑定/解绑，employee_no 一致性校验、409 open_id 冲突、AuditLog 记录头尾 8 位哈希、D-18 空 employee_no 豁免
- **Phase 28 登录页粒子背景** — 277 行零依赖原生 Canvas 组件：面积自适应粒子数（40-150）、120px 距离阈值连线、120px 鼠标排斥、DPR 缩放、prefers-reduced-motion 降级、visibilitychange 暂停；UAT 22 项 + 1 hotfix（去掉 `<main>` 不透明背景使 Canvas 可见）

**Known gaps / deferred:**
- FUI-03 二维码 3 分钟刷新 → Deferred（依赖飞书 QR 能力申请）
- LOGIN-01 登录页左右双栏重设计 → Won't Do（当前布局 + 粒子背景已足够，Phase 29 取消）

---

## v1.1 体验优化与业务规则完善 (Shipped: 2026-04-07)

**Phases completed:** 7 phases, 13 plans, 17 tasks

**Key accomplishments:**

- 4 binding API endpoints with token_version-based JWT invalidation for forced re-login on unbind
- Admin bind/unbind in UserAdmin, employee 3-step self-bind in Settings, yellow warning banner for unbound non-admin users
- PerformanceRecord + SalaryAdjustmentRecord models, pure-computation EligibilityEngine with 4 three-state rules (tenure/interval/performance/leave), 28 unit tests, configurable thresholds
- EligibilityService wiring DB to engine with 5 API endpoints, ImportService extended for performance grades and salary adjustments, FeishuService extended for performance record sync -- completing all three ELIG-09 data import channels
- Batch eligibility query with filter-before-paginate, two-level override approval with role-step binding, Excel export with 5000 row cap, and full RBAC hardening via AccessScopeService
- Role-aware eligibility management page with filterable batch list, Excel export, step-aware override approval, and employee access restriction
- PPT image extraction with SHA1 dedup, vision evaluation LLM prompt with 5-dimension relevance scoring, and >5MB image compression
- ParseService wires PPT image extraction and standalone image evaluation into the parse flow with batch failure isolation, plus EvidenceCard renders vision metadata with Chinese labels and quality badge coloring
- SharingRequest model + hash-only dedup refactor + atomic upload+request creation + 72h lazy expiry — all HIGH review concerns resolved.
- 1. [Rule 1 - Bug] Fixed Unicode curly quotes in generated JSX

---
