"""add_sync_type_and_mapping_failed_count_to_feishu_sync_logs

Revision ID: 31_01_sync_log_observability
Revises: 30_01_leading_zero_fallback
Create Date: 2026-04-21

Phase 31 / IMPORT-03 / IMPORT-04 / D-01 / D-02 / D-03.
Two-phase migration for sync_type NOT NULL (SQLite-safe per PITFALLS.md Pitfall 16 / 31-RESEARCH Pitfall B):
  1. batch add_column sync_type (nullable=True) + mapping_failed_count (NOT NULL, server_default='0')
  2. UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL
  3. batch alter_column sync_type to nullable=False

Rationale: existing rows before Phase 31 were all produced by sync_attendance (only sync type writing
FeishuSyncLog). D-03 locks explicit UPDATE (auditable) over server_default='attendance' (magic).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31_01_sync_log_observability'
down_revision: Union[str, None] = '30_01_leading_zero_fallback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Stage 1: add both columns — sync_type initially nullable, mapping_failed_count NOT NULL with default
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.add_column(
            sa.Column('sync_type', sa.String(length=32), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'mapping_failed_count',
                sa.Integer(),
                nullable=False,
                server_default='0',
            )
        )

    # Stage 2: backfill existing rows (all are historically sync_attendance records)
    op.execute("UPDATE feishu_sync_logs SET sync_type='attendance' WHERE sync_type IS NULL")

    # Stage 3: enforce NOT NULL on sync_type
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.alter_column(
            'sync_type',
            existing_type=sa.String(length=32),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.drop_column('mapping_failed_count')
        batch_op.drop_column('sync_type')
