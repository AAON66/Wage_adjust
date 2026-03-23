from __future__ import annotations

import json

import httpx

from backend.app.core.config import Settings
from backend.app.parsers.base_parser import ParsedDocument
from backend.app.services.llm_service import DeepSeekPromptLibrary, DeepSeekService


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
        assert request.headers['Authorization'] == 'Bearer test-key'
        assert request.headers['Content-Type'] == 'application/json'
        assert json.loads(request.content)['model'] == 'deepseek-chat'
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


def test_evaluation_generation_keeps_primary_model() -> None:
    seen_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_models.append(json.loads(request.content)['model'])
        return httpx.Response(
            200,
            json={
                'choices': [
                    {
                        'message': {
                            'content': json.dumps(
                                {
                                    'overall_score': 82,
                                    'ai_level': 'Level 4',
                                    'confidence_score': 0.81,
                                    'explanation': '中文说明',
                                    'needs_manual_review': False,
                                    'dimensions': [],
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(deepseek_api_key='test-key', deepseek_model='deepseek-reasoner')
    service = DeepSeekService(settings, client=client)
    result = service.generate_evaluation(
        {'name': '张三'},
        [{'summary': '交付了 AI 项目'}],
        fallback_payload={'overall_score': 70, 'ai_level': 'Level 3', 'confidence_score': 0.5, 'dimensions': []},
    )
    assert result.used_fallback is False
    assert seen_models == ['deepseek-reasoner']


def test_parsing_timeout_prefers_parsing_specific_timeout() -> None:
    settings = Settings(
        deepseek_api_key='test-key',
        deepseek_model='deepseek-reasoner',
        deepseek_timeout_seconds=30,
        deepseek_parsing_timeout_seconds=120,
    )
    service = DeepSeekService(settings)
    timeout = service._resolve_timeout('evidence_extraction')
    assert timeout.read == 120
    assert service._resolve_model_name('evidence_extraction') == 'deepseek-chat'


def test_evaluation_prompt_requires_chinese_output() -> None:
    messages = DeepSeekPromptLibrary().build_evaluation_messages({'name': '寮犱笁'}, [{'summary': '椤圭洰鎴愭灉'}])
    system_prompt = messages[0]['content']
    assert 'Chinese-speaking managers and HR reviewers' in system_prompt
    assert 'Simplified Chinese' in system_prompt
