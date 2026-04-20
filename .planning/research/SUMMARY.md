# Project Research Summary

**Project:** 公司综合调薪工具 — v1.4 员工端体验完善与导入链路稳定性
**Domain:** 企业内部调薪平台（员工自助可见 + 绩效分档 + 多源导入一致性）
**Researched:** 2026-04-20
**Confidence:** HIGH

---

## Executive Summary

v1.4 是一个"纯业务层"里程碑：四块新增能力（员工端资格自助、绩效档次 20/70/10、历史绩效展示、导入链路修复）+ 一块文档债务补齐（Phase 11 SUMMARY/UAT），全部可用**现有技术栈**落地，无需新增任何后端或前端依赖。核心工程挑战在三处：(a) 员工端可见性意味着第一次将员工角色纳入资格 API 的访问主体——必须从一开始就把横向越权和 PII masking 做对；(b) 20/70/10 分档需要在"纯引擎 + 小样本守卫 + 快照稳定性"三条约束下设计，否则会引发员工信任危机；(c) 工号前导零的根因在上游数据源（Excel 存储层 + 飞书"数字"字段类型），必须在模板、读入、迁移三端联动修复。

研究结论：沿用 `api/ → services/ → engines/ → models/` 分层，新增 1 个纯引擎（`PerformanceTierEngine`）、1 个服务（`PerformanceService`）、1 个路由（`/api/v1/performance`）、1 个员工端自助端点（`GET /eligibility/me`），其他全部是现有方法扩展。导入链路的核心修复是给飞书 4 个同步方法补齐 `FeishuSyncLog` + 四类计数器（synced / updated / unmatched / mapping_failed / failed），把"假成功"问题一次性暴露在 HR 可见的日志里。Excel 模板下载的 bug 根因是 `ImportService.SUPPORTED_TYPES` 缺 `hire_info` / `non_statutory_leave` 两项——补齐即可。

最大风险是**工号前导零的存量迁移**——盲目 `zfill` 会破坏合法 4 位工号员工的账号。必须做"人工确认清单 + AuditLog + 回滚脚本"三件套，不接受自动批量补零。其次是**档位稳定性**——v1.4 必须引入 `PerformanceTierSnapshot` 表或等效的 `lru_cache + 显式 invalidate`，避免"HR 补录一条就全员漂移"的信任崩塌。第三是**员工端横向越权**——必须走 `/eligibility/me` 无参数路由，不接受 `/eligibility/{employee_id}` 让 employee 角色访问的任何变体。

---

## Key Findings

### Recommended Stack

v1.4 **零新增依赖**。现有栈（FastAPI 0.115 + SQLAlchemy 2.0 + SQLite 3.50 + pandas 2.2.3 + openpyxl 3.1.5 + React 18 + Axios）完整覆盖所有需求。绩效分档用 SQLAlchemy 2.0 原生的 `func.percent_rank().over()` 窗口函数（SQLite 3.25+ 支持，实测 3.50.4）；工号前导零用 `pandas dtype=str` + openpyxl `cell.number_format = '@'`；Excel 模板下载用 FastAPI `Response(content=bytes)` + RFC 5987 `Content-Disposition`；飞书继续用 httpx 直调，拒绝迁移到 `lark-oapi` SDK（40+ 间接依赖，无业务收益）。

**Core technologies（保持不变）：**
- FastAPI 0.115.0 + SQLAlchemy 2.0.36 — `/api/v1` 版本化路由 + ORM，窗口函数 `.over()` 原生支持
- SQLite 3.50.4 (runtime) — `PERCENT_RANK()` / `NTILE()` 在 3.25 起原生支持；v1.4 开发期主库
- pandas 2.2.3 + openpyxl 3.1.5 — Excel 读写；`dtype=str` 已正确配置
- httpx 0.28.1 + 现有 `FeishuService`（1100 行稳定代码）— 飞书 bitable 集成
- React 18.3.1 + Axios 1.8.4 + 现有 `AuthContext` / `ProtectedRoute` — 员工端自助页直接复用

**Stack 决策点（已选）：**
- 绩效分档：**`PERCENT_RANK()`** 优于 `NTILE(10)`（同等级员工保持同百分位，不会被机械切桶）
- 工号前导零修复：**模板 + 读入 + 飞书 + 迁移四端联动**，不引入 `calamine` / `fastexcel`
- 模板下载：**`Response(content=bytes)`** 优于 `StreamingResponse`（模板 < 50KB，不需要流式）
- 飞书集成：**保持 httpx 直调**，不迁移 SDK

详见 [STACK.md](./STACK.md)。

### Expected Features

四大类共 20+ feature，P1 MVP 聚焦"员工端价值闭环 + 导入稳定性"；P2/P3 是体验加分（进度条/ETA/申诉/趋势图/回滚）。

