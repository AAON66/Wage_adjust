from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.evidence import EvidenceItem
from backend.app.utils.prompt_safety import scan_for_prompt_manipulation


DIMENSIONS: tuple[tuple[str, str, float, tuple[str, ...]], ...] = (
    (
        'TOOL',
        'AI 工具掌握度',
        0.15,
        ('tooling', 'automation', 'agent', 'prompt', 'workflow', 'copilot', 'llm', '模型', '提示词', '智能体', '自动化', '工作流'),
    ),
    (
        'DEPTH',
        'AI 应用深度',
        0.15,
        ('architecture', 'deployment', 'integration', 'design', 'analysis', 'complex', '架构', '部署', '集成', '设计', '分析', '复杂'),
    ),
    (
        'LEARN',
        'AI 学习速度',
        0.20,
        ('learn', 'training', 'course', 'study', 'certification', 'mentor', '学习', '培训', '课程', '研究', '认证', '辅导'),
    ),
    (
        'SHARE',
        '知识分享',
        0.20,
        ('share', 'document', 'playbook', 'workshop', 'guide', 'knowledge', '分享', '文档', '手册', '宣讲', '指南', '知识'),
    ),
    (
        'IMPACT',
        '业务影响力',
        0.30,
        ('impact', 'save', 'efficiency', 'delivery', 'launch', 'roi', 'revenue', '影响', '降本', '提效', '交付', '上线', '收益'),
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

PROMPT_MANIPULATION_PENALTY = 24.0


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
        suspicious_ratio = suspicious_count / len(evidence_items)
        average_confidence = sum(self._effective_confidence(item) for item in evidence_items) / len(evidence_items)
        source_diversity = len({item.source_type for item in evidence_items})
        total_text_length = sum(len(self._safe_text(item)) for item in evidence_items)
        evidence_reliability = sum(self._effective_reliability(item) for item in evidence_items) / len(evidence_items)
        normalized_richness = min(total_text_length / 2500, 1.0)
        suspicious_penalty = suspicious_ratio * PROMPT_MANIPULATION_PENALTY

        dimensions: list[EvaluatedDimension] = []
        strongest_dimension: str | None = None
        strongest_score = -1.0
        for code, label, weight, keywords in DIMENSIONS:
            keyword_hits = self._count_keyword_hits(evidence_items, keywords)
            keyword_bonus = min(keyword_hits * 4.5, 18.0)
            base_score = 42.0 + keyword_bonus
            confidence_bonus = average_confidence * 18.0
            diversity_bonus = min(source_diversity / 4, 1.0) * 10.0
            reliability_bonus = evidence_reliability * 12.0
            richness_bonus = normalized_richness * 10.0
            raw_score = max(
                20.0,
                min(98.0, base_score + confidence_bonus + diversity_bonus + reliability_bonus + richness_bonus - suspicious_penalty),
            )
            weighted_score = round(raw_score * weight, 2)
            rationale = self._build_dimension_rationale(
                label=label,
                raw_score=raw_score,
                keyword_hits=keyword_hits,
                source_diversity=source_diversity,
                average_confidence=average_confidence,
                evidence_reliability=evidence_reliability,
                suspicious_count=suspicious_count,
            )
            dimension = EvaluatedDimension(
                code=code,
                label=label,
                weight=weight,
                raw_score=round(raw_score, 2),
                weighted_score=weighted_score,
                rationale=rationale,
            )
            dimensions.append(dimension)
            if dimension.raw_score > strongest_score:
                strongest_dimension = dimension.label
                strongest_score = dimension.raw_score

        overall_score = round(sum(item.weighted_score for item in dimensions), 2)
        ai_level = self._map_level(overall_score)
        needs_manual_review = (
            average_confidence < 0.68
            or source_diversity < 2
            or any(item.raw_score < 55 for item in dimensions)
            or suspicious_count > 0
        )
        explanation = self._build_explanation(
            evidence_count=len(evidence_items),
            average_confidence=average_confidence,
            strongest_dimension=strongest_dimension,
            overall_score=overall_score,
            ai_level=ai_level,
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

    def _build_dimension_rationale(
        self,
        *,
        label: str,
        raw_score: float,
        keyword_hits: int,
        source_diversity: int,
        average_confidence: float,
        evidence_reliability: float,
        suspicious_count: int,
    ) -> str:
        rationale = (
            f'当前维度“{label}”识别到 {keyword_hits} 个相关能力信号，覆盖 {source_diversity} 类证据来源，'
            f'平均置信度 {average_confidence:.2f}，证据可靠度 {evidence_reliability:.2f}，因此给出 {raw_score:.2f} 分。'
        )
        if keyword_hits == 0:
            rationale += '该维度直接证据偏少，建议结合项目材料或主管补充说明继续复核。'
        elif keyword_hits <= 2:
            rationale += '该维度已有一定支撑，但还需要更具体的项目结果或过程细节来增强判断。'
        else:
            rationale += '该维度证据较充分，能够支撑当前评分判断。'
        if suspicious_count:
            rationale += f'同时检测到 {suspicious_count} 条疑似引导评分内容，相关材料已降权处理。'
        return rationale

    def _build_explanation(
        self,
        *,
        evidence_count: int,
        average_confidence: float,
        strongest_dimension: str | None,
        overall_score: float,
        ai_level: str,
        suspicious_count: int,
    ) -> str:
        explanation = (
            f'综合分析基于 {evidence_count} 份证据材料，平均置信度 {average_confidence:.2f}。'
            f'当前表现最突出的维度是“{strongest_dimension or "待补充"}”，综合得分 {overall_score:.2f}，对应 {ai_level}。'
        )
        if suspicious_count:
            explanation += f'另检测到 {suspicious_count} 条疑似引导评分内容，系统已自动降权并建议人工复核。'
        return explanation

    def _count_keyword_hits(self, evidence_items: list[EvidenceItem], keywords: tuple[str, ...]) -> int:
        total = 0
        for item in evidence_items:
            metadata_tags = item.metadata_json.get('tags', []) if isinstance(item.metadata_json, dict) else []
            haystack = f"{item.title} {item.content} {' '.join(str(tag) for tag in metadata_tags)}"
            haystack = scan_for_prompt_manipulation(haystack).sanitized_text.lower()
            total += sum(haystack.count(keyword) for keyword in keywords)
        return total

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