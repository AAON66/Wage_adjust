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
PROJECT_OUTCOME_KEYWORDS = (
    'readme',
    'summary',
    'overview',
    'impact',
    'result',
    'outcome',
    'achievement',
    'deliverable',
    'report',
    '复盘',
    '总结',
    '成果',
    '项目',
)
IMPLEMENTATION_KEYWORDS = (
    'backend',
    'frontend',
    'service',
    'api',
    'controller',
    'component',
    'page',
    'prompt',
    'workflow',
    'agent',
    'automation',
    'config',
    'settings',
    'src',
    'server',
    'model',
)
CODE_FILE_TYPES = {'py', 'js', 'ts', 'tsx', 'jsx', 'json', 'yml', 'yaml', 'toml', 'sql', 'sh', 'java', 'go', 'cs', 'cpp', 'zip'}

PROMPT_MANIPULATION_SUMMARY = '材料中疑似存在引导评分或操纵提示词的内容，相关段落已被系统忽略。'


@dataclass
class ExtractedEvidence:
    title: str
    content: str
    confidence_score: float
    source_type: str
    metadata: dict[str, object]


class RequiredLLMError(RuntimeError):
    pass


@dataclass
class EvidenceSummaryContext:
    kind: str
    source_type: str
    summary_template: str
    summary_focus: list[str]
    credibility_notes: str
    default_tags: list[str]


