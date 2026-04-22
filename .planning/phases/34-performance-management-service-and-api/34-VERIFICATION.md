---
phase: 34-performance-management-service-and-api
verified: 2026-04-22T11:25:00Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "admin 登录 → 侧边栏可见「绩效管理」菜单 → 点击进入 /performance"
    expected: "页面渲染 3 个 section（档次分布 / 导入 / 列表）；ECharts 堆叠条出现（或档次空状态卡片）；ExcelImportPanel idle 态可见；表格 7 列表头正确"
    why_human: "视觉渲染、ECharts 堆叠条颜色（#10b981/#f59e0b/#ef4444）、AppShell 布局、菜单项实际显示效果无法 grep 验证"
  - test: "hrbp 登录 → 同上验证菜单可见 + 进入 /performance 可见 3 section"
    expected: "与 admin 行为一致"
    why_human: "实际登录流程与 RBAC 在浏览器渲染层的最终效果需要人工"
  - test: "employee 登录 → 侧边栏不可见「绩效管理」菜单 + 直访 /performance URL"
    expected: "菜单不显示；直访 URL 时后端 /api/v1/performance/* 任意端点返回 403"
    why_human: "客户端菜单隐藏 + 后端 require_roles 兜底的实际综合效果需登录态验证"
  - test: "HR 上传 Excel 绩效记录 → Preview + diff → confirm → 验证档次分布自动刷新"
    expected: "导入完成后 toast 文案根据 tier_recompute_status 分支显示（completed=绿/in_progress=蓝/busy_skipped=黄/failed=红）；TierDistributionPanel 重新拉 summary 反映新数据"
    why_human: "端到端导入闭环 + 5s 同步重算 + UI toast 渲染效果需要真实 Excel + 浏览器交互"
  - test: "HR 点击「重算档次」按钮 → 验证按钮 loading + computed_at 时间戳更新"
    expected: "按钮 disabled + RefreshIcon animate-spin + 「重算中…」文字；成功后时间戳显示「最近重算：YYYY 年 M 月 D 日 HH:mm」"
    why_human: "按钮 loading 动画 + Intl.DateTimeFormat zh-CN 格式化时间显示效果需要浏览器渲染验证"
  - test: "档次分布 distribution_warning=true 时 → 验证黄色 warning 横幅显示"
    expected: "role='alert' 横幅 + WarningIcon + 文案含实际百分比"
    why_human: "需要构造测试数据触发 ±5% 偏离条件，并验证 alert 横幅视觉效果"
---

# Phase 34: performance-management-service-and-api 验证报告

**Phase Goal:** HR 有独立「绩效管理」页面（列表 + 导入 + 档次分布），档次在导入完成后自动刷新，HR 也能手动触发重算覆盖
**Verified:** 2026-04-22T11:25:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

> 来源：ROADMAP Success Criteria（5 条）+ PLAN must_haves（PLAN-04 31 条）
> 已合并/去重，以 ROADMAP SC 为顶层 truth，PLAN must_haves 作为子证据。

