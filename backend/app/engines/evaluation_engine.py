from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from backend.app.models.evidence import EvidenceItem


DIMENSIONS: tuple[tuple[str, str, float, tuple[str, ...]], ...] = (
    ('TOOL', 'AI tool mastery', 0.15, ('tooling', 'automation', 'agent', 'prompt', 'workflow', 'copilot', 'llm')),
    ('DEPTH', 'AI application depth', 0.15, ('architecture', 'deployment', 'integration', 'design', 'analysis', 'complex')),
    ('LEARN', 'AI learning velocity', 0.20, ('learn', 'training', 'course', 'study', 'certification', 'mentor')),
    ('SHARE', 'Knowledge sharing', 0.20, ('share', 'document', 'playbook', 'workshop', 'guide', 'knowledge')),
    ('IMPACT', 'Business impact', 0.30, ('impact', 'save', 'efficiency', 'delivery', 'launch', 'roi', 'revenue')),
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

        average_confidence = sum(item.confidence_score for item in evidence_items) / len(evidence_items)
        source_diversity = len({item.source_type for item in evidence_items})
        total_text_length = sum(len(item.content or '') for item in evidence_items)
        evidence_reliability = sum(SOURCE_RELIABILITY.get(item.source_type, 0.95) for item in evidence_items) / len(evidence_items)
        normalized_richness = min(total_text_length / 2500, 1.0)

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
            raw_score = max(35.0, min(98.0, base_score + confidence_bonus + diversity_bonus + reliability_bonus + richness_bonus))
            weighted_score = round(raw_score * weight, 2)
            rationale = (
                f'{label} used {keyword_hits} keyword hits, {source_diversity} source types, '
                f'average confidence {average_confidence:.2f}, and evidence reliability {evidence_reliability:.2f}.'
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
        needs_manual_review = average_confidence < 0.68 or source_diversity < 2 or any(item.raw_score < 55 for item in dimensions)
        explanation = (
            f'Generated from {len(evidence_items)} evidence items with average confidence {average_confidence:.2f}. '
            f'The strongest dimension is {strongest_dimension or "N/A"}, the overall score is {overall_score:.2f}, '
            f'and the result maps to {ai_level}.'
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

    def _count_keyword_hits(self, evidence_items: list[EvidenceItem], keywords: tuple[str, ...]) -> int:
        total = 0
        for item in evidence_items:
            metadata_tags = item.metadata_json.get('tags', []) if isinstance(item.metadata_json, dict) else []
            haystack = f"{item.title} {item.content} {' '.join(str(tag) for tag in metadata_tags)}".lower()
            total += sum(haystack.count(keyword) for keyword in keywords)
        return total

    def _map_level(self, overall_score: float) -> str:
        for label, threshold in LEVEL_THRESHOLDS:
            if overall_score >= threshold:
                return label
        return 'Level 1'


