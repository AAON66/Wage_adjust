# Phase 31: 飞书同步可观测性 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 31-feishu-sync-observability
**Areas discussed:** 模型扩展与 sync_type 列, 同步日志页面 UI 形态, 写入日志的代码落地, partial 状态与并发触发语义

---

## 模型扩展与 sync_type 列

### Q1: FeishuSyncLog 如何区分五种同步类型？

| Option | Description | Selected |
|--------|-------------|----------|
| 新增 sync_type 枚举列 (Recommended) | 新增 sync_type: str NOT NULL 列，值枚举 attendance/performance/salary_adjustments/hire_info/non_statutory_leave。命名和 Celery task 的 sync_type 参数一致，历史记录 backfill 为 'attendance' | ✓ |
| 复用 mode 列扩展枚举 | 当前 mode 值是 full/incremental——扩展为 'attendance:full' / 'performance' 等复合字符串。避免表结构变更但 mode 语义混杂，不推荐 | |
| 不加 sync_type，分表存储 | 为四种新同步方法建独立的 FeishuEligibilitySyncLog 表。与历史 attendance 日志彻底分开，但查询/UI 需要 union | |

**User's choice:** 新增 sync_type 枚举列

### Q2: mapping_failed_count （字段类型转换失败）如何落地？

| Option | Description | Selected |
|--------|-------------|----------|
| 新增独立列 mapping_failed_count (Recommended) | 加新列 mapping_failed_count INTEGER DEFAULT 0 NOT NULL；skipped_count 语义让给「跳过」（如同步工号存在但无变更）。HR 在 UI 上可直接区分「schema 错误」与「无更新」 | ✓ |
| 复用 skipped_count，不加新列 | 保持现模型不动，mapping 失败和真实的 skipped 合并计入 skipped_count。UI 无法区分两种处境，但 Alembic 改动最小 | |
| 改名 skipped_count 为 mapping_failed_count | 将现 skipped_count 列重命名，语义收紧为「映射/解析失败」。BC 风险（老 sync_attendance 的 skipped 含「源数据更新时间较早」那种跳过，语义迁移有损耗） | |

**User's choice:** 新增独立列 mapping_failed_count

### Q3: 现有 FeishuSyncLog 里的历史 attendance 日志如何处理？

| Option | Description | Selected |
|--------|-------------|----------|
| Alembic 迁移时 backfill sync_type='attendance' (Recommended) | 在 op.batch_alter_table 同一个 migration 里，add_column(nullable=True) 后 update 并设 NOT NULL。无损耗，HR 历史 KPI 连续 | ✓ |
| 历史记录保留 sync_type=NULL | 迁移后 sync_type 允许 NULL，新写入都填值。前端对 NULL 显示「历史记录(未分类)」；数据库约束更宽松但 UI 需额外逻辑 | |
| 历史记录清空 | 迁移时删除所有历史 FeishuSyncLog 记录再加 NOT NULL 列。最干净但丢失已有同步历史，不推荐 | |

**User's choice:** Alembic 迁移时 backfill sync_type='attendance'

### Q4: 现有 mode 列 (full/incremental) 如何和 sync_type 共存？

| Option | Description | Selected |
|--------|-------------|----------|
| 保留 mode，新 sync_type 方法填 'full' 默认 (Recommended) | mode 对 attendance 有意义（全量/增量），对其他四类都填 'full'。前端切换 sync_type 时可隐藏 mode 列。最小改动 | ✓ |
| 扩展 mode 枚举包含 manual/scheduled | 把 mode 语义演变成「触发方式」，值为 manual/scheduled。sync_type 指同步什么数据，mode 指怎么触发。语义更清晰但破坏历史语义 | |
| 删除 mode 列 | attendance 的 full/incremental 关心点迁移到其他机制（如日志注释）。Alembic drop_column + 代码清理，风险较高 | |

**User's choice:** 保留 mode，新 sync_type 方法填 'full' 默认