**Must have (table stakes)：**
- **员工端资格自助**：三态可视化、未通过规则清单、规则说明 tooltip、周期归属、刷新时间戳、**self-only 访问**、**随时可见（不绑 visibility date）**
- **绩效 1/2/3 档**：档位 + tooltip 说明 + 样本量注释；HR 端看分布图；**不显示排名、不显示具体百分位、不显示同档名单**
- **评估详情/调薪建议历史绩效表**：周期/等级/绩效分/评语四字段；按时间倒序；与当前周期关联高亮；空状态兜底
- **导入链路修复**：Preview + diff（insert/update/no-change/冲突分类）、字段级 diff、按业务键 upsert、**空值 = 不修改**（行业默认）、Excel 模板返回真实 .xlsx、工号前导零全链路、飞书同步根因修复、审计日志
- **Phase 11 补齐**：SUMMARY.md + 四角色 UAT 清单

**Should have (v1.x 后续)：**
- 达成进度条（"司龄 11/12 月 = 92%"）+ 预计达标日期（ETA）
- 档位趋势（过去 N 周期的档位变化）+ 分布健康度告警
- 导入来源 badge（Excel/飞书/手动）+ AI/绩效并排展示优化
- 员工申诉/复核入口（复用 v1.1 override 流程）

**Defer (v2+)：**
- 资格历史快照（需建 `EligibilityResult` 快照表）
- 导入回滚按钮（需 pre-image snapshot）
- 预览阶段可编辑（减少下载-改-上传循环）
- 同岗位族分档对照
- 实时变更 WebSocket 推送

**Anti-Features（明确拒绝）：**
- 员工端显示排名 / 同档其他人 / 精确百分位 / 具体分数 — 合规红线
- 强切 20/70/10（忽略等级相同人员的边界） — 数学精准但员工投诉来源
- 频繁跳档（单次迟到就掉档） — 档位应稳定，依赖绩效等级的平滑性
- 静默覆盖导入（无 preview）— HR 数据不可误覆盖
- 空单元格 = 清空字段（默认行为）— 歧义大，行业默认 noop
- 自动去除前导零（"数据清洁"）— 会破坏联表键

详见 [FEATURES.md](./FEATURES.md)。

### Architecture Approach

v1.4 **不改变后端分层**（`api/ → services/ → engines/ → models/`）也不改变前端分层（`pages/ → services/ → types/api.ts`）。每个新功能要么是"新垂直切片按既有约定落地"，要么是"在既有 service/engine 加方法"。不重写任何共享抽象。

**Major components（新增 10 个 / 扩展 12 个）：**
1. **`PerformanceTierEngine`**（新，纯引擎）— 输入排序好的 `(employee_id, grade)` 列表，输出 `{eid: 1|2|3|None}`；`len < min_sample_size` 时全员返回 `None`；无 I/O、无 DB、完全可单测
2. **`PerformanceService` + `/api/v1/performance` 路由**（新）— `GET /performance/records`（列表）、`GET /performance/tier-summary`（HR 看分布）、`GET /performance/me/tier`（员工自读）；服务层持 `@lru_cache(year)`，导入完成后显式 `invalidate(year)`
3. **`EligibilityService.check_self(user)`**（扩展）— 从 `current_user.employee_id` 解析，委托给既有 `check_employee()`，复用 override 逻辑；**不走 AccessScopeService**（self-access 无需跨员工授权），对应新端点 `GET /eligibility/me`
4. **`FeishuService._with_sync_log()` helper**（扩展）— 抽出同步日志脚手架，套用到 `sync_performance_records` / `sync_salary_adjustments` / `sync_hire_info` / `sync_non_statutory_leave` 四个方法；复用 `sync_attendance` 已验证的模式；新增 `unmatched_employee_nos` 前 20 个工号落 `FeishuSyncLog`
5. **`FeishuService._map_fields` 工号修复**（扩展）— 对 `employee_no` 字段**永远**按 text 处理；优先读飞书 `text` 子字段；拒绝 `str(int(value))` 路径
6. **`ImportService.SUPPORTED_TYPES` 补齐**（扩展）— 新增 `hire_info` / `non_statutory_leave` 两个 import_type + 对应 `REQUIRED_COLUMNS` / `COLUMN_ALIASES` / `_import_*` 方法 + `build_template_xlsx` 分支
7. **`MyReview.tsx` 扩展**（前端）— 添加"调薪资格"标签页 + "绩效档次"徽章，**不新增 `/my-eligibility` 路由**（员工端首页统一在 `/my-review`）
8. **`PerformanceManagement.tsx` + `/performance` 路由**（新，HR 端）— 归入"系统管理"菜单组，角色 admin + hrbp
9. **`PerformanceHistoryPanel.tsx`**（新组件）— 复用到 `EvaluationDetail` + `SalaryDetail` 两处；对应后端 `GET /eligibility/{employee_id}/performance-records` 已存在
10. **Alembic `v14_01_restore_employee_no_leading_zeros.py`**（新数据迁移）— 必须 `--dry-run` 先跑，输出可疑清单给 HR 人工确认后才执行

**Permission model 约束：**
- 员工端自助走 `get_current_user` + `user.employee_id`，**不经过 `AccessScopeService`**（self-access 与跨员工授权语义不同）
- HR/manager/admin 端继续走 `AccessScopeService.ensure_*_access`
- `/performance` 路由 admin + hrbp 可见；员工只读 `/performance/me/tier`

详见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

### Critical Pitfalls

v1.4 最需要警惕的 5 个致命坑（全部 HIGH 优先级，任意一个落地不到位都会引发生产事故）：

