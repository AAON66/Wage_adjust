# Phase 31: 飞书同步可观测性 - Research

**Researched:** 2026-04-21
**Domain:** 后端 SQLAlchemy/FastAPI 同步日志聚合与事务分离 + 前端 React 独立路由页面（Tab + 五色 badge + CSV 下载）
**Confidence:** HIGH（所有改动点均为既定代码扩展，无外部依赖、无新语言/框架引入）

## Summary

本阶段是 v1.4 第二个 phase，目标是让 HR 能在独立的「同步日志」页面自助诊断飞书同步失败/部分失败的根因。技术上分三层改造：（1）`FeishuSyncLog` 模型加两列 `sync_type` + `mapping_failed_count`，并按 Phase 30 既定的 `op.batch_alter_table` 模式走 Alembic 两阶段迁移；（2）`FeishuService` 抽出 `_with_sync_log(sync_type, fn, ...)` helper 统一 running log / 终态 / failed log 三段式写入，四个新 sync 方法（`sync_performance_records / sync_salary_adjustments / sync_hire_info / sync_non_statutory_leave`）从「返回 dict」改造为「返回 `_SyncCounters` dataclass + 业务体内 upsert」并由 helper 调度，`sync_attendance` 同步重构到同一 helper；（3）前端新增 `/feishu/sync-logs` 路由页面（admin+hrbp），复用 `SyncStatusCard` 的五色 badge 视觉语言拆分为 `CountersBadgeCluster` 组件，Tab 切分五类同步 + 点击详情抽屉 + 每行 CSV 下载。

关键工程风险集中在三处：（a）`FeishuSyncLog` 写入事务与业务 upsert 事务的分离 — 业务 `db.rollback()` 不能连带清掉 log，必须用独立 `SessionLocal()` 写终态（`sync_attendance` 现行 failed 分支已建立此模式）；（b）Celery task `feishu_sync_eligibility_task` 的 `performance_grades` → `performance` key 名迁移必须同时改四处（task sync_methods dict、`ELIGIBILITY_IMPORT_TYPES` set、前端 `SYSTEM_FIELDS_BY_TYPE` key、`EligibilityManagementPage` 的 tab key），且需评估 in-flight task 兼容（Celery broker 中已排队的旧 key 任务）；（c）409 不写日志与 SC4（两次触发 → 两条独立记录）的语义一致性 — 锁命中 raise HTTPException 不触发 helper，锁释放后的第二次点击正常进入 helper 写第二条 log。

**Primary recommendation:** 按 D-10/D-11 严格执行 helper 提炼 — helper 负责 log 生命周期（running → success/partial/failed），业务 fn 只返回 `_SyncCounters` 实例；helper 对独立 session 写 log 终态的 try/except 内部打 `logger.exception` 不重抛（避免掩盖业务异常）。Alembic 迁移按 D-03 三步走：`add_column(sync_type, nullable=True)` → `UPDATE ... WHERE sync_type IS NULL` → `alter_column(nullable=False)`，全程 `op.batch_alter_table` 包裹。前端先抽 `CountersBadgeCluster` 子组件再堆页面，避免一次性写 500+ 行巨组件。

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### 模型扩展（FeishuSyncLog schema）
- **D-01:** 新增 `sync_type: str` 列（NOT NULL），枚举值 `attendance / performance / salary_adjustments / hire_info / non_statutory_leave`，命名与 `feishu_sync_eligibility_task` 的 `sync_type` 参数一致（注意 Celery task 目前 key 名是 `performance_grades`，迁移时统一改为 `performance`，避免双命名）
- **D-02:** 新增 `mapping_failed_count: int` 列（NOT NULL DEFAULT 0），专表「字段类型/格式转换失败」（如 year 无法 `int(float(...))`、grade 不在枚举、adjustment_date 解析失败等）；`skipped_count` 语义收紧为「业务跳过」（如源数据 source_modified_at 更早、无有效字段更新）
- **D-03:** Alembic 迁移用 `op.batch_alter_table` 单次加两列：先 `add_column(sync_type, nullable=True)` → `UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL` → `alter_column(nullable=False)`；`mapping_failed_count` 直接加 `DEFAULT 0 NOT NULL`（SQLite 兼容）
- **D-04:** 保留 `mode` 列不动，语义仍为 `full / incremental`（对 `sync_attendance` 有意义）；四个新 sync_type 方法写入时固定 `mode='full'`；前端列表展示 mode 列时仅对 `sync_type='attendance'` 显示，其他隐藏

#### 同步日志页面 UI 形态
- **D-05:** 新增独立前端路由 `/feishu/sync-logs`（对应 `SyncLogsPage.tsx`），`admin + hrbp` 可见；导航菜单新增「同步日志」入口，挂在既有「飞书集成」分组下；`employee / manager` 角色看不到
- **D-06:** 页面顶部 Tab 切换：`全部 / 考勤 / 绩效 / 薪调 / 入职信息 / 社保假勤`，Tab 选中决定 `GET /feishu/sync-logs?sync_type=...&page=&page_size=` 的查询参数；默认 page_size=20，支持分页（Phase 31 不引入游标分页，offset 即可）
- **D-07:** 每行用五色分段 badge 团展示 `{success, updated, unmatched, mapping_failed, failed}`：绿=success, 蓝=updated, 橙=unmatched, 紫=mapping_failed, 红=failed；badge 数值为 0 时置灰弱化；点击任一 badge 展开详情抽屉（抽屉含 error_message、unmatched_employee_nos 全量列表、leading_zero_fallback_count 黄字提示）
- **D-08:** 每行右侧 Action 列放「下载未匹配工号 CSV」按钮，仅当 `unmatched_count > 0` 时启用。CSV 单列 `employee_no`、前 20 行（`unmatched_employee_nos[:20]`）、文件名格式 `sync-log-{log_id}-unmatched.csv`；下载走 `GET /feishu/sync-logs/{log_id}/unmatched.csv` 返回 `text/csv; charset=utf-8`，权限 `admin+hrbp`
- **D-09:** 顶层 status 展示 4 色 badge：`success=绿 / partial=橙 / failed=红 / running=蓝带 spinner`；`rejected` 状态不写日志（D-15），因此 UI 不显示

#### 写入日志的代码落地
- **D-10:** 新增 helper `FeishuService._with_sync_log(self, sync_type: str, fn: Callable, *args, triggered_by=None, **kwargs) -> FeishuSyncLog`：内部 (1) 用独立 `SessionLocal()` session 创建 `status='running'` 的 FeishuSyncLog 并 commit → (2) 调用 `fn(sync_log_id=log.id, ...)` 业务函数（业务函数用 `self.db` 完成 upsert 并 commit）→ (3) 用独立 session 写终态 counters + 派生 status → commit；(4) 业务 fn 抛异常时用独立 session 写 `status='failed'` + `error_message`（沿用 `sync_attendance` 既定模式）
- **D-11:** 定义内部 dataclass `_SyncCounters(success: int, updated: int, unmatched: int, mapping_failed: int, failed: int, leading_zero_fallback: int, total_fetched: int, unmatched_nos: list[str])`；四个 sync_xxx 业务方法改造为返回 `_SyncCounters` 实例；helper 按 dataclass 字段一一填入 FeishuSyncLog，避免 dict key 拼写错误
- **D-12:** `sync_attendance` 也重构到 `_with_sync_log('attendance', ...)` 模式，删除内部手写 FeishuSyncLog 创建/终态代码；向后兼容 mode='full'/'incremental' 语义；现有 `sync_with_retry` 调 `sync_attendance` 的路径保持不变（只是 `sync_attendance` 内部委托到 helper）
- **D-13:** FeishuSyncLog commit 事务与业务 upsert 事务分离：业务 rollback 不会连带 log 回滚，确保「同步失败」能被观测到；独立 session 写 log 终态的 try/except 内部打 `logger.exception` 但不再抛出（避免掩盖业务异常）

#### partial 状态与并发触发语义
- **D-14:** `status` 派生规则（硬切）：running 结束时若 `unmatched + mapping_failed + failed > 0` → `status='partial'`；否则 → `status='success'`。业务 fn 抛异常 → `status='failed'`。无百分比阈值，无「全员失败转 failed」额外规则
- **D-15:** `is_sync_running(sync_type: str | None = None)` 升级为 per-sync_type 分桶锁：传 sync_type 时仅查该 type 的 `status='running'` 记录；不传时查所有 running（保留兼容性）。同 sync_type 第二次触发返回 409；不同 sync_type 可并行（`sync_performance` 和 `sync_hire_info` 可同时跑）
- **D-16:** 409 冲突**不写** FeishuSyncLog（避免 `status='rejected'` 污染数据库）：接口直接返回 `{error: 'sync_in_progress', sync_type, message}`；前端按 sync_type 展示「该类型同步正在进行中」提示。SC4 的「两条独立记录」语义解释为：锁释放后的第二次点击正常触发并写入第二条 log（而非 409 也写日志）
- **D-17:** `expire_stale_running_logs(timeout_minutes=30)` 保留现有语义，对所有 sync_type 统一生效；`trigger_sync` / 四个新 Celery task 入口统一先调 `expire_stale_running_logs` 再检查 `is_sync_running(sync_type)`

### Claude's Discretion

- Alembic 迁移文件名 / revision id
- `_SyncCounters` 具体字段顺序 / dataclass 是否加 `@dataclass(frozen=True)`
- `/feishu/sync-logs` 前端页面的具体配色与 badge 视觉语言（沿用现有 Tailwind + var(--color-*) design token 即可）
- `SyncLogsPage.tsx` 是否拆分子组件（如 `SyncLogRow`, `CountersBadgeCluster`, `SyncLogDetailDrawer`）
- Celery task 内部捕获 `HTTPException(409)` 的 idempotent 行为（task 应 retry 还是直接标 failed）
- 旧 Celery task `feishu_sync_eligibility_task` 的 `performance_grades` → `performance` 过渡期兼容策略（可加一次性 alias dict）
- 前端 Tab 中文标签细节文案

### Deferred Ideas (OUT OF SCOPE)