---

## 同步日志页面 UI 形态

### Q5: 「同步日志」在前端的存在形式？

| Option | Description | Selected |
|--------|-------------|----------|
| 新增独立 /feishu/sync-logs 路由页面 (Recommended) | 独立导航入口（admin+hrbp 可见），与 AttendanceManagement 解耦。可覆盖五种 sync_type 不仅限考勤，Phase 32 导入日志必要时可复用同一页面 | ✓ |
| AttendanceManagement 页面加 Tab | 在考勤管理页面内加「同步日志」tab，导航不变。紧耦合，对 performance/hire_info 路径不直观 | |
| 扩展 FeishuConfig 页面 | 在飞书配置页面下方添加日志列表。适合配置类角色查看但 HR 日常诊断入口不明显 | |

**User's choice:** 新增独立 /feishu/sync-logs 路由页面

### Q6: sync_type 筛选与数据呈现粒度？

| Option | Description | Selected |
|--------|-------------|----------|
| Tab 切换 + 分页列表 (Recommended) | 顶部 Tab: 全部 / 考勤 / 绩效 / 薪调 / 入职信息 / 社保假勤；下面标准分页列表。HR 多数日常看「全部」，诊断单类时切 Tab | ✓ |
| 仅最近 20 条，无筛选 | 权和到一个挞序列表，五 sync_type 混排，badge 区分。无分页负担，但历史诊断能力弱 | |
| 下拉 select 筛选 + 分页 | 用下拉框选 sync_type，不占顶部空间。移动端友好但 HR 桌面场景交互较慢 | |

**User's choice:** Tab 切换 + 分页列表

### Q7: 列表列结构如何呈现五类计数器？

| Option | Description | Selected |
|--------|-------------|----------|
| 五色分段 badge 团 (Recommended) | 在每行的一列里用 5 个色彩 badge：绿=success, 蓝=updated, 橙=unmatched, 紫=mapping_failed, 红=failed。计数点击展开详情抽屉 | ✓ |
| 五列独立显示数字 | 表格 5 列独立标题 success/updated/unmatched/mapping_failed/failed，不用颜色。空间占用大但非颜色弱身者友好 | |
| 合并为「成功/异常」两色 | success+updated 合为绿色 OK 计数，unmatched+mapping_failed+failed 合为红色异常计数，展开抽屉看明细。UI 简洁但锁死了忽略 SC3 要求的「五类分别展示」，不推荐 | |

**User's choice:** 五色分段 badge 团

### Q8: 「下载未匹配工号 CSV」按钮的位置与内容？

| Option | Description | Selected |
|--------|-------------|----------|
| 每行操作列 + 仅工号 (Recommended) | 列表每行右侧 Action 列放「下载 CSV」按钮（仅当 unmatched_count>0 时启用）。CSV 单列 employee_no，前 20 行，文件名 sync-log-{id}-unmatched.csv。符合 SC3 字面要求 | ✓ |
| 详情抽屉 + 多列 CSV | 点击每行展开详情抽屉，抽屉内部放下载按钮。CSV 含 employee_no+原因+同步时间三列。更丰富但交互多一步 | |
| 顶部全选下载汇总 | 页面顶部放一个「下载近 30 天所有未匹配 CSV」聚合按钮。容易产生大文件，偏离 SC3「按条拿前 20」语义 | |

**User's choice:** 每行操作列 + 仅工号

---

## 写入日志的代码落地

### Q9: 四个 sync_xxx 方法如何写入 FeishuSyncLog？

