from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a local .env file."""

    app_name: str = "Wage Adjust Platform"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = False

    database_url: str = "sqlite+pysqlite:///./wage_adjust.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    jwt_secret_key: str = Field("change_me", min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    allow_self_registration: bool = False

    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "your_access_key"
    storage_secret_key: str = "your_secret_key"
    storage_bucket_name: str = "wage-adjust-files"
    storage_base_dir: str = "uploads"
    max_upload_size_mb: int = 200
    archive_max_evidence_items: int = 24
    archive_parser_max_files: int = 36
    archive_parser_max_member_bytes: int = 160_000
    archive_parser_max_snippet_chars: int = 6_000
    archive_parser_max_text_chars: int = 72_000

    deepseek_api_key: str = "your_deepseek_api_key"
    deepseek_api_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-reasoner"
    deepseek_parsing_model: str = ""
    deepseek_evaluation_model: str = ""
    deepseek_timeout_seconds: int = 30
    deepseek_parsing_timeout_seconds: int = 120
    deepseek_evaluation_timeout_seconds: int = 120
    deepseek_max_retries: int = 2
    deepseek_requests_per_minute: int = 20
    deepseek_require_real_call_for_parsing: bool = True

    backend_cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ]
    )
    redis_url: str = "redis://localhost:6379/0"
    national_id_encryption_key: str = ''

    feishu_encryption_key: str = ''

    public_api_key: str = "your_public_api_key"
    public_api_rate_limit: str = "1000/hour"

    # Eligibility thresholds (D-04)
    eligibility_min_tenure_months: int = 6
    eligibility_min_adjustment_interval_months: int = 6
    eligibility_performance_fail_grades: str = 'C,D,E'
    eligibility_max_non_statutory_leave_days: float = 30.0

    log_level: str = "INFO"
    log_format: str = "json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("BACKEND_CORS_ORIGINS must be a JSON array or comma list.")
                return [str(item) for item in parsed]
            return [item.strip() for item in text.split(",") if item.strip()]
        raise ValueError("BACKEND_CORS_ORIGINS must be a list or string.")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""
    return Settings()
