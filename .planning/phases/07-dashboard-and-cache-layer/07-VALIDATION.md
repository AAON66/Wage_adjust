---
phase: 7
slug: dashboard-and-cache-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 7 — 验证策略

> 执行期间反馈采样的逐阶段验证合同。

---

## 测试基础设施

| 属性 | 值 |
|----------|-------|
| **框架** | pytest 8.3.5 (后端) / tsc --noEmit (前端) |
| **配置文件** | 无独立 pytest.ini |
| **快速运行命令** | `pytest backend/tests/test_services/test_dashboard_service.py -x` |
| **完整套件命令** | `pytest backend/tests/ -x` |
| **预估运行时间** | ~20 秒 |

---

## 采样频率

- **每次任务提交后:** 运行 `pytest backend/tests/test_services/test_dashboard_service.py -x`
- **每个 plan wave 后:** 运行 `pytest backend/tests/ -x && cd frontend && npx tsc --noEmit`
- **`/gsd:verify-work` 之前:** 完整套件必须全绿
- **最大反馈延迟:** 20 秒

---

## 逐任务验证映射

| 任务 ID | Plan | Wave | 需求 | 测试类型 | 自动化命令 | 文件存在 | 状态 |
|---------|------|------|------|----------|-----------|---------|------|
| 07-01-01 | 01 | 0 | DASH-01 | unit | `pytest backend/tests/test_services/test_dashboard_sql.py -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 0 | DASH-02 | unit | `pytest backend/tests/test_services/test_cache_service.py -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 0 | DASH-03..07 | integration | `pytest backend/tests/test_api/test_dashboard_api.py -x` | ❌ W0 | ⬜ pending |

*状态: ⬜ 待定 · ✅ 通过 · ❌ 失败 · ⚠️ 不稳定*

---

## Wave 0 需求

- [ ] `backend/tests/test_services/test_dashboard_sql.py` — SQL 聚合替换全表扫描 (DASH-01)
- [ ] `backend/tests/test_services/test_cache_service.py` — Redis 缓存 TTL + key 格式 (DASH-02)
- [ ] `backend/tests/test_api/test_dashboard_api.py` — API 端点响应结构 (DASH-03..07)

---

## 仅手动验证

| 行为 | 需求 | 为何手动 | 测试步骤 |
|------|------|---------|---------|
| ECharts 图表渲染 | DASH-03, DASH-04 | 需浏览器视觉验证 | 打开看板页面，确认 AI 等级分布和调薪直方图正确渲染 |
| 部门下钻展开 | DASH-06 | 需浏览器交互验证 | 点击部门行，确认页内展开详细图表 |
| KPI 30秒刷新 | DASH-07 | 需观察实时行为 | 等待30秒确认待审批数自动更新 |

---

## 验证签署

- [ ] 所有任务有自动化验证或 Wave 0 依赖
- [ ] 采样连续性满足
- [ ] Wave 0 覆盖所有缺失引用
- [ ] 反馈延迟 < 20s
- [ ] 前置条件中设置 `nyquist_compliant: true`

**审批:** 待定
