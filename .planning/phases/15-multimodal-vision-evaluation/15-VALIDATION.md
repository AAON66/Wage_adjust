---
phase: 15
slug: multimodal-vision-evaluation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.5 |
| **Config file** | backend/tests/ |
| **Quick run command** | `python -m pytest backend/tests/ -x -q` |
| **Full suite command** | `python -m pytest backend/tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/ -x -q`
- **After every plan wave:** Run `python -m pytest backend/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | VISION-01 | unit | `python -m pytest backend/tests/test_ppt_image_extraction.py -v` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | VISION-02 | unit | `python -m pytest backend/tests/test_vision_evaluation.py -v` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | VISION-03 | unit | `python -m pytest backend/tests/test_vision_json_output.py -v` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | VISION-04 | unit | `python -m pytest backend/tests/test_vision_batch.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_ppt_image_extraction.py` — stubs for VISION-01
- [ ] `backend/tests/test_vision_evaluation.py` — stubs for VISION-02
- [ ] `backend/tests/test_vision_json_output.py` — stubs for VISION-03
- [ ] `backend/tests/test_vision_batch.py` — stubs for VISION-04

*Existing infrastructure covers test framework — only test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual quality assessment accuracy | VISION-02 | Requires human judgment on AI quality scores | Upload sample images, verify scores are reasonable (1-5 range, decorative images score low) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
