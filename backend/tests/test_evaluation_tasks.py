from __future__ import annotations

from backend.app.tasks.evaluation_tasks import generate_evaluation_task


def test_generate_evaluation_task_name() -> None:
    assert generate_evaluation_task.name == 'tasks.generate_evaluation'


def test_generate_evaluation_task_max_retries() -> None:
    assert generate_evaluation_task.max_retries == 2


def test_generate_evaluation_task_has_soft_time_limit() -> None:
    assert generate_evaluation_task.soft_time_limit == 300


def test_generate_evaluation_task_has_time_limit() -> None:
    assert generate_evaluation_task.time_limit == 360


def test_generate_evaluation_task_retry_backoff() -> None:
    assert generate_evaluation_task.retry_backoff is True