1. **员工端资格接口横向越权（Pitfall 1）** — 绝不接受 `/eligibility/{employee_id}` 让 employee 角色调用；必须走无参数的 `/eligibility/me`，内部用 `current_user.employee_id` 解析；测试必须覆盖"两个 employee 账号互访 403"
2. **工号前导零修复的存量迁移（Pitfall 5 + 6）** — 根因在数据源（Excel 存储层 + 飞书"数字"字段类型），不是 pandas 配置；存量数据**绝不盲目 zfill**——必须输出"可疑清单 CSV" → HR 人工签字确认 → 管理员 API 逐个改名（带 AuditLog + 回滚）
3. **档位"HR 补录一条就全员漂移"（Pitfall 4）** — 必须引入 `PerformanceTierSnapshot` 表或 `lru_cache + 显式 invalidate`；员工端永远读快照；UI 顶部显示"基于 YYYY-MM-DD HH:MM 数据生成"；导入完成后主动触发一次重算
4. **飞书同步"假成功"（Pitfall 7）** — 当前 `sync_performance_records` / `sync_salary_adjustments` 等 4 方法**根本没写 FeishuSyncLog**（只有 `sync_attendance` 写）；必须拆四类计数器 `{success, updated, unmatched, mapping_failed, failed}`；`success` 语义重定义为 `unmatched + mapping_failed + failed == 0`，否则降级 `partial`；同步完成跑 sanity check `COUNT(*) updated_at > started_at ≈ synced_count`
5. **员工端 PII 暴露（Pitfall 18）** — `EligibilityRuleResult.detail` 当前带具体日期（"2024-12-01 入职"）和薪资数字；员工端必须走 `EligibilityMaskingService` 脱敏层：`TENURE` → "已入职 X 月，距达标还需 Y 月"；`ADJUSTMENT_INTERVAL` → "距上次调薪未满 X 月"；`PERFORMANCE` → "近一次绩效未达标"（不暴露等级）

次要但高频的坑（MEDIUM 优先级）：
- **百分位边界 ties**（Pitfall 2）— 同等级员工一律归入同档，ties 向下归（保护员工不被"踩边界降档"）
- **小样本分档无意义**（Pitfall 3）— `min_sample_size = 50`（ARCHITECTURE 推荐）或 20（PITFALLS 建议，**已决议取 50** 详见下方"决策冲突"）；低于阈值返回 `tier=null`，UI 显示"样本不足"
- **重复导入覆盖语义**（Pitfall 8）— 默认 `merge`（空值保留旧值）；`replace`（空值清空）需 HR 显式勾选开关；审计 `overwrite_mode`
- **并发导入脏写**（Pitfall 9）— 参照 `FeishuService.is_sync_running()` 模式加互斥锁；Celery `queue='single'` + concurrency=1
- **Excel 模板下载 404/0 字节**（Pitfall 10）— 根因是 `ImportService.SUPPORTED_TYPES` 缺 `hire_info` / `non_statutory_leave`；前端 axios 必须 `responseType: 'blob'`
- **Celery 任务用请求级 Session**（Pitfall 14）— Celery 任务签名**绝不接受 `db: Session` 参数**；标准模板 `SessionLocal() + try/finally close`
- **RBAC 新路由漏接 `AccessScopeService`**（Pitfall 13）— PR checklist 强制；每个涉及员工数据的路由都要过"跨部门访问 403"测试

详见 [PITFALLS.md](./PITFALLS.md)。

---

## Cross-Cutting Themes

研究过程中显现的三条贯穿四个文档的主线：

### Theme 1: 可观测性优先（Architecture + Pitfalls）

飞书同步"假成功"、导入覆盖语义歧义、档位漂移这三个问题有共同根因：**关键业务动作没把状态写到 HR 可见的位置**。v1.4 的每个 phase 都必须带"观测增量"：
- 飞书同步 → `FeishuSyncLog` + 四类计数器 + UI 日志页
- 导入 → `ImportBatch` + 字段级 diff + `action: overwrite` 明细
- 档位 → `PerformanceTierSnapshot` + "基于 YYYY-MM-DD 生成" UI 标签
- 工号迁移 → `AuditLog(action='employee_no_rename')` + 可疑清单 CSV

不做可观测性，v1.4 上线一周 HR 就会用工单把工程淹没。

### Theme 2: "employee" 角色是全新的 API 访问主体（Architecture + Pitfalls + Features）

v1.3 之前 employee 角色只在 `MyReview` 看自己的评估结果，访问控制逻辑简单。v1.4 第一次把员工角色引入**资格 API** 和**绩效 API**，访问主体首次扩到全员工，带来三项硬性要求：
- 路由层：自助端点一律**无参数**（`/eligibility/me`、`/performance/me/tier`），拒绝 `{employee_id}` 变体给员工调用
- 服务层：引入 `check_self(user)` 模式，从 `user.employee_id` 解析，不走 `AccessScopeService`（self-scope 与 cross-scope 语义不同）
- Schema 层：引入 `EligibilityMaskingService` 对员工端脱敏（日期、薪资、具体等级），HR 端继续全量

### Theme 3: 上游数据源是问题的真正源头（Stack + Pitfalls）