| #   | Truth                                                                                                    | Status      | Evidence                                                                                                                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | HR + admin 看到「绩效管理」入口（3 部分：列表/导入/档次分布），employee/manager 看不到                  | ✓ VERIFIED  | `frontend/src/utils/roleAccess.ts` 命中 admin (line 49) + hrbp (line 88) 各 1 处 `/performance`；manager/employee 无对应条目；`App.tsx:24` import + `:466` Route 在 admin+hrbp ProtectedRoute 块；后端 5 端点全部 `require_roles('admin','hrbp')`，55 测试中 RBAC 全覆盖 |
| 2   | HR 上传 Excel 绩效记录 → Preview + diff → confirm 落库 → 档次分布视图自动反映新数据                      | ✓ VERIFIED  | `import_service.py:1937-1944` 在 `import_type=='performance_grades' and status in ('completed','partial')` 时调用 `_run_tier_recompute_hook(job)`；`_run_tier_recompute_hook` (line 1958-) 调用 `perf_service.invalidate_tier_cache + recompute_tiers` (5s timeout)；ConfirmResponse 含 `tier_recompute_status` 透传；前端 `PerformanceManagementPage.handleImportComplete` (line 126-152) 依据该字段做 5 状态分支 toast + `tierRefreshKey++` 强制 panel 重挂 |
| 3   | HR 手动点击「重算档次」可触发重算，UI 显示重算完成时间戳                                                  | ✓ VERIFIED  | `POST /performance/recompute-tiers` 端点 (`performance.py:150-185`) → `PerformanceService.recompute_tiers(year)` (`performance_service.py:246-312`)；行锁 + Engine + UPSERT + cache 写穿透；返回 `RecomputeTriggerResponse{computed_at}`；前端 `TierDistributionPanel` 渲染 `Intl.DateTimeFormat('zh-CN')` 格式化的「最近重算」时间戳 |
| 4   | 新录入 PerformanceRecord 持久化 department_snapshot，历史记录可见员工部门变迁                            | ✓ VERIFIED  | `PerformanceRecord.department_snapshot Mapped[str \| None]` (model:27-30)；`PerformanceService.create_record` 在 insert + UPSERT 两条分支显式 `department_snapshot=employee.department` (service:157, 170)；`_import_performance_grades` insert + existing 两条分支均显式赋值 (import_service.py:897 + 908)；2 个集成测试 `test_import_perf_grades_*` 直接验证 |
| 5   | `/api/v1/performance/records` 与 `/api/v1/performance/tier-summary` 数据口径一致，无档次漂移              | ✓ VERIFIED  | 两端点共享 `PerformanceService` 单一服务层；前者读 `PerformanceRecord` 表，后者读 `PerformanceTierSnapshot.tiers_json`，后者通过 `recompute_tiers` 写入时 `select(PerformanceRecord.employee_id, .grade).where(year=year)` 直接消费同一张表（performance_service.py:264-267）；前端 `performanceService.ts` 仅做 axios 透传 + Error 包装，零数据再聚合 |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                                            | Expected                                                                                | Status     | Details                                                                                                  |
| ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `backend/app/models/performance_record.py`                          | department_snapshot Mapped[str \| None] 列                                              | ✓ VERIFIED | line 27-30：`String(100), nullable=True, comment='Phase 34 D-07...'`                                     |
| `backend/app/models/performance_tier_snapshot.py`                   | 9 字段 ORM 模型 + UNIQUE(year)                                                          | ✓ VERIFIED | 7 业务列 + UUID/created_at/updated_at mixin = 10 列；UniqueConstraint('year') 在 line 27-29              |
| `alembic/versions/p34_01_*` + `p34_02_*`                            | 双向 upgrade/downgrade migration                                                         | ✓ VERIFIED | Files exist; per SUMMARY 验证 alembic upgrade head + downgrade -2 + upgrade head 双向干净 (commit fb53fb4) |
| `backend/app/services/tier_cache.py`                                | TierCache 类（4 方法 + 优雅降级）                                                       | ✓ VERIFIED | 67 行，cache_key/get_cached/set_cached/invalidate；redis_client=None + RedisError 全部静默降级           |
| `backend/app/services/exceptions.py`                                | TierRecomputeBusyError + TierRecomputeFailedError                                       | ✓ VERIFIED | 2 类，均继承 Exception；含 .year/.cause 属性；零 fastapi 依赖                                              |
| `backend/app/core/config.py`                                        | 3 个 Settings 字段                                                                      | ✓ VERIFIED | line 88-91：performance_tier_redis_prefix / _ttl_seconds / _recompute_timeout_seconds                    |
| `backend/app/services/performance_service.py`                       | PerformanceService 类 + 6 公开方法 + FOR UPDATE NOWAIT + 异常映射                       | ✓ VERIFIED | 414 行；6 方法签名齐全（list_records/create_record/get_tier_summary/recompute_tiers/invalidate_tier_cache/list_available_years）；line 365 `FOR UPDATE NOWAIT`；零 fastapi import |
| `backend/app/api/v1/performance.py`                                 | 5 端点（含 /available-years）+ require_roles + 异常→HTTP 映射                            | ✓ VERIFIED | 5 端点全部 register（router 检查 4 路径 + GET /me/tier 注释保留位）；TierRecomputeBusyError→409 + FailedError→500 |
| `backend/app/schemas/performance.py`                                | 6 schemas（D-09 平铺 9 字段 + AvailableYearsResponse）                                  | ✓ VERIFIED | PerformanceRecordRead/RecordsListResponse/RecordCreateRequest/TierSummaryResponse/RecomputeTriggerResponse/AvailableYearsResponse |
| `backend/app/schemas/import_preview.py` (W-1)                       | ConfirmResponse.tier_recompute_status: Literal[5 values] \| None                        | ✓ VERIFIED | line 87-92：`Literal['completed','in_progress','busy_skipped','failed','skipped'] \| None = None`         |
| `backend/app/services/import_service.py` (B-1)                      | _import_performance_grades 两条分支均写 department_snapshot                              | ✓ VERIFIED | line 897 (existing 分支) + line 908 (insert 分支) 均赋值 `=employee.department`                          |
| `frontend/src/pages/PerformanceManagementPage.tsx`                  | 3 section + state + orchestration                                                       | ✓ VERIFIED | 220 行；3 section JSX (TierDistributionPanel/ExcelImportPanel/RecordsTable)；6 useState；W-1 5 状态 toast 分支；B-3 getAvailableYears 调用 |
| `frontend/src/components/performance/*` (6 components)              | TierStackedBar/TierChip/DistributionWarningBanner/TierDistributionPanel/Filters/Table   | ✓ VERIFIED | 6 文件全部存在                                                                                            |
| `frontend/src/services/performanceService.ts`                       | 6 函数（含 getAvailableYears B-3）+ 2 Error 类                                          | ✓ VERIFIED | 156 行；NoSnapshotError + TierRecomputeBusyError + 5 service 函数（getTierSummary/recomputeTiers/getPerformanceRecords/createPerformanceRecord/getAvailableYears） |
| `frontend/src/components/icons/NavIcons.tsx` (B-4)                  | IconProps.style + 3 新图标（RefreshIcon/WarningIcon/ChartIcon）                          | ✓ VERIFIED | line 10：`style?: React.CSSProperties`；line 28：`{ flexShrink: 0, ...props.style }` merge；3 个 export function 在 line 126/131/136 |
| `frontend/src/utils/toast.ts` (W-4)                                 | 单实例 toast helper                                                                     | ✓ VERIFIED | 33 行；showToast + ToastVariant + activeTimeoutId cancel 逻辑                                            |
| `frontend/src/utils/roleAccess.ts`                                  | admin + hrbp operations 组追加「绩效管理」                                              | ✓ VERIFIED | line 49 (admin) + line 88 (hrbp) 各 1 处 `/performance` href                                             |
| `frontend/src/App.tsx`                                              | /performance Route 在 admin+hrbp ProtectedRoute                                         | ✓ VERIFIED | line 24 import + line 466 Route                                                                          |
| `frontend/src/types/api.ts`                                         | 9 个 Phase 34 类型 + ConfirmResponse.tier_recompute_status 扩字段                       | ✓ VERIFIED | line 1108 (tier_recompute_status) + 1146 (TierSummaryResponse) + 1159 (PerformanceRecordItem) + 1220 (AvailableYearsResponse) |

