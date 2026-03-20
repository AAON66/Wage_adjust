from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import Integer, String, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.app.core.config import Settings
from backend.app.core.database import Base, create_db_engine, create_session_factory, init_database
from backend.app.dependencies import get_db


class WidgetRecord(Base):
    __tablename__ = "test_widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


def make_temp_database_url(file_name: str) -> str:
    temp_root = Path(".tmp").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    database_path = (temp_root / f"{uuid4().hex}-{file_name}").as_posix()
    return f"sqlite+pysqlite:///{database_path}"


def test_create_db_engine_for_sqlite() -> None:
    settings = Settings(database_url=make_temp_database_url("app.db"))

    engine = create_db_engine(settings)

    assert engine.url.render_as_string(hide_password=False).startswith("sqlite+pysqlite:///")


def test_init_database_creates_registered_tables() -> None:
    settings = Settings(database_url=make_temp_database_url("tables.db"))
    engine = create_db_engine(settings)

    init_database(engine)

    inspector = inspect(engine)
    assert "test_widgets" in inspector.get_table_names()
    Base.metadata.drop_all(bind=engine)


def test_get_db_yields_session_and_closes_it() -> None:
    settings = Settings(database_url=make_temp_database_url("dependency.db"))
    session_factory = create_session_factory(settings)
    tracked_session = session_factory()
    closed = {"value": False}

    def fake_get_db_session():
        try:
            yield tracked_session
        finally:
            closed["value"] = True
            tracked_session.close()

    with patch("backend.app.dependencies.get_db_session", fake_get_db_session):
        dependency = get_db()
        session = next(dependency)
        assert isinstance(session, Session)

        try:
            next(dependency)
        except StopIteration:
            pass

    assert closed["value"] is True