| Option | Description | Selected |
|--------|-------------|----------|
| _with_sync_log(sync_type) 统一装饰器 (Recommended) | 新增 helper `_with_sync_log(self, sync_type, fn, *args, **kwargs) -> FeishuSyncLog`；负责创建 running log → 执行 fn → 聚合 counters → 推导 status → commit。四方法内部仅保留业务逻辑与 counter dict。IMPORT-03 Requirements 字面命名与此一致 | ✓ |
| 每个方法内部内嵌 | 复制 sync_attendance 的 try/except/commit 模式到每个方法里。代码重复但无抑制层，调试更直接 | |
| 在 Celery task 层包装 | feishu_sync_eligibility_task 返回 dict 后，Celery 层写入 FeishuSyncLog。问题：绕过了直接调用方法的场景（如未来 scheduler 直调） | |

**User's choice:** _with_sync_log(sync_type) 统一装饰器

### Q10: 五类 counter 在四个方法里的映射如何紧绷一致？

| Option | Description | Selected |
|--------|-------------|----------|
| _SyncCounters dataclass，fn 返回实例 (Recommended) | 定义内部 dataclass `_SyncCounters(success, updated, unmatched, mapping_failed, failed, leading_zero_fallback, total_fetched, unmatched_nos)`；四方法改造为返回该实例；helper 根据实例填 FeishuSyncLog。保证名字不失配 | ✓ |
| 方法返回 dict，helper 按 key 填 | 保持现方法返回 dict 的风格，helper 按 key 拿值。实现简单但 key 拼写错误不会被类型检查发现 | |
| 方法直接操作 FeishuSyncLog | helper 创建 log 实例后传入，方法内部 `sync_log.synced_count += 1` 这样原地更新。耦合 ORM，测试麻烦 | |

**User's choice:** _SyncCounters dataclass

### Q11: FeishuSyncLog 的 commit 事务如何划分？

| Option | Description | Selected |
|--------|-------------|----------|
| 独立事务 + 业务存贮分开 commit (Recommended) | helper 先 SessionLocal() 事务写入 running log。业务方法使用原 self.db 完成所有 upsert 后 commit。helper 再用独立 session 更新 log 终态（避免业务 rollback 连带 log 丢失，sync_attendance 现有 failed 分支已是这个模式） | ✓ |
| 共享 self.db 同一事务 commit | log 与业务 upsert 同事务。业务 rollback 也会连带回滚 log，失去「API 200 失败没有日志」的诊断价值，不推荐 | |
| log 单独 session + 业务转子方法 | helper 负责 2 次 log commit；业务方法换为子函数先回验证、后落库两阶段。结构最干净但改动最大，Phase 31 不必到位 | |

**User's choice:** 独立事务 + 业务存贮分开 commit

### Q12: sync_xxx 抛异常时，FeishuSyncLog 如何收尾？

| Option | Description | Selected |
|--------|-------------|----------|
| 沚 sync_attendance：独立 session 写 failed (Recommended) | 复用 sync_attendance 现有的 `fail_db = SessionLocal()` + `fail_log.status = 'failed'` + `error_message` 模式。业务 session rollback 后独立 session 补上 failed 终态。helper 统一处理，四方法不重复写 | ✓ |
| 异常不写日志，只在 Celery 结果里标记 failed | 倒退策略，仅在 Celery task 返回 {'status': 'failed', 'error': ...}。FeishuSyncLog 有 running log 但永远不最终化，需 expire_stale_running_logs 清理 | |
| 所有异常转化为 failed，unmatched 也计入 | 路径来自业务规则（入职日期解析失败等）全部计入 failed_count。与 SC1「mapping_failed/failed 分开」语义冲突，不推荐 | |

**User's choice:** 沚 sync_attendance：独立 session 写 failed

---

## partial 状态与并发触发语义

### Q13: partial 状态的派生规则？

| Option | Description | Selected |
|--------|-------------|----------|
| unmatched+mapping_failed+failed>0 即 partial (Recommended) | 直接按 SC2 字面：any(unmatched, mapping_failed, failed) > 0 则 partial；全部为 0 才是 success。规则硬切，无阈值问题 | ✓ |
| 阈值划分 partial/failed | total_fetched>0 且 success+updated == 0 则 failed（全部没落库）；success+updated>0 但有失败计数则 partial。更贴近 HR 痛点（「全年都丢」 vs 「部分丢」） | |
| 按 百分比阈值 | 错误数/total >= 50% 则 failed；<50% 且 >0 则 partial；==0 则 success。更柔和但需配置，Phase 31 范围外 | |

