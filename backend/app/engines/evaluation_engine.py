from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.evidence import EvidenceItem
from backend.app.utils.prompt_safety import scan_for_prompt_manipulation


@dataclass(frozen=True)
class DimensionDefinition:
    code: str
    label: str
    weight: float
    keywords: tuple[str, ...]


@dataclass
class DimensionSignals:
    definition: DimensionDefinition
    matched_evidence_count: int
    matched_source_count: int
    distinct_keyword_count: int
    total_keyword_hits: int
    average_confidence: float
    average_reliability: float
    average_text_richness: float
    suspicious_count: int
    top_titles: list[str]
    matched_keywords: list[str]


DIMENSIONS: tuple[DimensionDefinition, ...] = (
    DimensionDefinition(
        code='TOOL',
        label='AI 工具掌握度',
        weight=0.15,
        keywords=('tooling', 'automation', 'agent', 'prompt', 'workflow', 'copilot', 'llm', '模型', '提示词', '智能体', '自动化', '工作流'),
    ),
    DimensionDefinition(
        code='DEPTH',
        label='AI 应用深度',
        weight=0.15,
        keywords=('architecture', 'deployment', 'integration', 'design', 'analysis', 'complex', '架构', '部署', '集成', '设计', '分析', '复杂'),
    ),
    DimensionDefinition(
        code='LEARN',
        label='AI 学习速度',
        weight=0.20,
        keywords=('learn', 'training', 'course', 'study', 'certification', 'mentor', '学习', '培训', '课程', '研究', '认证', '辅导'),
    ),
    DimensionDefinition(
        code='SHARE',
        label='知识分享',
        weight=0.20,
        keywords=('share', 'document', 'playbook', 'workshop', 'guide', 'knowledge', '分享', '文档', '手册', '宣讲', '指南', '知识'),
    ),
    DimensionDefinition(
        code='IMPACT',
        label='业务影响力',
        weight=0.30,
        keywords=('impact', 'save', 'efficiency', 'delivery', 'launch', 'roi', 'revenue', '影响', '降本', '提效', '交付', '上线', '收益'),
    ),
)

SOURCE_RELIABILITY = {
    'self_report': 0.92,
    'file_parse': 1.0,
    'artifact_image': 0.96,
    'code_artifact': 1.05,
    'manager_review': 1.08,
    'business_metric': 1.12,
    'system_detected': 1.06,
}

LEVEL_THRESHOLDS = (
    ('Level 5', 88),
    ('Level 4', 76),
    ('Level 3', 64),
    ('Level 2', 52),
    ('Level 1', 0),
)

PROMPT_MANIPULATION_PENALTY = 18.0


@dataclass
class EvaluatedDimension:
    code: str
    label: str
    weight: float
    raw_score: float
    weighted_score: float
    rationale: str


@dataclass
class EvaluationResult:
    overall_score: float
    ai_level: str
    confidence_score: float
    explanation: str
    needs_manual_review: bool
    dimensions: list[EvaluatedDimension]


