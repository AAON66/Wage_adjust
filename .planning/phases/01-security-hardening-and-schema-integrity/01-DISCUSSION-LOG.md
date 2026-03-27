# Discussion Log — Phase 1: Security Hardening and Schema Integrity

**Date:** 2026-03-25
**Mode:** Interactive discuss-phase

---

## Area 1: National ID Encryption Algorithm (SEC-03)

**Question:** SM4（国密标准）vs AES-256-GCM？

**Options presented:**
1. SM4 — 国密标准，PIPL/等保 2.0 合规
2. AES-256-GCM — 国际标准，Python 生态支持更好
3. 你来决定

**User selected:** AES-256-GCM

**Notes:** No specific PIPL/等保 compliance requirement stated. `cryptography` library used. Key stored in `.env`.

---

## Area 2: Rate Limiter Storage Backend (SEC-02, SEC-05)

**Question:** slowapi 内存 vs Redis 后端？

**Options presented:**
1. 内存（per-process）— 无需额外服务，但多 worker 下失效
2. Redis — 跨进程准确限流，需要 Redis 运行
3. 分开处理 — 登录用 Redis，公开 API 用内存

**User follow-up:** "哪个更好部署到服务器？"

**Clarification provided:** Redis 更适合服务器部署（多 worker 场景内存后端形同虚设）。

**User selected:** Redis（开发环境降级内存，生产强制 Redis）

---

## Area 3: Alembic Migration Strategy (DB-01)

**Question:** 整合策略？

**Options presented:**
1. 彻底重置 — 删除旧迁移，生成全新 baseline
2. 保留历史 + 封顶 — 保留 4 个旧文件，新增 baseline
3. 标记旧文件为 fake-applied

**Context from user:** "现在的数据库都是 SQLite，不好用" → 无生产数据库历史包袱

**User selected:** 彻底重置（选项 1）

**Follow-up question:** Baseline 兼容 PostgreSQL 语法还是只管 SQLite？

**User selected:** 兼容 PostgreSQL（选项 1）

---

## Gray Area 4: python-jose CVE

**Not discussed** — User selected areas 1, 2, 3 only. Deferred to future phase.