- 基于 request_id 的去重幂等（比 sync_type 锁更严格）— v1.5+，当前锁够用
- 409 被拒事件写 `status='rejected'` 日志 — 会产生数据库噪声，HR 价值有限
- 按百分比阈值派生 failed vs partial（>=50% 失败转 failed）— 硬切规则够用
- CSV 多列（employee_no + 失败原因 + 行号）— 仅工号即可让 HR 去飞书源表格查
- 一键导出「近 30 天所有未匹配」聚合 CSV — HR 可按日志逐条下载合并
- 顶部聚合 KPI 横幅（今日同步失败总数 / 周趋势图）— v1.5+ 独立观测面板
- mode 列彻底删除或扩展为 manual/scheduled — Phase 31 不触碰
- sync_attendance 的 skipped_count 语义重新分类到 mapping_failed — 风险大，等实战数据验证
- 日志保留期 / 定时清理（例如 90 天前自动归档）— 当前表不大，v1.5+ 再看
- 独立 `MetricEvent` 表 / Prometheus / 全局可观测基础设施（v1.5+）
- `ImportService.ImportJob` 的导入日志观测（Phase 32 范畴）
- 导入/同步统一告警推送 / 邮件通知（v1.5+）

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IMPORT-03 | 飞书同步方法 `sync_performance_records / sync_salary_adjustments / sync_hire_info / sync_non_statutory_leave` 通过 `_with_sync_log` helper 统一写入 `FeishuSyncLog`，含 `{success, updated, unmatched, mapping_failed, failed}` 五类计数器 | `_with_sync_log` helper 设计（D-10）+ `_SyncCounters` dataclass（D-11）+ 四方法业务体保留 upsert 不变，只改外壳签名（见 Code Examples §"_with_sync_log helper 骨架"）；`FeishuSyncLog` 表 `add sync_type + mapping_failed_count` 两列（D-01/D-02），迁移走 `op.batch_alter_table`（D-03 + Pitfall 16） |
| IMPORT-04 | 飞书同步完成后运行 sanity check：若 `unmatched + mapping_failed + failed > 0`，顶层状态降级为 `partial`；UI 在「同步日志」页面按四类分别展示，并提供「下载未匹配工号 CSV」按钮（前 20 个工号） | `partial` 派生规则（D-14）在 helper 的终态分支；前端 `/feishu/sync-logs` 独立路由（D-05）+ Tab（D-06）+ 五色 badge（D-07）+ CSV 下载端点 `GET /feishu/sync-logs/{log_id}/unmatched.csv`（D-08）；`SyncLogRead` schema 增加 `sync_type / mapping_failed_count` 字段 + status 枚举加 `'partial'`；前端 `SyncLogRead` 类型同步 |

---

## Standard Stack

所有库均为项目既有依赖，Phase 31 **不新增任何依赖**。下表是本阶段实际会调用到的库与既定版本。

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | `/feishu/sync-logs` 路由、CSV StreamingResponse、`require_roles('admin', 'hrbp')` 依赖注入 | 项目既定 Web 框架，现有所有路由均基于此 [VERIFIED: requirements.txt] |
| SQLAlchemy | 2.0.36 | `FeishuSyncLog` ORM 扩展、`select(FeishuSyncLog).where(sync_type=...)` 过滤 | 项目唯一 ORM，`Mapped[T]` + `mapped_column(...)` 模式已贯穿 [VERIFIED: requirements.txt] |
| Alembic | 1.14.0 | Schema 迁移（add_column + alter_column + UPDATE） | 项目唯一迁移工具，`op.batch_alter_table` 模式已建立（Phase 30 `30_01_add_leading_zero_fallback_count.py` 可参考）[VERIFIED: alembic/versions/] |
| Pydantic v2 | 2.10.3 | `SyncLogRead` schema 加 `sync_type: str`, `mapping_failed_count: int` 字段 + status Literal 加 `'partial'` | 项目所有 schema 用 v2 `ConfigDict(from_attributes=True)` [VERIFIED: backend/app/schemas/feishu.py] |
| React | 18.3.1 | `/feishu/sync-logs` 页面、Tab 切换、抽屉 | 项目唯一前端框架 [VERIFIED: frontend/package.json] |
| React Router DOM | 7.6.0 | 新路由 `/feishu/sync-logs` 注册在 `App.tsx`，守门复用 `<ProtectedRoute allowedRoles={['admin', 'hrbp']}/>` | 项目所有路由均走同一 pattern [VERIFIED: frontend/src/App.tsx] |
| Axios | 1.8.4 | `getSyncLogs(syncType, page)` / `downloadUnmatchedCsv(logId)` 新 service 方法 | 项目所有前端 API 调用统一走 `frontend/src/services/api.ts` 的共享 axios 实例 [VERIFIED: frontend/src/services/feishuService.ts] |
| pytest | 8.3.5 | 新增单元测试覆盖 helper / partial 派生 / per-sync_type 锁 / CSV 下载 | 项目唯一测试框架，既有 `test_feishu_sync_log_model.py` / `test_feishu_leading_zero.py` 模板可复用 [VERIFIED: backend/tests/test_services/] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| csv (stdlib) | — | CSV 下载端点：`io.StringIO()` + `csv.writer` 生成 `employee_no` 单列文件 | D-08 的 `/feishu/sync-logs/{log_id}/unmatched.csv`，返回 `Response(content=..., media_type='text/csv; charset=utf-8', headers={'Content-Disposition': ...})` |
| dataclasses (stdlib) | — | `_SyncCounters` 内部 dataclass | D-11；推荐 `@dataclass(frozen=True, slots=True)` 形式，避免字段拼写错误 |
| httpx | 0.28.1 | 飞书 `_fetch_all_records` / `_ensure_token` — 现有路径，不改动 | 仅作为依赖存在，Phase 31 不直接使用 [VERIFIED: backend/app/services/feishu_service.py:78] |
| threading (stdlib) | — | `trigger_sync` 现有后台同步线程（`_run_sync_in_background`）— 仅考勤路径，不触碰 | Phase 31 四个新 sync_type 走 Celery task 路径（`feishu_sync_eligibility_task`），不走 threading [VERIFIED: backend/app/api/v1/feishu.py:214] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `op.batch_alter_table('feishu_sync_logs')` 两阶段迁移（nullable=True → UPDATE → nullable=False） | 单阶段 `op.add_column(sync_type, nullable=False, server_default='attendance')` | 单阶段看起来更简洁，但 SQLite 下 `server_default` 的回填行为在 Alembic 旧版本上不稳定；两阶段是 Phase 30 既定安全模式，显式 UPDATE 可审计。**坚持两阶段。** |
| 独立 `SessionLocal()` 写 log 终态 | 同 `self.db` 写 log + 业务 upsert 放在同事务内 | 同事务方案会让业务 rollback 连带 log rollback — 同步失败时 HR 看不到任何日志记录。**必须用独立 session（D-13 已锁定）。** |
| `_SyncCounters` dataclass | 继续返回 dict，helper 用 `counters.get('success', 0)` 取值 | dict 模式易 typo（如 `mapping_faild`）静默返回 0；dataclass + mypy 或 frozen=True 能在构造时就报错。**使用 dataclass（D-11 已锁定）。** |
| 前端抽 `CountersBadgeCluster` 子组件 | 全部塞在 `SyncLogsPage.tsx` 单文件 | 不抽分就会形成 500+ 行巨组件，后续 Phase 32（导入日志类似需求）无法复用。**抽子组件是 Claude's Discretion 推荐项（见 D-5x 块）。** |
| CSV 端点返回 `StreamingResponse` | 返回 `Response(content=..., media_type='text/csv')` | 20 行 CSV 体量小（<1KB），用 `Response` 更简单；`StreamingResponse` 在 `iter([content])` 模式下也能跑但徒增一层封装。**推荐 `Response`（参考现有 `eligibility_import.py:152` 的 template download 用了 StreamingResponse，Phase 31 可二选一，但 Response 更简洁）。** |

**Installation:** 本阶段无需 `pip install` / `npm install` — 所有依赖已存在。

**Version verification:** 不适用 — 本阶段不引入新依赖。已核对 `requirements.txt` / `frontend/package.json`，上表所有库均已锁定在项目现有版本。

---

## Architecture Patterns

### Recommended File/Module Layout

```
backend/
├── alembic/versions/
│   └── 31_01_feishu_sync_log_observability.py    # NEW: add sync_type + mapping_failed_count
├── app/
│   ├── models/
│   │   └── feishu_sync_log.py                     # MODIFY: add 2 Mapped columns
│   ├── schemas/
│   │   └── feishu.py                              # MODIFY: SyncLogRead add fields + Literal 'partial'
│   ├── services/
│   │   └── feishu_service.py                      # MODIFY: add _with_sync_log + _SyncCounters + refactor 5 sync_* methods + is_sync_running(sync_type)
│   ├── api/v1/
│   │   └── feishu.py                              # MODIFY: /sync-logs?sync_type=&page= + /sync-logs/{id}/unmatched.csv + trigger_sync 409 with sync_type
│   └── tasks/
│       └── feishu_sync_tasks.py                   # MODIFY: sync_methods key 'performance_grades'→'performance'
├── tests/
│   ├── test_services/
│   │   ├── test_feishu_sync_log_model.py          # EXTEND: add sync_type + mapping_failed_count asserts
│   │   ├── test_feishu_with_sync_log_helper.py    # NEW: helper unit tests (happy + partial + failed + rollback isolation)
│   │   └── test_feishu_per_sync_type_lock.py      # NEW: is_sync_running(sync_type) tests
│   └── test_api/
│       ├── test_feishu_sync_logs_api.py           # NEW: GET /sync-logs?sync_type + CSV endpoint + 409 semantics
│       └── test_feishu_unmatched_csv.py           # NEW: CSV content / filename / role gate

frontend/
├── src/
│   ├── pages/
│   │   └── SyncLogsPage.tsx                       # NEW: route component (admin+hrbp only)
│   ├── components/
│   │   └── feishu-sync-logs/
│   │       ├── CountersBadgeCluster.tsx           # NEW: 5-color segmented badge
│   │       ├── SyncLogRow.tsx                     # NEW: one row = status + counters + mode + action
│   │       └── SyncLogDetailDrawer.tsx            # NEW: click badge → drawer with full unmatched_employee_nos
│   ├── services/
│   │   └── feishuService.ts                       # MODIFY: getSyncLogs(syncType, page) + downloadUnmatchedCsv(logId)
│   ├── types/
│   │   └── api.ts                                 # MODIFY: SyncLogRead add fields + status 'partial'
│   ├── utils/
│   │   └── roleAccess.ts                          # MODIFY: admin + hrbp ROLE_MODULES 加「同步日志」item
│   └── App.tsx                                    # MODIFY: <Route path="/feishu/sync-logs" .../>
```

