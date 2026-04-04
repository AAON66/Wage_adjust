# Phase 15: Multimodal Vision Evaluation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

AI 评估可对 PPT 中提取的图片和独立上传的图片进行视觉内容理解和质量评估，结果作为证据项纳入整体五维评分计算。

</domain>

<decisions>
## Implementation Decisions

### 视觉评估输出结构
- **D-01:** 质量评级使用 1-5 数字评分（1=低质量, 5=高质量），与现有五维评分体系一致
- **D-02:** 视觉模型自动推断图片与 AI 能力维度的关联度（工具掌握/应用深度/成果转化等），而非固定映射
- **D-03:** 输出为结构化 JSON：包含图片描述（description）、质量评级（quality_score 1-5）、维度关联度（dimension_relevance: {dimension_name: relevance_score}）

### PPT 图片提取策略
- **D-04:** 提取 PPT 中所有嵌入图片，由视觉模型判断是否有价值（装饰图自动低分）
- **D-05:** 提取的图片关联到来源 slide 页码，保持上下文可追溯

### 批量处理与容错
- **D-06:** 多图片串行处理，逐个调用视觉 API，复用现有 rate limiter
- **D-07:** 单图失败时跳过并记录错误原因，继续处理其余图片，最终结果中标记哪些失败
- **D-08:** 不设图片数量上限，但超大图片（>5MB）自动压缩后再调用

### 评分集成方式
- **D-09:** 每张图片的视觉评估结果作为一个 EvidenceItem 纳入现有评估引擎，由引擎统一处理加权评分
- **D-10:** 没有图片的员工正常评估不受影响，视觉证据为 0 不扣分

### Claude's Discretion
- PPT 图片提取的具体实现方式（python-pptx API）
- 视觉 API prompt 模板设计
- EvidenceItem 的 source_type 命名和 metadata 结构
- 图片压缩的具体阈值和方法

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 解析器
- `backend/app/parsers/image_parser.py` — 现有图片解析器（只读元数据），需增强为视觉理解
- `backend/app/parsers/ppt_parser.py` — 现有 PPT 解析器（只提取文字），需增加图片提取

### LLM 服务
- `backend/app/services/llm_service.py` — 已有 `extract_image_text()` 和 `build_image_ocr_messages()`，支持 base64 图片编码和 DeepSeek Vision API

### 评估引擎
- `backend/app/engines/evaluation_engine.py` — EvidenceItem 结构、五维加权评分逻辑
- `backend/app/services/evaluation_service.py` — 评估流程编排（解析 → 证据 → 引擎 → LLM → 存储）

### 模型
- `backend/app/models/evidence.py` — 现有 Evidence 模型（如果存在）
- `backend/app/models/evaluation.py` — AIEvaluation 模型

### 需求文档
- `.planning/REQUIREMENTS.md` — VISION-01, VISION-02, VISION-03, VISION-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DeepSeekService.extract_image_text()`: 已实现 base64 图片编码 + Vision API 调用 + 自动压缩
- `build_image_ocr_messages()`: 已有视觉消息构建器
- `InMemoryRateLimiter`: 已有速率限制器，视觉调用可复用
- `EvidenceItem`: 已有证据项结构（source_type, title, content, confidence_score, metadata_json）

### Established Patterns
- 解析器继承 `BaseParser`，返回结构化解析结果
- LLM 调用使用 `httpx` 同步客户端 + 重试逻辑
- 评估引擎为纯计算，不访问 DB

### Integration Points
- `PptParser.parse()` 需要增加图片提取逻辑
- `ImageParser.parse()` 需要调用视觉 API 而非仅返回元数据
- `EvaluationService` 的证据收集流程需要包含视觉证据

</code_context>

<specifics>
## Specific Ideas

- 视觉 API 的 prompt 应明确要求输出结构化 JSON，包含 description、quality_score、dimension_relevance
- PPT 图片提取时保留 slide_number 信息作为 metadata
- 图片压缩使用 Pillow resize，已在 llm_service 中有类似实现
- 失败图片的 EvidenceItem 设 confidence_score=0 并在 metadata 中标记 vision_failed=true

</specifics>

<deferred>
## Deferred Ideas

None — 讨论保持在阶段范围内

</deferred>

---

*Phase: 15-multimodal-vision-evaluation*
*Context gathered: 2026-04-04*
