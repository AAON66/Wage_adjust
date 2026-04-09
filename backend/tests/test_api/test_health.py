from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.app.main import create_app


def _make_response(*, ping_result: dict[str, object] | None) -> tuple[TestClient, object]:
    app = create_app()
    inspector = MagicMock()
    inspector.ping.return_value = ping_result
    inspect_patch = patch(
        'backend.app.celery_app.celery_app.control.inspect',
        return_value=inspector,
    )
    return TestClient(app), inspect_patch


def test_celery_health_returns_200() -> None:
    client, inspect_patch = _make_response(ping_result=None)

    with inspect_patch, client:
        response = client.get('/api/v1/health/celery')

    assert response.status_code == 200


def test_celery_health_response_fields() -> None:
    client, inspect_patch = _make_response(ping_result=None)

    with inspect_patch, client:
        response = client.get('/api/v1/health/celery')

    payload = response.json()
    assert set(payload) == {'status', 'workers_online', 'checked_at'}


def test_celery_health_unhealthy_when_no_workers() -> None:
    client, inspect_patch = _make_response(ping_result=None)

    with inspect_patch, client:
        response = client.get('/api/v1/health/celery')

    assert response.json()['status'] == 'unhealthy'
    assert response.json()['workers_online'] == 0


def test_celery_health_healthy_when_workers_online() -> None:
    client, inspect_patch = _make_response(
        ping_result={'celery@worker1': {'ok': 'pong'}},
    )

    with inspect_patch, client:
        response = client.get('/api/v1/health/celery')

    assert response.json()['status'] == 'healthy'
    assert response.json()['workers_online'] == 1


def test_celery_health_no_auth_required() -> None:
    client, inspect_patch = _make_response(ping_result=None)

    with inspect_patch, client:
        response = client.get('/api/v1/health/celery')

    assert response.status_code == 200


def test_celery_health_checked_at_iso_format() -> None:
    client, inspect_patch = _make_response(ping_result=None)

    with inspect_patch, client:
        response = client.get('/api/v1/health/celery')

    datetime.fromisoformat(response.json()['checked_at'])
