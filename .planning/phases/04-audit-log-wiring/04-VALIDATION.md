---
phase: 4
slug: audit-log-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 4 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Quick run** | `.venv/Scripts/python.exe -m pytest backend/tests/test_audit/ -q --tb=short` |
| **Full suite** | `.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short` |
| **Frontend lint** | `cd frontend && npm run lint` |

## Per-Task Verification Map

| Task | Requirement | Automated Command | Status |
|------|-------------|-------------------|--------|
| 04-01 | AUDIT-02 | `pytest backend/tests/test_audit/ -k test_schema -q` | ⬜ |
| 04-02 | AUDIT-02 | `pytest backend/tests/test_audit/ -k test_evaluation_mutations -q` | ⬜ |
| 04-03 | AUDIT-01, AUDIT-03 | `pytest backend/tests/test_audit/ -k test_query -q` | ⬜ |
| 04-04 | AUDIT-01 | `cd frontend && npm run lint` | ⬜ |
| 04-05 | ALL | `pytest backend/tests/test_audit/ -q` | ⬜ |

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| Admin UI audit log table with filters | Browser rendering |
| Date range filter produces correct results | UI interaction |

## Wave 0 Requirements

- [ ] `backend/tests/test_audit/` directory with `__init__.py`
- [ ] Test stubs for AUDIT-01, AUDIT-02, AUDIT-03