class EvidenceService:
    def __init__(self, settings: Settings, *, llm_service: DeepSeekService | None = None) -> None:
        self.settings = settings
        self.llm = llm_service or DeepSeekService(settings)

    def extract_from_parsed_document(
        self,
        parsed: ParsedDocument,
        *,
        file_name: str,
        file_type: str,
        require_llm: bool = False,
    ) -> ExtractedEvidence:
        source_scan = scan_for_prompt_manipulation(parsed.text)
        summary_context = self._build_summary_context(parsed, file_name=file_name, file_type=file_type)
        sanitized_parsed = ParsedDocument(
            text=source_scan.sanitized_text,
            title=parsed.title,
            metadata={
                **parsed.metadata,
                'evidence_kind': summary_context.kind,
                'summary_template': summary_context.summary_template,
                'summary_focus': summary_context.summary_focus,
            },
        )

        fallback = self._fallback_payload(
            sanitized_parsed,
            file_name=file_name,
            file_type=file_type,
            safety_scan=source_scan,
            summary_context=summary_context,
        )
        llm_result = self.llm.extract_evidence(sanitized_parsed, file_name=file_name, file_type=file_type, fallback_payload=fallback)
        if require_llm and llm_result.used_fallback:
            raise RequiredLLMError(self._build_llm_required_error(llm_result.reason))
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

        source_type = str(payload.get('source_type') or fallback['source_type'] or summary_context.source_type)
        credibility_notes = payload.get('credibility_notes', fallback['credibility_notes'] or summary_context.credibility_notes)
        if merged_scan.detected:
            credibility_notes = f'{credibility_notes} 系统已拦截疑似操纵评分的提示词片段。'

        metadata = {
            **sanitized_parsed.metadata,
            'file_name': file_name,
            'file_type': file_type,
            'source_type': source_type,
            'tags': self._merge_tags(summary_context.default_tags, payload.get('tags', fallback['tags'])),
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

    def _build_llm_required_error(self, reason: str | None) -> str:
        if reason == 'deepseek_not_configured':
            return '当前后端尚未配置可用的 LLM，无法执行 AI 解析。请先在后端环境中配置 DEEPSEEK_API_KEY。'
        if reason and 'rate limit' in reason.lower():
            return '当前 LLM 解析请求过于频繁，请稍后重试。'
        if reason:
            return f'LLM 解析调用失败：{reason}'
        return 'LLM 解析调用失败，请稍后重试。'

    def _fallback_payload(
        self,
        parsed: ParsedDocument,
        *,
        file_name: str,
        file_type: str,
        safety_scan: PromptSafetyScanResult,
        summary_context: EvidenceSummaryContext,
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
        summary = self._summarize_text(parsed.text, parsed.title, summary_context=summary_context)
        if safety_scan.detected and not summary:
            summary = PROMPT_MANIPULATION_SUMMARY
        return {
            'title': parsed.title or Path(file_name).stem or 'Parsed evidence',
            'summary': summary,
            'confidence_score': round(min(max(confidence, 0.05), 0.95), 2),
            'source_type': summary_context.source_type,
            'tags': self._merge_tags(summary_context.default_tags, tags or ['artifact']),
            'credibility_notes': summary_context.credibility_notes,
        }

    def _summarize_text(self, text: str, title: str, *, summary_context: EvidenceSummaryContext) -> str:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        if not cleaned:
            return ''
        snippet = cleaned[:260]
        title_hint = self._humanize_title(title)
        if summary_context.kind == 'project_outcome':
            return (
                f'项目成果摘要：该材料主要围绕{title_hint}相关工作，体现了项目推进、交付内容或阶段性结果。'
                f'从材料可见，核心信息包括：{snippet}'
            )[:4000]
        if summary_context.kind == 'implementation_detail':
            return (
                f'实现说明：该材料展示了{title_hint}相关模块或代码实现，说明 AI/自动化能力已落到具体系统、流程或功能中。'
                f'材料中的关键信息包括：{snippet}'
            )[:4000]
        return cleaned[:4000]

    def _build_summary_context(self, parsed: ParsedDocument, *, file_name: str, file_type: str) -> EvidenceSummaryContext:
        location_hint = str(parsed.metadata.get('archive_member_path') or file_name or parsed.title).lower()
        title_hint = (parsed.title or '').lower()
        combined_hint = f'{location_hint} {title_hint}'

        kind = 'general_artifact'
        if any(keyword in combined_hint for keyword in PROJECT_OUTCOME_KEYWORDS):
            kind = 'project_outcome'
        elif file_type in CODE_FILE_TYPES or any(keyword in combined_hint for keyword in IMPLEMENTATION_KEYWORDS):
            kind = 'implementation_detail'

        source_type = 'file_parse'
        if file_type in {'png', 'jpg', 'jpeg'}:
            source_type = 'artifact_image'
        elif file_type in CODE_FILE_TYPES:
            source_type = 'code_artifact'

        if kind == 'project_outcome':
            return EvidenceSummaryContext(
                kind=kind,
                source_type=source_type,
                summary_template='按项目成果摘要输出：先说明做了什么项目或事项，再说明交付结果、覆盖范围或量化影响。',
                summary_focus=['项目事项', '交付结果', '业务影响'],
                credibility_notes='系统按项目成果类材料生成摘要，重点保留工作事项、交付结果和业务影响。',
                default_tags=['delivery'],
            )
        if kind == 'implementation_detail':
            return EvidenceSummaryContext(
                kind=kind,
                source_type=source_type,
                summary_template='按源码实现摘要输出：先说明涉及的模块或系统，再说明实现的能力、接入的流程，以及对业务或研发流程的支持。',
                summary_focus=['模块范围', '实现能力', '流程落点'],
                credibility_notes='系统按源码实现类材料生成摘要，重点保留模块能力、落地位置和流程作用。',
                default_tags=['tooling'],
            )
        return EvidenceSummaryContext(
            kind=kind,
            source_type=source_type,
            summary_template='按通用材料摘要输出，概括核心工作内容与可确认的结果。',
            summary_focus=['核心内容', '可确认结果'],
            credibility_notes='系统按通用材料摘要生成证据，重点保留可确认的工作内容和结果。',
            default_tags=['artifact'],
        )

    def _normalize_tags(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(',') if item.strip()]
        return ['artifact']

    def _merge_tags(self, primary: list[str], secondary: object) -> list[str]:
        merged: list[str] = []
        for tag in [*primary, *self._normalize_tags(secondary)]:
            if tag and tag not in merged:
                merged.append(tag)
        return merged or ['artifact']

    def _humanize_title(self, title: str) -> str:
        base = Path(title).stem or title or '当前材料'
        normalized = re.sub(r'[_\-]+', ' ', base).strip()
        return normalized or '当前材料'

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
