from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import ParsedDocument
from backend.app.services.llm_service import DeepSeekService


KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    'tooling': ('ai', 'automation', 'agent', 'prompt', 'workflow', 'copilot', 'llm'),
    'delivery': ('impact', 'delivery', 'launch', 'ship', 'save', 'improve', 'efficiency', 'roi'),
    'learning': ('learn', 'training', 'course', 'certification', 'study', 'mentor'),
    'sharing': ('share', 'document', 'playbook', 'workshop', 'knowledge', 'guide'),
}


@dataclass
class ExtractedEvidence:
    title: str
    content: str
    confidence_score: float
    source_type: str
    metadata: dict[str, object]


class EvidenceService:
    def __init__(self, settings: Settings, *, llm_service: DeepSeekService | None = None) -> None:
        self.settings = settings
        self.llm = llm_service or DeepSeekService(settings)

    def extract_from_parsed_document(self, parsed: ParsedDocument, *, file_name: str, file_type: str) -> ExtractedEvidence:
        fallback = self._fallback_payload(parsed, file_name=file_name, file_type=file_type)
        llm_result = self.llm.extract_evidence(parsed, file_name=file_name, file_type=file_type, fallback_payload=fallback)
        payload = llm_result.payload
        title = str(payload.get('title') or parsed.title or Path(file_name).stem or 'Parsed evidence')
        content = str(payload.get('summary') or parsed.text[:4000])[:4000]
        confidence_score = self._clamp_confidence(float(payload.get('confidence_score', fallback['confidence_score'])))
        source_type = str(payload.get('source_type') or fallback['source_type'])
        metadata = {
            **parsed.metadata,
            'file_name': file_name,
            'file_type': file_type,
            'tags': self._normalize_tags(payload.get('tags', fallback['tags'])),
            'credibility_notes': payload.get('credibility_notes', fallback['credibility_notes']),
            'llm_provider': llm_result.provider,
            'llm_used_fallback': llm_result.used_fallback,
        }
        if llm_result.reason:
            metadata['llm_reason'] = llm_result.reason
        return ExtractedEvidence(
            title=title[:255],
            content=content,
            confidence_score=confidence_score,
            source_type=source_type,
            metadata=metadata,
        )

    def _fallback_payload(self, parsed: ParsedDocument, *, file_name: str, file_type: str) -> dict[str, object]:
        lowered = f"{parsed.title} {parsed.text}".lower()
        tags = [label for label, keywords in KEYWORD_GROUPS.items() if any(keyword in lowered for keyword in keywords)]
        confidence = 0.35
        if parsed.text.strip():
            confidence += min(len(parsed.text.strip()) / 5000, 0.25)
        if len(tags) >= 2:
            confidence += 0.15
        if parsed.metadata:
            confidence += 0.1
        source_type = 'file_parse'
        if file_type in {'png', 'jpg', 'jpeg'}:
            source_type = 'artifact_image'
        elif file_type in {'py', 'js', 'ts', 'tsx', 'zip'}:
            source_type = 'code_artifact'
        summary = self._summarize_text(parsed.text)
        return {
            'title': parsed.title or Path(file_name).stem or 'Parsed evidence',
            'summary': summary,
            'confidence_score': round(min(confidence, 0.95), 2),
            'source_type': source_type,
            'tags': tags or ['artifact'],
            'credibility_notes': 'Fallback evidence extraction used local heuristics based on file content richness and keywords.',
        }

    def _summarize_text(self, text: str) -> str:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        if not cleaned:
            return 'No textual evidence could be extracted from the uploaded material.'
        return cleaned[:4000]

    def _normalize_tags(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(',') if item.strip()]
        return ['artifact']

    def _clamp_confidence(self, value: float) -> float:
        return round(max(0.0, min(value, 1.0)), 2)
