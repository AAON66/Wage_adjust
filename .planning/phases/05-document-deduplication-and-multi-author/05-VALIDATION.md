---
phase: 5
slug: document-deduplication-and-multi-author
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 5 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Quick run** | `.venv/Scripts/python.exe -m pytest backend/tests/test_submission/ -q --tb=short` |
| **Full suite** | `.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short` |
| **Frontend lint** | `cd frontend && npm run lint` |

## Per-Task Verification Map

| Task | Requirement | Automated Command | Status |
|------|-------------|-------------------|--------|
| 05-01 | SUB-01 | `pytest backend/tests/test_submission/ -k test_dedup -q` | ⬜ |
| 05-02 | SUB-02, SUB-03 | `pytest backend/tests/test_submission/ -k test_contributor -q` | ⬜ |
| 05-03 | SUB-04 | `pytest backend/tests/test_submission/ -k test_score_scaling -q` | ⬜ |
| 05-04 | SUB-05 | `pytest backend/tests/test_submission/ -k test_approval_contributors -q` | ⬜ |
| 05-05 | ALL | `pytest backend/tests/test_submission/ -q` + `npm run lint` | ⬜ |

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| 上传重复文件时显示拒绝消息（含已有记录引用） | UI 交互 |
| 贡献者百分比输入控件（合计必须为100%） | 表单交互 |
| 审批页面显示所有贡献者及百分比 | 页面渲染 |

## Wave 0 Requirements

- [ ] `backend/tests/test_submission/` 目录含 `__init__.py`
- [ ] SUB-01 到 SUB-05 的测试桩
