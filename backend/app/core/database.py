from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import MetaData, create_engine, inspect
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
    ensure_schema_compatibility(target_engine)


def ensure_schema_compatibility(target_engine: Engine) -> None:
    inspector = inspect(target_engine)
    table_names = set(inspector.get_table_names())
    with target_engine.begin() as connection:
        if 'dimension_scores' in table_names:
            dimension_score_columns = {column['name'] for column in inspector.get_columns('dimension_scores')}
            missing_dimension_score_columns: list[tuple[str, str]] = []
            if 'ai_raw_score' not in dimension_score_columns:
                missing_dimension_score_columns.append(('ai_raw_score', 'FLOAT NOT NULL DEFAULT 0'))
            if 'ai_weighted_score' not in dimension_score_columns:
                missing_dimension_score_columns.append(('ai_weighted_score', 'FLOAT NOT NULL DEFAULT 0'))
            if 'ai_rationale' not in dimension_score_columns:
                missing_dimension_score_columns.append(('ai_rationale', "TEXT NOT NULL DEFAULT ''"))
            for column_name, column_type in missing_dimension_score_columns:
                connection.exec_driver_sql(f'ALTER TABLE dimension_scores ADD COLUMN {column_name} {column_type}')

        if 'employees' in table_names:
            employee_columns = {column['name'] for column in inspector.get_columns('employees')}
            if 'sub_department' not in employee_columns:
                connection.exec_driver_sql('ALTER TABLE employees ADD COLUMN sub_department VARCHAR(128)')
            if 'id_card_no' not in employee_columns:
                connection.exec_driver_sql('ALTER TABLE employees ADD COLUMN id_card_no VARCHAR(32)')

        if 'users' in table_names:
            user_columns = {column['name'] for column in inspector.get_columns('users')}
            if 'id_card_no' not in user_columns:
                connection.exec_driver_sql('ALTER TABLE users ADD COLUMN id_card_no VARCHAR(32)')

        if 'approval_records' in table_names:
            approval_columns = {column['name'] for column in inspector.get_columns('approval_records')}
            if 'step_order' not in approval_columns:
                connection.exec_driver_sql('ALTER TABLE approval_records ADD COLUMN step_order INTEGER NOT NULL DEFAULT 1')

        if 'salary_recommendations' in table_names:
            salary_recommendation_columns = {column['name'] for column in inspector.get_columns('salary_recommendations')}
            if 'explanation' not in salary_recommendation_columns:
                connection.exec_driver_sql('ALTER TABLE salary_recommendations ADD COLUMN explanation TEXT')
            if 'defer_until' not in salary_recommendation_columns:
                connection.exec_driver_sql('ALTER TABLE salary_recommendations ADD COLUMN defer_until DATETIME')
            if 'defer_target_score' not in salary_recommendation_columns:
                connection.exec_driver_sql('ALTER TABLE salary_recommendations ADD COLUMN defer_target_score FLOAT')
            if 'defer_reason' not in salary_recommendation_columns:
                connection.exec_driver_sql('ALTER TABLE salary_recommendations ADD COLUMN defer_reason TEXT')
