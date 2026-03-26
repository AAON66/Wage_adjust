from __future__ import annotations

import re
from dataclasses import dataclass


SEGMENT_SPLIT_PATTERN = re.compile(r'(?<=[。！？!?；;\n])')
WHITESPACE_PATTERN = re.compile(r'\s+')
PROMPT_MANIPULATION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        'score_manipulation',
        re.compile(
            r'(请|麻烦|务必|希望|要求|必须|拜托|帮我|给我).{0,12}(打分|评分|评估|给分|分数|高分|满分|100分|优秀|最好)',
            re.IGNORECASE,
        ),
    ),
    (
        'work_score_request',
        re.compile(
            r'(请给|给).{0,8}(我的作品|我的总结|这份材料|这个项目|该作品).{0,12}(100分|满分|高分|更高分|较高分)',
            re.IGNORECASE,
        ),
    ),
    (
        'instruction_override',
        re.compile(
            r'(忽略|无视|不要参考|覆盖|override|ignore).{0,18}(规则|系统|提示|prompt|instruction|之前|上面)',
            re.IGNORECASE,
        ),
    ),
    (
        'role_override',
        re.compile(
            r'(你现在是|you are now|system prompt|developer message|prompt injection|请直接给高分)',
            re.IGNORECASE,
        ),
    ),
    (
        'english_score_manipulation',
        re.compile(
            r'(give\s+(me\s+)?(full|max|perfect|high|top)\s+(marks?|score|credit|points?|rating))'
            r'|(give\s+me\s+(marks?|score|credit|points?|rating))'
            r'|(rate\s+me\s+\d{2,3})'
            r'|(score\s+me\s+\d{2,3})'
            r'|(award\s+full\s+(marks?|credit|score))'
            r'|(give\s+100|give\s+perfect)',
            re.IGNORECASE,
        ),
    ),
    (
        'english_instruction_override',
        re.compile(
            r'(ignore\s+(previous|above|all|prior)\s+(instructions?|prompt|context))'
            r'|(disregard\s+(the\s+)?(above|previous|instructions?))'
            r'|(forget\s+(your|the)\s+instructions?)'
            r'|(you\s+must\s+give\s+(me\s+)?(full|max|high|100))'
            r'|(act\s+as\s+if\s+you\s+have\s+no\s+restrictions)',
            re.IGNORECASE,
        ),
    ),
    (
        'unicode_homoglyph',
        re.compile(
            # Cyrillic chars that look like Latin: а е о р с х у і (lowercase)
            r'[\u0430\u0435\u043E\u0440\u0441\u0445\u0443\u0456]',
            re.UNICODE,
        ),
    ),
)


@dataclass
class PromptSafetyScanResult:
    sanitized_text: str
    detected: bool
    reasons: list[str]
    blocked_segments: list[str]


def scan_for_prompt_manipulation(text: str) -> PromptSafetyScanResult:
    normalized_text = text or ''
    stripped_text = normalized_text.strip()
    if not stripped_text:
        return PromptSafetyScanResult(sanitized_text='', detected=False, reasons=[], blocked_segments=[])

    segments = [segment.strip() for segment in SEGMENT_SPLIT_PATTERN.split(normalized_text) if segment.strip()]
    if not segments:
        segments = [stripped_text]

    safe_segments: list[str] = []
    reasons: list[str] = []
    blocked_segments: list[str] = []
    for segment in segments:
        matched_reasons = [label for label, pattern in PROMPT_MANIPULATION_PATTERNS if pattern.search(segment)]
        if matched_reasons:
            reasons.extend(matched_reasons)
            blocked_segments.append(segment[:160])
            continue
        safe_segments.append(segment)

    sanitized_text = ''.join(safe_segments)
    sanitized_text = WHITESPACE_PATTERN.sub(' ', sanitized_text).strip()
    return PromptSafetyScanResult(
        sanitized_text=sanitized_text,
        detected=bool(blocked_segments),
        reasons=_dedupe(reasons),
        blocked_segments=_dedupe(blocked_segments),
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