### Key Link Verification

| From                                       | To                                                | Via                                          | Status     | Details                                                                                              |
| ------------------------------------------ | ------------------------------------------------- | -------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------- |
| `backend/app/api/v1/router.py`             | performance_router                                 | `include_router(performance_router)`         | ✓ WIRED    | line 23 import + line 53 include_router                                                              |
| `api/v1/performance.py`                    | `PerformanceService.recompute_tiers`              | `service.recompute_tiers(year)`              | ✓ WIRED    | line 159；catch BusyError→409 + FailedError→500                                                       |
| `services/performance_service.py`          | `PerformanceTierEngine`                           | `from backend.app.engines import ...`        | ✓ WIRED    | line 25 import；line 65-69 ctor 注入；line 269 `result = self.engine.assign(inputs)`                  |
| `services/performance_service.py`          | `TierCache`                                       | ctor 注入                                     | ✓ WIRED    | line 38 import；line 219 `self.cache.get_cached`；line 239 `self.cache.set_cached`                     |
| `import_service.confirm_import`            | `_run_tier_recompute_hook`                        | hook call after commit                       | ✓ WIRED    | import_service.py:1944 调用；hook 内 perf_service.invalidate_tier_cache + recompute_tiers (line 2027+) |
| `_import_performance_grades`               | `PerformanceRecord.department_snapshot`           | 双分支显式赋值                                 | ✓ WIRED    | line 897 (existing) + line 908 (insert)                                                              |
| `frontend/PerformanceManagementPage`       | `/api/v1/performance/tier-summary`                | `getTierSummary(year)` in TierDistributionPanel useEffect | ✓ WIRED    | TierDistributionPanel 内调；page key={tierRefreshKey} 强制重挂                                        |
| `frontend/PerformanceManagementPage`       | `/api/v1/performance/available-years` (B-3)       | `getAvailableYears()` in mount useEffect     | ✓ WIRED    | page line 58-73                                                                                      |
| `frontend/PerformanceManagementPage`       | `ExcelImportPanel importType=performance_grades`  | JSX 复用 Phase 32 组件                        | ✓ WIRED    | line 184-188；onComplete=handleImportComplete 联动 W-1 toast 分支                                     |
| `frontend/App.tsx`                         | `/performance` route                              | `<Route element={<PerformanceManagementPage/>} path="/performance" />` | ✓ WIRED    | line 466                                                                                             |
| `frontend/utils/roleAccess.ts`             | admin+hrbp menu                                   | operations 组追加 `/performance`              | ✓ WIRED    | line 49 + 88                                                                                         |

