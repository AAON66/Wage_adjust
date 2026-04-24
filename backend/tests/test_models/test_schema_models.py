from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import create_db_engine, init_database
from backend.app.models import Base, load_model_modules
from backend.app.models.performance_record import PerformanceRecord


EXPECTED_TABLES = {
    "users",
    "employees",
    "evaluation_cycles",
    "employee_submissions",
    "uploaded_files",
    "evidence_items",
    "ai_evaluations",
    "dimension_scores",
    "certifications",
    "salary_recommendations",
    "approval_records",
    "import_jobs",
    "audit_logs",
}


def make_temp_database_url() -> str:
    temp_root = Path(".tmp").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f"schema-{uuid4().hex}.db").as_posix()
    return f"sqlite+pysqlite:///{database_path}"


def test_model_schema_creates_expected_tables() -> None:
    load_model_modules()
    settings = Settings(database_url=make_temp_database_url())
    engine = create_db_engine(settings)

    init_database(engine)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(table_names)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def temp_db_url() -> str:
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    url = f'sqlite:///{path}'
    yield url
    Path(path).unlink(missing_ok=True)


@pytest.fixture()
def alembic_cfg(temp_db_url: str) -> Config:
    repo_root = Path(__file__).resolve().parents[3]
    cfg = Config(str(repo_root / 'alembic.ini'))
    cfg.set_main_option('sqlalchemy.url', temp_db_url)
    os.environ['DATABASE_URL'] = temp_db_url
    get_settings.cache_clear()
    yield cfg
    os.environ.pop('DATABASE_URL', None)
    get_settings.cache_clear()


def test_performance_record_comment_defaults_to_none(
    db_session, employee_factory,
) -> None:
    employee = employee_factory(employee_no='CMT0001')
    record = PerformanceRecord(
        employee_id=employee.id,
        employee_no=employee.employee_no,
        year=2025,
        grade='A',
        source='manual',
        department_snapshot=employee.department,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    assert record.comment is None


def test_performance_record_comment_persists_long_text(
    db_session, employee_factory,
) -> None:
    employee = employee_factory(employee_no='CMT0002')
    comment = '优秀执行力，Q4 超额完成 120%。' * 20
    record = PerformanceRecord(
        employee_id=employee.id,
        employee_no=employee.employee_no,
        year=2025,
        grade='B',
        source='manual',
        department_snapshot=employee.department,
        comment=comment,
    )
    db_session.add(record)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(PerformanceRecord, record.id)
    assert loaded is not None
    assert loaded.comment == comment


def test_performance_record_comment_column_exists_after_upgrade(
    alembic_cfg: Config, temp_db_url: str,
) -> None:
    command.upgrade(alembic_cfg, '36_01_add_comment_perf')
    engine = sa.create_engine(temp_db_url)
    inspector = sa.inspect(engine)
    columns = {
        column['name']: column
        for column in inspector.get_columns('performance_records')
    }

    assert 'comment' in columns
    comment_column = columns['comment']
    assert comment_column['nullable'] is True
    assert isinstance(comment_column['type'], sa.Text | sa.String)


def test_performance_record_comment_column_removed_after_downgrade(
    alembic_cfg: Config, temp_db_url: str,
) -> None:
    command.upgrade(alembic_cfg, '36_01_add_comment_perf')
    command.downgrade(alembic_cfg, 'p34_02_tier_snapshot')

    engine = sa.create_engine(temp_db_url)
    inspector = sa.inspect(engine)
    columns = {column['name'] for column in inspector.get_columns('performance_records')}
    assert 'comment' not in columns
