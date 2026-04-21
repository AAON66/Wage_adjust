"""add_leading_zero_fallback_count_to_feishu_sync_logs

Revision ID: 30_01_leading_zero_fallback
Revises: a26_01_feishu_open_id
Create Date: 2026-04-21

Adds leading_zero_fallback_count to feishu_sync_logs to track how many records
were matched via the lstrip('0') tolerant fallback in _build_employee_map.
Phase 30 / EMPNO-04 / D-03 / D-04 / D-05.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30_01_leading_zero_fallback'
down_revision: Union[str, None] = 'a26_01_feishu_open_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.add_column(
            sa.Column(
                'leading_zero_fallback_count',
                sa.Integer(),
                nullable=False,
                server_default='0',
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('feishu_sync_logs') as batch_op:
        batch_op.drop_column('leading_zero_fallback_count')