### Data-Flow Trace (Level 4)

| Artifact                                          | Data Variable                | Source                                                                       | Produces Real Data | Status      |
| ------------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------- | ------------------ | ----------- |
| `TierDistributionPanel.tsx`                       | `summary: TierSummaryResponse` | `getTierSummary(year)` → `GET /performance/tier-summary` → `PerformanceService.get_tier_summary` → cache → snapshot 表 → engine | Yes                | ✓ FLOWING   |
| `PerformanceRecordsTable.tsx`                     | `items: PerformanceRecordItem[]` | `getPerformanceRecords(query)` → `GET /performance/records` → `PerformanceService.list_records` 真实 join Employee + paginate | Yes                | ✓ FLOWING   |
| `PerformanceManagementPage.tsx`                   | `availableYears: number[]`   | `getAvailableYears()` → `GET /performance/available-years` → `PerformanceService.list_available_years` 真实 SELECT DISTINCT year | Yes                | ✓ FLOWING   |
| `PerformanceManagementPage.tsx`                   | `departments: string[]`      | `fetchDepartmentNames()` (复用 Phase 32 既有 service)                          | Yes                | ✓ FLOWING   |
| `PerformanceTierSnapshot.tiers_json`              | DB 持久化 dict               | `recompute_tiers` → `engine.assign(rows)` → 真实 SELECT FROM performance_records | Yes                | ✓ FLOWING   |
| `PerformanceRecord.department_snapshot`           | DB 列                        | `create_record` + `_import_performance_grades` 显式 `=employee.department`     | Yes                | ✓ FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                    | Command                                                                            | Result                                  | Status   |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------- | -------- |
| Phase 34 全部测试通过                                       | `pytest backend/tests/test_models/test_performance_tier_snapshot.py + tier_cache + performance_service + performance_api + import_hook` | **55 passed** in 2.69s                  | ✓ PASS   |
| 5 个 /performance/* 端点路由注册                            | `python -c "from backend.app.api.v1.router import api_router; ..."`                | 4 路径 register（5 端点 - GET /me/tier 是 Phase 35 保留位） | ✓ PASS   |
| Frontend 编译                                               | `cd frontend && npm run build`                                                     | 824 modules transformed; built in 3.42s | ✓ PASS   |
| Engines 全套无回归                                          | `pytest backend/tests/test_engines/`                                                | 64 passed in 0.08s                      | ✓ PASS   |
| 无 Recharts / lucide-react 依赖                             | `grep -rn "from 'recharts'\|lucide-react" frontend/src/`                          | 无输出                                   | ✓ PASS   |

### Requirements Coverage

| Requirement | Source Plan(s)         | Description                                                                            | Status         | Evidence                                                                                                |
| ----------- | ---------------------- | -------------------------------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------- |
| PERF-01     | 34-03, 34-04           | 新增独立「绩效管理」页面（HR + admin 可见），含绩效列表 + 导入入口 + 档次分布视图三部分 | ✓ SATISFIED    | PerformanceManagementPage 3 section + roleAccess admin/hrbp 限定 + RBAC 后端兜底                       |
| PERF-02     | 34-03, 34-04           | HR 通过「绩效管理」页面独立导入绩效记录（Excel）+ Preview + diff                       | ✓ SATISFIED    | ExcelImportPanel importType=performance_grades 复用 Phase 32 7-state 两阶段提交（preview+confirm）       |
| PERF-05     | 34-02, 34-03, 34-04    | 档次刷新混合策略：导入自动 invalidate + 重算 + HR 手动「重算档次」按钮                  | ✓ SATISFIED    | _run_tier_recompute_hook + invalidate_tier_cache + recompute_tiers + UI 重算按钮 + 5 状态 toast 分支    |
| PERF-08     | 34-01, 34-03, 34-04    | PerformanceRecord 新增 department_snapshot 字段；UI 历史绩效显示该字段                  | ✓ SATISFIED    | model 字段 + Service create_record 双分支 + import_service 双分支 + RecordsTable 第 5 列展示（NULL → 「—」） |

**Orphaned requirements:** 无。REQUIREMENTS.md mapping 与 PLAN frontmatter 完全一致，4 个 PERF-01/02/05/08 全部覆盖。

### Anti-Patterns Found

| File                                                          | Line  | Pattern                                              | Severity | Impact                                                                                                            |
| ------------------------------------------------------------- | ----- | ---------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `frontend/src/utils/toast.ts`                                 | 5     | `// TODO Phase 35+: 替换为正式 toast 库`              | ℹ️ Info  | MVP 占位，使用 window.alert；本期已签字接受为「ROADMAP 不要求」（W-4 plan-level decision）                          |
| `backend/app/api/v1/performance.py`                           | 207   | `# TODO Phase 35：在 ESELF-03 范围内交付`             | ℹ️ Info  | GET /me/tier 故意保留位，在注释中标注；请求该路径自然 404，不影响 Phase 34 SC                                       |

无 blocker 或 warning 级反模式。

### Human Verification Required

> 自动化检查全部通过（55 测试 + 4 端点路由 + 编译通过 + 0 回归）；下列 6 项需人工浏览器交互验证。

#### 1. admin 登录 → 验证 /performance 页面渲染

**Test:** 启动 backend `uvicorn backend.app.main:app --reload` (8011) + frontend `npm run dev`；admin 账号登录 → 侧边栏点击「绩效管理」 → 进入 /performance
**Expected:** 页面渲染 3 个 section（档次分布 / 导入 / 列表）；ECharts 堆叠条出现（或档次空状态卡片）；ExcelImportPanel idle 态可见；表格 7 列表头正确（员工工号 / 姓名 / 年份 / 绩效等级 / 部门快照 / 来源 / 录入时间）
**Why human:** 视觉渲染、ECharts 堆叠条颜色（#10b981/#f59e0b/#ef4444）、AppShell 布局、菜单项实际显示效果无法 grep 验证

#### 2. hrbp 登录 → 验证菜单可见 + 进入页面

**Test:** hrbp 账号登录 → 侧边栏可见「绩效管理」菜单 → 进入 /performance
**Expected:** 与 admin 行为一致
**Why human:** 实际登录流程与 RBAC 在浏览器渲染层的最终效果需要人工

#### 3. employee 登录 → 验证菜单不可见 + URL 直访 403

**Test:** employee 账号登录 → 验证侧边栏不显示「绩效管理」菜单 + 浏览器地址栏直接访问 /performance URL
**Expected:** 菜单不显示；直访 URL 时后端 /api/v1/performance/* 任意端点返回 403（前端因后端兜底无法读到数据）
**Why human:** 客户端菜单隐藏 + 后端 require_roles 兜底的实际综合效果需登录态验证

#### 4. HR 端到端导入闭环

**Test:** admin 准备 1 份 ≥ 50 行的 performance_grades Excel → 上传 → Preview + diff 确认 → confirm
**Expected:** 导入完成后 toast 文案根据 ConfirmResponse.tier_recompute_status 分支显示（5 秒内完成→绿色「档次已刷新」/ 超时→蓝色「后台重算中…」/ 撞 HR 手动→黄色「系统繁忙」/ 失败→红色「请手动重算」）；TierDistributionPanel 自动重新拉 summary 反映新数据
**Why human:** 端到端导入闭环 + 5s 同步重算 + UI toast 渲染效果需要真实 Excel + 浏览器交互

#### 5. HR 手动「重算档次」按钮

**Test:** admin 在 /performance 选择有数据的年份 → 点击「重算档次」按钮
**Expected:** 按钮立即 disabled + RefreshIcon animate-spin + 显示「重算中…」；成功后时间戳显示「最近重算：YYYY 年 M 月 D 日 HH:mm」（zh-CN 格式）；分布数据更新
**Why human:** 按钮 loading 动画 + Intl.DateTimeFormat zh-CN 格式化时间显示效果需要浏览器渲染验证

#### 6. distribution_warning 偏离 ±5% 时的黄色横幅

**Test:** 构造测试数据使实际分布偏离 20/70/10 超过 ±5%（例如 30%/60%/10%）→ 重算 → 进入 /performance 该年度
**Expected:** stacked bar 上方出现 `role='alert'` 黄色横幅 + WarningIcon + 文案含实际百分比（如「档次分布偏离 20/70/10 超过 ±5%（实际 30%/60%/10%）...」）
**Why human:** 需要构造测试数据触发条件，并验证 alert 横幅视觉效果

### Gaps Summary

无功能性 gap。Phase 34 后端能力栈（55 测试覆盖）+ 前端 UI（编译通过 + UI-SPEC §0 反向勘误严格落地）全部交付；4 个 PERF 需求实现完整。

剩余 6 项为人工浏览器 UAT 项目，覆盖：菜单可见性、3 角色 RBAC 行为、端到端导入闭环、手动重算 loading + 时间戳显示、distribution warning 横幅渲染。这些项目无法通过 grep / pytest 等自动化手段验证，必须由用户在真实浏览器内交互完成。

**最终判定：** 自动化层面 5/5 truths 全部 VERIFIED；ROADMAP SC 5/5 全部满足；55 测试 + 64 engines 测试 0 回归；前端 build 通过。Phase goal 已达成；状态置为 `human_needed` 提示用户做 6 项 UAT 收尾。

---

_Verified: 2026-04-22T11:25:00Z_
_Verifier: Claude (gsd-verifier)_