### Pattern 1: 事务分离 + 独立 Session 写日志终态（D-10 / D-13）

**What:** helper 用 `SessionLocal()` 创建独立 session 写 log 的 running/finished/failed 记录；业务 fn 用 `self.db` 完成 upsert。两个事务互不影响 — 业务 rollback 不清空 log，log commit 失败也不影响业务数据。

**When to use:** 任何「主业务 + 可观测日志」分离场景；本项目 `sync_attendance` 既定模式（feishu_service.py:476-490 failed 分支），Phase 31 提炼为通用 helper。

**Example:** 参考 `backend/app/services/feishu_service.py:474-491`：

```python
# 现有 sync_attendance 的 failed 分支（D-10 原型）
except Exception as exc:
    self.db.rollback()
    # Save failure status in a new session to avoid polluted session state
    try:
        fail_db = SessionLocal()
        try:
            fail_log = fail_db.get(FeishuSyncLog, sync_log_id)
            if fail_log:
                fail_log.status = 'failed'
                fail_log.error_message = str(exc)[:2000]
                fail_log.leading_zero_fallback_count = fallback_counter['count']
                fail_log.finished_at = datetime.now(timezone.utc)
                fail_db.commit()
        finally:
            fail_db.close()
    except Exception:
        logger.exception('Failed to save sync failure log')
    raise
```

Phase 31 helper 将 running log 创建也改走独立 session（现有 `sync_attendance` 是 `self.db.add(sync_log) + self.db.flush()` 同事务创建，然后终态也在 `self.db.commit()` — **这意味着业务 rollback 会把 running log 一起回滚掉**，Phase 31 helper 必须修正这点）。

### Pattern 2: `_SyncCounters` dataclass + helper 调度（D-11）

**What:** 业务 fn 只返回计数器 dataclass；helper 负责把 dataclass 字段映射到 FeishuSyncLog 列。业务 fn 签名改为 `def _sync_performance_body(self, *, sync_log_id: str, app_token, table_id, field_mapping) -> _SyncCounters`。

**When to use:** 所有「需要观测指标的长流程」 — 比 dict 返回更强类型、更少拼写错误。

**Example:**

```python
# backend/app/services/feishu_service.py
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class _SyncCounters:
    success: int = 0                        # 新增记录数
    updated: int = 0                        # 更新现有记录数
    unmatched: int = 0                      # 工号未匹配到 employee
    mapping_failed: int = 0                 # D-02: 字段类型/格式转换失败
    failed: int = 0                         # upsert / commit 异常
    leading_zero_fallback: int = 0          # Phase 30 D-03: lstrip('0') 命中计数
    total_fetched: int = 0                  # 飞书拉取总数
    unmatched_nos: tuple[str, ...] = ()     # 前 100 个未匹配工号；tuple 以满足 frozen
```

### Pattern 3: per-sync_type 分桶锁 + 409 不写日志（D-15 / D-16）

**What:** `is_sync_running(sync_type: str | None = None)` 可选接受 sync_type；有值时只查该 type 的 running 记录。409 冲突在路由层抛 HTTPException，**不进入 helper**，因此不会产生 `status='rejected'` 脏日志。

**When to use:** 所有「同类型互斥 + 不同类型可并行」场景。

**Example:**

```python
# is_sync_running 升级
def is_sync_running(self, sync_type: str | None = None) -> bool:
    stmt = select(FeishuSyncLog).where(FeishuSyncLog.status == 'running')
    if sync_type is not None:
        stmt = stmt.where(FeishuSyncLog.sync_type == sync_type)
    return self.db.execute(stmt.limit(1)).scalar_one_or_none() is not None

# trigger_sync 改造（feishu.py）
service.expire_stale_running_logs(timeout_minutes=30)
if service.is_sync_running(sync_type='attendance'):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={'error': 'sync_in_progress', 'sync_type': 'attendance',
                'message': '考勤同步正在进行中，请稍后再试'},
    )
```

### Pattern 4: 前端 Tab + 分页 + 五色 badge 复用（D-06 / D-07）

**What:** `SyncLogsPage.tsx` 用 `useState<SyncTypeTab>` 驱动 Tab，Tab 切换触发 fetch；`CountersBadgeCluster` 组件接 5 个数值 + 映射到 5 个 CSS 变量 token。

**When to use:** 任何多维度筛选 + 计数器展示的列表页面（Phase 32 导入日志也会复用）。

**Example:**

```tsx
// CountersBadgeCluster.tsx
interface CountersBadgeClusterProps {
  success: number; updated: number; unmatched: number;
  mappingFailed: number; failed: number;
  onBadgeClick?: (key: string) => void;
}

const BADGE_TOKENS = [
  { key: 'success',  label: '成功',    color: 'var(--color-success, #00B42A)' },
  { key: 'updated',  label: '更新',    color: 'var(--color-info, #1456F0)' },
  { key: 'unmatched',label: '未匹配',  color: 'var(--color-warning, #FF7D00)' },
  { key: 'mapping_failed', label: '映射失败', color: 'var(--color-violet, #722ED1)' },
  { key: 'failed',   label: '写库失败', color: 'var(--color-danger, #F53F3F)' },
] as const;
```

### Anti-Patterns to Avoid

- **在 helper 内部吞掉业务异常：** helper 的独立 session `try/except` 必须重抛业务异常，否则 Celery task 无法知道任务失败、不会重试。D-13 明确："独立 session 写 log 终态的 try/except 内部打 `logger.exception` 但不再抛出" — 指 **log 写入本身失败时** 不重抛（这是 log 写入的异常），**不是说业务 fn 的异常不重抛**。关键区分点。
- **用 `self.db` 创建 running log：** 当业务 fn 中途 `self.db.rollback()` 时，running log 会被一起清掉 — HR 永远看不到这条失败记录。必须用独立 `SessionLocal()`。
- **把 sync_type 做成 Enum 但不序列化成 str：** Pydantic v2 的 `Literal['attendance', 'performance', ...]` 比 `enum.Enum` 更轻量、JSON 序列化天然正确；`SyncLogRead.status` 已是 Literal 模式，保持一致。
- **Alembic 单阶段 `add_column(nullable=False, server_default='attendance')`：** SQLite 下虽然理论上可行，但与项目既定模式不符（Phase 30 走两阶段）。此外，存量 `feishu_sync_logs` 历史行全部是考勤同步，直接 server_default 回填可能掩盖迁移审计信号。两阶段 + 显式 UPDATE 更安全。
- **在 Celery task 里加 `@celery_app.task(soft_time_limit=600)` 超时后悄悄不写 log：** 现有 `feishu_sync_eligibility_task` 已有 `soft_time_limit=600`，触发时会抛 `SoftTimeLimitExceeded` — helper 会按 failed 路径写 log。但要验证 in-flight 的 running log 不会被标记为 `running` 泄漏（靠 `expire_stale_running_logs(30min)` 兜底）。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV 行转义（employee_no 含引号 / 换行） | 手写 `','.join(nos)` | `csv.writer(io.StringIO())` + `writerow` | 标准库已处理 quoting / escape；手写易漏引号转义 |
| Alembic SQLite 兼容的列增删改 | 直接 `op.add_column` / `op.alter_column` | `with op.batch_alter_table(...) as batch_op: batch_op.add_column(...)` | SQLite 不支持 ALTER COLUMN / DROP COLUMN；项目已统一（Pitfall 16） |
| Celery task 内部写 DB | `Depends(get_db)` 或外层闭包捕获 session | `db = SessionLocal(); try/finally db.close()` | 跨线程 session 污染 — Pitfall 14 已明确 |
| 前端 blob 下载 | `window.open(url)` 或 `<a href>` 直链 | `api.get(url, { responseType: 'blob' })` + `URL.createObjectURL(blob)` + 动态 `<a>` | 携带 JWT header、处理 Content-Disposition filename、支持权限错误显示；参考 Phase 23 已建立的模式 |
| FeishuSyncLog 字段改动的前端类型同步 | 手抄 TypeScript interface | 必须同时改 `frontend/src/types/api.ts` + 编译时 `tsc --noEmit` 检查 | 前后端类型同步是项目既定做法（没有 openapi-generator） |
| 事务分离写日志终态 | try/finally 里重用 `self.db` | 独立 `SessionLocal()` | 业务 rollback 会连带 log rollback — 同步失败观测不到（D-13） |

**Key insight:** 本阶段没有「新造轮子」的诱惑 — 所有重活（CSV、Alembic batch、Axios blob、pydantic schema）都有现成模式；核心工作是 **重构 + 扩展**，风险在于把旧模式用错位（比如 helper 提炼不完整，`sync_attendance` 部分代码留在旧位置）。

---

## Runtime State Inventory

> 本阶段是纯代码/schema 扩展，涉及数据库 schema 变更但不涉及 rename；仍按模板填写以明确 state 边界。

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | SQLite `wage_adjust.db` 中 `feishu_sync_logs` 表：存量行全部是 `sync_attendance` 产生的（截止 Phase 30）。Phase 31 迁移需对这些存量行 `UPDATE ... SET sync_type='attendance' WHERE sync_type IS NULL`（D-03） | 数据迁移（Alembic `upgrade()` 内完成 UPDATE）。**None（产生式数据库是 SQLite dev）** — 生产 PostgreSQL 尚未切换，此处仅 dev DB 影响。 |
| Live service config | Celery broker (Redis) 中可能存在 in-flight 的 `feishu_sync_eligibility_task(sync_type='performance_grades', ...)`（旧 key 名）。Phase 31 要把 key 改成 `'performance'` | **代码编辑**：在 `feishu_sync_eligibility_task` 的 `sync_methods` dict 内接受旧 key alias：`sync_methods = {'performance': ..., 'performance_grades': ...}` 过渡一版；Phase 32 之后移除 `performance_grades` alias。前端 `EligibilityManagementPage` / `FeishuSyncPanel` 同步改 key（D-01 已锁定）。|
| OS-registered state | 无 — Phase 31 不涉及 Windows Task Scheduler / pm2 / launchd / systemd。现有 Feishu scheduler（`backend/app/scheduler/feishu_scheduler.py`）由 backend 启动时在进程内 APScheduler 驱动，不注册到 OS 层 | None — 验证方法：grep `scheduler/` 目录无 OS-level 注册逻辑。 |
| Secrets/env vars | 无新增 — Phase 31 不引入任何新 env var / secret。`FEISHU_ENCRYPTION_KEY` 沿用 | None。 |
| Build artifacts / installed packages | 无新增依赖 — 无 `pip install` / `npm install`。既有 `.venv` / `node_modules` 无需重装。Alembic 迁移需在本地 SQLite + 未来 PostgreSQL 都执行一次 | **代码编辑 + 迁移运行**：`alembic upgrade head` 在 dev 机器上运行；部署时纳入部署步骤。 |