工号前导零丢失、飞书同步未落库、Excel 模板下载失败——表面上是 Python 代码 bug，实际上根因都在上游：
- 前导零：Excel 存储层识别"数字列"时已丢零；飞书多维表格"数字"字段类型返回 float；pandas `dtype=str` 救不回已丢的信息
- 飞书未落库：飞书字段映射失败（`_map_fields` 返回 None）、工号匹配失败、字段类型意外——都在上游
- 模板下载：`SUPPORTED_TYPES` 和 `ELIGIBILITY_IMPORT_TYPES` 不同步

v1.4 的修复策略统一为"**源头强约束 + 读入端兜底 + 展示端诊断**"三层：
- 源头：xlsx 模板用 `cell.number_format = '@'`；飞书字段类型校验非 text 拒绝
- 兜底：`_map_fields` 永远按 text 处理 `employee_no`；`_build_employee_map` leading-zero 容忍匹配（加 metrics）
- 诊断：`FeishuSyncLog.unmatched_employee_nos`、导入 `result_summary` 字段级 diff、档位 snapshot 时间戳

---

## Decision Conflicts Resolved

研究过程中三份文档在少数决策点上给出了不同推荐，已在本 SUMMARY 中统一：

### Conflict 1: 绩效分档用"等级映射"还是"严格百分位"？

| 来源 | 推荐 | 理由 |
|------|------|------|
| FEATURES.md | **等级映射（A→1, B→2, C→3）优先** | 与现有 `PerformanceRecord.grade` 字段语义无缝 |
| STACK.md | **`PERCENT_RANK()`** | 数据库层 O(N log N)；同等级保持同百分位 |
| ARCHITECTURE.md | **`PerformanceTierEngine` 纯函数**（未定义算法细节） | 架构层无偏好 |

**Resolution：以 `PERCENT_RANK()` 为计算口径，按 grade 排序；边界情况（样本 < 50、全员同分、ties）交由 `PerformanceTierEngine.assign()` 统一处理。** 等级映射作为"上游绩效分档本身已经分档"的业务现实——当实际分布严重失衡（如 40% 被判 1 档）时触发告警由 HR 复核，**不做硬切**。Engine 层保持纯函数，接收排序好的列表，不做 SQL；SQL 侧只负责 `ORDER BY grade`，分档决策在 Python。

### Conflict 2: 样本量阈值是 20 还是 50？

| 来源 | 推荐 | 理由 |
|------|------|------|
| FEATURES.md | **≥ 50 人** | "避免 3 人的 10% 闹剧" |
| PITFALLS.md | **≥ 20 人** | "基本统计意义即可" |
| ARCHITECTURE.md | **`min_sample_size: int = 50`**（默认值） | 与 FEATURES 一致 |

**Resolution：默认 `min_sample_size = 50`，但**配置化**到 `Settings.performance_tier_min_sample_size`（Pitfall 3 要求）**。默认 50 保护小公司/早期阶段的员工免于"我是 1 档（共 3 人）"的误解；若某些客户确实员工 < 50 仍想看分档，HR 可在配置里调到 20。前端 UI 遇到 `tier=null` 一律显示"本年度全公司绩效样本不足（需 ≥N 人），暂不分档"，N 由后端返回。

### Conflict 3: 档位缓存用 `lru_cache` 还是 `PerformanceTierSnapshot` 表？

| 来源 | 推荐 | 理由 |
|------|------|------|
| ARCHITECTURE.md | **`@lru_cache(year)` + 手动 `invalidate()`** | 简单；~200KB 内存；导入少且低频 |
| PITFALLS.md | **`PerformanceTierSnapshot` 表** | 显式快照；audit log 可追溯；多进程一致 |

**Resolution：v1.4 MVP 用 `@lru_cache` 起步；schema 同时创建 `PerformanceTierSnapshot` 表但留空**。MVP 先靠单进程缓存把功能交付；若后续（v1.5+）出现 uvicorn 多 worker / Celery worker 之间缓存不一致、或审计层面需要"档位历史"，再切换到 snapshot 表。**关键约束：Service 层必须暴露 `invalidate_tier_cache(year)` 方法，在 import 完成回调中显式调用**——无论当前实现是 `lru_cache` 还是 snapshot 表，调用方无感知，未来切换零改动。

---

## Unified "Watch Out For" List

合并四份文档的警示清单，按"phase DoD 固定项"列出（每个 phase 结束前必须逐项验证）：

**A. 员工端资格 phase**
- [ ] 路由是 `/eligibility/me`，**不是** `/eligibility/{employee_id}`
- [ ] 单测覆盖"两个 employee 账号互访 → 403"
- [ ] `detail` 字段经过 `EligibilityMaskingService` 脱敏，不含 YYYY-MM-DD 或薪资数字
- [ ] 前端 `useAuth().user` 依赖稳定化（useMemo），Network 面板确认不会被打 10 次以上
- [ ] 页面显示"数据更新于 YYYY-MM-DD HH:MM"