**User's choice:** unmatched+mapping_failed+failed>0 即 partial

### Q14: is_sync_running 并发锁如何演变？

| Option | Description | Selected |
|--------|-------------|----------|
| 按 sync_type 分桶锁 (Recommended) | is_sync_running(sync_type) 变成 per-sync_type 锁；同 sync_type 并发返 409，不同 sync_type 可同时跑。HR 同时点「同步绩效」和「同步入职」不互掉。SC4「两条独立记录」通过忽略锁不观测到 | ✓ |
| 全局锁，所有同步串行 | 保持现 is_sync_running() 全局语义，任何同步运行时其他触发都 409。更安全但 HR 等待时间长 | |
| 放开锁，允许完全并发 | 删除锁检查，重复点击确实生成两条记录。符合 SC4 字面但 HR 误点会飙飞书 API，不推荐 | |

**User's choice:** 按 sync_type 分桶锁

### Q15: SC4 所说「网络抖动或重复点击」产生两条独立记录，具体如何解释？

| Option | Description | Selected |
|--------|-------------|----------|
| 前后两次调用均写入各自的 FeishuSyncLog (Recommended) | 锁机制下、同 sync_type 的第二次调用如果遇到锁返 409——409 本身也产生一条 sync_log (status='rejected')？还是仅投递 API 错误？ 选项：409 仅接口错误不写日志；第二次点击在第一次成功结束后才允许跑，产生第二条独立 log | ✓ |
| 409 也写 rejected 状态日志 | 被 409 拒绝的次数也成一条日志 (status='rejected')，HR 能看到「这次被拒」。完全对应 SC4 字面但数据库噪声 | |
| 加入 request_id 去重 | 同一 request_id 判重复点击，同请求 id 返回现有 sync_log_id 而不新建。更严谨但超出 Phase 31 范围 | |

**User's choice:** 前后两次调用均写入各自的 FeishuSyncLog

### Q16: 旧版 sync_attendance 的 status 语义是否同步迁移到 partial？

| Option | Description | Selected |
|--------|-------------|----------|
| 一同迁移到 partial 语义 (Recommended) | sync_attendance 现 status 仅 success/running/failed，迁移后支持 partial；unmatched_count>0 时同样降级为 partial。五 sync_type 语义统一，前端色 badge 法则一致 | ✓ |
| 保持 sync_attendance 独立语义 | attendance 仍按老语义 success/failed；partial 仅对四个新 sync_type 生效。前端按 sync_type 分支劲断状态 badge，逻辑复杂 | |
| sync_attendance 并到 _with_sync_log，但不改 status | 仅 counter 统一，status 映射分两套。耦合最低但 UI 需要写两种色 badge 逻辑 | |

**User's choice:** sync_attendance 并到 partial 语义

---

## Claude's Discretion

- Alembic 迁移文件名 / revision id
- `_SyncCounters` 字段顺序与是否 frozen dataclass
- `/feishu/sync-logs` 前端页面具体配色（沿用现有 design token）
- 子组件拆分粒度（`SyncLogRow` / `CountersBadgeCluster` / `SyncLogDetailDrawer`）
- Celery task 内部捕获 409 的 idempotent 行为
- 旧 Celery task `performance_grades` → `performance` key 名过渡期兼容
- 前端 Tab 中文标签文案细节

## Deferred Ideas

见 CONTEXT.md `<deferred>` section — 含 request_id 去重、409 写 rejected 日志、百分比阈值 partial 规则、多列 CSV、聚合 KPI 横幅、日志保留期策略等 9 条。
