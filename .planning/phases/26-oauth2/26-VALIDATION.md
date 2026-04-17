---
phase: 26
slug: oauth2
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py -x` |
| **Full suite command** | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py backend/tests/test_api/test_feishu_oauth_integration.py -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py -x`
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | FAUTH-04 | T-26-01 | .env.example 只含空值模板 | verify | `python -c "from backend.app.models.user import User; assert hasattr(User, 'feishu_open_id')"` | ✅ | ✅ green |
| 26-01-02 | 01 | 1 | FAUTH-04 | — | Alembic 迁移成功 | verify | `alembic upgrade head` | ✅ | ✅ green |
| 26-02-01a | 02 | 2 | FAUTH-01 | T-26-03 | state CSRF 校验 + 一次性消费 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestGenerateAuthorizeUrl -v` | ✅ | ✅ green |
| 26-02-01b | 02 | 2 | FAUTH-02 | T-26-04 | code 防重放 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestHandleCallbackSuccess -v` | ✅ | ✅ green |
| 26-02-01c | 02 | 2 | FAUTH-03 | T-26-08 | 已绑定用户直接识别 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestBoundUserFastPath -v` | ✅ | ✅ green |
| 26-02-01d | 02 | 2 | FAUTH-02 | T-26-03 | state 无效时拒绝 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestStateCsrfValidation -v` | ✅ | ✅ green |
| 26-02-01e | 02 | 2 | FAUTH-02 | T-26-03 | state 使用后删除 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestStateConsumedAfterUse -v` | ✅ | ✅ green |
| 26-02-01f | 02 | 2 | FAUTH-02 | T-26-04 | 同一 code 不可重复使用 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestCodeReplayPrevention -v` | ✅ | ✅ green |
| 26-02-01g | 02 | 2 | FAUTH-05 | T-26-08 | employee_no 无匹配时 400 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestUnmatchedEmployeeError -v` | ✅ | ✅ green |
| 26-02-01h | 02 | 2 | FAUTH-05 | T-26-08 | Employee 无 User 时 400 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestNoUserForEmployeeError -v` | ✅ | ✅ green |
| 26-02-01i | 02 | 2 | FAUTH-02 | — | 飞书 API 错误码映射 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestFeishuApiErrorMapping -v` | ✅ | ✅ green |
| 26-02-01j | 02 | 2 | FAUTH-02 | T-26-09 | Redis 不可用返回 503 | unit | `python -m pytest backend/tests/test_services/test_feishu_oauth_service.py::TestRedisUnavailable -v` | ✅ | ✅ green |
| 26-02-02a | 02 | 2 | FAUTH-01 | — | /authorize 端点返回 URL + state | integration | `python -m pytest backend/tests/test_api/test_feishu_oauth_integration.py::TestFeishuAuthorizeEndpoint -v` | ✅ | ✅ green |
| 26-02-02b | 02 | 2 | FAUTH-02 | — | /callback 成功返回 tokens | integration | `python -m pytest backend/tests/test_api/test_feishu_oauth_integration.py::TestFeishuCallbackEndpoint::test_callback_success_returns_tokens -v` | ✅ | ✅ green |
| 26-02-02c | 02 | 2 | FAUTH-02 | T-26-03 | /callback 无效 state 返回 400 | integration | `python -m pytest backend/tests/test_api/test_feishu_oauth_integration.py::TestFeishuCallbackEndpoint::test_callback_invalid_state_returns_400 -v` | ✅ | ✅ green |
| 26-02-02d | 02 | 2 | FAUTH-05 | T-26-08 | /callback 未匹配返回 400 | integration | `python -m pytest backend/tests/test_api/test_feishu_oauth_integration.py::TestFeishuCallbackEndpoint::test_callback_unmatched_employee_returns_400 -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-17
