from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect

from backend.app.core.config import Settings
from backend.app.core.database import create_db_engine, init_database
from backend.app.models import Base, load_model_modules


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
