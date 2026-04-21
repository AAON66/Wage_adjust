---
phase: 32
slug: eligibility-import-completion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest（前端按需，可选） |
| **Config file** | `pyproject.toml` / `backend/tests/conftest.py` |
| **Quick run command** | `.venv/bin/pytest backend/tests/test_import_service.py -x -q` |
| **Full suite command** | `.venv/bin/pytest backend/tests/ -x` |
| **Estimated runtime** | ~30 秒（quick）/ ~3 分钟（full） |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest backend/tests/test_import_service.py -x -q`
- **After every plan wave:** Run `.venv/bin/pytest backend/tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 秒（quick） / 180 秒（full）

---

## Per-Task Verification Map

> 由 gsd-planner 在生成 PLAN.md 时按 task 粒度填写。Wave 0 必须先准备好缺失的测试文件骨架（见下表）。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 0 | IMPORT-01/02 | — | 测试桩 + fixture 就绪 | unit | `.venv/bin/pytest backend/tests/test_import_service_phase32.py --co -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_import_service_phase32.py` — 覆盖 IMPORT-01/02/05/07 的 unit 测试桩（模板生成、preview 结构、merge/replace 行为、冲突检测）
- [ ] `backend/tests/test_import_concurrency.py` — 覆盖 IMPORT-06：is_import_running / 409 / 双 Tab 竞争
- [ ] `backend/tests/test_import_idempotency.py` — 覆盖 SC5：重复导入按业务键 upsert，不产生重复行
- [ ] `backend/tests/test_import_audit_log.py` — 覆盖 D-13：AuditLog `target_type/target_id`（注意真实字段名！）+ overwrite_mode 详情
- [ ] `backend/tests/test_eligibility_import_api.py` — 覆盖 `POST /imports/upload` → preview / `POST /imports/{job_id}/confirm` 端到端
- [ ] `backend/tests/conftest.py` — 新增 fixture：`tmp_uploads_dir`（pytest tmp_path 隔离 uploads/imports/）/ `import_job_factory` / `xlsx_factory`（构造 hire_info / non_statutory_leave 测试 xlsx）
- [ ] `backend/tests/fixtures/imports/` — 测试用 xlsx 样本（合法 + 冲突 + 日期序列号 + 空单元格）

*若已有 `backend/tests/test_import_service.py` 覆盖 employees/certifications/grades 类型，新增类型沿用同一模式即可。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 浏览器实际下载 .xlsx 文件并能用 openpyxl 读回 | IMPORT-02 | 需真实浏览器触发 blob 下载 + 跨平台（Chrome / Safari / Edge） | 1) 启动前后端 → 2) 进入「调薪资格导入」 → 3) 切到 hire_info Tab → 4) 点「下载模板」 → 5) `python -c "from openpyxl import load_workbook; print(load_workbook('hire_info_template.xlsx').sheetnames)"` 应输出 `['Sheet']` |
| Replace 模式二次确认 modal 必勾选才可继续 | IMPORT-05 | UI 交互需视觉验证 | 1) 上传任意 xlsx → 2) 选「替换模式」→ 3) 点「确认导入」→ 4) 校验 modal 出现且「继续」按钮在勾选前禁用 |
| HR 双 Tab 并发提交 → 第二个 Tab 收到 409 toast | IMPORT-06 | 真实 UI 双 Tab 时序 | 1) Tab A 上传未 confirm（status=previewing） → 2) Tab B 也上传 → 3) Tab B 应收到 409 + toast「该类型导入正在进行中」 |
| Preview 抽屉里 Insert/Update/No-change/Conflict 4 色 badge 与 GitHub PR 风格 diff | IMPORT-07 | 视觉验收 | 1) 上传含 4 类行为的 xlsx → 2) 校验顶部计数卡片颜色 + 折叠/展开行为 + old→new 字段并排 |

---

## Validation Sign-Off

- [ ] 所有 task 都有 `<automated>` verify 或 Wave 0 依赖
- [ ] 采样连续性：不允许 3 个连续 task 没有 automated verify
- [ ] Wave 0 覆盖所有 MISSING 引用
- [ ] 无 watch-mode 标志
- [ ] 反馈延迟 < 30 秒（quick）
- [ ] `nyquist_compliant: true` 在 frontmatter 设置

**Approval:** pending
