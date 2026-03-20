from __future__ import annotations

from fastapi import Query
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_endpoint_returns_application_status() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["api_prefix"] == "/api/v1"


def test_api_v1_meta_route_is_registered() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/system/meta")

    assert response.status_code == 200
    assert response.json()["api_prefix"] == "/api/v1"


def test_cors_preflight_uses_configured_origins() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_global_exception_handler_returns_structured_error() -> None:
    app = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"] == "internal_server_error"


def test_validation_exception_handler_returns_details() -> None:
    app = create_app()

    @app.get("/validated")
    async def validated(limit: int = Query(..., ge=1)) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(app) as client:
        response = client.get("/validated?limit=0")

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
    assert response.json()["details"]
