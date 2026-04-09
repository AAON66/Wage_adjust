from __future__ import annotations

from backend.app.celery_app import celery_app


def test_celery_broker_uses_redis() -> None:
    assert 'redis://' in celery_app.conf.broker_url


def test_celery_serializer_is_json() -> None:
    assert celery_app.conf.task_serializer == 'json'


def test_celery_accept_content_json_only() -> None:
    assert celery_app.conf.accept_content == ['json']


def test_celery_does_not_hijack_root_logger() -> None:
    assert celery_app.conf.worker_hijack_root_logger is False


def test_db_health_check_task_registered() -> None:
    assert 'tasks.db_health_check' in celery_app.tasks


def test_db_health_check_task_name() -> None:
    from backend.app.tasks.test_tasks import db_health_check

    assert db_health_check.name == 'tasks.db_health_check'


def test_celery_include_has_test_tasks() -> None:
    assert 'backend.app.tasks.test_tasks' in celery_app.conf.include