**B. 绩效档次引擎 phase**
- [ ] 单测覆盖 ties（10 员工同分，全部归入同档）
- [ ] 单测覆盖 sample_size < 50 → `tier=null`
- [ ] 单测覆盖人数 = 0, 1, 2, 3 的边界
- [ ] 返回结果带 `sample_size` 和 `insufficient_sample` 字段
- [ ] `min_sample_size` 可通过 `Settings.performance_tier_min_sample_size` 配置

**C. 绩效档次展示 phase**
- [ ] 两次连续请求返回相同 snapshot（不抖动）
- [ ] 前端显示"基于 YYYY-MM-DD HH:MM 生成"标签
- [ ] 员工端**不**显示排名、不显示同档其他人、不显示精确百分位
- [ ] 导入完成后主动调用 `invalidate_tier_cache(year)`
- [ ] 历史绩效每条显示 `department_snapshot`

**D. 工号前导零修复 phase**
- [ ] xlsx 模板用 openpyxl 读回 `cell.number_format == '@'`
- [ ] 飞书 `list_bitable_fields` 校验 `employee_no` 字段 type=text；非 text 配置保存拒绝
- [ ] `FeishuService._map_fields` 对 `employee_no` 路径**不调用** `str(int(value))`
- [ ] `EmployeeCreate` / `EmployeeUpdate` Pydantic `field_validator` 拒绝 `int/float` 类型的 employee_no
- [ ] 迁移脚本先 `--dry-run` 输出可疑清单 CSV，HR 签字后才执行
- [ ] 所有 `employee_no` 改名操作写 `AuditLog(action='employee_no_rename', detail={before, after})`
- [ ] `_build_employee_map` leading-zero 容忍匹配加 metrics 告警

**E. 飞书同步根因修复 phase**
- [ ] `sync_performance_records` / `sync_salary_adjustments` / `sync_hire_info` / `sync_non_statutory_leave` 全部写 `FeishuSyncLog`
- [ ] `FeishuSyncLog` 含 `{success, updated, unmatched, mapping_failed, failed}` 五类计数
- [ ] `unmatched_employee_nos` 前 20 个工号落库
- [ ] 同步完成跑 sanity check：`COUNT(updated_at > started_at) ≈ synced_count`
- [ ] UI 日志页拆四类展示，附"下载未匹配工号 CSV"按钮

**F. 调薪资格导入修复 phase**
- [ ] `ImportService.SUPPORTED_TYPES` 包含 `hire_info` / `non_statutory_leave`
- [ ] `build_template_xlsx` 对这两个类型返回非空 bytes
- [ ] 前端 axios 调用模板下载 API 带 `responseType: 'blob'`
- [ ] E2E 测试：`openpyxl.load_workbook(BytesIO(resp.content))` 能成功读回模板
- [ ] 模板下载路由 `require_roles('admin', 'hrbp')`
- [ ] 导入 API 签名含 `overwrite_mode: Literal['merge', 'replace']`（默认 merge）
- [ ] 单测覆盖 merge/replace × 空值/非空值 × 存在/不存在 四矩阵
- [ ] 互斥锁：同 `import_type` 的 `ImportJob` 同时只能有一个 `processing`

**G. 历史绩效展示 phase**
- [ ] `PerformanceRecord` 新增 `department_snapshot` 字段（可 nullable，新记录必填）
- [ ] UI 每条历史绩效显示记录时所在部门
- [ ] 空状态展示"暂无绩效记录"
- [ ] 按 `cycle_start_date desc` 排序

**H. Phase 11 导航验证 phase**
- [ ] `.planning/milestones/v1.1/phases/phase-11/SUMMARY.md` 补齐（如 v1.1 归档已封存，在 v1.4 对应 phase 下新建 VERIFICATION.md）
- [ ] UAT 清单覆盖 admin / hrbp / manager / employee 四角色
- [ ] v1.4 新增菜单项（`绩效管理`、员工端`调薪资格`标签）纳入 UAT
- [ ] PR diff ≤ 10 文件（验证 vs 修复严格拆分）

**I. 全 phase DoD 固定项**
- [ ] 新路由若返回员工数据，有 `AccessScopeService` 调用或明确的 self-scope 守门
- [ ] 新 Celery 任务签名**没有** `db: Session` 参数；用 `SessionLocal() + try/finally`
- [ ] 新 Schema 用 Pydantic v2 语法（`@field_validator`、`@model_validator`，不用 `@validator`）
- [ ] 表结构变更用 `op.batch_alter_table`（SQLite 兼容）
- [ ] 本地 SQLite + PostgreSQL 双跑迁移（若环境可用）

---

## Implications for Roadmap

基于研究，推荐 8 个 phase，按"数据完整性 → 导入稳定性 → 纯计算基础 → 读侧功能 → 独立页面 → 文档补齐"顺序：

### Phase A: 工号前导零修复 + 存量数据迁移
**Rationale:** 下游每个特性（档次、资格、飞书重同步、历史绩效）都以稳定的 `employee_no` 为键；修复晚了等于所有导入重跑。风险最高，必须最先交付且有时间 revert。
**Delivers:** Pydantic validator、`_map_fields` 修复、xlsx 模板 `@` 格式、飞书字段类型校验、可疑清单 CSV、Alembic 数据迁移（dry-run → HR 确认 → `--commit`）
**Addresses:** 类别 4 table stakes "工号前导零保留"
**Avoids:** Pitfall 5、6（存量工号盲目补零破坏账号）
**Research flag:** 需要与 HR 确认"存量可疑工号清单"——建议单独 `/gsd-research-phase` 或在 Requirements 阶段对齐

