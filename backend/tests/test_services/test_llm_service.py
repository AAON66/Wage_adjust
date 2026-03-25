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


def test_evidence_prompt_includes_summary_template_guidance() -> None:
    messages = DeepSeekPromptLibrary().build_evidence_messages(
        ParsedDocument(
            text='智能质检流程上线并缩短人工复核时间。',
            title='impact-summary.md',
            metadata={
                'evidence_kind': 'project_outcome',
                'summary_template': '按项目成果摘要输出',
                'summary_focus': ['项目事项', '交付结果', '业务影响'],
            },
        ),
        file_name='repo.zip',
        file_type='zip',
    )
    system_prompt = messages[0]['content']
    user_payload = json.loads(messages[1]['content'])

    assert 'metadata.evidence_kind' in system_prompt
    assert 'project_outcome' in system_prompt
    assert 'implementation_detail' in system_prompt
    assert user_payload['metadata']['summary_template'] == '按项目成果摘要输出'
    assert user_payload['metadata']['summary_focus'] == ['项目事项', '交付结果', '业务影响']


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
    assert seen_models == ['deepseek-chat']


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


def test_evaluation_timeout_prefers_evaluation_specific_timeout() -> None:
    settings = Settings(
        deepseek_api_key='test-key',
        deepseek_model='deepseek-reasoner',
        deepseek_timeout_seconds=30,
        deepseek_evaluation_timeout_seconds=120,
    )
    service = DeepSeekService(settings)
    timeout = service._resolve_timeout('evaluation_generation')
    assert timeout.read == 120
    assert service._resolve_model_name('evaluation_generation') == 'deepseek-chat'


def test_evaluation_prompt_includes_manager_style_examples() -> None:
    messages = DeepSeekPromptLibrary().build_evaluation_messages(
        {
            'name': '李四',
            'department_scoring_context': {
                'profile_label': '研发与技术画像',
                'profile_summary': '重点关注工程效率与稳定性。',
                'reasoning_style': {
                    'tone': '使用真实主管复核口吻。',
                    'rules': ['不要照抄示例语料。'],
                },
                'score_policy': {
                    'default_expectation': '只要证据能说明员工已稳定、真实地在本岗位使用 AI 并形成产出，单维度通常应落在 68-85 分区间。',
                    'low_score_rule': '只有在证据明显不足或能力未达标时，才应低于 60 分。',
                },
            },
            'dimension_specs': [
                {
                    'code': 'DEPTH',
                    'label': 'AI 应用深度',
                    'weight': 0.25,
                    'focus': '重点看 AI 是否进入架构和发布链路。',
                    'manager_examples': {
                        'meets_expectation': ['AI 已进入研发主流程，如开发、测试、发布或问题处理。'],
                        'strong_performance': ['AI 已嵌入架构设计、发布链路或稳定性治理。'],
                    },
                },
            ],
        },
        [{'summary': '构建了发布流水线自动化'}],
    )
    system_prompt = messages[0]['content']
    user_payload = json.loads(messages[1]['content'])

    assert 'manager_examples' in system_prompt
    assert 'realistic manager review tone' in system_prompt
    assert '68-85 range' in system_prompt
    assert user_payload['department_scoring_context']['reasoning_style']['tone'] == '使用真实主管复核口吻。'
    assert user_payload['dimension_specs'][0]['manager_examples']['meets_expectation']
    assert user_payload['dimension_specs'][0]['manager_examples']['strong_performance']