**Canonical question — After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?**

1. **Celery broker 中排队的 in-flight task**：旧 `sync_type='performance_grades'` 字符串。mitigation: sync_methods dict 加 alias（Claude's Discretion 明确提到）过渡一版，运维在升级前先 drain Celery queue。
2. **浏览器端用户** localStorage 可能缓存旧 tab key — SyncLogsPage 是新页面，无存量问题；EligibilityManagementPage 若有 state 持久化（当前无 localStorage 使用，`useState` 即起即丢）也不受影响。

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SQLite | Local dev `wage_adjust.db` | ✓ | 3.x (Python stdlib) | — |
| PostgreSQL | 生产（未切换） | ✗（未迁移） | — | 继续用 SQLite（v1.4 允许） |
| Redis | Celery broker（`feishu_sync_eligibility_task` 路径） | 需 Celery worker 运行环境 | 5.x | threading fallback 仅 `sync_attendance` 路径使用；四个新 sync_type 必须 Celery，无 threading 回退 |
| Python venv `.venv` | 后端运行 | ✓ | 3.10+ | — |
| Node.js | 前端开发 | ✓ | 18+（package-lock.json 锁定） | — |

**Missing dependencies with no fallback:** 无阻塞项。

**Missing dependencies with fallback:** Redis 不启动时，`/eligibility-import/feishu/sync` 端点的 Celery task 会排队但不执行；这是 Phase 23 既有行为，非 Phase 31 引入。Phase 31 的测试环境可走 Celery `task_always_eager=True` 配置绕开 broker。

---

## Common Pitfalls

### Pitfall A: `_with_sync_log` helper 内吞掉业务异常

**What goes wrong:** helper 的独立 session 写 failed log 时抓了所有异常，导致业务 fn 的真实异常被掩盖，Celery task 无法感知失败，不会重试。HR 看到 `status='failed'` 但 Celery 日志却是 success。

**Why it happens:** D-13 条款「独立 session 写 log 终态的 try/except 内部打 `logger.exception` 但不再抛出」被误读成「连带业务异常一起吞」。

**How to avoid:** helper 代码结构必须严格分层：

```python
def _with_sync_log(self, sync_type, fn, *, triggered_by=None, mode='full', **kwargs):
    # Stage 1: 独立 session 写 running log
    log_db = SessionLocal()
    try:
        sync_log = FeishuSyncLog(sync_type=sync_type, mode=mode, status='running', ...)
        log_db.add(sync_log); log_db.commit()
        sync_log_id = sync_log.id
    finally:
        log_db.close()

    counters: _SyncCounters | None = None
    business_exc: Exception | None = None
    try:
        # Stage 2: 业务 fn 用 self.db
        counters = fn(sync_log_id=sync_log_id, **kwargs)  # 业务 fn 内部 self.db.commit()
    except Exception as exc:
        business_exc = exc
        try:
            self.db.rollback()
        except Exception:
            logger.exception('Business session rollback failed')

    # Stage 3: 独立 session 写终态
    finalize_db = SessionLocal()
    try:
        log_row = finalize_db.get(FeishuSyncLog, sync_log_id)
        if log_row is None:
            logger.error('FeishuSyncLog %s disappeared', sync_log_id)
        elif business_exc is not None:
            log_row.status = 'failed'
            log_row.error_message = str(business_exc)[:2000]
            log_row.finished_at = datetime.now(timezone.utc)
            finalize_db.commit()
        else:
            # Apply counters + derive status (D-14)
            _apply_counters_to_log(log_row, counters)
            finalize_db.commit()
    except Exception:
        logger.exception('Failed to finalize FeishuSyncLog %s', sync_log_id)
        # 不 raise — 避免覆盖 business_exc
    finally:
        finalize_db.close()

    if business_exc is not None:
        raise business_exc  # 必须重抛业务异常！
    return sync_log_id
```

**Warning signs:**
- Celery task 日志里没有 exception traceback，但 FeishuSyncLog 显示 failed
- 测试用例 `test_helper_reraises_business_exception` 不存在
- helper 内部 `except Exception: pass` 无 `logger.exception`

**Phase to address:** HIGH — Phase 31 helper 核心正确性。

---

### Pitfall B: `op.batch_alter_table` 两阶段迁移在 SQLite 上 UPDATE 失败导致 nullable=False 阶段被卡住

**What goes wrong:** 按 D-03 顺序 `add_column(nullable=True) → UPDATE → alter_column(nullable=False)`，但 SQLite 的 `op.batch_alter_table` 在 `recreate='auto'` 下可能在 UPDATE 之前就重建了表（丢 UPDATE 结果），或 UPDATE 跑在未来新建的临时表上。

**Why it happens:** `op.batch_alter_table` 会根据操作推断是否 recreate；add_column 通常不 recreate，但 alter_column 会。两个 batch_alter_table 块中间夹 UPDATE 可能破坏假设。

**How to avoid:** 拆成三个独立 `op.batch_alter_table` / 或把 UPDATE 放在两个 batch_alter_table 之间，明确 SQL：

```python
# alembic/versions/31_01_feishu_sync_log_observability.py
def upgrade() -> None:
    # Stage 1: add sync_type (nullable) + mapping_failed_count (with default)
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.add_column(
            sa.Column('sync_type', sa.String(length=32), nullable=True)
        )
        batch_op.add_column(
            sa.Column('mapping_failed_count', sa.Integer(), nullable=False, server_default='0')
        )

    # Stage 2: backfill existing rows
    op.execute("UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL")

    # Stage 3: enforce nullable=False
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.alter_column('sync_type', existing_type=sa.String(length=32), nullable=False)

def downgrade() -> None:
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.drop_column('mapping_failed_count')
        batch_op.drop_column('sync_type')
```

**Warning signs:**
- `alembic upgrade head` 报 `NOT NULL constraint failed: feishu_sync_logs.sync_type`
- PostgreSQL 本地跑过但 SQLite 失败（或反之）
- revision chain 里 `30_01_leading_zero_fallback` 不是 parent

**Phase to address:** HIGH — Pitfall 16 已映射到「每个涉及表结构变更的 phase」。

---

### Pitfall C: `sync_type` 枚举名与现有 Celery task key 不一致导致 in-flight task 失败

**What goes wrong:** Phase 31 约定 `sync_type='performance'`（D-01），但 `feishu_sync_eligibility_task` 现有 `sync_methods` dict key 是 `'performance_grades'`；现有前端 `EligibilityManagementPage` 也用 `'performance_grades'`。若四处不同步改动，会出现：task 用 `'performance_grades'` → helper 写 `sync_type='performance_grades'` → UI Tab 按 `'performance'` 筛选时这些日志不可见。

**Why it happens:** 同名概念的三个独立 key 定义（后端 ELIGIBILITY_IMPORT_TYPES 常量 + Celery sync_methods dict + 前端 SYSTEM_FIELDS_BY_TYPE）分散在多个文件。

**How to avoid:** 统一改动点 checklist：

1. `backend/app/schemas/eligibility_import.py:6` `ELIGIBILITY_IMPORT_TYPES` set：`'performance_grades'` → `'performance'`
2. `backend/app/tasks/feishu_sync_tasks.py:39` `sync_methods` dict key：`'performance_grades'` → `'performance'`（可加一次性 alias `'performance_grades'` 过渡）
3. `frontend/src/components/eligibility-import/FeishuSyncPanel.tsx:22` `SYSTEM_FIELDS_BY_TYPE` key
4. `frontend/src/pages/EligibilityManagementPage.tsx`（tab key / importType state）
5. `frontend/src/services/eligibilityImportService.ts`（`EligibilityImportType` type）
6. **新增 sync_type 白名单** 在 FeishuSyncLog 写入端校验：`if sync_type not in {'attendance', 'performance', 'salary_adjustments', 'hire_info', 'non_statutory_leave'}: raise ValueError`

验证：grep `'performance_grades'` 应返回 **0 结果**（除 alias 兼容代码）。

**Warning signs:**
- UI Tab「绩效」切换后列表空，但数据库有 `sync_type='performance_grades'` 记录
- Celery task retries 失败，错误是 `'performance_grades' not in sync_methods`
- 前端 SYSTEM_FIELDS_BY_TYPE 的 key 和后端 ELIGIBILITY_IMPORT_TYPES 不匹配

**Phase to address:** HIGH — 影响 SC1（四方法每次执行产生一条记录）的正确性验证。

---

### Pitfall D: 409 不写日志 vs SC4 两次触发两条日志的语义自洽

**What goes wrong:** D-16 锁定「409 不写日志」；SC4 要求「同步流程被触发两次能看到两条记录」。若直接把 SC4 解读成「两次触发都产生 log」，会与 D-16 冲突。

**Why it happens:** 表述歧义 — 「两次触发」可能指「一次锁定期间内的两次点击」（此时第二次 409），也可能指「先触发 A → A 完成 → 再触发 A」（此时第二次正常写 log）。

**How to avoid:** 在 Plan 阶段 / 实现测试中明确：

- **Case 1: 锁定期内重复点击** → 第一次 running log 已存在，第二次请求 409、不写 log、前端显示「同步中，请稍后」
- **Case 2: 锁释放后再次触发** → is_sync_running 返回 False，helper 正常创建第二条 running log → 最终两条独立 log

