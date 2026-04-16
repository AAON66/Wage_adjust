# Milestones

## v1.2 生产就绪与数据管理完善 (Shipped: 2026-04-16)

**Phases completed:** 7 phases, 18 plans, 34 tasks
**Timeline:** 9 days (2026-04-07 → 2026-04-16), 144 commits
**Files modified:** 227 (+22,544 / -2,096)
**Codebase:** ~33,164 Python LOC + ~21,398 TypeScript LOC
**Git range:** 6929ec3..9928ae0
**Audit:** 19/19 requirements satisfied (tech_debt status)

**Key accomplishments:**

1. Python 3.9 全量兼容 — 440+ 处 PEP 604/585 注解降级，numpy/Pillow 版本锁定，SQLite FK pragma
2. Celery+Redis 异步基础设施 — Worker DB 生命周期修复，健康检查端点，Docker 编排，运行时 proof
3. AI 评估与批量导入异步化 — Celery task + 前端 useTaskPolling 实时进度轮询
4. 调薪资格统一导入管理 — 6 Tab 页面，Excel 拖拽上传 + 飞书多维表格字段映射同步（4 种数据类型）
5. 文件共享拒绝/超时清理 — 副本自动删除 + 待同意标签 + 历史保留
6. 生产部署配置 — gunicorn+uvicorn Dockerfile + Nginx 前端 + docker-compose.prod.yml 四服务编排

**Known tech debt:**
- llm_service.py 本地重复 InMemoryRateLimiter（应从 core 导入）
- FeishuSyncPanel 手写轮询未使用 useTaskPolling（不显示同步进度）
- Python 3.9 和 Docker 运行时需人工验证

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
