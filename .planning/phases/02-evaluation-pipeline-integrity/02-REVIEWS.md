---
phase: 2
reviewers: [codex]
reviewed_at: 2026-03-27T00:00:00Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md, 02-05-PLAN.md, 02-06-PLAN.md]
---

# Cross-AI Plan Review — Phase 2

> Gemini: 未安装，跳过
> Claude: 当前运行时（跳过以保证独立性）
> Codex (gpt-5.4): ✓ 已完成

---

## Codex Review

### Summary

The phase is decomposed sensibly: schema first, service hardening next, behavior fixes after that, then UI and tests. The plans are detailed enough to be executable and usually specify concrete artifacts, verification commands, and dependency edges. The main weakness is that a few requirements are only partially operationalized, especially prompt-injection sanitization and end-to-end UI/API verification. As written, the phase would likely deliver most of the backend integrity fixes, but there is still meaningful risk that one or two success criteria are only "implemented on paper" rather than proven in behavior.

### Strengths

- Clear wave structure: schema groundwork in `02-01`, service changes in `02-02` to `02-04`, UI in `02-05`, and consolidated tests in `02-06`.
- Good requirement traceability. Most plans tie artifacts and verify steps back to specific `EVAL-*` requirements.
- Strong operational detail for backend changes: batch Alembic migrations, explicit ORM/schema updates, retry formulas, Redis key derivation, and concrete API/UI fields.
- Good attention to production concerns: exponential backoff with jitter, Redis-backed shared rate limiting, graceful Redis fallback, and prompt hashing for auditability.
- Good recognition of SQLite/PostgreSQL realities and no-live-service testing constraints.
- The frontend plan is aligned with the user-facing success criteria rather than only backend correctness.
- The final test plan is broad and intentionally avoids live DeepSeek and Redis dependencies, which is the right verification strategy.

### Concerns

- `HIGH`: `EVAL-08` is not fully closed. The plans extend `prompt_safety.py` with more patterns, but they do not clearly state where uploaded content and OCR output are actually sanitized before prompt construction. Detection rules alone do not satisfy "sanitized against prompt injection before LLM embedding."
- `HIGH`: Re-evaluation write semantics are underspecified. `02-04` says `used_fallback` and `prompt_hash` must be written on every evaluation, but it does not explicitly require replacing prior `DimensionScore` rows in a transaction. If old rows survive re-runs, auditability and UI correctness can drift.
- `MEDIUM`: `02-03` modifies `llm_service.py` in the objective and tasks, but that file is missing from `files_modified`. In a wave-based executor, that is an ownership/review gap.
- `MEDIUM`: The test count is inconsistent. `02-01` requires 22 stub tests, while `02-06` names 21 tests. That creates avoidable plan drift and brittle verify commands.
- `MEDIUM`: The Redis sliding-window sketch uses `str(now)` as the sorted-set member. Concurrent requests with identical timestamps can collide and undercount. A unique member per request is safer.
- `MEDIUM`: Redis fallback is graceful, but silently degrading to in-memory limiting in production weakens the whole point of `EVAL-02`. A warning log is probably not enough; this should at least emit a metric or fail a health check in production mode.
- `MEDIUM`: `02-05` only verifies UI work with `tsc --noEmit`. That proves type safety, not that the warning banner and dimension panel actually render under the required statuses.
- `MEDIUM`: Success criterion 1 depends on the evaluation detail payload already containing all five dimensions, weights, and rationale text. The plans assume this backend shape exists or is already serialized, but they do not explicitly prove it with an API contract test.
- `LOW`: `server_default='0'` for a Boolean is fine for SQLite, but it is less clean for PostgreSQL than using `sa.false()` or equivalent DB-aware defaults.
- `LOW`: The fallback banner only covers whole-evaluation fallback. If OCR is skipped or image extraction partially fails while the rest of the evaluation is AI-backed, reviewers may still miss that evidence quality degraded.

### Suggestions

- Add an explicit task that wires prompt-safety sanitization into the exact prompt-building path used by evaluations, including OCR-derived text, and test the sanitized output rather than just pattern detection.
- Add explicit transactional re-evaluation behavior: delete or replace prior `DimensionScore` rows before writing new ones, and verify row counts remain stable across reruns.
- Fix plan metadata inconsistencies now: align the stub-test count, add `llm_service.py` to `02-03 files_modified`, and make requirement ownership consistent between backend and frontend plans.
- Add API-level tests for `GET /api/v1/evaluations/{id}` that assert `used_fallback`, `dimension_scores`, `weight`, `ai_rationale`, and `prompt_hash` are present as expected.
- Add frontend rendering tests for the banner and dimension panel instead of relying only on TypeScript compilation.
- Change the Redis sorted-set member to something unique per request, such as `f"{now}:{uuid4()}"`, while keeping `now` as the score.
- Define prompt-hash behavior for fallback evaluations explicitly: either `NULL` because no LLM prompt existed, or a separate deterministic hash of fallback inputs if reproducibility is required there too.
- Consider a user-visible indicator for partial OCR degradation, not just full evaluation fallback.

### Risk Assessment

**Overall risk: MEDIUM**

The plans are substantially better than average: they are specific, sequenced, and mostly testable. The risk stays at medium because there is one material requirement gap (`EVAL-08` sanitization wiring), one important behavioral ambiguity (re-evaluation overwrite semantics), and a few execution inconsistencies that could cause drift during implementation. If those are tightened before execution, this could drop to low risk.

---

## Consensus Summary

> 仅有 Codex 一位评审者，无需交叉对比。以下直接呈现关键结论。

### 核心优势

- 波次结构清晰合理（Schema → 后端修复 → 前端 → 测试），依赖顺序正确
- 需求追踪完整，每个计划明确关联 EVAL-* ID
- 后端操作细节充分（Alembic batch migration、重试公式、Redis key 推导）
- 测试策略正确：不依赖真实 DeepSeek/Redis，全 mock 覆盖

### 主要问题（须在执行前修复）

| 严重级别 | 问题 | 涉及计划 |
|---------|------|---------|
| HIGH | EVAL-08 仅扩展了检测模式，但未在 prompt 构建路径中明确调用 sanitize（包括 OCR 结果） | 02-04 |
| HIGH | 重评估时旧 DimensionScore 行是否被替换未说明——若不删旧行，评分可能累积膨胀 | 02-04 |
| MEDIUM | 02-03 的 `files_modified` 缺少 `llm_service.py` | 02-03 |
| MEDIUM | 测试桩数量不一致：02-01 写 22 个，02-06 写 21 个 | 02-01, 02-06 |
| MEDIUM | Redis sorted-set 成员用 `str(now)`，并发时可能碰撞导致计数偏低 | 02-02 |
| MEDIUM | Redis 降级为内存限速时仅记录警告，应增加 health check 或指标上报 | 02-02 |
| MEDIUM | 前端验证仅用 `tsc --noEmit`，未验证 banner 和维度面板实际渲染 | 02-05 |

### 行动建议

要将风险从 MEDIUM 降为 LOW，在执行前需要：
1. 在 `02-04` 中明确 sanitize 的调用位置（评估 prompt 构建时对所有输入内容调用）
2. 在 `02-04` 中加入重评估行覆盖语义（先删除/替换旧 DimensionScore 行再写新数据）
3. 对齐测试桩数量（22 or 21，选一个）
4. 补充 API 合约测试（`GET /evaluations/{id}` 断言所有字段存在）