SC4 的「独立记录，不会静默合并或丢失」语义按 Case 2 实现；Case 1 不产生 log 但产生 HTTP 409 响应（可在前端 toast 层观测）。

**Test 要点：**
```python
def test_second_sync_after_first_completes_creates_second_log():
    # Arrange: 触发第一次 → wait for status='success' → 触发第二次
    # Assert: db 有 2 条 FeishuSyncLog with sync_type='performance', status in (success, partial, failed)

def test_second_sync_during_first_returns_409_no_log():
    # Arrange: 触发第一次 → 未完成时触发第二次
    # Assert: 第二次返回 409 + db 仍只有 1 条 FeishuSyncLog
```

**Warning signs:**
- Plan 中测试用例只覆盖一种情况
- HR UAT 反馈「重复点击没报错也没第二条日志」（说明锁未生效）

**Phase to address:** MEDIUM — SC 验证正确性的核心点。

---

### Pitfall E: `partial` 派生规则颗粒度：`unmatched` 是否包含容忍匹配救回的记录

**What goes wrong:** Phase 30 引入的 `leading_zero_fallback_count` 是「救回来的」成功匹配（已计入 success/updated），而 `unmatched_count` 是「真正没匹配到」的记录。如果 helper 把 `fallback_count` 误当作 unmatched 之一，会错误降级 `status='partial'`。

**Why it happens:** `_lookup_employee` 返回 employee_id ≠ None 时 fallback_counter 递增，但此时记录最终成功 upsert 为 success / updated；容忍匹配不算失败。

**How to avoid:** D-14 派生规则**只**基于 `{unmatched, mapping_failed, failed}` 三项：

```python
def _derive_status(c: _SyncCounters) -> str:
    if c.unmatched + c.mapping_failed + c.failed > 0:
        return 'partial'
    return 'success'
# leading_zero_fallback_count NOT in the formula
```

**Test:**
```python
def test_partial_status_ignores_leading_zero_fallback_count():
    counters = _SyncCounters(success=10, leading_zero_fallback=5, unmatched=0, mapping_failed=0, failed=0)
    assert _derive_status(counters) == 'success'  # 不是 partial
```

**Warning signs:**
- UI 显示 status=partial 但五色 badge 全是绿/蓝（无橙/紫/红）
- `leading_zero_fallback_count > 0` 就触发 status 降级

**Phase to address:** MEDIUM — SC2 正确性。

---

### Pitfall F: `sync_attendance` helper 迁移打破 `sync_with_retry` 现有语义

**What goes wrong:** `sync_with_retry(mode, triggered_by)` 现在调 `self.sync_attendance(mode, triggered_by)` 3 次；如果 sync_attendance 被改为走 helper 后返回类型从 `FeishuSyncLog` 变成 `_SyncCounters`，retry 逻辑破了。

**Why it happens:** D-12 要求 sync_attendance「重构到 `_with_sync_log('attendance', ...)` 模式」— 字面读可能误为改变外部签名。

**How to avoid:** `sync_attendance` 外部签名不变（仍返回 `FeishuSyncLog`），内部改为：

```python
def sync_attendance(self, mode: str, triggered_by: str | None = None) -> FeishuSyncLog:
    sync_log_id = self._with_sync_log(
        sync_type='attendance',
        fn=self._sync_attendance_body,  # 新的私有业务 fn，返回 _SyncCounters
        triggered_by=triggered_by,
        mode=mode,
    )
    # 重新查 FeishuSyncLog 返回给调用方
    return self.db.get(FeishuSyncLog, sync_log_id)
```

`sync_with_retry` 不动。

**Warning signs:**
- 现有 `test_sync_with_retry_*` 测试集体失败
- `sync_attendance` 返回类型变成 dict / _SyncCounters

**Phase to address:** HIGH — 向后兼容是 D-12 显式要求。

---

### Pitfall G: CSV 端点的权限与 PII 暴露

**What goes wrong:** `GET /feishu/sync-logs/{log_id}/unmatched.csv` 如果忘加 `require_roles('admin', 'hrbp')`，任何登录用户甚至未登录用户都能拿到工号列表；即使工号本身不是强 PII，暴露给无权限角色也违反项目「员工端看不到其他员工信息」原则。

**Why it happens:** 新 route 容易漏守门（Pitfall 13）。

**How to avoid:** 强制 `_current_user: User = Depends(require_roles('admin', 'hrbp'))`，并在测试中覆盖：

```python
def test_csv_download_requires_admin_or_hrbp():
    for role in ('employee', 'manager'):
        resp = client.get(f'/api/v1/feishu/sync-logs/{log_id}/unmatched.csv',
                          headers={'Authorization': f'Bearer {token_for(role)}'})
        assert resp.status_code == 403
```

**Warning signs:**
- 路由签名里只有 `db: Session = Depends(get_db)`，无 `require_roles`
- manager / employee 账号能下载到 CSV

**Phase to address:** HIGH — Pitfall 13 已明确「每个涉及员工数据的 phase 都需验证」。

---

### Pitfall H: Celery task `performance_grades → performance` key 名 in-flight 兼容

**What goes wrong:** 升级部署瞬间，broker 中已排队的 `feishu_sync_eligibility_task(sync_type='performance_grades', ...)` 触发时，新代码 `sync_methods` dict 查不到 key 直接 `return {'status': 'failed', ...}`，HR 看到 Celery 失败但无任何 FeishuSyncLog。

**Why it happens:** key 名迁移未考虑 Celery broker 持久化排队状态。

**How to avoid:** 过渡期（建议持续 1 次 release cycle）在 `sync_methods` dict 加 alias：

```python
# backend/app/tasks/feishu_sync_tasks.py
sync_methods = {
    'performance': service.sync_performance_records,
    'performance_grades': service.sync_performance_records,  # alias for in-flight tasks
    'salary_adjustments': service.sync_salary_adjustments,
    'hire_info': service.sync_hire_info,
    'non_statutory_leave': service.sync_non_statutory_leave,
}
# FeishuSyncLog 写入时规范化：
canonical_sync_type = 'performance' if sync_type == 'performance_grades' else sync_type
```

下一个 release 移除 alias，同步更新 `ELIGIBILITY_IMPORT_TYPES` 剔除 `'performance_grades'`。

**Warning signs:**
- Phase 31 上线当天 Celery worker error rate 突增
- 数据库里 FeishuSyncLog.sync_type 既有 `'performance'` 又有 `'performance_grades'`

**Phase to address:** MEDIUM — 运维工程细节，影响上线平滑度。

---

### Pitfall I: 前端 SyncLogsPage 路由未被 admin/hrbp 之外的角色阻断

**What goes wrong:** 新增路由 `/feishu/sync-logs` 未挂在 `<ProtectedRoute allowedRoles={['admin', 'hrbp']}/>` 下；employee / manager 手动输 URL 能看到页面骨架（虽然后端 API 会返 403，但 UI 会短暂显示空壳）。

**Why it happens:** 新路由复制既有 route 格式时漏了守门嵌套。

**How to avoid:** App.tsx 示例：

```tsx
<Route element={<ProtectedRoute allowedRoles={['admin', 'hrbp']} />}>
  <Route element={<SyncLogsPage />} path="/feishu/sync-logs" />
</Route>
```

对照 `AttendanceManagementPage` 的注册模式（App.tsx:459-463）验证一致性。

**Warning signs:**
- employee 账号能进入 `/feishu/sync-logs` 页面（即使数据为空）
- navigateMenu 显示「同步日志」在错误角色下

**Phase to address:** HIGH — Pitfall 1 / 13 映射。

---

## Code Examples

### `_with_sync_log` helper 骨架（feishu_service.py）

```python
# 放在 FeishuService 类方法区，sync_attendance 之上
from dataclasses import dataclass, asdict

@dataclass(frozen=True, slots=True)
class _SyncCounters:
    success: int = 0
    updated: int = 0
    unmatched: int = 0
    mapping_failed: int = 0
    failed: int = 0
    leading_zero_fallback: int = 0
    total_fetched: int = 0
    unmatched_nos: tuple[str, ...] = ()


def _derive_status(counters: _SyncCounters) -> str:
    """D-14: partial if any of {unmatched, mapping_failed, failed} > 0."""
    if counters.unmatched + counters.mapping_failed + counters.failed > 0:
        return 'partial'
    return 'success'


def _apply_counters_to_log(log: FeishuSyncLog, c: _SyncCounters) -> None:
    log.total_fetched = c.total_fetched
    log.synced_count = c.success
    log.updated_count = c.updated
    log.unmatched_count = c.unmatched
    log.mapping_failed_count = c.mapping_failed
    log.failed_count = c.failed
    log.leading_zero_fallback_count = c.leading_zero_fallback
    log.status = _derive_status(c)
    log.finished_at = datetime.now(timezone.utc)
    if c.unmatched_nos:
        log.unmatched_employee_nos = json.dumps(list(c.unmatched_nos))
```

### 业务 fn 签名改造样例（sync_performance_records）

```python
def _sync_performance_records_body(
    self,
    *,
    sync_log_id: str,
    app_token: str,
    table_id: str,
    field_mapping: dict[str, str] | None = None,
) -> _SyncCounters:
    # ... 复用既有 upsert 逻辑 ...
    # 把 skipped 分流到 mapping_failed（D-02 新语义）
    # year 解析失败 / grade 非法 → mapping_failed += 1
    # source 更早或无有效更新 → skipped（业务跳过，不计入 partial）
    return _SyncCounters(
        success=synced,
        updated=updated,
        unmatched=unmatched,
        mapping_failed=mapping_failed,
        failed=failed,
        leading_zero_fallback=fallback_counter['count'],
        total_fetched=total,
        unmatched_nos=tuple(unmatched_nos),
    )


def sync_performance_records(
    self,
    *,
    app_token: str,
    table_id: str,
    field_mapping: dict[str, str] | None = None,
    triggered_by: str | None = None,
) -> FeishuSyncLog:
    sync_log_id = self._with_sync_log(
        sync_type='performance',
        fn=self._sync_performance_records_body,
        triggered_by=triggered_by,
        app_token=app_token,
        table_id=table_id,
        field_mapping=field_mapping,
    )
    return self.db.get(FeishuSyncLog, sync_log_id)
```

