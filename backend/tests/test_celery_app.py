from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

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


def test_session_local_uses_global_engine() -> None:
    from backend.app.core.database import SessionLocal, engine

    assert SessionLocal.kw['bind'] is engine


def test_create_session_factory_reuses_explicit_engine(tmp_path: Path) -> None:
    from backend.app.core.database import create_session_factory

    sqlite_path = tmp_path / 'celery-explicit-engine.db'
    explicit_engine = create_engine(
        f"sqlite:///{sqlite_path}", connect_args={'check_same_thread': False}, future=True
    )
    session_factory = create_session_factory(engine_instance=explicit_engine)

    assert session_factory.kw['bind'] is explicit_engine
    session = session_factory()
    try:
        assert session.execute(text('SELECT 1')).scalar() == 1
    finally:
        session.close()
        explicit_engine.dispose()


def test_evaluation_task_registered() -> None:
    assert 'tasks.generate_evaluation' in celery_app.tasks


def test_import_task_registered() -> None:
    assert 'tasks.run_import' in celery_app.tasks


def test_include_contains_evaluation_tasks() -> None:
    assert 'backend.app.tasks.evaluation_tasks' in celery_app.conf.include


def test_include_contains_import_tasks() -> None:
    assert 'backend.app.tasks.import_tasks' in celery_app.conf.include


def test_disposed_session_factory_engine_still_executes_queries(tmp_path: Path) -> None:
    from backend.app.core.database import create_session_factory

    sqlite_path = tmp_path / 'celery-dispose-reconnect.db'
    explicit_engine = create_engine(
        f"sqlite:///{sqlite_path}", connect_args={'check_same_thread': False}, future=True
    )
    session_factory = create_session_factory(engine_instance=explicit_engine)

    first_session = session_factory()
    try:
        assert first_session.execute(text('SELECT 1')).scalar() == 1
    finally:
        first_session.close()

    session_factory.kw['bind'].dispose()

    second_session = session_factory()
    try:
        assert second_session.execute(text('SELECT 1')).scalar() == 1
    finally:
        second_session.close()
        explicit_engine.dispose()
