from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import ParsedDocument
from backend.app.services.llm_service import DeepSeekService
from backend.app.utils.prompt_safety import PromptSafetyScanResult, scan_for_prompt_manipulation


KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    'tooling': ('ai', 'automation', 'agent', 'prompt', 'workflow', 'copilot', 'llm'),
    'delivery': ('impact', 'delivery', 'launch', 'ship', 'save', 'improve', 'efficiency', 'roi'),
    'learning': ('learn', 'training', 'course', 'certification', 'study', 'mentor'),
    'sharing': ('share', 'document', 'playbook', 'workshop', 'knowledge', 'guide'),
}

PROMPT_MANIPULATION_SUMMARY = '材料中疑似存在引导评分或操纵提示词的内容，相关段落已被系统忽略。'


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
        source_scan = scan_for_prompt_manipulation(parsed.text)
        sanitized_parsed = ParsedDocument(
            text=source_scan.sanitized_text,
            title=parsed.title,
            metadata=parsed.metadata,
        )

        fallback = self._fallback_payload(sanitized_parsed, file_name=file_name, file_type=file_type, safety_scan=source_scan)
        llm_result = self.llm.extract_evidence(sanitized_parsed, file_name=file_name, file_type=file_type, fallback_payload=fallback)
        payload = llm_result.payload

        title_scan = scan_for_prompt_manipulation(str(payload.get('title') or sanitized_parsed.title or Path(file_name).stem or 'Parsed evidence'))
        content_scan = scan_for_prompt_manipulation(str(payload.get('summary') or sanitized_parsed.text[:4000]))
        merged_scan = self._merge_scans(source_scan, title_scan, content_scan)

        title = title_scan.sanitized_text or sanitized_parsed.title or Path(file_name).stem or 'Parsed evidence'
        content = content_scan.sanitized_text[:4000]
        if not content:
            content = PROMPT_MANIPULATION_SUMMARY if merged_scan.detected else fallback['summary']  # type: ignore[assignment]

        confidence_score = self._clamp_confidence(float(payload.get('confidence_score', fallback['confidence_score'])))
        if merged_scan.detected:
            confidence_score = self._clamp_confidence(confidence_score - 0.25)

        source_type = str(payload.get('source_type') or fallback['source_type'])
        credibility_notes = payload.get('credibility_notes', fallback['credibility_notes'])
        if merged_scan.detected:
            credibility_notes = f'{credibility_notes} 系统已拦截疑似操纵评分的提示词片段。'

        metadata = {
            **parsed.metadata,
            'file_name': file_name,
            'file_type': file_type,
            'tags': self._normalize_tags(payload.get('tags', fallback['tags'])),
            'credibility_notes': credibility_notes,
            'llm_provider': llm_result.provider,
            'llm_used_fallback': llm_result.used_fallback,
            'prompt_manipulation_detected': merged_scan.detected,
            'blocked_instruction_count': len(merged_scan.blocked_segments),
            'blocked_instruction_examples': merged_scan.blocked_segments[:3],
            'blocked_instruction_reasons': merged_scan.reasons,
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

    def _fallback_payload(
        self,
        parsed: ParsedDocument,
        *,
        file_name: str,
        file_type: str,
        safety_scan: PromptSafetyScanResult,
    ) -> dict[str, object]:
        lowered = f"{parsed.title} {parsed.text}".lower()
        tags = [label for label, keywords in KEYWORD_GROUPS.items() if any(keyword in lowered for keyword in keywords)]
        confidence = 0.35
        if parsed.text.strip():
            confidence += min(len(parsed.text.strip()) / 5000, 0.25)
        if len(tags) >= 2:
            confidence += 0.15
        if parsed.metadata:
            confidence += 0.1
        if safety_scan.detected:
            confidence -= 0.2
        source_type = 'file_parse'
        if file_type in {'png', 'jpg', 'jpeg'}:
            source_type = 'artifact_image'
        elif file_type in {'py', 'js', 'ts', 'tsx', 'zip'}:
            source_type = 'code_artifact'
        summary = self._summarize_text(parsed.text)
        if safety_scan.detected and not summary:
            summary = PROMPT_MANIPULATION_SUMMARY
        return {
            'title': parsed.title or Path(file_name).stem or 'Parsed evidence',
            'summary': summary,
            'confidence_score': round(min(max(confidence, 0.05), 0.95), 2),
            'source_type': source_type,
            'tags': tags or ['artifact'],
            'credibility_notes': 'Fallback evidence extraction used local heuristics based on file content richness and keywords.',
        }

    def _summarize_text(self, text: str) -> str:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        if not cleaned:
            return ''
        return cleaned[:4000]

    def _normalize_tags(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(',') if item.strip()]
        return ['artifact']

    def _clamp_confidence(self, value: float) -> float:
        return round(max(0.0, min(value, 1.0)), 2)

    def _merge_scans(self, *scans: PromptSafetyScanResult) -> PromptSafetyScanResult:
        reasons: list[str] = []
        blocked_segments: list[str] = []
        for scan in scans:
            reasons.extend(scan.reasons)
            blocked_segments.extend(scan.blocked_segments)
        return PromptSafetyScanResult(
            sanitized_text='',
            detected=any(scan.detected for scan in scans),
            reasons=self._dedupe(reasons),
            blocked_segments=self._dedupe(blocked_segments),
        )

    def _dedupe(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result