### API 路由扩展（feishu.py）

```python
from fastapi import Query, Response
from typing import Literal
import csv, io

SyncTypeLiteral = Literal['attendance', 'performance', 'salary_adjustments', 'hire_info', 'non_statutory_leave']


@router.get('/sync-logs', response_model=list[SyncLogRead])
def get_sync_logs(
    sync_type: SyncTypeLiteral | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> list[SyncLogRead]:
    service = FeishuService(db)
    logs = service.get_sync_logs(sync_type=sync_type, page=page, page_size=page_size)
    return [_sync_log_to_read(log) for log in logs]


@router.get('/sync-logs/{log_id}/unmatched.csv')
def download_unmatched_csv(
    log_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles('admin', 'hrbp')),
) -> Response:
    log = db.get(FeishuSyncLog, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail='sync log not found')
    try:
        nos = json.loads(log.unmatched_employee_nos or '[]')
    except json.JSONDecodeError:
        nos = []
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['employee_no'])
    for no in nos[:20]:          # D-08: 前 20 个
        writer.writerow([no])
    return Response(
        content=buf.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=sync-log-{log_id}-unmatched.csv'},
    )
```

### Alembic 迁移（31_01_feishu_sync_log_observability.py）

```python
"""add_sync_type_and_mapping_failed_count_to_feishu_sync_logs

Revision ID: 31_01_sync_log_observability
Revises: 30_01_leading_zero_fallback
Create Date: 2026-04-21

Phase 31 / IMPORT-03 / IMPORT-04 / D-01 / D-02 / D-03.
Two-phase migration for sync_type NOT NULL (SQLite-safe).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '31_01_sync_log_observability'
down_revision: Union[str, None] = '30_01_leading_zero_fallback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.add_column(sa.Column('sync_type', sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column('mapping_failed_count', sa.Integer(), nullable=False, server_default='0')
        )

    op.execute("UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL")

    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.alter_column(
            'sync_type',
            existing_type=sa.String(length=32),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.drop_column('mapping_failed_count')
        batch_op.drop_column('sync_type')
```

### 前端类型与服务（types/api.ts + feishuService.ts）

```typescript
// frontend/src/types/api.ts
export type SyncLogSyncType =
  | 'attendance'
  | 'performance'
  | 'salary_adjustments'
  | 'hire_info'
  | 'non_statutory_leave';

export interface SyncLogRead {
  id: string;
  sync_type: SyncLogSyncType;              // NEW
  mode: string;
  status: 'running' | 'success' | 'partial' | 'failed';  // NEW: 'partial'
  total_fetched: number;
  synced_count: number;
  updated_count: number;
  skipped_count: number;
  unmatched_count: number;
  mapping_failed_count: number;             // NEW
  failed_count: number;
  leading_zero_fallback_count: number;
  error_message: string | null;
  unmatched_employee_nos: string[] | null;
  started_at: string;
  finished_at: string | null;
  triggered_by: string | null;
}

// frontend/src/services/feishuService.ts
export async function getSyncLogs(
  opts: { syncType?: SyncLogSyncType; page?: number; pageSize?: number } = {},
): Promise<SyncLogRead[]> {
  const params: Record<string, unknown> = {};
  if (opts.syncType) params.sync_type = opts.syncType;
  if (opts.page) params.page = opts.page;
  if (opts.pageSize) params.page_size = opts.pageSize;
  const response = await api.get<SyncLogRead[]>('/feishu/sync-logs', { params });
  return response.data;
}

export async function downloadUnmatchedCsv(logId: string): Promise<void> {
  const response = await api.get<Blob>(`/feishu/sync-logs/${logId}/unmatched.csv`, {
    responseType: 'blob',
  });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `sync-log-${logId}-unmatched.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sync_attendance` 内部手写 running/failed log（`self.db` 写 running、独立 session 写 failed） | Phase 31 提炼为 `_with_sync_log` helper，五个 sync 方法统一复用 | Phase 31 | 一处改动影响所有同步类型观测语义，减少四处重复代码 |
| 四个新 sync 方法返回 dict `{synced, skipped, failed, total}` | 返回 `_SyncCounters` dataclass，字段拼写由类型系统保证 | Phase 31 | 计数器命名/遗漏导致的 silent bug 降为 0 |
| `FeishuSyncLog.status` 只有 `running/success/failed` | 加 `partial` 状态，按 `unmatched+mapping_failed+failed>0` 派生 | Phase 31 / D-14 | HR 能直观区分「全对 vs 部分失败 vs 完全失败」 |
| `is_sync_running()` 全局锁（任何 sync_type 都阻塞） | per-sync_type 分桶锁，同时支持全局查询（传 None 参数） | Phase 31 / D-15 | 绩效同步和入职信息同步可并行，HR UX 改善 |
| `skipped_count` 混合「业务跳过 + 字段映射失败」 | `skipped_count` 收紧为业务跳过；新增 `mapping_failed_count` | Phase 31 / D-02 | HR 诊断「为什么 120 条拉下来只落库 80」时能看清 40 条到底是类型错了还是业务过滤了 |
| 考勤页 `SyncStatusCard` 单独展示最新同步状态 | 新增独立 `/feishu/sync-logs` 页面展示所有 sync_type 的历史列表 | Phase 31 / D-05 | HR 不用到「考勤管理」页面里才能看飞书同步情况，且其他四类同步终于有观测入口 |

**Deprecated/outdated:**
- `ELIGIBILITY_IMPORT_TYPES` set 中的 `'performance_grades'` key：Phase 31 后逐步替换为 `'performance'`（过渡期保留 alias，Phase 32 移除）
- `sync_performance_records / sync_salary_adjustments / sync_hire_info / sync_non_statutory_leave` 的 dict 返回签名：Phase 31 内部改为 `_SyncCounters`，但外部签名改返回 `FeishuSyncLog`（更有观测价值）

---

## Assumptions Log

> 所有「以为如此但未在本会话中二次核对」的判断都在此登记。

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Celery broker 中可能有排队的 `sync_type='performance_grades'` in-flight task | Runtime State Inventory / Pitfall H | 若 Redis queue 实际为空，alias 是多余代码；若非空而未加 alias，上线当天会出现 task 失败 |
| A2 | 存量 `feishu_sync_logs` 行全部是 sync_attendance 产生（Phase 30 之前只有考勤同步写 log） | Runtime State Inventory / Pitfall B | 若存量有非考勤行（比如曾经跑过测试数据的 `sync_type` 已被设置），UPDATE 逻辑可能覆盖已有数据。缓解：UPDATE 语句加 `WHERE sync_type IS NULL` 而不是无条件 |
| A3 | `op.batch_alter_table` 对「两次 add_column + 中间 UPDATE + 再 alter_column nullable=False」的顺序在 SQLite 1.14.0 上行为稳定（按 Pitfall B 示例） | Pitfall B / Alembic 迁移 | 若 batch_alter_table 的 recreate='auto' 推断和示例不符，UPDATE 可能跑在旧表上被丢弃。建议本地双跑 SQLite + PostgreSQL 验证 |
| A4 | 前端 `CountersBadgeCluster` 可从 `SyncStatusCard` 的五色 badge 抽取，无需引入新 CSS token | Pattern 4 / Claude's Discretion | 若抽取时发现 `var(--color-violet)` token 未定义，需额外在 Tailwind theme 或 global CSS 新增一个 — 小改动但不在计划内 |
| A5 | FeishuSyncLog 的 `unmatched_employee_nos` 字段存的是 JSON 字符串（非 List），CSV 端点需要 `json.loads` 后取前 20 | Code Examples / CSV 端点 | 若上游某处把它存成其他格式，解析会失败。现状 feishu_service.py:468 证实是 `json.dumps(unmatched_nos)`，但 API response 已 loads 为 `List[str]` — ORM 层仍是 Text JSON |
| A6 | `status='rejected'` 作为「409 被拒绝」的状态不存在于当前代码 — D-16 锁定不写 | Decisions § D-16 | 若代码某处现有 rejected 逻辑，需一并清理；grep 确认：`'rejected'` 字符串在 feishu_service 里未出现，假设成立 |

**If this table is empty:** 不适用 — 上述假设需在 Plan 阶段或首个实现 Wave 用一次性验证动作确认。

---

## Open Questions

1. **过渡期 `performance_grades` alias 保留多久？**
   - 什么我们知道：Phase 31 上线后立即、Phase 32 肯定要移除（CONTEXT 暗示 Phase 32 会动 ELIGIBILITY_IMPORT_TYPES）。
   - 什么不清楚：是否在 Phase 31 内一次性清掉（降低复杂度，但承担 in-flight 风险）vs Phase 32 清（更稳，但代码里多一个 TODO）。
   - 推荐：Phase 31 保留 alias + TODO 注释 `# TODO(phase-32): remove performance_grades alias`；运维在升级 Phase 31 前 drain Celery queue。Plan 阶段确认。

2. **`skipped_count` 语义变更的数据迁移**
   - 什么我们知道：D-02 说「`skipped_count` 语义收紧为业务跳过」，新增 `mapping_failed_count` 专表字段映射失败。
   - 什么不清楚：存量日志的 `skipped_count` 保持不变，还是迁移时把一部分迁到 `mapping_failed_count`？
   - 推荐：**存量不迁移**（Phase 30 EMPNO-04 同理的保守原则）。新语义只在 Phase 31 之后产生的 log 上生效；存量 `skipped_count` 保留原语义。文档在 `SUMMARY.md` 明确记录。

3. **CSV 下载是否按 sync_type 差异化内容？**
   - 什么我们知道：D-08 锁定 CSV 单列 `employee_no`、前 20 行。
   - 什么不清楚：不同 sync_type 的 unmatched_employee_nos 字段都存在且口径一致？
   - 推荐：所有五类 sync 都已在容忍匹配命中后退还 emp_no 到 unmatched_nos（见 sync_attendance:394, sync_performance_records:538 等），Phase 31 helper 从 `_SyncCounters.unmatched_nos` 统一填入 `FeishuSyncLog.unmatched_employee_nos` — 口径一致。

