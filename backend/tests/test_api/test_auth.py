from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.database import Base, create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db
from backend.app.main import create_app
from backend.app.models import load_model_modules


class AuthDatabaseContext:
    def __init__(self) -> None:
        temp_root = Path(".tmp").resolve()
        temp_root.mkdir(parents=True, exist_ok=True)
        database_path = (temp_root / f"auth-{uuid4().hex}.db").as_posix()
        self.settings = Settings(database_url=f"sqlite+pysqlite:///{database_path}")
        self.engine = create_db_engine(self.settings)
        self.session_factory = create_session_factory(self.settings)
        load_model_modules()
        init_database(self.engine)

    def override_get_db(self):
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()



def build_test_client() -> TestClient:
    context = AuthDatabaseContext()
    app = create_app()
    app.dependency_overrides[get_db] = context.override_get_db
    return TestClient(app)



def test_register_login_refresh_and_me_flow() -> None:
    with build_test_client() as client:
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "owner@example.com",
                "password": "Password123",
                "role": "admin",
            },
        )
        assert register_response.status_code == 201
        register_body = register_response.json()
        assert register_body["user"]["email"] == "owner@example.com"
        access_token = register_body["tokens"]["access_token"]
        refresh_token = register_body["tokens"]["refresh_token"]

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "admin"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Password123"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["token_type"] == "bearer"

        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        assert refresh_response.json()["access_token"]



def test_duplicate_registration_returns_conflict() -> None:
    with build_test_client() as client:
        payload = {
            "email": "duplicate@example.com",
            "password": "Password123",
            "role": "employee",
        }
        assert client.post("/api/v1/auth/register", json=payload).status_code == 201

        duplicate_response = client.post("/api/v1/auth/register", json=payload)
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["error"] == "http_error"



def test_invalid_login_and_invalid_token_are_rejected() -> None:
    with build_test_client() as client:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "person@example.com",
                "password": "Password123",
                "role": "employee",
            },
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": "WrongPassword"},
        )
        assert login_response.status_code == 401

        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert me_response.status_code == 401
        assert me_response.json()["error"] == "http_error"