### Phase B: 飞书同步观测性修复（`FeishuSyncLog` 脚手架 + 四类计数器）
**Rationale:** B 依赖 A（工号修复后才能正确计入 `unmatched_count`）；解锁 HR 自助诊断能力，是 v1.3 导入链路债务的根因修复。
**Delivers:** `_with_sync_log` helper、4 个同步方法套壳、`unmatched_employee_nos` 落库、UI 日志页四类拆分
**Uses:** 现有 `FeishuSyncLog` model + `sync_attendance` 同步日志模式
**Implements:** ARCHITECTURE Theme 1（可观测性优先）
**Avoids:** Pitfall 7（飞书同步假成功）
**Research flag:** 无（复用 `sync_attendance` 已验证模式）

### Phase C: `ImportService` 补齐 `hire_info` / `non_statutory_leave` + Excel 模板修复
**Rationale:** Phase C 与 B 互不依赖，可并行；但先完成 B 让 HR 能诊断 C 的 bug。
**Delivers:** `SUPPORTED_TYPES` 补齐、`build_template_xlsx` 分支、`_import_hire_info` / `_import_non_statutory_leave` 方法、前端 `responseType: 'blob'` 封装、E2E 测试（openpyxl 读回）
**Uses:** 现有 `FastAPI Response(content=bytes)` + RFC 5987 `Content-Disposition`
**Avoids:** Pitfall 10（模板下载 404/Content-Type 错）
**Research flag:** 无

### Phase D: 导入覆盖语义 + 并发互斥 + 审计
**Rationale:** D 依赖 A（工号稳定后 upsert 才安全）、C（模板修复后 HR 才能完整测试）；独立 phase 因为涉及 API signature 变更（`overwrite_mode`）。
**Delivers:** `ImportService.run_import(overwrite_mode)` 签名、Preview + diff UI、按业务键 upsert、互斥锁（参照 `is_sync_running`）、`AuditLog` 记录 `overwrite_mode`
**Avoids:** Pitfall 8（覆盖语义歧义）、Pitfall 9（并发脏写）
**Research flag:** 需要对齐"Preview + diff" UI 细节（字段级 diff 展示、Insert/Update/No-change 分类）——建议 Requirements 阶段产出 UI 线框

### Phase E: `PerformanceTierEngine` 纯引擎 + 单测
**Rationale:** E 不依赖任何前置数据（纯函数），但在 D 之后交付能用已修复的导入链路跑端到端验证。
**Delivers:** `backend/app/engines/performance_tier_engine.py`、`TierThresholds` dataclass、20+ 单测（ties / 全员同分 / 人数 0-3 / sample<50）
**Uses:** dataclass + 纯函数（无 I/O）；延续 `EligibilityEngine` 模式
**Avoids:** Pitfall 2（ties）、Pitfall 3（小样本）
**Research flag:** 无（PERCENT_RANK 决策已在 SUMMARY 锁定）

### Phase F: `PerformanceService` + `/api/v1/performance` 路由 + 档次快照 / 缓存
**Rationale:** F 依赖 E（引擎先稳定），提供 HR 端 + 员工端读口径。
**Delivers:** `PerformanceService`（list / tier-summary / me/tier）、`/api/v1/performance` 路由、`@lru_cache(year)` + `invalidate_tier_cache(year)`、`PerformanceTierSnapshot` 表 schema 预留、import 回调触发 invalidate
**Uses:** SQLAlchemy `func.percent_rank().over()`、`lru_cache`
**Implements:** ARCHITECTURE 新 service + router 约定
**Avoids:** Pitfall 4（档位漂移）
**Research flag:** 需决定"档位在导入后自动刷新 vs HR 手动触发"——Requirements 阶段对齐

### Phase G: 员工端 `/eligibility/me` + `/performance/me/tier` + MyReview 扩展
**Rationale:** G 依赖 A（工号）+ F（档次 API）；是 v1.4 用户可见价值的交付点。
**Delivers:** `EligibilityService.check_self(user)`、`GET /eligibility/me`、`GET /performance/me/tier`、`MyEligibilityPanel` 组件、`MyReview.tsx` 新增"调薪资格"标签页 + 档位徽章、`EligibilityMaskingService` 脱敏、`useAuth` 引用稳定化
**Implements:** ARCHITECTURE Theme 2（employee 角色是全新访问主体）
**Avoids:** Pitfall 1（横向越权）、Pitfall 17（useEffect 抖动）、Pitfall 18（PII 暴露）
**Research flag:** **需要 Requirements 阶段与 HR/合规对齐 masking 文案**——这是 phase 能否上线的合规门槛；建议 `/gsd-research-phase` 深挖

