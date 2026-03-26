from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app


def _make_settings() -> Settings:
    return Settings(
        environment='development',
        database_url='sqlite+pysqlite:///:memory:',
        jwt_secret_key='test_secret_key_for_testing_only',
        public_api_key='test_public_key',
    )


def test_eleven_failed_logins_return_429() -> None:
    """After 10 failed attempts, the 11th returns 429.

    Uses a MagicMock Redis client injected into _check_and_increment_failed_login
    to exercise the REAL counter logic without a live Redis server.
    """
    import backend.app.api.v1.auth as auth_module

    # Cleanest approach: patch _get_redis_client per-call to return a mock
    # whose .get() returns None for first 10 calls and b'10' on the 11th
    attempt = 0

    def mock_redis_client(settings):
        nonlocal attempt
        mock = MagicMock()
        # On the 11th call (attempt >= 10), .get() returns b'10' -> triggers 429
        mock.get.return_value = b'10' if attempt >= 10 else None
        pipe = MagicMock()
        mock.pipeline.return_value = pipe
        attempt += 1
        return mock

    with patch.object(auth_module, '_get_redis_client', side_effect=mock_redis_client):
        settings = _make_settings()
        app = create_app(settings)
        client = TestClient(app, raise_server_exceptions=False)

        # 10 failures — each calls the real _check_and_increment_failed_login
        # which sees mock.get() return None -> no 429 yet
        for i in range(10):
            resp = client.post(
                '/api/v1/auth/login',
                json={'email': 'x@x.com', 'password': 'WrongPass1!'},
            )
            assert resp.status_code == 401, f'Expected 401 on attempt {i + 1}, got {resp.status_code}'

        # 11th failure — mock.get() now returns b'10' -> real logic raises 429
        resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'x@x.com', 'password': 'WrongPass1!'},
        )
        assert resp.status_code == 429, f'Expected 429 on attempt 11, got {resp.status_code}'


def test_successful_login_does_not_count_against_limit() -> None:
    """A successful login calls _reset_failed_login, not the increment function."""
    import backend.app.api.v1.auth as auth_module
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.orm import sessionmaker, Session
    from backend.app.core.database import Base
    from backend.app.core.security import get_password_hash
    from backend.app.dependencies import get_db
    from backend.app.models import load_model_modules
    from backend.app.models.user import User

    settings = _make_settings()
    load_model_modules()  # ensure all model classes are registered before create_all
    # Use StaticPool so all connections share the same in-memory SQLite database
    engine = create_engine(
        'sqlite+pysqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

    # Create a test user in the in-memory DB
    with SessionLocal() as db:
        user = User(
            email='good@example.com',
            hashed_password=get_password_hash('CorrectPass1!'),
            role='employee',
        )
        db.add(user)
        db.commit()

    reset_calls = []
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # no prior failed attempts

    with patch.object(auth_module, '_get_redis_client', return_value=mock_redis):
        with patch.object(
            auth_module, '_reset_failed_login', side_effect=lambda ip, s: reset_calls.append(ip)
        ):
            app = create_app(settings)
            # Wire the test DB session so login can find the test user
            def override_get_db():
                db = SessionLocal()
                try:
                    yield db
                finally:
                    db.close()
            app.dependency_overrides[get_db] = override_get_db
            client = TestClient(app, raise_server_exceptions=False)

            resp = client.post(
                '/api/v1/auth/login',
                json={'email': 'good@example.com', 'password': 'CorrectPass1!'},
            )
            assert resp.status_code == 200, f'Expected 200, got {resp.status_code}: {resp.text}'
            assert len(reset_calls) == 1, 'Expected _reset_failed_login to be called once on success'
