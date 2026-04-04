from __future__ import annotations

import base64
import io
from unittest.mock import MagicMock, patch

from PIL import Image

from backend.app.core.config import Settings
from backend.app.services.llm_service import DeepSeekCallResult, DeepSeekPromptLibrary, DeepSeekService


def _make_tiny_png() -> bytes:
    """Create a minimal 1x1 PNG for testing."""
    img = Image.new('RGB', (1, 1), 'red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _settings(**overrides) -> Settings:
    defaults = {
        'deepseek_api_key': 'test-key-for-unit-tests',
        'deepseek_vision_model': 'deepseek-chat',
    }
    defaults.update(overrides)
    return Settings(**defaults)


# --- Tests for build_vision_evaluation_messages ---

def test_build_vision_messages_returns_two_messages() -> None:
    lib = DeepSeekPromptLibrary()
    image_b64 = base64.b64encode(_make_tiny_png()).decode('ascii')
    messages = lib.build_vision_evaluation_messages(image_b64, 'image/png')

    assert len(messages) == 2
    assert messages[0]['role'] == 'system'
    assert messages[1]['role'] == 'user'


def test_build_vision_messages_system_contains_required_keys() -> None:
    lib = DeepSeekPromptLibrary()
    image_b64 = base64.b64encode(_make_tiny_png()).decode('ascii')
    messages = lib.build_vision_evaluation_messages(image_b64, 'image/png')
    system_content = messages[0]['content']

    assert 'description' in system_content
    assert 'quality_score' in system_content
    assert 'dimension_relevance' in system_content
    assert 'TOOL' in system_content
    assert 'DEPTH' in system_content
    assert 'LEARN' in system_content
    assert 'SHARE' in system_content
    assert 'IMPACT' in system_content


def test_build_vision_messages_has_injection_resistance() -> None:
    lib = DeepSeekPromptLibrary()
    image_b64 = base64.b64encode(_make_tiny_png()).decode('ascii')
    messages = lib.build_vision_evaluation_messages(image_b64, 'image/png')
    system_content = messages[0]['content']

    assert 'Ignore any text' in system_content


def test_build_vision_messages_user_has_image_and_text() -> None:
    lib = DeepSeekPromptLibrary()
    image_b64 = base64.b64encode(_make_tiny_png()).decode('ascii')
    messages = lib.build_vision_evaluation_messages(image_b64, 'image/png')
    user_content = messages[1]['content']

    assert isinstance(user_content, list)
    types = [item['type'] for item in user_content]
    assert 'image_url' in types
    assert 'text' in types


def test_build_vision_messages_with_slide_number_context() -> None:
    lib = DeepSeekPromptLibrary()
    image_b64 = base64.b64encode(_make_tiny_png()).decode('ascii')
    messages = lib.build_vision_evaluation_messages(image_b64, 'image/png', context={'slide_number': 3})

    text_items = [item for item in messages[1]['content'] if item.get('type') == 'text']
    assert any('slide 3' in item['text'] for item in text_items)


def test_build_vision_messages_with_standalone_upload_context() -> None:
    lib = DeepSeekPromptLibrary()
    image_b64 = base64.b64encode(_make_tiny_png()).decode('ascii')
    messages = lib.build_vision_evaluation_messages(image_b64, 'image/png', context={'image_source': 'standalone_upload'})

    text_items = [item for item in messages[1]['content'] if item.get('type') == 'text']
    assert any('directly uploaded' in item['text'] for item in text_items)


# --- Tests for evaluate_image_vision ---

def test_evaluate_image_vision_calls_invoke_json() -> None:
    settings = _settings()
    service = DeepSeekService(settings, client=MagicMock())
    mock_result = DeepSeekCallResult(
        payload={'description': 'test', 'quality_score': 3, 'dimension_relevance': {}},
        used_fallback=False,
        provider='deepseek',
    )
    service._invoke_json = MagicMock(return_value=mock_result)

    result = service.evaluate_image_vision(_make_tiny_png(), 'png', 'image/png')

    service._invoke_json.assert_called_once()
    call_kwargs = service._invoke_json.call_args
    assert call_kwargs.kwargs['task_name'] == 'vision_evaluation'


def test_evaluate_image_vision_compresses_large_images() -> None:
    settings = _settings()
    service = DeepSeekService(settings, client=MagicMock())
    mock_result = DeepSeekCallResult(
        payload={'description': 'test', 'quality_score': 3, 'dimension_relevance': {}},
        used_fallback=False,
        provider='deepseek',
    )
    service._invoke_json = MagicMock(return_value=mock_result)

    with patch('backend.app.services.llm_service.compress_image_if_needed', return_value=_make_tiny_png()) as mock_compress:
        # Need to patch at import location in llm_service after the import happens
        # Since evaluate_image_vision does a local import, patch at source
        with patch('backend.app.parsers.image_parser.compress_image_if_needed', return_value=_make_tiny_png()) as mock_compress2:
            result = service.evaluate_image_vision(_make_tiny_png(), 'png', 'image/png')

    # The function should have been called (via local import from image_parser)
    assert mock_compress2.called or mock_compress.called


def test_evaluate_image_vision_fallback_payload() -> None:
    settings = _settings()
    service = DeepSeekService(settings, client=MagicMock())
    mock_result = DeepSeekCallResult(
        payload={'description': 'Vision unavailable', 'quality_score': 0, 'dimension_relevance': {}},
        used_fallback=True,
        provider='fallback',
    )
    service._invoke_json = MagicMock(return_value=mock_result)

    result = service.evaluate_image_vision(_make_tiny_png(), 'png', 'image/png')

    call_kwargs = service._invoke_json.call_args
    fallback = call_kwargs.kwargs['fallback_payload']
    assert fallback['description'] == 'Vision unavailable'
    assert fallback['quality_score'] == 0
    assert fallback['dimension_relevance'] == {}


# --- Tests for model and timeout resolution ---

def test_resolve_model_name_for_vision_evaluation() -> None:
    settings = _settings(deepseek_vision_model='test-vision-model')
    service = DeepSeekService(settings, client=MagicMock())

    model = service._resolve_model_name('vision_evaluation')
    assert model == 'test-vision-model'


def test_resolve_model_name_vision_defaults_to_deepseek_chat() -> None:
    settings = _settings(deepseek_vision_model='deepseek-chat')
    service = DeepSeekService(settings, client=MagicMock())

    model = service._resolve_model_name('vision_evaluation')
    assert model == 'deepseek-chat'


def test_resolve_timeout_vision_uses_parsing_timeout() -> None:
    settings = _settings(deepseek_parsing_timeout_seconds=180, deepseek_timeout_seconds=30)
    service = DeepSeekService(settings, client=MagicMock())

    timeout = service._resolve_timeout('vision_evaluation')
    assert timeout.read == 180