### Phase H: HR 端独立 `绩效管理` 页 + 历史绩效面板复用到 EvaluationDetail / SalaryDetail
**Rationale:** H 依赖 F（`/performance/records` API），是 HR 端读侧交付的收官。
**Delivers:** `PerformanceManagement.tsx`、`/performance` 路由、`PerformanceHistoryPanel.tsx`（复用到 `EvaluationDetail` + 调薪建议详情）、`roleAccess.ts` 菜单项、分布直方图（复用 echarts）、`department_snapshot` 字段落库
**Avoids:** Pitfall 11（跨部门/离职历史口径混乱）
**Research flag:** 无

### Phase I: Phase 11 导航验证补齐（文档 + UAT，无代码改动）
**Rationale:** 独立文档债务；不与其他 phase 耦合；严格限定为 verification-only，不重写。
**Delivers:** SUMMARY.md 补齐（或 VERIFICATION.md）、四角色 UAT 清单执行截图、v1.4 新增菜单项纳入 UAT
**Avoids:** Pitfall 19（Phase 11 验证变隐式重写）
**Research flag:** 无

### Phase Ordering Rationale

1. **A 最先**：工号是后续所有数据键的前提；修复晚了意味着 B-H 全部重跑。
2. **B 早于 C/D**：先恢复飞书同步的可观测性，HR 才能自助诊断 C、D 的 bug；B 本身零依赖。
3. **C 与 B 可并行**：Excel 模板修复不依赖飞书；实际排期可以 B/C 同时启动但 B 先合并（因其他 phase 依赖其日志结构）。
4. **D 在 C 之后**：模板修复后 HR 才能完整测试覆盖语义；D 含 API 签名变更，单独 phase 降低审查复杂度。
5. **E 在 D 之后**：E 是纯引擎无依赖，但放到 D 之后能用"干净的导入数据"做集成测试。
6. **F 在 E 之后**：F 是 E 的消费者（Service 调 Engine）。
7. **G 是用户可见价值**：G 依赖 A（工号）+ F（档次 API）；放在中后段让前置修复稳定后交付。
8. **H 最后交付 HR 端体验**：HR 独立页 + 历史面板是锦上添花，可接受最后做。
9. **I 独立**：文档债务，不阻塞任何 phase；可插入任意空档期。

### Research Flags

**Phases 需要 `/gsd-research-phase`（额外研究）：**
- **Phase A**：存量工号"可疑清单"的人工确认流程——需要与 HR 对齐 SOP、审批权限、回滚窗口
- **Phase D**：Preview + diff UI 细节——需要产出线框图确认字段级 diff 展示方式
- **Phase F**：档位刷新触发策略（自动 vs 手动）——产品决策
- **Phase G**：`EligibilityMaskingService` 脱敏文案——需合规审阅

**Phases 标准模式（跳过 research-phase）：**
- **Phase B**：复用 `sync_attendance` 已验证的 sync_log 模式
- **Phase C**：FastAPI + openpyxl 模板下载标准实现；前端 axios blob 下载标准封装
- **Phase E**：纯引擎单测；延续 `EligibilityEngine` 模式
- **Phase H**：React + echarts 标准列表 + 直方图
- **Phase I**：verification-only 不需要技术研究

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 所有推荐通过代码审读 + 官方文档 + 社区共识三重验证；本机 Python/SQLite/pandas 版本已实测；零新增依赖无需试错 |
| Features | MEDIUM-HIGH | 业界主流做法（Workday/SAP/国内 HRIS）可验证；20/70/10 档位可见度、preview + diff upsert、空值 noop 等共识充分；**具体 UI 取舍和 HR 合规 masking 文案是团队决策**（已标注到 Requirements 阶段） |
| Architecture | HIGH | 基于实际代码审读（`eligibility_service.py`、`feishu_service.py`、`import_service.py`、`access_scope_service.py`）；所有决策都有"既有模式可参照"作为退路；不引入新共享抽象 |
| Pitfalls | HIGH | 来自 v1.0-v1.3 实战经验 + 当前代码里可定位的潜在 bug（如 `FeishuService._map_fields:240-245`、`ImportService.SUPPORTED_TYPES` 缺失）；Recovery steps 可操作 |

**Overall confidence:** HIGH

### Gaps to Address

需要在 Requirements 阶段或 phase planning 时补齐：

1. **合规 masking 文案** — `EligibilityMaskingService` 的每条规则该如何表述？合规团队需审阅（Gap 影响 Phase G）；建议在 Requirements 阶段单独产出"员工可见文案对照表"
2. **存量工号"可疑清单"边界** — 工号是纯数字 + 长度 < 公司标准 + 飞书源有补零版本的记录，如何定义"公司标准长度"？是否所有部门统一？（Gap 影响 Phase A）；建议单独 SOP 与 HR 签字
3. **档位刷新策略** — 自动 invalidate vs HR 手动触发 vs 定时（每日 02:00）？三选一或组合？（Gap 影响 Phase F）；建议 Requirements 阶段与产品决策
4. **"20/70/10 硬切 vs 按等级映射 + 分布告警"的业务倾向** — 本 SUMMARY 已决议按 PERCENT_RANK 排序 + ties 同档，但当实际分布是 `30/60/10` 时产品希望"挪人"还是"告警"？（Gap 影响 Phase E/F）
5. **员工跨部门/离职再入职的历史绩效口径** — `previous_employee_ids` 如何维护？admin 手动标注还是 HR 导入？（Gap 影响 Phase H，可 defer 到 v1.5）
6. **Phase 11 SUMMARY 归档位置** — v1.1 milestone 若已封存，补齐文档放在何处？（Gap 影响 Phase I，实操层面）
7. **绩效周期 cadence（季度/半年/年度）混用** — PITFALLS 提到 schema 应预留 `period_type` 字段，v1.4 是否做？（Gap 标记为 LOW，建议 v1.5 处理，但 v1.4 表结构需留位避免未来 batch_alter_table）

