from __future__ import annotations

from backend.app.tasks.import_tasks import run_import_task


def test_run_import_task_name() -> None:
    assert run_import_task.name == 'tasks.run_import'


def test_run_import_task_max_retries() -> None:
    assert run_import_task.max_retries == 2


def test_run_import_task_has_soft_time_limit() -> None:
    assert run_import_task.soft_time_limit == 600


def test_run_import_task_has_time_limit() -> None:
    assert run_import_task.time_limit == 660


def test_run_import_task_retry_backoff() -> None:
    assert run_import_task.retry_backoff is True
