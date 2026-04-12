from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _mock_auth():
    """Bypass authentication for all tests in this module."""
    fake_user = MagicMock()
    fake_user.id = 'test-user-id'
    fake_user.role = 'admin'

    from backend.app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: fake_user
    yield
    app.dependency_overrides.clear()


@patch('backend.app.api.v1.tasks.AsyncResult')
def test_get_task_status_pending(mock_async_result, client):
    mock_result = MagicMock()
    mock_result.state = 'PENDING'
    mock_async_result.return_value = mock_result

    response = client.get('/api/v1/tasks/some-task-id')
    assert response.status_code == 200
    data = response.json()
    assert data['task_id'] == 'some-task-id'
    assert data['status'] == 'pending'


@patch('backend.app.api.v1.tasks.AsyncResult')
def test_get_task_status_started(mock_async_result, client):
    mock_result = MagicMock()
    mock_result.state = 'STARTED'
    mock_result.info = {'status': 'running', 'user_id': 'test-user-id'}
    mock_async_result.return_value = mock_result

    response = client.get('/api/v1/tasks/some-task-id')
    assert response.status_code == 200
    data = response.json()
    assert data['task_id'] == 'some-task-id'
    assert data['status'] == 'running'


@patch('backend.app.api.v1.tasks.AsyncResult')
def test_get_task_status_progress(mock_async_result, client):
    mock_result = MagicMock()
    mock_result.state = 'PROGRESS'
    mock_result.info = {'processed': 50, 'total': 100, 'errors': 2, 'user_id': 'test-user-id'}
    mock_async_result.return_value = mock_result

    response = client.get('/api/v1/tasks/some-task-id')
    assert response.status_code == 200
    data = response.json()
    assert data['task_id'] == 'some-task-id'
    assert data['status'] == 'running'
    assert data['progress']['processed'] == 50
    assert data['progress']['total'] == 100
    assert data['progress']['errors'] == 2


@patch('backend.app.api.v1.tasks.AsyncResult')
def test_get_task_status_success(mock_async_result, client):
    mock_result = MagicMock()
    mock_result.state = 'SUCCESS'
    mock_result.info = {'status': 'completed', 'result': {'id': 'eval-1'}}
    mock_result.result = {'status': 'completed', 'result': {'id': 'eval-1'}}
    mock_async_result.return_value = mock_result

    response = client.get('/api/v1/tasks/some-task-id')
    assert response.status_code == 200
    data = response.json()
    assert data['task_id'] == 'some-task-id'
    assert data['status'] == 'completed'
    assert data['result'] == {'id': 'eval-1'}


@patch('backend.app.api.v1.tasks.AsyncResult')
def test_get_task_status_success_failed_payload(mock_async_result, client):
    """When task completes but returns a failed status in payload."""
    mock_result = MagicMock()
    mock_result.state = 'SUCCESS'
    mock_result.info = {'status': 'failed', 'error': 'LLM timeout'}
    mock_result.result = {'status': 'failed', 'error': 'LLM timeout'}
    mock_async_result.return_value = mock_result

    response = client.get('/api/v1/tasks/some-task-id')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'failed'
    assert data['error'] == 'LLM timeout'


@patch('backend.app.api.v1.tasks.AsyncResult')
def test_get_task_status_failure(mock_async_result, client):
    mock_result = MagicMock()
    mock_result.state = 'FAILURE'
    mock_result.result = Exception('timeout')
    mock_async_result.return_value = mock_result

    response = client.get('/api/v1/tasks/some-task-id')
    assert response.status_code == 200
    data = response.json()
    assert data['task_id'] == 'some-task-id'
    assert data['status'] == 'failed'
    assert 'timeout' in data['error']