---

## Sources

### Primary (HIGH confidence)

**Codebase（直接审读）：**
- `backend/app/services/feishu_service.py` — `_map_fields:240-245`（employee_no float→int 强转 bug）、`sync_attendance` vs 其他 4 方法的 sync_log 不对称
- `backend/app/services/import_service.py` — `_load_table:381-396`（dtype=str 已配）、`build_template_xlsx:254-309`、`SUPPORTED_TYPES` 缺 hire_info/non_statutory_leave
- `backend/app/services/eligibility_service.py` — `check_employee` + `check_employees_batch` + override 逻辑
- `backend/app/services/access_scope_service.py` — 数据所有权守门模式
- `backend/app/engines/eligibility_engine.py` — 纯引擎模式先例
- `backend/app/models/performance_record.py` — UNIQUE(employee_id, year) 约束
- `backend/app/api/v1/eligibility_import.py` — `ELIGIBILITY_IMPORT_TYPES` vs `ImportService.SUPPORTED_TYPES` 不同步
- `frontend/src/utils/roleAccess.ts` — `ROLE_MODULES['employee']` 菜单约定
- `frontend/src/App.tsx:432-433` — `/my-review` 路由定义
- `frontend/src/components/eligibility/EligibilityListTab.tsx` — `RULE_STATUS_BADGE` 可抽取复用

**官方文档：**
- [pandas 2.2.3 read_excel docs](https://pandas.pydata.org/pandas-docs/version/2.2.3/reference/api/pandas.read_excel.html) — dtype/converters 语义
- [pandas GH#46895](https://github.com/pandas-dev/pandas/issues/46895) — read_excel vs read_csv 前导零差异
- [SQLite Window Functions](https://sqlite.org/windowfunctions.html) — PERCENT_RANK / NTILE 3.25+ 原生支持
- [FastAPI Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/) — Response vs StreamingResponse
- [FastAPI issue #3622](https://github.com/fastapi/fastapi/issues/3622) — BytesIO seek(0) 陷阱
- [openpyxl Styles](https://openpyxl.readthedocs.io/en/3.1/styles.html) — `number_format = '@'` text 格式

**本机实测：**
- `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` → `3.50.4`（远超 3.25 门槛）

### Secondary (MEDIUM confidence)

- [Vitality Curve (Wikipedia)](https://en.wikipedia.org/wiki/Vitality_curve) — 20/70/10 模型 + GE/Microsoft/AIG/Amazon 案例
- [Stack Ranking Analysis (AIHR)](https://www.aihr.com/hr-glossary/stack-ranking/) — 行业采用率 42% → 14%
- [2026 HR Compliance Checklist (BBSI)](https://www.bbsi.com/business-owner-resources/2026-hr-compliance-checklist?hs_amp=true) — EU Pay Transparency Directive 2026-06 生效
- [Workday Merit Process](https://www.suretysystems.com/insights/aligning-rewards-and-performance-with-the-workday-merit-process/) — merit eligibility 机制
- [SAP SuccessFactors Eligibility Rules](https://userapps.support.sap.com/sap/support/knowledge/en/2084628) — eligibility engine 三层粒度
- [Upsert vs Replace with Staging](https://medium.com/@tzhaonj/data-engineering-upsert-vs-replace-and-how-a-staging-table-can-help-you-find-the-perfect-middle-ea6db324b9ef) — staging + preview 工业范式
- [Rollback Strategy Planning (Ispirer)](https://www.ispirer.com/blog/how-to-plan-rollback-strategy) — 回滚最佳实践
- [Python.org discussion — leading zeros in spreadsheets](https://discuss.python.org/t/when-reading-spreadsheet-how-to-keep-leading-zeros/61389) — 根因在 Excel 存储层
- [GoCo / ChartHop / PerformYard](https://www.goco.io/hris-platform/performance-management) — Employee Timeline UI 参考

### Tertiary (LOW confidence — 需验证)

- `lark-oapi` 1.5.3 在中大规模调用场景下的稳定性——已决议不迁移，仅作为备选参考
- PostgreSQL 迁移下 `func.percent_rank()` 兼容性——逻辑上通用，但 v1.4 不落地实测

### Planning context

- `.planning/PROJECT.md` — v1.4 target features + layering invariants + known issues
- `.planning/RETROSPECTIVE.md` — v1.0-v1.3 debt（filter-before-paginate、Phase 11 SUMMARY 缺失）
- `.planning/MILESTONES.md` — v1.3 飞书 OAuth/前置集成经验
- `.planning/codebase/ARCHITECTURE.md` — 分层约束 `api → services → engines → models`

---

*Research completed: 2026-04-20*
*Ready for roadmap: yes*