class EvaluationEngine:
    def evaluate(self, evidence_items: list[EvidenceItem]) -> EvaluationResult:
        if not evidence_items:
            raise ValueError('At least one evidence item is required to generate an evaluation.')

        suspicious_count = sum(1 for item in evidence_items if self._has_prompt_manipulation(item))
        average_confidence = sum(self._effective_confidence(item) for item in evidence_items) / len(evidence_items)
        average_reliability = sum(self._effective_reliability(item) for item in evidence_items) / len(evidence_items)

        dimensions: list[EvaluatedDimension] = []
        strongest_dimension: EvaluatedDimension | None = None
        weakest_dimension: EvaluatedDimension | None = None

        for definition in DIMENSIONS:
            signals = self._collect_dimension_signals(definition, evidence_items)
            raw_score = self._score_dimension(
                signals,
                total_evidence_count=len(evidence_items),
                global_average_confidence=average_confidence,
                global_average_reliability=average_reliability,
            )
            dimension = EvaluatedDimension(
                code=definition.code,
                label=definition.label,
                weight=definition.weight,
                raw_score=raw_score,
                weighted_score=round(raw_score * definition.weight, 2),
                rationale=self._build_dimension_rationale(signals, raw_score),
            )
            dimensions.append(dimension)

            if strongest_dimension is None or dimension.raw_score > strongest_dimension.raw_score:
                strongest_dimension = dimension
            if weakest_dimension is None or dimension.raw_score < weakest_dimension.raw_score:
                weakest_dimension = dimension

        overall_score = round(sum(item.weighted_score for item in dimensions), 2)
        ai_level = self._map_level(overall_score)
        needs_manual_review = (
            average_confidence < 0.68
            or suspicious_count > 0
            or any(item.raw_score < 50 for item in dimensions)
            or sum(1 for item in dimensions if item.raw_score < 55) >= 2
        )
        explanation = self._build_explanation(
            evidence_count=len(evidence_items),
            average_confidence=average_confidence,
            overall_score=overall_score,
            ai_level=ai_level,
            strongest_dimension=strongest_dimension,
            weakest_dimension=weakest_dimension,
            suspicious_count=suspicious_count,
        )
        return EvaluationResult(
            overall_score=overall_score,
            ai_level=ai_level,
            confidence_score=round(average_confidence, 2),
            explanation=explanation,
            needs_manual_review=needs_manual_review,
            dimensions=dimensions,
        )

    def map_level(self, overall_score: float) -> str:
        return self._map_level(overall_score)

    def _collect_dimension_signals(
        self,
        definition: DimensionDefinition,
        evidence_items: list[EvidenceItem],
    ) -> DimensionSignals:
        matched_evidence_count = 0
        matched_sources: set[str] = set()
        distinct_keywords: set[str] = set()
        total_keyword_hits = 0
        confidences: list[float] = []
        reliabilities: list[float] = []
        text_richness_values: list[float] = []
        suspicious_count = 0
        ranked_titles: list[tuple[float, str]] = []

        for item in evidence_items:
            item_is_suspicious = self._has_prompt_manipulation(item)
            if item_is_suspicious:
                suspicious_count += 1

            haystack = self._normalized_haystack(item)
            matched_keywords = [keyword for keyword in definition.keywords if keyword in haystack]
            if not matched_keywords:
                continue

            matched_evidence_count += 1
            matched_sources.add(item.source_type)
            distinct_keywords.update(matched_keywords)
            keyword_hits = sum(haystack.count(keyword) for keyword in matched_keywords)
            total_keyword_hits += keyword_hits

            confidence = self._effective_confidence(item)
            reliability = self._effective_reliability(item)
            confidences.append(confidence)
            reliabilities.append(reliability)
            text_richness_values.append(min(len(self._safe_text(item)) / 1200, 1.0))

            ranking_score = len(set(matched_keywords)) * 2 + min(keyword_hits, 6) + confidence * 2
            ranked_titles.append((ranking_score, item.title.strip() or '未命名材料'))

        ranked_titles.sort(key=lambda item: item[0], reverse=True)
        top_titles = self._dedupe([title for _, title in ranked_titles])[:2]

        return DimensionSignals(
            definition=definition,
            matched_evidence_count=matched_evidence_count,
            matched_source_count=len(matched_sources),
            distinct_keyword_count=len(distinct_keywords),
            total_keyword_hits=total_keyword_hits,
            average_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
            average_reliability=round(sum(reliabilities) / len(reliabilities), 2) if reliabilities else 0.0,
            average_text_richness=round(sum(text_richness_values) / len(text_richness_values), 2) if text_richness_values else 0.0,
            suspicious_count=suspicious_count,
            top_titles=top_titles,
            matched_keywords=self._dedupe(list(distinct_keywords))[:4],
        )

    def _score_dimension(
        self,
        signals: DimensionSignals,
        *,
        total_evidence_count: int,
        global_average_confidence: float,
        global_average_reliability: float,
    ) -> float:
        suspicious_penalty = signals.suspicious_count * 6.0
        if signals.matched_evidence_count == 0:
            fallback_score = 34.0 + global_average_confidence * 6.0 + global_average_reliability * 4.0 - suspicious_penalty
            return round(max(28.0, min(52.0, fallback_score)), 2)

        keyword_coverage = signals.distinct_keyword_count / len(signals.definition.keywords)
        matched_ratio = signals.matched_evidence_count / total_evidence_count
        source_diversity = min(signals.matched_source_count / 3, 1.0)
        hit_intensity = min(signals.total_keyword_hits / max(signals.matched_evidence_count * 4, 1), 1.0)

        raw_score = (
            28.0
            + keyword_coverage * 24.0
            + matched_ratio * 16.0
            + source_diversity * 8.0
            + signals.average_confidence * 12.0
            + signals.average_reliability * 8.0
            + signals.average_text_richness * 6.0
            + hit_intensity * 8.0
            - suspicious_penalty
        )
        if signals.matched_evidence_count == 1 and keyword_coverage < 0.18:
            raw_score -= 4.0

        return round(max(20.0, min(96.0, raw_score)), 2)

    def _build_dimension_rationale(self, signals: DimensionSignals, raw_score: float) -> str:
        label = signals.definition.label
        if signals.matched_evidence_count == 0:
            rationale = (
                f'当前维度“{label}”在现有材料中缺少直接支撑证据，未检索到和该维度强相关的文件内容。'
                f'当前 {raw_score:.2f} 分主要来自材料整体可信度的兜底估计，不建议直接把它当作高分依据。'
            )
        else:
            keyword_text = '、'.join(signals.matched_keywords) if signals.matched_keywords else '相关项目表述'
            evidence_text = '、'.join(f'《{title}》' for title in signals.top_titles) if signals.top_titles else '当前材料内容'
            rationale = (
                f'当前维度“{label}”直接匹配到 {signals.matched_evidence_count} 份材料，覆盖 {signals.matched_source_count} 类来源，'
                f'命中 {signals.distinct_keyword_count} 个核心信号词（{keyword_text}）。'
                f'主要依据来自 {evidence_text}，因此给出 {raw_score:.2f} 分。'
            )
            if signals.matched_evidence_count == 1:
                rationale += '目前直接证据仍偏少，建议结合更多同类成果继续复核。'
            else:
                rationale += '该分数已明显受真实材料内容差异影响，而不是统一套用同一个基准分。'

        if signals.suspicious_count:
            rationale += f'同时检测到 {signals.suspicious_count} 份材料含疑似引导评分内容，相关文本已降权处理。'
        return rationale

    def _build_explanation(
        self,
        *,
        evidence_count: int,
        average_confidence: float,
        overall_score: float,
        ai_level: str,
        strongest_dimension: EvaluatedDimension | None,
        weakest_dimension: EvaluatedDimension | None,
        suspicious_count: int,
    ) -> str:
        explanation = (
            f'综合分析基于 {evidence_count} 份真实材料内容逐维匹配后生成，平均置信度 {average_confidence:.2f}。'
            f'当前最强维度为“{strongest_dimension.label if strongest_dimension else "待补充"}”，'
            f'相对薄弱维度为“{weakest_dimension.label if weakest_dimension else "待补充"}”，'
            f'综合得分 {overall_score:.2f}，对应 {ai_level}。'
        )
        if suspicious_count:
            explanation += f'另检测到 {suspicious_count} 份材料含疑似引导评分内容，系统已自动降权并建议人工复核。'
        return explanation

    def _normalized_haystack(self, item: EvidenceItem) -> str:
        metadata_tags = item.metadata_json.get('tags', []) if isinstance(item.metadata_json, dict) else []
        text = f"{item.title} {item.content} {' '.join(str(tag) for tag in metadata_tags)}"
        return scan_for_prompt_manipulation(text).sanitized_text.lower()

    def _effective_confidence(self, item: EvidenceItem) -> float:
        confidence = item.confidence_score
        if self._has_prompt_manipulation(item):
            confidence = max(0.05, confidence - 0.25)
        return confidence

    def _effective_reliability(self, item: EvidenceItem) -> float:
        reliability = SOURCE_RELIABILITY.get(item.source_type, 0.95)
        if self._has_prompt_manipulation(item):
            reliability = max(0.55, reliability - 0.35)
        return reliability

    def _safe_text(self, item: EvidenceItem) -> str:
        return scan_for_prompt_manipulation(f'{item.title} {item.content}').sanitized_text

    def _has_prompt_manipulation(self, item: EvidenceItem) -> bool:
        if isinstance(item.metadata_json, dict) and item.metadata_json.get('prompt_manipulation_detected'):
            return True
        return scan_for_prompt_manipulation(f'{item.title} {item.content}').detected

    def _map_level(self, overall_score: float) -> str:
        for label, threshold in LEVEL_THRESHOLDS:
            if overall_score >= threshold:
                return label
        return 'Level 1'

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
