from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import Settings, get_settings

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""

    metadata = MetaData(naming_convention=naming_convention)


def _engine_kwargs(settings: Settings) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "echo": settings.database_echo,
        "future": True,
    }

    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["max_overflow"] = settings.database_max_overflow

    return kwargs


def create_db_engine(settings: Settings | None = None) -> Engine:
    """Build a SQLAlchemy engine from application settings."""
    resolved_settings = settings or get_settings()
    return create_engine(resolved_settings.database_url, **_engine_kwargs(resolved_settings))


def create_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Create a configured session factory for the current environment."""
    engine = create_db_engine(settings)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


engine: Engine = create_db_engine()
SessionLocal: sessionmaker[Session] = create_session_factory()


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session and guarantee cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database(engine_instance: Engine | None = None) -> None:
    """Create all registered tables for the configured engine."""
    target_engine = engine_instance or engine
    Base.metadata.create_all(bind=target_engine)