4. **`mode` 字段对非 attendance 类型固定为 `'full'` — 前端如何渲染？**
   - 什么我们知道：D-04 说「前端列表展示 mode 列时仅对 `sync_type='attendance'` 显示，其他隐藏」。
   - 什么不清楚：具体是整列隐藏，还是某行显示「—」？
   - 推荐：行内按 sync_type 条件渲染 `mode`：attendance 时显示 full/incremental badge，其他显示空白或 `—`。Plan 阶段与视觉稿对齐。

---

## Validation Architecture

> `workflow.nyquist_validation = true`（.planning/config.json），本章节必须完整填写。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5（后端）+ `tsc --noEmit`（前端 lint-only） |
| Config file | 项目根无 pytest.ini / pyproject.toml；走默认 discovery（backend/tests/test_*.py） |
| Quick run command | `pytest backend/tests/test_services/test_feishu_with_sync_log_helper.py -x -v` |
| Full suite command | `pytest backend/tests -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMPORT-03 | 四方法每次执行写一条 FeishuSyncLog（sync_type 正确、counters 五项齐备） | integration | `pytest backend/tests/test_services/test_feishu_sync_methods_write_log.py -x` | ❌ Wave 0 |
| IMPORT-03 | `_with_sync_log` helper：happy path 写 running→success 两次 commit，独立 session | unit | `pytest backend/tests/test_services/test_feishu_with_sync_log_helper.py::test_helper_happy_path -x` | ❌ Wave 0 |
| IMPORT-03 | `_with_sync_log` helper：业务 rollback 不回滚 log（D-13 事务隔离） | unit | `pytest backend/tests/test_services/test_feishu_with_sync_log_helper.py::test_business_rollback_does_not_affect_log -x` | ❌ Wave 0 |
| IMPORT-03 | `_SyncCounters` dataclass 五字段齐全 + frozen=True | unit | `pytest backend/tests/test_services/test_feishu_sync_counters_dataclass.py -x` | ❌ Wave 0 |
| IMPORT-03 | sync_attendance 重构后外部签名仍返回 FeishuSyncLog（向后兼容） | integration | `pytest backend/tests/test_services/test_feishu_service.py::test_sync_attendance_returns_log -x` | ⚠️ 文件存在但内容是 xfail stubs — 需补实现 |
| IMPORT-03 | sync_with_retry 调 sync_attendance 仍然工作 | integration | `pytest backend/tests/test_services/test_feishu_sync_retry.py -x` | ❌ Wave 0 |
| IMPORT-04 | partial 派生规则：unmatched+mapping_failed+failed>0 → partial | unit | `pytest backend/tests/test_services/test_feishu_partial_status_derivation.py -x` | ❌ Wave 0 |
| IMPORT-04 | partial 派生规则：leading_zero_fallback>0 不触发 partial | unit | `pytest backend/tests/test_services/test_feishu_partial_status_derivation.py::test_fallback_count_ignored -x` | ❌ Wave 0 |
| IMPORT-04 | GET /feishu/sync-logs?sync_type=performance 仅返回该 type 记录 | API integration | `pytest backend/tests/test_api/test_feishu_sync_logs_api.py::test_get_logs_filtered_by_sync_type -x` | ❌ Wave 0 |
| IMPORT-04 | GET /feishu/sync-logs 分页（page=1 / page=2） | API integration | `pytest backend/tests/test_api/test_feishu_sync_logs_api.py::test_pagination -x` | ❌ Wave 0 |
| IMPORT-04 | GET /feishu/sync-logs/{id}/unmatched.csv 返回 text/csv，前 20 行 | API integration | `pytest backend/tests/test_api/test_feishu_unmatched_csv.py::test_csv_download_content -x` | ❌ Wave 0 |
| IMPORT-04 | CSV 端点要求 admin/hrbp，employee/manager 返回 403 | API integration | `pytest backend/tests/test_api/test_feishu_unmatched_csv.py::test_csv_download_role_gated -x` | ❌ Wave 0 |
| IMPORT-04 | SyncLogRead schema 有 sync_type / mapping_failed_count / status='partial' | schema | `pytest backend/tests/test_api/test_feishu_sync_logs_api.py::test_schema_shape -x` | ❌ Wave 0 |
| SC3（D-15） | is_sync_running(sync_type='performance') 只查该 type；其他 type 可并行 | unit | `pytest backend/tests/test_services/test_feishu_per_sync_type_lock.py -x` | ❌ Wave 0 |
| SC3（D-16） | 409 不写 log：锁定期内二次触发 | API integration | `pytest backend/tests/test_api/test_feishu_sync_logs_api.py::test_409_does_not_write_log -x` | ❌ Wave 0 |
| SC4（D-16） | 两次完整同步 → 两条独立 log | integration | `pytest backend/tests/test_api/test_feishu_sync_logs_api.py::test_sequential_syncs_create_separate_logs -x` | ❌ Wave 0 |
| D-01 | sync_type 枚举值白名单（attendance / performance / salary_adjustments / hire_info / non_statutory_leave） | unit | `pytest backend/tests/test_services/test_feishu_sync_type_whitelist.py -x` | ❌ Wave 0 |
| D-02 | mapping_failed_count 覆盖：year 解析失败 / grade 非法 / date 解析失败 | integration | `pytest backend/tests/test_services/test_feishu_mapping_failed_counter.py -x` | ❌ Wave 0 |
| D-03 | Alembic migration upgrade + downgrade 双向跑通 SQLite | migration | `alembic upgrade head && alembic downgrade -1` | N/A — 手工 smoke |
| D-03 | Migration 后 FeishuSyncLog 查询能按 sync_type 过滤 | integration | `pytest backend/tests/test_models/test_feishu_sync_log_migration.py -x` | ❌ Wave 0 |
| D-05 / D-06 | 前端 `SyncLogsPage.tsx` TypeScript 无编译错误 | lint | `cd frontend && npm run lint` | N/A — 全量 lint |
| D-07 / D-08 | 前端 `CountersBadgeCluster` + `SyncLogDetailDrawer` / CSV 下载按钮 — 人工 UAT（VALIDATION.md 记录 Playwright 人工步骤） | manual | 浏览器打开 /feishu/sync-logs 验证 Tab、badge、抽屉、CSV 下载 | — |
| D-17 | expire_stale_running_logs 对五类 sync_type 都生效 | unit | `pytest backend/tests/test_services/test_feishu_expire_stale.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/test_services/test_feishu_with_sync_log_helper.py backend/tests/test_services/test_feishu_partial_status_derivation.py -x` — helper / partial 派生两个核心文件 < 10s
- **Per wave merge:** `pytest backend/tests/test_services backend/tests/test_api -k feishu -x` — 所有 feishu 相关测试 < 60s
- **Phase gate:** `pytest backend/tests -x && cd frontend && npm run lint` — 全量 + 前端 lint；manual UAT 用 `31-HUMAN-UAT.md` 对照；VALIDATION.md 完整记录

### Wave 0 Gaps

- [ ] `backend/tests/test_services/test_feishu_with_sync_log_helper.py` — helper happy path / business exception / rollback isolation / log finalize exception swallow
- [ ] `backend/tests/test_services/test_feishu_sync_counters_dataclass.py` — dataclass frozen + fields validation
- [ ] `backend/tests/test_services/test_feishu_sync_methods_write_log.py` — 四 sync 方法都走 helper、都写 log
- [ ] `backend/tests/test_services/test_feishu_partial_status_derivation.py` — _derive_status 12+ 用例（full success / all counters zero / 仅 unmatched / 仅 mapping_failed / 仅 failed / 两两组合 / leading_zero ignored）
- [ ] `backend/tests/test_services/test_feishu_per_sync_type_lock.py` — is_sync_running(None) vs is_sync_running('attendance') 四种组合 + 不同 sync_type 并行允许
- [ ] `backend/tests/test_services/test_feishu_mapping_failed_counter.py` — year / grade / date / type 四类 mapping failure 计数
- [ ] `backend/tests/test_services/test_feishu_sync_type_whitelist.py` — 非法 sync_type 直接 ValueError
- [ ] `backend/tests/test_services/test_feishu_sync_retry.py` — sync_with_retry 重试 3 次仍然产生正确 FeishuSyncLog
- [ ] `backend/tests/test_services/test_feishu_expire_stale.py` — 五类 sync_type 的 running log 都能被 expire
- [ ] `backend/tests/test_models/test_feishu_sync_log_migration.py` — migration upgrade 后 sync_type / mapping_failed_count 字段可查询
- [ ] `backend/tests/test_api/test_feishu_sync_logs_api.py` — list / filter / pagination / 409 no log / sequential logs
- [ ] `backend/tests/test_api/test_feishu_unmatched_csv.py` — content / filename / role gate / missing log 404 / empty nos 返回单行 header
- [ ] `backend/tests/test_services/test_feishu_service.py` — 把 8 个 xfail stubs 升级为真正实现（或确认本 phase 不涉及这些 requirement 就保留 xfail）

---

## Security Domain

> `security_enforcement` 默认启用（config.json 未明确 disable）— 本章必填。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT HS256 via `python-jose`；新路由沿用 `get_current_user` + `require_roles('admin', 'hrbp')` |
| V3 Session Management | yes | 现有 access/refresh token 机制不变；新端点依赖 axios 拦截器刷新 |
| V4 Access Control | yes | `require_roles('admin', 'hrbp')` 守门 `/feishu/sync-logs` 所有端点；前端路由用 `<ProtectedRoute allowedRoles={['admin', 'hrbp']}/>`（Pitfall I） |
| V5 Input Validation | yes | Pydantic v2：`SyncTypeLiteral` 约束 sync_type；`page: int = Query(ge=1)` / `page_size: int = Query(ge=1, le=100)` 边界 |
| V6 Cryptography | no | 本阶段不涉及加解密；`FeishuConfig` 的 encrypted_app_secret 由现有 `encrypt_value/decrypt_value` 处理 |
| V7 Error Handling | yes | helper 的独立 session 异常 `logger.exception` 不泄露 stack；business exception 重抛后由 FastAPI 全局 handler 转为 500 + 脱敏 message |
| V8 Data Protection | yes | CSV 只含 employee_no（工号不是强 PII）；角色守门确保只有 HR 可下载；response headers 设 `Content-Disposition` 强制 attachment，防止浏览器直接渲染 |
| V9 Communication | yes | HTTPS 由 reverse proxy 终止；CSV 通过现有 JWT-authenticated 通道下载 |
| V10 Malicious Code | no | 本阶段无 eval/exec；CSV 生成走 `csv.writer`，不构造动态 SQL |
| V11 Business Logic | yes | `partial` 派生规则（D-14）确保 HR 看到的 status 反映真实数据质量；per-sync_type 锁（D-15）防止竞态条件 |
| V12 Files and Resources | yes | CSV 端点不涉及文件系统 — 内存生成；无 path traversal 风险 |
| V13 API and Web Service | yes | 新 endpoints 沿用 `/api/v1/feishu/*` 版本化路径；Pydantic 响应模型严格约束 |
| V14 Configuration | no | 本阶段无配置变更 |

### Known Threat Patterns for FastAPI + SQLAlchemy + React

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection 在 `unmatched.csv` 端点的 log_id 路径参数 | Tampering | log_id 经 `db.get(FeishuSyncLog, log_id)` 走 SQLAlchemy ORM，参数化查询；SQL injection 不可能（除非手写原始 SQL） |
| 横向越权：employee 访问 `/feishu/sync-logs?sync_type=...` 看到飞书同步数据 | Information disclosure | `require_roles('admin', 'hrbp')` 硬守门；employee/manager 返回 403 |
| 前端路由泄露：未登录用户看到 SyncLogsPage 骨架 | Information disclosure | `<ProtectedRoute allowedRoles={['admin', 'hrbp']}/>` 嵌套 + 后端 API 返 401/403（双保险） |
| CSV 注入（employee_no 含 `=HYPERLINK(...)` 恶意公式） | Tampering（Excel opening 端） | employee_no 来自飞书源 / DB，非用户直接输入；但建议在 `csv.writer` 行前缀 `'` 防御（非项目硬要求，可做 defense in depth） |
| Timing attack 泄露 log_id 是否存在 | Information disclosure | 返回 404 vs 403 时序差 — 项目现有端点已接受此风险，本阶段沿用 |
| 并发竞态：两个 admin 同时触发同一 sync_type | Tampering / DoS | per-sync_type 锁（D-15）+ expire_stale_running_logs（D-17）兜底 |
| Stale running log 阻塞同步 | Denial of Service | `expire_stale_running_logs(timeout_minutes=30)` 每次 trigger 前跑一次（feishu.py:205 现有），覆盖所有 sync_type（D-17） |

---

## Project Constraints (from CLAUDE.md)

遵循项目 `./CLAUDE.md` 的以下硬约束（本阶段必然触及的条款）：

- **分层方向**：`api/ → services/ → engines/ → models/` — 本阶段所有改动严格按层，不从 models 调 services。
- **评分规则/系数配置化**：不适用（本阶段无业务规则引入），但 sync_type 枚举作为常量集中在 `ELIGIBILITY_IMPORT_TYPES` 白名单，不散落多处。
- **AI 结果结构化 JSON**：不适用（无 AI 调用）。
- **上传解析→评分→API 输出 Schema 对接**：本阶段仅改 SyncLogRead schema，前后端类型同步（types/api.ts + schemas/feishu.py）。
- **关键业务结果可审计、可解释、可追踪**：FeishuSyncLog 新增 `sync_type` + `mapping_failed_count` 直接增强可审计性；helper 事务分离保证「同步失败」可观测（D-13）。
- **对外 API 版本化 `/api/v1/...`**：新端点在 `/api/v1/feishu/sync-logs` + `/api/v1/feishu/sync-logs/{id}/unmatched.csv`，遵循既有前缀。
- **批量导入幂等性**：本阶段不改导入逻辑（留给 Phase 32）；但 per-sync_type 锁保证同步幂等（D-15）。
- **看板数据口径一致**：不适用（非看板改动）。
- **完成任务前必须测试**：Validation Architecture 章节已列 20+ 个需新建的测试文件。
- **遇到外部依赖阻塞时停止**：本阶段无外部阻塞。
- **所有重要变更让后续代理看懂**：helper / dataclass 设计显式化（D-10/D-11），Plan 阶段需详细注释 skipped vs mapping_failed 语义差异。
- **Pydantic v2** + `ConfigDict(from_attributes=True)`：SyncLogRead 沿用。
- **`from __future__ import annotations`**：所有新文件必须首行。
- **keyword-only 参数（`*`）**：helper 签名 `_with_sync_log(self, sync_type, fn, *, triggered_by=None, **kwargs)` 遵循。
- **单引号字符串**：所有新 Python 代码。
- **强制 `strict: true` TypeScript**：前端新组件 / 服务需通过 `npm run lint`。
- **没有 ESLint 配置**：前端仅 `tsc --noEmit` 检查。
- **没有 Prettier**：保持 2-space / 4-space 手动一致性。

---

## Sources

### Primary (HIGH confidence)
- `backend/app/models/feishu_sync_log.py` — FeishuSyncLog 当前字段定义（已读） [VERIFIED: 本会话 Read]
- `backend/app/services/feishu_service.py` — sync_attendance + 四个 sync_* 方法 + is_sync_running + expire_stale_running_logs 当前实现（完整读取） [VERIFIED: 本会话 Read]
- `backend/app/api/v1/feishu.py` — trigger_sync / get_sync_logs / get_sync_status 当前路由 [VERIFIED: 本会话 Read]
- `backend/app/api/v1/eligibility_import.py` — trigger_feishu_sync task 入口 + ELIGIBILITY_IMPORT_TYPES 使用 [VERIFIED: 本会话 Read]
- `backend/app/schemas/feishu.py` — SyncLogRead / SyncTriggerRequest 当前定义 [VERIFIED: 本会话 Read]
- `backend/app/schemas/eligibility_import.py` — ELIGIBILITY_IMPORT_TYPES 常量 [VERIFIED: 本会话 Read]
- `backend/app/tasks/feishu_sync_tasks.py` — feishu_sync_eligibility_task sync_methods dict [VERIFIED: 本会话 Read]
- `backend/tests/test_services/test_feishu_sync_log_model.py` — FeishuSyncLog 测试模板 [VERIFIED: 本会话 Read]
- `backend/tests/test_services/test_feishu_leading_zero.py` — _lookup_employee + _map_fields + validate_field_mapping 测试模式（in-memory SQLite + StaticPool + MagicMock httpx） [VERIFIED: 本会话 Read]
- `alembic/versions/30_01_add_leading_zero_fallback_count.py` — batch_alter_table 单列加法参考 [VERIFIED: 本会话 Read]
- `frontend/src/App.tsx` — 路由注册模式 + ProtectedRoute 嵌套 [VERIFIED: 本会话 Read]
- `frontend/src/components/attendance/SyncStatusCard.tsx` — 五色 badge 视觉参考 [VERIFIED: 本会话 Read]
- `frontend/src/services/feishuService.ts` — getSyncLogs / getLatestSyncStatus 现有服务 [VERIFIED: 本会话 Read]
- `frontend/src/types/api.ts` — SyncLogRead 类型当前定义（行 781-797） [VERIFIED: 本会话 Read]
- `frontend/src/utils/roleAccess.ts` — admin/hrbp ROLE_MODULES 结构 [VERIFIED: 本会话 Read]
- `.planning/phases/31-feishu-sync-observability/31-CONTEXT.md` — 本阶段 D-01~D-17 全部决策 + canonical_refs [VERIFIED: 本会话 Read]
- `.planning/phases/30-employee-no-leading-zero/30-CONTEXT.md` — Phase 30 leading_zero_fallback_count 前置决策 [VERIFIED: 本会话 Read]
- `.planning/ROADMAP.md` — Phase 31 四条 SC [VERIFIED: 本会话 Read]
- `.planning/REQUIREMENTS.md` — IMPORT-03/IMPORT-04 原始定义 [VERIFIED: 本会话 Read]
- `.planning/codebase/CONVENTIONS.md` / `ARCHITECTURE.md` / `TESTING.md` — 项目既定模式 [VERIFIED: 本会话 Read]
- `.planning/research/PITFALLS.md` — Pitfall 7 / Pitfall 9 / Pitfall 13 / Pitfall 14 / Pitfall 15 / Pitfall 16 [VERIFIED: 本会话 Read]
- `.planning/config.json` — workflow.nyquist_validation = true [VERIFIED: 本会话 Read]

### Secondary (MEDIUM confidence)
- `backend/app/services/attendance_service.py:93` — `get_latest_sync_status` 被 `/sync-status` 端点调用 [VERIFIED: 本会话 grep]
- `frontend/src/components/eligibility-import/FeishuSyncPanel.tsx` — 前端 Feishu sync 触发路径（SYSTEM_FIELDS_BY_TYPE key 位置） [VERIFIED: 本会话 Read（前 100 行）]

### Tertiary (LOW confidence — 需 Plan 阶段验证)
- Celery broker 中是否有 in-flight `performance_grades` task — 运维可用 `celery inspect active` 确认 [ASSUMED]
- `frontend/src/components/layout/AppShell.tsx` 的 `getRoleModules` 能否直接增加 nav item 通过 `roleAccess.ts` — 假设成立（已读 AppShell，机制清晰） [ASSUMED，但置信度高]
- `var(--color-violet)` token 是否在项目 Tailwind theme 中定义 — 需 grep tailwind.config.js 确认 [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 全部是项目既定库，无新依赖
- Architecture / helper design: HIGH — 直接在 `sync_attendance` 既定模式上提炼，无新发明
- Pitfalls: HIGH — 项目 PITFALLS.md 已覆盖所有关键风险（Alembic、Celery session、RBAC、事务分离）；本阶段特有的 6 个 Pitfall（A-I）都源自 CONTEXT 决策的精读
- Validation: HIGH — pytest 模式已有 `test_feishu_sync_log_model.py` / `test_feishu_leading_zero.py` 作模板
- Security: HIGH — ASVS 分类清晰，威胁模型简单（角色守门 + 事务分离为主）
- Runtime state: MEDIUM — Celery broker in-flight task 的假设需运维确认（A1）

**Research date:** 2026-04-21
**Valid until:** 2026-05-21（30 天；若 v1.4 milestone 进度显著变化或 Celery 基础设施改动则需重验证）
