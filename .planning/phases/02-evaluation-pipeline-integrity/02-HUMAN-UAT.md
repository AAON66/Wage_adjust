---
status: complete
phase: 02-evaluation-pipeline-integrity
source: [02-VERIFICATION.md]
started: 2026-03-26T00:00:00Z
updated: 2026-03-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Yellow fallback banner renders when used_fallback = true
expected: When an evaluation has used_fallback=true (rule-engine path, DeepSeek unavailable), the EvaluationDetail page shows a visible yellow warning banner with text indicating "rule-engine estimate, AI not used". Banner must be visually distinct from normal state.
result: pass

### 2. Image OCR wired to live DeepSeek Vision API
expected: When a PNG/JPG file is uploaded as evidence and DeepSeek is configured, the parsed text content in the evaluation is real extracted text from the image — not the stub string "OCR reserved for later task". Requires DEEPSEEK_API_KEY configured and `deepseek_service` wired into the files upload call site.
result: pass

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
