from __future__ import annotations

import pytest
from unittest.mock import patch

from backend.app.core.config import Settings
from backend.app.main import validate_startup_config


def test_production_refuses_change_me_jwt_secret() -> None:
    settings = Settings(
        environment='production',
        jwt_secret_key='change_me',
        public_api_key='safe_key_abc123',
        database_url='sqlite+pysqlite:///:memory:',
    )
    # Mock Redis ping to succeed so only the JWT check fires
    with patch('backend.app.main.redis_lib') as mock_redis:
        mock_redis.from_url.return_value.ping.return_value = True
        with pytest.raises(RuntimeError, match='JWT_SECRET_KEY'):
            validate_startup_config(settings)


def test_production_refuses_default_public_api_key() -> None:
    settings = Settings(
        environment='production',
        jwt_secret_key='safe_jwt_secret_key_abc',
        public_api_key='your_public_api_key',
        database_url='sqlite+pysqlite:///:memory:',
    )
    with patch('backend.app.main.redis_lib') as mock_redis:
        mock_redis.from_url.return_value.ping.return_value = True
        with pytest.raises(RuntimeError, match='PUBLIC_API_KEY'):
            validate_startup_config(settings)


def test_development_allows_placeholder_secrets() -> None:
    settings = Settings(
        environment='development',
        jwt_secret_key='change_me',
        public_api_key='your_public_api_key',
        database_url='sqlite+pysqlite:///:memory:',
    )
    # Must not raise — development mode is permissive (no Redis check either)
    validate_startup_config(settings)


def test_production_with_safe_secrets_does_not_raise() -> None:
    settings = Settings(
        environment='production',
        jwt_secret_key='safe_random_jwt_key_xyz',
        public_api_key='safe_random_api_key_abc',
        database_url='sqlite+pysqlite:///:memory:',
    )
    with patch('backend.app.main.redis_lib') as mock_redis:
        mock_redis.from_url.return_value.ping.return_value = True
        validate_startup_config(settings)  # must not raise


def test_production_refuses_when_redis_unreachable() -> None:
    """D-05: production startup fails if Redis cannot be reached."""
    settings = Settings(
        environment='production',
        jwt_secret_key='safe_jwt_secret_key_xyz',
        public_api_key='safe_api_key_abc',
        database_url='sqlite+pysqlite:///:memory:',
    )
    with patch('backend.app.main.redis_lib') as mock_redis:
        mock_redis.from_url.return_value.ping.side_effect = ConnectionError('refused')
        with pytest.raises(RuntimeError, match='Redis'):
            validate_startup_config(settings)
