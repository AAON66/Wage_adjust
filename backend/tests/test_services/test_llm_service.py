from __future__ import annotations

import json

import httpx

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import ParsedDocument
from backend.app.services.llm_service import DeepSeekService


def test_llm_service_uses_fallback_when_not_configured() -> None:
    settings = Settings(deepseek_api_key='your_deepseek_api_key')
    service = DeepSeekService(settings)
    result = service.extract_evidence(
        ParsedDocument(text='AI workflow improved delivery.', title='Project summary', metadata={}),
        file_name='summary.md',
        file_type='md',
        fallback_payload={'summary': 'fallback', 'confidence_score': 0.6, 'source_type': 'file_parse', 'tags': ['artifact']},
    )
    assert result.used_fallback is True
    assert result.payload['summary'] == 'fallback'


def test_llm_service_parses_json_response_with_retry() -> None:
    calls = {'count': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls['count'] += 1
        if calls['count'] == 1:
            return httpx.Response(503, json={'error': 'temporary'})
        return httpx.Response(
            200,
            json={
                'choices': [
                    {
                        'message': {
                            'content': json.dumps({'summary': 'structured output', 'confidence_score': 0.88, 'source_type': 'file_parse', 'tags': ['tooling']})
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(deepseek_api_key='test-key', deepseek_max_retries=1)
    service = DeepSeekService(settings, client=client, sleeper=lambda _: None)
    result = service.extract_evidence(
        ParsedDocument(text='AI workflow improved delivery.', title='Project summary', metadata={}),
        file_name='summary.md',
        file_type='md',
        fallback_payload={'summary': 'fallback', 'confidence_score': 0.6, 'source_type': 'file_parse', 'tags': ['artifact']},
    )
    assert result.used_fallback is False
    assert result.payload['summary'] == 'structured output'
    assert calls['count'] == 2
