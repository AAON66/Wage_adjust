from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


@pytest.fixture()
def temp_db_url():
    """Create an isolated SQLite database file for this migration test."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    url = f'sqlite:///{path}'
    yield url
    Path(path).unlink(missing_ok=True)


@pytest.fixture()
def alembic_cfg(temp_db_url):
    """Alembic Config pointing at the project alembic.ini but using a temp SQLite URL."""
    # Locate the project alembic.ini at repo root
    repo_root = Path(__file__).resolve().parents[3]
    ini_path = repo_root / 'alembic.ini'
    cfg = Config(str(ini_path))
    # Override the URL so migrations run against our temp DB instead of the dev DB
    cfg.set_main_option('sqlalchemy.url', temp_db_url)
    # Also override via env var so env.py's get_settings() path doesn't override us
    os.environ['DATABASE_URL'] = temp_db_url
    # Clear get_settings() cache so the new env var takes effect
    from backend.app.core.config import get_settings
    get_settings.cache_clear()
    yield cfg
    # Cleanup env var + cache
    os.environ.pop('DATABASE_URL', None)
    get_settings.cache_clear()


def test_upgrade_to_31_01_creates_sync_type_and_mapping_failed_count_columns(
    alembic_cfg, temp_db_url,
) -> None:
    """D-01 / D-02: After upgrade to 31_01, feishu_sync_logs has both new columns."""
    command.upgrade(alembic_cfg, '31_01_sync_log_observability')
    engine = sa.create_engine(temp_db_url)
    inspector = sa.inspect(engine)
    cols = {c['name'] for c in inspector.get_columns('feishu_sync_logs')}
    assert 'sync_type' in cols
    assert 'mapping_failed_count' in cols


def test_upgrade_backfills_existing_rows_to_attendance(
    alembic_cfg, temp_db_url,
) -> None:
    """D-03: Upgrade to 30_01 first, insert a legacy row (no sync_type), then upgrade to 31_01.

    Expect sync_type='attendance' after backfill, mapping_failed_count=0 via server_default.
    """
    command.upgrade(alembic_cfg, '30_01_leading_zero_fallback')
    engine = sa.create_engine(temp_db_url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO feishu_sync_logs
                (id, mode, status, total_fetched, synced_count, updated_count, skipped_count,
                 unmatched_count, failed_count, leading_zero_fallback_count, started_at, created_at)
                VALUES (:id, 'full', 'success', 0, 0, 0, 0, 0, 0, 0, :started_at, :started_at)
                """
            ),
            {'id': 'legacy-row', 'started_at': datetime.now(timezone.utc).isoformat()},
        )
    command.upgrade(alembic_cfg, '31_01_sync_log_observability')
    engine = sa.create_engine(temp_db_url)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT sync_type, mapping_failed_count FROM feishu_sync_logs WHERE id = 'legacy-row'"
            )
        ).fetchone()
    assert row is not None
    assert row[0] == 'attendance'  # D-03 backfill
    assert row[1] == 0             # server_default='0'


def test_upgrade_enforces_sync_type_not_null(alembic_cfg, temp_db_url) -> None:
    """D-01: After upgrade 31_01, inserting a row without sync_type raises IntegrityError."""
    command.upgrade(alembic_cfg, '31_01_sync_log_observability')
    engine = sa.create_engine(temp_db_url)
    with engine.begin() as conn:
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(
                sa.text(
                    """
                    INSERT INTO feishu_sync_logs
                    (id, mode, status, total_fetched, synced_count, updated_count, skipped_count,
                     unmatched_count, failed_count, mapping_failed_count, leading_zero_fallback_count,
                     started_at, created_at)
                    VALUES (:id, 'full', 'success', 0, 0, 0, 0, 0, 0, 0, 0, :started_at, :started_at)
                    """
                ),
                {
                    'id': 'missing-sync-type',
                    'started_at': datetime.now(timezone.utc).isoformat(),
                },
            )


def test_downgrade_from_31_01_drops_both_columns(alembic_cfg, temp_db_url) -> None:
    """D-01/D-02: Downgrade from 31_01 back to 30_01 removes sync_type + mapping_failed_count."""
    command.upgrade(alembic_cfg, '31_01_sync_log_observability')
    command.downgrade(alembic_cfg, '30_01_leading_zero_fallback')
    engine = sa.create_engine(temp_db_url)
    inspector = sa.inspect(engine)
    cols = {c['name'] for c in inspector.get_columns('feishu_sync_logs')}
    assert 'sync_type' not in cols
    assert 'mapping_failed_count' not in cols
