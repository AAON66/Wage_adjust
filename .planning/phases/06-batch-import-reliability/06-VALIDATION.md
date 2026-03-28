---
phase: 6
slug: batch-import-reliability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 6 — 验证策略

> 执行期间反馈采样的逐阶段验证合同。

---

## 测试基础设施

| 属性 | 值 |
|----------|-------|
| **框架** | pytest 8.3.5 |
| **配置文件** | 无独立 pytest.ini（使用默认） |
| **快速运行命令** | `pytest backend/tests/test_services/test_import_service.py -x` |
| **完整套件命令** | `pytest backend/tests/ -x` |
| **预估运行时间** | ~15 秒 |

---

## 采样频率

- **每次任务提交后:** 运行 `pytest backend/tests/test_services/test_import_service.py backend/tests/test_api/test_import_api.py -x`
- **每个 plan wave 后:** 运行 `pytest backend/tests/ -x`
- **`/gsd:verify-work` 之前:** 完整套件必须全绿
- **最大反馈延迟:** 15 秒

---

## 逐任务验证映射

| 任务 ID | Plan | Wave | 需求 | 测试类型 | 自动化命令 | 文件存在 | 状态 |
|---------|------|------|------|----------|-----------|---------|------|
| 06-01-01 | 01 | 0 | IMP-01, IMP-02 | unit | `pytest backend/tests/test_services/test_import_partial_success.py -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 0 | IMP-02, IMP-03 | integration | `pytest backend/tests/test_api/test_import_207.py -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 0 | IMP-04, IMP-06 | unit | `pytest backend/tests/test_services/test_import_xlsx.py -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 0 | IMP-05 | unit | `pytest backend/tests/test_services/test_import_upsert_audit.py -x` | ❌ W0 | ⬜ pending |

*状态: ⬜ 待定 · ✅ 通过 · ❌ 失败 · ⚠️ 不稳定*

---

## Wave 0 需求

- [ ] `backend/tests/test_services/test_import_partial_success.py` — 覆盖 IMP-01, IMP-02（惰性验证 + SAVEPOINT 部分提交）
- [ ] `backend/tests/test_api/test_import_207.py` — 覆盖 IMP-02, IMP-03（HTTP 207 响应 + 汇总统计）
- [ ] `backend/tests/test_services/test_import_xlsx.py` — 覆盖 IMP-04, IMP-06（GBK 编码 + xlsx 模板）
- [ ] `backend/tests/test_services/test_import_upsert_audit.py` — 覆盖 IMP-05（employee_no 幂等 upsert）

---

## 仅手动验证

| 行为 | 需求 | 为何手动 | 测试步骤 |
|------|------|---------|---------|
| 前端模板下载 UI | IMP-06 | 需浏览器交互验证下载 | 1. 打开导入页面 2. 点击"下载模板" 3. 验证 xlsx 文件包含正确列头和示例行 |
| 前端导入结果展示 | IMP-03 | 需浏览器交互验证 UI 展示 | 1. 上传含错误行的文件 2. 验证汇总统计和失败行表格展示正确 |

---

## 验证签署

- [ ] 所有任务有 `<automated>` 验证或 Wave 0 依赖
- [ ] 采样连续性：不超过 3 个连续任务没有自动化验证
- [ ] Wave 0 覆盖所有缺失引用
- [ ] 无 watch-mode 标志
- [ ] 反馈延迟 < 15s
- [ ] 前置条件中设置 `nyquist_compliant: true`

**审批:** 待定
