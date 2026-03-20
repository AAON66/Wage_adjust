from __future__ import annotations

import json
import re
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import ParsedDocument
from backend.app.utils.helpers import compact_dict


JSON_BLOCK_PATTERN = re.compile(r'\{.*\}', re.DOTALL)


@dataclass
class DeepSeekCallResult:
    payload: dict[str, Any]
    used_fallback: bool
    provider: str
    reason: str | None = None


class InMemoryRateLimiter:
    def __init__(self, limit: int, *, window_seconds: int = 60, clock: Callable[[], float] | None = None) -> None:
        self.limit = max(limit, 1)
        self.window_seconds = window_seconds
        self.clock = clock or time.monotonic
        self.events: deque[float] = deque()

    def acquire(self) -> None:
        now = self.clock()
        while self.events and now - self.events[0] >= self.window_seconds:
            self.events.popleft()
        if len(self.events) >= self.limit:
            raise RuntimeError('DeepSeek rate limit reached for the current minute window.')
        self.events.append(now)


class DeepSeekPromptLibrary:
    def build_evidence_messages(self, parsed: ParsedDocument, *, file_name: str, file_type: str) -> list[dict[str, str]]:
        return [
            {
                'role': 'system',
                'content': (
                    'You extract structured evidence from employee achievement materials. '
                    'Return JSON with keys: summary, title, confidence_score, source_type, tags, credibility_notes.'
                ),
            },
            {
                'role': 'user',
                'content': json.dumps(
                    {
                        'file_name': file_name,
                        'file_type': file_type,
                        'title': parsed.title,
                        'metadata': parsed.metadata,
                        'content': parsed.text[:6000],
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def build_evaluation_messages(self, employee_profile: dict[str, Any], evidence_items: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [
            {
                'role': 'system',
                'content': (
                    'You are an enterprise AI capability evaluator. Return JSON with keys: overall_score, ai_level, '
                    'confidence_score, explanation, needs_manual_review, dimensions. '
                    'Each dimension item must include code, label, weight, raw_score, weighted_score, rationale.'
                ),
            },
            {
                'role': 'user',
                'content': json.dumps({'employee_profile': employee_profile, 'evidence_items': evidence_items}, ensure_ascii=False),
            },
        ]

    def build_salary_messages(self, evaluation_context: dict[str, Any], salary_context: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                'role': 'system',
                'content': (
                    'You are a compensation strategy assistant. Return JSON with keys: explanation, risk_flags, '
                    'budget_commentary, fairness_commentary.'
                ),
            },
            {
                'role': 'user',
                'content': json.dumps({'evaluation': evaluation_context, 'salary': salary_context}, ensure_ascii=False),
            },
        ]


class DeepSeekService:
    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        sleeper: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.sleeper = sleeper or time.sleep
        self.prompts = DeepSeekPromptLibrary()
        self.rate_limiter = InMemoryRateLimiter(settings.deepseek_requests_per_minute, clock=clock)

    def extract_evidence(self, parsed: ParsedDocument, *, file_name: str, file_type: str, fallback_payload: dict[str, Any]) -> DeepSeekCallResult:
        return self._invoke_json(
            task_name='evidence_extraction',
            messages=self.prompts.build_evidence_messages(parsed, file_name=file_name, file_type=file_type),
            fallback_payload=fallback_payload,
        )

    def generate_evaluation(self, employee_profile: dict[str, Any], evidence_items: list[dict[str, Any]], fallback_payload: dict[str, Any]) -> DeepSeekCallResult:
        return self._invoke_json(
            task_name='evaluation_generation',
            messages=self.prompts.build_evaluation_messages(employee_profile, evidence_items),
            fallback_payload=fallback_payload,
        )

    def generate_salary_explanation(self, evaluation_context: dict[str, Any], salary_context: dict[str, Any], fallback_payload: dict[str, Any]) -> DeepSeekCallResult:
        return self._invoke_json(
            task_name='salary_explanation',
            messages=self.prompts.build_salary_messages(evaluation_context, salary_context),
            fallback_payload=fallback_payload,
        )

    def _invoke_json(self, *, task_name: str, messages: list[dict[str, str]], fallback_payload: dict[str, Any]) -> DeepSeekCallResult:
        if not self._is_configured():
            return DeepSeekCallResult(payload=fallback_payload, used_fallback=True, provider='fallback', reason='deepseek_not_configured')

        try:
            self.rate_limiter.acquire()
        except RuntimeError as exc:
            return DeepSeekCallResult(payload=fallback_payload, used_fallback=True, provider='fallback', reason=str(exc))

        last_error: Exception | None = None
        for attempt in range(self.settings.deepseek_max_retries + 1):
            try:
                response = self._client().post(
                    f"{self.settings.deepseek_api_base_url.rstrip('/')}/chat/completions",
                    json={
                        'model': self.settings.deepseek_model,
                        'messages': messages,
                        'temperature': 0.2,
                        'response_format': {'type': 'json_object'},
                    },
                    timeout=self.settings.deepseek_timeout_seconds,
                )
                response.raise_for_status()
                parsed = self._parse_response_payload(response.json())
                if parsed is None:
                    return DeepSeekCallResult(payload=fallback_payload, used_fallback=True, provider='deepseek', reason='invalid_json_response')
                return DeepSeekCallResult(payload=parsed, used_fallback=False, provider='deepseek')
            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt >= self.settings.deepseek_max_retries:
                    break
                self.sleeper(0.2 * (attempt + 1))
        return DeepSeekCallResult(
            payload=compact_dict({**fallback_payload, 'llm_fallback_reason': str(last_error) if last_error else 'unknown_error'}),
            used_fallback=True,
            provider='fallback',
            reason=str(last_error) if last_error else 'unknown_error',
        )

    def _parse_response_payload(self, body: dict[str, Any]) -> dict[str, Any] | None:
        try:
            content = body['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError('DeepSeek response payload is missing message content.') from exc
        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise ValueError('DeepSeek response content is not JSON text.')
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = JSON_BLOCK_PATTERN.search(content)
            if not match:
                return None
            return json.loads(match.group(0))

    def _client(self) -> httpx.Client:
        if self.client is not None:
            return self.client
        return httpx.Client()

    def _is_configured(self) -> bool:
        api_key = self.settings.deepseek_api_key.strip()
        return bool(api_key and not api_key.startswith('your_') and 'change_me' not in api_key)
