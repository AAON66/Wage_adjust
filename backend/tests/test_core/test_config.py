from __future__ import annotations

from backend.app.core.config import Settings


def test_settings_parse_json_cors_origins() -> None:
    settings = Settings(
        backend_cors_origins='["http://localhost:3000", "http://localhost:5173"]'
    )

    assert settings.backend_cors_origins == [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = Settings(backend_cors_origins="http://a.test,http://b.test")

    assert settings.backend_cors_origins == ["http://a.test", "http://b.test"]
